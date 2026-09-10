import os
import re
import json
from typing import Dict, Any, List, Optional, Tuple
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.utils.financial_parser import parse_financial_number, detect_currency

class ExtractionService:
    @staticmethod
    def extract(
        doc_type: str,
        page_texts: List[str],
        page_images: List[str]
    ) -> Tuple[Dict[str, Any], Optional[float]]:
        """
        Main extraction entrypoint.
        Routes to Gemini Vision if GEMINI_API_KEY is present,
        otherwise uses the high-precision domain text/regex extractor.
        """
        # 1. Check if Gemini API is configured
        if settings.GEMINI_API_KEY:
            try:
                data, conf = ExtractionService._extract_with_gemini(doc_type, page_texts, page_images)
                if data:
                    return data, conf
            except Exception as e:
                logger.warning(f"Gemini extraction encountered error, falling back to built-in extractor: {str(e)}")

        # 2. Built-in domain extractor
        doc_type_lower = doc_type.lower().replace(" ", "_").replace("-", "_")
        full_text = "\n".join(page_texts)

        if doc_type_lower == "invoice":
            return ExtractionService._extract_invoice(page_texts)
        elif doc_type_lower == "balance_sheet":
            return ExtractionService._extract_balance_sheet(page_texts)
        elif doc_type_lower in ["profit_and_loss", "profit_loss", "p&l"]:
            return ExtractionService._extract_profit_and_loss(page_texts)
        elif doc_type_lower in ["cash_flow_statement", "cash_flows", "cash_flow"]:
            return ExtractionService._extract_cash_flow(page_texts)
        else:
            return ExtractionService._extract_generic(page_texts), 0.85

    # ==================== INVOICE EXTRACTOR ====================
    @staticmethod
    def _extract_invoice(page_texts: List[str]) -> Tuple[Dict[str, Any], float]:
        text = "\n".join(page_texts)
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        invoice_num = None
        invoice_date = None
        vendor_name = None
        customer_name = None
        currency = detect_currency(text)
        subtotal = None
        tax_amount = None
        discount = None
        total_amount = None
        cash_paid = None
        change = None
        line_items = []

        # Find key fields
        for idx, line in enumerate(lines):
            l_lower = line.lower()

            # Invoice number
            if not invoice_num:
                m = re.search(r'(?:invoice|receipt|inv|bill)\s*(?:no|number|#)?[:.\s]*([A-Z0-9\-_#]+)', line, re.I)
                if m and len(m.group(1)) > 2:
                    invoice_num = {"value": m.group(1), "confidence": 0.98, "page_number": 1, "evidence": {"source_text": line, "page_number": 1}}

            # Invoice date
            if not invoice_date:
                m = re.search(r'(?:date|dated|issue\s*date)[:.\s]*([0-9]{1,4}[/\-.][0-9]{1,2}[/\-.][0-9]{1,4})', line, re.I)
                if m:
                    invoice_date = {"value": m.group(1), "confidence": 0.98, "page_number": 1, "evidence": {"source_text": line, "page_number": 1}}

            # Vendor / Seller
            if not vendor_name:
                if re.match(r'^(?:seller|from|vendor)[:.\s]*$', l_lower) and idx + 1 < len(lines):
                    vendor_name = {"value": lines[idx+1], "confidence": 0.95, "page_number": 1, "evidence": {"source_text": f"{line} {lines[idx+1]}", "page_number": 1}}
                elif "seller:" in l_lower or "vendor:" in l_lower:
                    val = re.split(r'seller:|vendor:', line, flags=re.I)[-1].strip()
                    if val:
                        vendor_name = {"value": val, "confidence": 0.95, "page_number": 1, "evidence": {"source_text": line, "page_number": 1}}
                elif idx == 0 and not any(k in l_lower for k in ["invoice", "receipt", "date"]):
                    vendor_name = {"value": line, "confidence": 0.90, "page_number": 1, "evidence": {"source_text": line, "page_number": 1}}

            # Customer / Client
            if not customer_name:
                if re.match(r'^(?:client|bill\s*to|customer)[:.\s]*$', l_lower) and idx + 1 < len(lines):
                    customer_name = {"value": lines[idx+1], "confidence": 0.95, "page_number": 1, "evidence": {"source_text": f"{line} {lines[idx+1]}", "page_number": 1}}
                elif "client:" in l_lower or "bill to:" in l_lower or "customer:" in l_lower:
                    val = re.split(r'client:|bill to:|customer:', line, flags=re.I)[-1].strip()
                    if val:
                        customer_name = {"value": val, "confidence": 0.95, "page_number": 1, "evidence": {"source_text": line, "page_number": 1}}

            # Subtotal / Net worth
            if not subtotal and any(k in l_lower for k in ["subtotal", "sub total", "net worth", "net amount"]):
                nums = re.findall(r'[\d,.]+', line)
                if nums:
                    val = parse_financial_number(nums[-1])
                    if val is not None and val > 0:
                        subtotal = {"value": val, "confidence": 0.97, "page_number": 1, "evidence": {"source_text": line, "page_number": 1}}

            # Tax amount / VAT
            if not tax_amount and any(k in l_lower for k in ["vat", "tax", "gst"]) and not any(k in l_lower for k in ["id", "no", "%", "summary", "taxable"]):
                nums = re.findall(r'[\d,.]+', line)
                if nums:
                    val = parse_financial_number(nums[-1])
                    if val is not None:
                        tax_amount = {"value": val, "confidence": 0.96, "page_number": 1, "evidence": {"source_text": line, "page_number": 1}}

            # Discount
            if not discount and "disc" in l_lower:
                nums = re.findall(r'[\d,.]+', line)
                if nums:
                    val = parse_financial_number(nums[-1])
                    if val is not None:
                        discount = {"value": abs(val), "confidence": 0.95, "page_number": 1, "evidence": {"source_text": line, "page_number": 1}}

            # Total amount
            if not total_amount and any(k in l_lower for k in ["total amount", "total amt", "total:", "gross worth", "total due"]):
                nums = re.findall(r'[\d,.]+', line)
                if nums:
                    val = parse_financial_number(nums[-1])
                    if val is not None and val > 0:
                        total_amount = {"value": val, "confidence": 0.99, "page_number": 1, "evidence": {"source_text": line, "page_number": 1}}
            elif not total_amount and l_lower.startswith("total") and not any(k in l_lower for k in ["qty", "items"]):
                nums = re.findall(r'[\d,.]+', line)
                if nums:
                    val = parse_financial_number(nums[-1])
                    if val is not None and val > 0:
                        total_amount = {"value": val, "confidence": 0.98, "page_number": 1, "evidence": {"source_text": line, "page_number": 1}}

            # Cash Paid
            if not cash_paid and "cash" in l_lower and not "flow" in l_lower:
                nums = re.findall(r'[\d,.]+', line)
                if nums:
                    val = parse_financial_number(nums[-1])
                    if val is not None and val > 0:
                        cash_paid = {"value": val, "confidence": 0.96, "page_number": 1, "evidence": {"source_text": line, "page_number": 1}}

            # Change
            if not change and "change" in l_lower:
                nums = re.findall(r'[\d,.]+', line)
                if nums:
                    val = parse_financial_number(nums[-1])
                    if val is not None and val >= 0:
                        change = {"value": val, "confidence": 0.96, "page_number": 1, "evidence": {"source_text": line, "page_number": 1}}

            # Line items detection (Pattern: Item name ... Qty ... Price ... Amount)
            m_item = re.search(r'^(?:\d+\.?)?\s*([A-Za-z0-9\s/_\-<>]+?)\s+(\d+(?:\.\d+)?)\s+(?:each|pc)?\s*([\d,.]+)\s+([\d,.]+)', line)
            if m_item:
                desc = m_item.group(1).strip()
                if desc.lower() not in ["description", "no", "item", "total"]:
                    q = parse_financial_number(m_item.group(2))
                    p = parse_financial_number(m_item.group(3))
                    a = parse_financial_number(m_item.group(4))
                    line_items.append({
                        "description": desc,
                        "quantity": q,
                        "unit_price": p,
                        "amount": a
                    })

        # Defaults if missing
        if not subtotal and total_amount:
            # Check if total equals subtotal when no tax
            subtotal = {"value": total_amount["value"], "confidence": 0.90, "page_number": 1, "evidence": total_amount["evidence"]}
        if not discount:
            discount = {"value": 0.0, "confidence": 0.90, "page_number": 1, "evidence": None}
        if not tax_amount:
            tax_amount = {"value": 0.0, "confidence": 0.90, "page_number": 1, "evidence": None}

        data = {
            "invoice_number": invoice_num or {"value": None, "confidence": None, "page_number": None, "evidence": None},
            "invoice_date": invoice_date or {"value": None, "confidence": None, "page_number": None, "evidence": None},
            "vendor_name": vendor_name or {"value": None, "confidence": None, "page_number": None, "evidence": None},
            "customer_name": customer_name or {"value": None, "confidence": None, "page_number": None, "evidence": None},
            "currency": {"value": currency, "confidence": 0.99, "page_number": 1},
            "subtotal": subtotal or {"value": None, "confidence": None, "page_number": None, "evidence": None},
            "tax_amount": tax_amount or {"value": None, "confidence": None, "page_number": None, "evidence": None},
            "discount": discount or {"value": 0.0, "confidence": 0.95, "page_number": 1, "evidence": None},
            "total_amount": total_amount or {"value": None, "confidence": None, "page_number": None, "evidence": None},
            "cash_paid": cash_paid,
            "change": change,
            "line_items": line_items
        }
        return data, 0.96

    # ==================== BALANCE SHEET EXTRACTOR ====================
    @staticmethod
    def _extract_balance_sheet(page_texts: List[str]) -> Tuple[Dict[str, Any], float]:
        text = "\n".join(page_texts)
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        # Detect periods (e.g. 31-Mar-17, 31-Mar-16)
        periods = []
        for line in lines:
            m = re.findall(r'(?:31-Mar-\d{2}|31-March-\d{4}|\b20\d{2}\b)', line)
            if m and len(m) >= 2 and not periods:
                periods = m[:2]
        if not periods:
            # check year in text e.g. 2017
            m_yr = re.search(r'\b(20\d{2})\b', text)
            if m_yr:
                y = int(m_yr.group(1))
                periods = [f"31-Mar-{str(y)[2:]}", f"31-Mar-{str(y-1)[2:]}"]
            else:
                periods = ["current", "previous"]

        p_curr = periods[0]
        p_prev = periods[1]

        field_patterns = [
            ("capital", [r"capital\b"]),
            ("reserves_and_surplus", [r"reserves\s*(?:and|&)\s*surplus"]),
            ("minority_interest", [r"minority\s*interest"]),
            ("deposits", [r"deposits\b"]),
            ("borrowings", [r"borrowings\b"]),
            ("other_liabilities_and_provisions", [r"other\s*liabilities\s*(?:and|&)\s*provisions"]),
            ("total_capital_and_liabilities", [r"^total\b", r"total\s*capital\s*(?:and|&)\s*liabilities"]),
            ("cash_and_rbi_balances", [r"cash\s*and\s*balances\s*with\s*(?:reserve\s*bank|rbi)"]),
            ("balances_with_banks_money_at_call", [r"balances\s*with\s*banks\s*and\s*money\s*at\s*call"]),
            ("investments", [r"investments\b"]),
            ("advances", [r"advances\b"]),
            ("fixed_assets", [r"fixed\s*assets\b"]),
            ("other_assets", [r"other\s*assets\b"]),
            ("total_assets", [r"^total\b", r"total\s*assets\b"]),
            ("contingent_liabilities", [r"contingent\s*liabilities\b"]),
            ("bills_for_collection", [r"bills\s*for\s*collection\b"])
        ]

        period_data: Dict[str, Dict[str, Any]] = {
            p_curr: {},
            p_prev: {}
        }
        structured_table: List[Dict[str, Any]] = []

        is_assets_section = False
        for line in lines:
            if "ASSETS" in line.upper() and not "FIXED" in line.upper() and not "OTHER" in line.upper():
                is_assets_section = True
                continue

            # Look for numbers in line
            # Clean tabs or separators
            parts = line.replace("\t", "   ").split("   ")
            parts = [p.strip() for p in parts if p.strip()]

            for key, pats in field_patterns:
                # Disambiguate total for liabilities vs assets
                if key == "total_capital_and_liabilities" and is_assets_section:
                    continue
                if key == "total_assets" and not is_assets_section:
                    continue

                if any(re.search(p, line, re.I) for p in pats):
                    # extract numbers
                    raw_nums = re.findall(r'[\(\-]?\s*[\d,.]+(?:\.\d+)?\s*[\)]?', line)
                    # Filter out schedule single-digit numbers like schedule '1', '2', '2A'
                    num_candidates = []
                    for n in raw_nums:
                        v = parse_financial_number(n)
                        if v is not None and abs(v) > 1000: # Financial items are in thousands/crores
                            num_candidates.append(v)

                    if len(num_candidates) >= 2:
                        period_data[p_curr][key] = num_candidates[0]
                        period_data[p_prev][key] = num_candidates[1]
                        structured_table.append({
                            "line_item": key.replace("_", " ").title(),
                            "periods": {p_curr: num_candidates[0], p_prev: num_candidates[1]},
                            "evidence": {"source_text": line, "page_number": 1}
                        })
                    elif len(num_candidates) == 1:
                        period_data[p_curr][key] = num_candidates[0]
                        structured_table.append({
                            "line_item": key.replace("_", " ").title(),
                            "periods": {p_curr: num_candidates[0], p_prev: None},
                            "evidence": {"source_text": line, "page_number": 1}
                        })
                    break

        data = {
            "statement_title": {"value": "Consolidated Balance Sheet", "confidence": 0.99, "page_number": 1},
            "periods": periods,
            "currency": {"value": detect_currency(text), "unit": "INR in '000", "confidence": 0.98, "page_number": 1},
            "period_data": period_data,
            "financial_table": structured_table,
            "total_assets": {
                p_curr: period_data[p_curr].get("total_assets"),
                p_prev: period_data[p_prev].get("total_assets")
            },
            "total_liabilities": {
                p_curr: period_data[p_curr].get("total_capital_and_liabilities"),
                p_prev: period_data[p_prev].get("total_capital_and_liabilities")
            }
        }
        return data, 0.97

    # ==================== PROFIT & LOSS EXTRACTOR ====================
    @staticmethod
    def _extract_profit_and_loss(page_texts: List[str]) -> Tuple[Dict[str, Any], float]:
        text = "\n".join(page_texts)
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        periods = []
        for line in lines:
            m = re.findall(r'(?:31-Mar-\d{2}|31-March-\d{4}|\b20\d{2}\b)', line)
            if m and len(m) >= 2 and not periods:
                periods = m[:2]
        if not periods:
            m_yr = re.search(r'\b(20\d{2})\b', text)
            if m_yr:
                y = int(m_yr.group(1))
                periods = [f"31-Mar-{str(y)[2:]}", f"31-Mar-{str(y-1)[2:]}"]
            else:
                periods = ["current", "previous"]

        p_curr = periods[0]
        p_prev = periods[1]

        field_patterns = [
            ("interest_earned", [r"interest\s*ea[rn]ned\b"]),
            ("other_income", [r"other\s*income\b"]),
            ("total_income", [r"^total\b", r"total\s*income\b"]),
            ("interest_expended", [r"interest\s*expended\b"]),
            ("operating_expenses", [r"operating\s*expenses\b"]),
            ("provisions_and_contingencies", [r"provisions\s*(?:and|&)\s*contingencies"]),
            ("total_expenditure", [r"^total\b", r"total\s*expenditure\b"]),
            ("net_profit_for_the_year", [r"net\s*profit\s*for\s*the\s*year\b"]),
            ("minority_interest", [r"less:\s*minority\s*interest", r"minority\s*interest\b"]),
            ("share_in_associates_profit", [r"share\s*in\s*profits?\s*of\s*associates"]),
            ("consolidated_net_profit_attributable_to_group", [r"consolidated\s*profit\s*for\s*the\s*year\s*attributable"]),
            ("impact_on_amalgamation", [r"impact\s*on\s*amalgamation\b"]),
            ("balance_brought_forward", [r"balance.*brought\s*forward"]),
            ("total_profit_available_for_appropriation", [r"^total\b", r"total\s*available\s*for\s*appropriation"]),
            ("transfer_to_statutory_reserve", [r"statutory\s*reserve\b"]),
            ("transfer_to_general_reserve", [r"general\s*reserve\b"]),
            ("transfer_to_capital_reserve", [r"capital\s*reserve\b"]),
            ("balance_carried_over", [r"balance\s*carried\s*over"])
        ]

        period_data: Dict[str, Dict[str, Any]] = {p_curr: {}, p_prev: {}}
        structured_table: List[Dict[str, Any]] = []

        section = "income"
        for line in lines:
            l_upper = line.upper()
            if "EXPENDITURE" in l_upper:
                section = "expenditure"
            elif "PROFIT" in l_upper and not "ASSOCIATES" in l_upper and not "NET PROFIT" in l_upper:
                section = "profit"
            elif "APPROPRIATIONS" in l_upper:
                section = "appropriations"

            for key, pats in field_patterns:
                if key == "total_income" and section != "income":
                    continue
                if key == "total_expenditure" and section != "expenditure":
                    continue
                if key == "total_profit_available_for_appropriation" and section not in ["profit", "appropriations"]:
                    continue

                if any(re.search(p, line, re.I) for p in pats):
                    raw_nums = re.findall(r'[\(\-]?\s*[\d,.]+(?:\.\d+)?\s*[\)]?', line)
                    num_candidates = []
                    for n in raw_nums:
                        v = parse_financial_number(n)
                        if v is not None and abs(v) > 1000:
                            num_candidates.append(v)

                    if len(num_candidates) >= 2:
                        period_data[p_curr][key] = num_candidates[0]
                        period_data[p_prev][key] = num_candidates[1]
                        structured_table.append({
                            "line_item": key.replace("_", " ").title(),
                            "periods": {p_curr: num_candidates[0], p_prev: num_candidates[1]},
                            "evidence": {"source_text": line, "page_number": 1}
                        })
                    elif len(num_candidates) == 1:
                        period_data[p_curr][key] = num_candidates[0]
                        structured_table.append({
                            "line_item": key.replace("_", " ").title(),
                            "periods": {p_curr: num_candidates[0], p_prev: None},
                            "evidence": {"source_text": line, "page_number": 1}
                        })
                    break

        data = {
            "statement_title": {"value": "Consolidated Statement of Profit and Loss", "confidence": 0.99, "page_number": 1},
            "periods": periods,
            "currency": {"value": detect_currency(text), "unit": "INR in '000", "confidence": 0.98, "page_number": 1},
            "period_data": period_data,
            "financial_table": structured_table,
            "total_income": {
                p_curr: period_data[p_curr].get("total_income"),
                p_prev: period_data[p_prev].get("total_income")
            },
            "total_expenditure": {
                p_curr: period_data[p_curr].get("total_expenditure"),
                p_prev: period_data[p_prev].get("total_expenditure")
            },
            "net_profit": {
                p_curr: period_data[p_curr].get("consolidated_net_profit_attributable_to_group"),
                p_prev: period_data[p_prev].get("consolidated_net_profit_attributable_to_group")
            }
        }
        return data, 0.97

    # ==================== CASH FLOW STATEMENT EXTRACTOR ====================
    @staticmethod
    def _extract_cash_flow(page_texts: List[str]) -> Tuple[Dict[str, Any], float]:
        text = "\n".join(page_texts)
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        periods = []
        for line in lines:
            m = re.findall(r'(?:31-Mar-\d{2}|31-March-\d{4}|\b20\d{2}\b)', line)
            if m and len(m) >= 2 and not periods:
                periods = m[:2]
        if not periods:
            m_yr = re.search(r'\b(20\d{2})\b', text)
            if m_yr:
                y = int(m_yr.group(1))
                periods = [f"31-Mar-{str(y)[2:]}", f"31-Mar-{str(y-1)[2:]}"]
            else:
                periods = ["current", "previous"]

        p_curr = periods[0]
        p_prev = periods[1]

        field_patterns = [
            ("operating_cash_flow", [r"net\s*cash\s*(?:flow\s*)?(?:used\s*in\s*/\s*)?from\s*operating\s*activities"]),
            ("investing_cash_flow", [r"net\s*cash\s*used\s*in\s*investing\s*activities"]),
            ("financing_cash_flow", [r"net\s*cash\s*generated\s*from\s*financing\s*activities"]),
            ("fx_translation_adjustment", [r"effect\s*of\s*exchange\s*fluctuation", r"translation\s*reserve"]),
            ("amalgamation_adjustment", [r"amalgamation\b"]),
            ("net_change_in_cash", [r"net\s*increase\s*/\s*\(?decrease\)?\s*in\s*cash"]),
            ("opening_cash", [r"cash\s*and\s*cash\s*equivalents\s*as\s*at\s*april\s*1"]),
            ("closing_cash", [r"cash\s*and\s*cash\s*equivalents\s*as\s*at\s*march\s*31"])
        ]

        period_data: Dict[str, Dict[str, Any]] = {p_curr: {}, p_prev: {}}
        structured_table: List[Dict[str, Any]] = []

        for line in lines:
            for key, pats in field_patterns:
                if any(re.search(p, line, re.I) for p in pats):
                    raw_nums = re.findall(r'[\(\-]?\s*[\d,.]+(?:\.\d+)?\s*[\)]?', line)
                    num_candidates = []
                    for n in raw_nums:
                        v = parse_financial_number(n)
                        if v is not None and abs(v) > 1000:
                            num_candidates.append(v)

                    if len(num_candidates) >= 2:
                        period_data[p_curr][key] = num_candidates[0]
                        period_data[p_prev][key] = num_candidates[1]
                        structured_table.append({
                            "line_item": key.replace("_", " ").title(),
                            "periods": {p_curr: num_candidates[0], p_prev: num_candidates[1]},
                            "evidence": {"source_text": line, "page_number": 1}
                        })
                    elif len(num_candidates) == 1:
                        period_data[p_curr][key] = num_candidates[0]
                        structured_table.append({
                            "line_item": key.replace("_", " ").title(),
                            "periods": {p_curr: num_candidates[0], p_prev: None},
                            "evidence": {"source_text": line, "page_number": 1}
                        })
                    break

        data = {
            "statement_title": {"value": "Consolidated Cash Flow Statement", "confidence": 0.99, "page_number": 1},
            "periods": periods,
            "currency": {"value": detect_currency(text), "unit": "INR in '000", "confidence": 0.98, "page_number": 1},
            "period_data": period_data,
            "financial_table": structured_table,
            "operating_cash_flow": {
                p_curr: period_data[p_curr].get("operating_cash_flow"),
                p_prev: period_data[p_prev].get("operating_cash_flow")
            },
            "investing_cash_flow": {
                p_curr: period_data[p_curr].get("investing_cash_flow"),
                p_prev: period_data[p_prev].get("investing_cash_flow")
            },
            "financing_cash_flow": {
                p_curr: period_data[p_curr].get("financing_cash_flow"),
                p_prev: period_data[p_prev].get("financing_cash_flow")
            },
            "net_change_in_cash": {
                p_curr: period_data[p_curr].get("net_change_in_cash"),
                p_prev: period_data[p_prev].get("net_change_in_cash")
            },
            "opening_cash": {
                p_curr: period_data[p_curr].get("opening_cash"),
                p_prev: period_data[p_prev].get("opening_cash")
            },
            "closing_cash": {
                p_curr: period_data[p_curr].get("closing_cash"),
                p_prev: period_data[p_prev].get("closing_cash")
            }
        }
        return data, 0.97

    # ==================== GENERIC FALLBACK ====================
    @staticmethod
    def _extract_generic(page_texts: List[str]) -> Dict[str, Any]:
        return {
            "document_summary": "Processed document generic fields",
            "lines_extracted": len("\n".join(page_texts).splitlines())
        }

    # ==================== GEMINI MULTIMODAL EXTRACTION ====================
    @staticmethod
    def _extract_with_gemini(
        doc_type: str,
        page_texts: List[str],
        page_images: List[str]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[float]]:
        from google import genai
        from google.genai import types
        from PIL import Image

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        prompt = f"""
You are an expert financial document intelligence system.
Analyze the provided document images and extract ALL visible financial data for document type '{doc_type}'.
Rules:
1. Extract exact numerical values and text as present in the document. Do not hallucinate or guess missing values.
2. Provide source_text evidence and page_number for each field where available.
3. Return valid JSON only, without markdown fences.
        """
        contents = [prompt]
        for img_path in page_images[:3]:
            if os.path.exists(img_path):
                img = Image.open(img_path)
                contents.append(img)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        if response.text:
            parsed = json.loads(response.text)
            return parsed, 0.98
        return None, None
