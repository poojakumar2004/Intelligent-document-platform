import math
from typing import Dict, Any, List, Optional
from backend.app.core.config import settings
from backend.app.core.logging import logger

class FinancialValidationService:
    @staticmethod
    def validate_document(doc_type: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Routes validation based on document_type.
        Returns dictionary with 'checks', 'overall_status', and 'issues'.
        """
        doc_type_lower = doc_type.lower().replace(" ", "_").replace("-", "_")
        if doc_type_lower == "invoice":
            return FinancialValidationService.validate_invoice(extracted_data)
        elif doc_type_lower == "balance_sheet":
            return FinancialValidationService.validate_balance_sheet(extracted_data)
        elif doc_type_lower in ["profit_and_loss", "profit_loss", "p&l"]:
            return FinancialValidationService.validate_profit_and_loss(extracted_data)
        elif doc_type_lower in ["cash_flow_statement", "cash_flows", "cash_flow"]:
            return FinancialValidationService.validate_cash_flow(extracted_data)
        else:
            return {
                "checks": [],
                "overall_status": "PASS",
                "issues": [f"Unknown document type '{doc_type}'; skipped financial rules."]
            }

    @staticmethod
    def _create_check(
        name: str,
        formula: str,
        operands: Dict[str, Optional[float]],
        calculated_value: Optional[float],
        reported_value: Optional[float],
        tolerance: float = settings.FINANCIAL_TOLERANCE,
        period: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Standardizes individual check output.
        If any operand is None or reported_value is None, marks NOT_APPLICABLE.
        """
        if None in operands.values() or reported_value is None or calculated_value is None:
            return {
                "name": name,
                "period": period,
                "formula": formula,
                "operands": operands,
                "calculated_value": calculated_value,
                "reported_value": reported_value,
                "variance": None,
                "status": "NOT_APPLICABLE",
                "message": "Required field not present in source document."
            }

        variance = round(abs(calculated_value - reported_value), 2)
        is_pass = variance <= tolerance

        return {
            "name": name,
            "period": period,
            "formula": formula,
            "operands": operands,
            "calculated_value": round(calculated_value, 2),
            "reported_value": round(reported_value, 2),
            "variance": variance,
            "status": "PASS" if is_pass else "FAIL",
            "message": "Calculation matches reported value." if is_pass else f"Variance of {variance} exceeds tolerance of {tolerance}."
        }

    # ==================== 1. INVOICE VALIDATION ====================
    @staticmethod
    def validate_invoice(data: Dict[str, Any]) -> Dict[str, Any]:
        checks: List[Dict[str, Any]] = []
        issues: List[str] = []

        subtotal = data.get("subtotal", {}).get("value") if isinstance(data.get("subtotal"), dict) else data.get("subtotal")
        tax_amount = data.get("tax_amount", {}).get("value") if isinstance(data.get("tax_amount"), dict) else data.get("tax_amount")
        discount = data.get("discount", {}).get("value") if isinstance(data.get("discount"), dict) else data.get("discount")
        total_amount = data.get("total_amount", {}).get("value") if isinstance(data.get("total_amount"), dict) else data.get("total_amount")
        cash_paid = data.get("cash_paid", {}).get("value") if isinstance(data.get("cash_paid"), dict) else data.get("cash_paid")
        change = data.get("change", {}).get("value") if isinstance(data.get("change"), dict) else data.get("change")
        line_items = data.get("line_items", [])

        # Check 1 & 2: Line items
        if line_items and isinstance(line_items, list) and len(line_items) > 0:
            line_sum = 0.0
            for idx, item in enumerate(line_items):
                qty = item.get("quantity")
                unit_price = item.get("unit_price")
                amount = item.get("amount")
                calc_amt = (qty * unit_price) if (qty is not None and unit_price is not None) else None
                checks.append(FinancialValidationService._create_check(
                    name=f"line_item_{idx+1}_check",
                    formula="quantity * unit_price",
                    operands={"quantity": qty, "unit_price": unit_price},
                    calculated_value=calc_amt,
                    reported_value=amount
                ))
                if amount is not None:
                    line_sum += amount

            reported_ref = subtotal if subtotal is not None else total_amount
            checks.append(FinancialValidationService._create_check(
                name="line_items_sum_check",
                formula="sum(line_item_amounts)",
                operands={"sum_of_lines": line_sum},
                calculated_value=line_sum,
                reported_value=reported_ref
            ))

        # Check 3: Taxable Amount + Tax - Discount ≈ Total
        tax_val = tax_amount if tax_amount is not None else 0.0
        disc_val = discount if discount is not None else 0.0
        calc_total = (subtotal + tax_val - disc_val) if subtotal is not None else None
        checks.append(FinancialValidationService._create_check(
            name="invoice_total_check",
            formula="subtotal + tax_amount - discount",
            operands={"subtotal": subtotal, "tax_amount": tax_amount, "discount": discount},
            calculated_value=calc_total,
            reported_value=total_amount
        ))

        # Check 4: Cash Paid - Total Amount ≈ Change (if cash or change mentioned)
        if cash_paid is not None or change is not None:
            calc_change = (cash_paid - total_amount) if (cash_paid is not None and total_amount is not None) else None
            checks.append(FinancialValidationService._create_check(
                name="cash_change_check",
                formula="cash_paid - total_amount",
                operands={"cash_paid": cash_paid, "total_amount": total_amount},
                calculated_value=calc_change,
                reported_value=change
            ))

        overall_status = "PASS"
        for c in checks:
            if c["status"] == "FAIL":
                overall_status = "FAIL"
                issues.append(f"{c['name']} FAILED: calculated {c['calculated_value']}, reported {c['reported_value']}, variance {c['variance']}")

        return {
            "checks": checks,
            "overall_status": overall_status,
            "issues": issues
        }

    # ==================== 2. BALANCE SHEET VALIDATION ====================
    @staticmethod
    def validate_balance_sheet(data: Dict[str, Any]) -> Dict[str, Any]:
        checks: List[Dict[str, Any]] = []
        issues: List[str] = []

        periods = data.get("periods", ["current", "previous"])
        per_period_data = data.get("period_data", {})

        for period in periods:
            p_data = per_period_data.get(period, {})
            total_liabilities = p_data.get("total_capital_and_liabilities")
            total_assets = p_data.get("total_assets")

            # Check 1: Total Capital & Liabilities ≈ Total Assets
            checks.append(FinancialValidationService._create_check(
                name="balance_sheet_equity_assets_reconciliation",
                period=period,
                formula="total_capital_and_liabilities ≈ total_assets",
                operands={"total_capital_and_liabilities": total_liabilities},
                calculated_value=total_liabilities,
                reported_value=total_assets
            ))

            # Check 2: Sum of liabilities components ≈ Total Liabilities
            liab_items = [
                p_data.get("capital"),
                p_data.get("reserves_and_surplus"),
                p_data.get("minority_interest"),
                p_data.get("deposits"),
                p_data.get("borrowings"),
                p_data.get("other_liabilities_and_provisions")
            ]
            valid_liab = [x for x in liab_items if x is not None]
            calc_sum_liab = sum(valid_liab) if len(valid_liab) >= 2 else None
            checks.append(FinancialValidationService._create_check(
                name="liabilities_components_sum_check",
                period=period,
                formula="capital + reserves + minority_interest + deposits + borrowings + other_liab",
                operands={
                    "capital": p_data.get("capital"),
                    "reserves": p_data.get("reserves_and_surplus"),
                    "deposits": p_data.get("deposits"),
                    "borrowings": p_data.get("borrowings")
                },
                calculated_value=calc_sum_liab,
                reported_value=total_liabilities
            ))

            # Check 3: Sum of assets components ≈ Total Assets
            asset_items = [
                p_data.get("cash_and_rbi_balances"),
                p_data.get("balances_with_banks_money_at_call"),
                p_data.get("investments"),
                p_data.get("advances"),
                p_data.get("fixed_assets"),
                p_data.get("other_assets")
            ]
            valid_assets = [x for x in asset_items if x is not None]
            calc_sum_assets = sum(valid_assets) if len(valid_assets) >= 2 else None
            checks.append(FinancialValidationService._create_check(
                name="assets_components_sum_check",
                period=period,
                formula="cash + bank_balances + investments + advances + fixed_assets + other_assets",
                operands={
                    "investments": p_data.get("investments"),
                    "advances": p_data.get("advances"),
                    "fixed_assets": p_data.get("fixed_assets"),
                    "other_assets": p_data.get("other_assets")
                },
                calculated_value=calc_sum_assets,
                reported_value=total_assets
            ))

        overall_status = "PASS"
        for c in checks:
            if c["status"] == "FAIL":
                overall_status = "FAIL"
                issues.append(f"{c['name']} [{c.get('period')}] FAILED: calc {c['calculated_value']}, rep {c['reported_value']}")

        return {
            "checks": checks,
            "overall_status": overall_status,
            "issues": issues
        }

    # ==================== 3. PROFIT & LOSS VALIDATION ====================
    @staticmethod
    def validate_profit_and_loss(data: Dict[str, Any]) -> Dict[str, Any]:
        checks: List[Dict[str, Any]] = []
        issues: List[str] = []

        periods = data.get("periods", ["current", "previous"])
        per_period_data = data.get("period_data", {})

        for period in periods:
            p_data = per_period_data.get(period, {})
            interest_earned = p_data.get("interest_earned")
            other_income = p_data.get("other_income")
            total_income = p_data.get("total_income")

            interest_expended = p_data.get("interest_expended")
            operating_expenses = p_data.get("operating_expenses")
            provisions = p_data.get("provisions_and_contingencies")
            total_expenditure = p_data.get("total_expenditure")

            net_profit_before_minority = p_data.get("net_profit_for_the_year")
            minority_interest = p_data.get("minority_interest")
            associates_profit = p_data.get("share_in_associates_profit") or 0.0
            group_profit = p_data.get("consolidated_net_profit_attributable_to_group")

            brought_forward = p_data.get("balance_brought_forward")
            total_appropriations = p_data.get("total_profit_available_for_appropriation")

            # Check 1: Interest Earned + Other Income ≈ Total Income
            calc_income = (interest_earned + other_income) if (interest_earned is not None and other_income is not None) else None
            checks.append(FinancialValidationService._create_check(
                name="total_income_check",
                period=period,
                formula="interest_earned + other_income",
                operands={"interest_earned": interest_earned, "other_income": other_income},
                calculated_value=calc_income,
                reported_value=total_income
            ))

            # Check 2: Interest Expended + Operating Expenses + Provisions ≈ Total Expenditure
            calc_exp = (interest_expended + operating_expenses + provisions) if (interest_expended is not None and operating_expenses is not None and provisions is not None) else None
            checks.append(FinancialValidationService._create_check(
                name="total_expenditure_check",
                period=period,
                formula="interest_expended + operating_expenses + provisions_and_contingencies",
                operands={"interest_expended": interest_expended, "operating_expenses": operating_expenses, "provisions": provisions},
                calculated_value=calc_exp,
                reported_value=total_expenditure
            ))

            # Check 3: Total Income - Total Expenditure ≈ Consolidated Net Profit
            calc_net_profit = (total_income - total_expenditure) if (total_income is not None and total_expenditure is not None) else None
            checks.append(FinancialValidationService._create_check(
                name="net_profit_before_minority_check",
                period=period,
                formula="total_income - total_expenditure",
                operands={"total_income": total_income, "total_expenditure": total_expenditure},
                calculated_value=calc_net_profit,
                reported_value=net_profit_before_minority
            ))

            # Check 4: Profit before Minority - Minority Interest + Associates ≈ Attributable Group Profit
            min_val = minority_interest if minority_interest is not None else 0.0
            calc_group = (net_profit_before_minority - min_val + associates_profit) if net_profit_before_minority is not None else None
            checks.append(FinancialValidationService._create_check(
                name="profit_attributable_to_group_check",
                period=period,
                formula="net_profit_before_minority - minority_interest + associates_profit",
                operands={"net_profit_before_minority": net_profit_before_minority, "minority_interest": minority_interest, "associates_profit": associates_profit},
                calculated_value=calc_group,
                reported_value=group_profit
            ))

            # Check 5: Current Profit + Brought Forward Profit ≈ Total Available for Appropriation
            impact = p_data.get("impact_on_amalgamation") or 0.0
            calc_approp = (group_profit + brought_forward + impact) if (group_profit is not None and brought_forward is not None) else None
            checks.append(FinancialValidationService._create_check(
                name="total_profit_available_for_appropriation_check",
                period=period,
                formula="group_profit + balance_brought_forward + impact_on_amalgamation",
                operands={"group_profit": group_profit, "balance_brought_forward": brought_forward, "impact_on_amalgamation": impact},
                calculated_value=calc_approp,
                reported_value=total_appropriations
            ))

        overall_status = "PASS"
        for c in checks:
            if c["status"] == "FAIL":
                overall_status = "FAIL"
                issues.append(f"{c['name']} [{c.get('period')}] FAILED: calc {c['calculated_value']}, rep {c['reported_value']}")

        return {
            "checks": checks,
            "overall_status": overall_status,
            "issues": issues
        }

    # ==================== 4. CASH FLOW STATEMENT VALIDATION ====================
    @staticmethod
    def validate_cash_flow(data: Dict[str, Any]) -> Dict[str, Any]:
        checks: List[Dict[str, Any]] = []
        issues: List[str] = []

        periods = data.get("periods", ["current", "previous"])
        per_period_data = data.get("period_data", {})

        for period in periods:
            p_data = per_period_data.get(period, {})
            operating_cf = p_data.get("operating_cash_flow")
            investing_cf = p_data.get("investing_cash_flow")
            financing_cf = p_data.get("financing_cash_flow")
            fx_adj = p_data.get("fx_translation_adjustment") or 0.0
            amalgamation_adj = p_data.get("amalgamation_adjustment") or 0.0

            net_increase = p_data.get("net_change_in_cash")
            opening_cash = p_data.get("opening_cash")
            closing_cash = p_data.get("closing_cash")

            # Check 1: Operating + Investing + Financing + FX (+ Amalgamation) ≈ Net Increase in Cash
            calc_net_increase = (operating_cf + investing_cf + financing_cf + fx_adj + amalgamation_adj) if (operating_cf is not None and investing_cf is not None and financing_cf is not None) else None
            checks.append(FinancialValidationService._create_check(
                name="net_change_in_cash_check",
                period=period,
                formula="operating_cf + investing_cf + financing_cf + fx_adjustment + amalgamation",
                operands={
                    "operating_cash_flow": operating_cf,
                    "investing_cash_flow": investing_cf,
                    "financing_cash_flow": financing_cf,
                    "fx_translation_adjustment": fx_adj,
                    "amalgamation_adjustment": amalgamation_adj
                },
                calculated_value=calc_net_increase,
                reported_value=net_increase
            ))

            # Check 2: Opening Cash + Net Increase ≈ Closing Cash
            calc_closing = (opening_cash + net_increase) if (opening_cash is not None and net_increase is not None) else None
            checks.append(FinancialValidationService._create_check(
                name="closing_cash_reconciliation_check",
                period=period,
                formula="opening_cash + net_increase_in_cash",
                operands={"opening_cash": opening_cash, "net_change_in_cash": net_increase},
                calculated_value=calc_closing,
                reported_value=closing_cash
            ))

        overall_status = "PASS"
        for c in checks:
            if c["status"] == "FAIL":
                overall_status = "FAIL"
                issues.append(f"{c['name']} [{c.get('period')}] FAILED: calc {c['calculated_value']}, rep {c['reported_value']}")

        return {
            "checks": checks,
            "overall_status": overall_status,
            "issues": issues
        }
