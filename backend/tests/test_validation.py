import unittest
from backend.app.services.financial_validation_service import FinancialValidationService
from backend.app.utils.financial_parser import parse_financial_number

class TestFinancialValidation(unittest.TestCase):
    def test_parse_financial_number(self):
        self.assertEqual(parse_financial_number("13,125.00"), 13125.0)
        self.assertEqual(parse_financial_number("(16,909)"), -16909.0)
        self.assertEqual(parse_financial_number("-5.59"), -5.59)
        self.assertEqual(parse_financial_number("-"), 0.0)
        self.assertEqual(parse_financial_number("126,27"), 126.27)
        self.assertEqual(parse_financial_number("6.431,342,479"), 6431342479.0)
        self.assertEqual(parse_financial_number("RM 70.30"), 70.30)
        self.assertEqual(parse_financial_number("$ 12,500.00"), 12500.0)

    def test_invoice_validation_pass(self):
        invoice_data = {
            "subtotal": {"value": 12500.00},
            "tax_amount": {"value": 625.00},
            "discount": {"value": 0.00},
            "total_amount": {"value": 13125.00},
            "cash_paid": {"value": 14000.00},
            "change": {"value": 875.00},
            "line_items": [
                {"description": "Service A", "quantity": 1.0, "unit_price": 12500.00, "amount": 12500.00}
            ]
        }
        res = FinancialValidationService.validate_invoice(invoice_data)
        self.assertEqual(res["overall_status"], "PASS")
        self.assertEqual(len(res["issues"]), 0)
        # Verify checks
        check_names = [c["name"] for c in res["checks"]]
        self.assertIn("invoice_total_check", check_names)
        self.assertIn("line_item_1_check", check_names)
        self.assertIn("line_items_sum_check", check_names)
        self.assertIn("cash_change_check", check_names)

    def test_invoice_validation_fail_variance(self):
        invoice_data = {
            "subtotal": {"value": 12500.00},
            "tax_amount": {"value": 625.00},
            "discount": {"value": 0.00},
            "total_amount": {"value": 14000.00}, # Incorrect reported total
            "line_items": []
        }
        res = FinancialValidationService.validate_invoice(invoice_data)
        self.assertEqual(res["overall_status"], "FAIL")
        self.assertGreater(len(res["issues"]), 0)

    def test_balance_sheet_validation(self):
        bs_data = {
            "periods": ["31-Mar-17"],
            "period_data": {
                "31-Mar-17": {
                    "capital": 5125091.0,
                    "reserves_and_surplus": 912814397.0,
                    "minority_interest": 2914389.0,
                    "deposits": 6431342479.0,
                    "borrowings": 984156439.0,
                    "other_liabilities_and_provisions": 587088812.0,
                    "total_capital_and_liabilities": 8923441607.0,
                    "cash_and_rbi_balances": 379105485.0,
                    "balances_with_banks_money_at_call": 114005711.0,
                    "investments": 2107771120.0,
                    "advances": 5854809871.0,
                    "fixed_assets": 38146997.0,
                    "other_assets": 429602423.0,
                    "total_assets": 8923441607.0
                }
            }
        }
        res = FinancialValidationService.validate_balance_sheet(bs_data)
        self.assertEqual(res["overall_status"], "PASS")
        self.assertEqual(len(res["issues"]), 0)

    def test_profit_and_loss_validation(self):
        pl_data = {
            "periods": ["31-Mar-17"],
            "period_data": {
                "31-Mar-17": {
                    "interest_earned": 732713529.0,
                    "other_income": 128776329.0,
                    "total_income": 861489858.0,
                    "interest_expended": 380415844.0,
                    "operating_expenses": 207510707.0,
                    "provisions_and_contingencies": 120689285.0,
                    "total_expenditure": 708615836.0,
                    "net_profit_for_the_year": 152874022.0,
                    "minority_interest": 367165.0,
                    "share_in_associates_profit": 23393.0,
                    "consolidated_net_profit_attributable_to_group": 152530250.0,
                    "impact_on_amalgamation": 274507.0,
                    "balance_brought_forward": 248255886.0,
                    "total_profit_available_for_appropriation": 401060643.0
                }
            }
        }
        res = FinancialValidationService.validate_profit_and_loss(pl_data)
        self.assertEqual(res["overall_status"], "PASS")
        self.assertEqual(len(res["issues"]), 0)

    def test_cash_flow_validation(self):
        cf_data = {
            "periods": ["31-Mar-17"],
            "period_data": {
                "31-Mar-17": {
                    "operating_cash_flow": 172815931.0,
                    "investing_cash_flow": -11476802.0,
                    "financing_cash_flow": -58929743.0,
                    "fx_translation_adjustment": -282622.0,
                    "amalgamation_adjustment": 295617.0,
                    "net_change_in_cash": 102422381.0,
                    "opening_cash": 390688815.0,
                    "closing_cash": 493111196.0
                }
            }
        }
        res = FinancialValidationService.validate_cash_flow(cf_data)
        self.assertEqual(res["overall_status"], "PASS")
        self.assertEqual(len(res["issues"]), 0)

    def test_missing_field_returns_not_applicable(self):
        # When operands are missing, validation should NOT fail, it should return NOT_APPLICABLE
        partial_data = {
            "subtotal": {"value": 1000.0},
            "tax_amount": {"value": None},
            "total_amount": {"value": None}
        }
        res = FinancialValidationService.validate_invoice(partial_data)
        check = [c for c in res["checks"] if c["name"] == "invoice_total_check"][0]
        self.assertEqual(check["status"], "NOT_APPLICABLE")

if __name__ == "__main__":
    unittest.main()
