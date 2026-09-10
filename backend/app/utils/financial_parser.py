import re
from typing import Optional, List, Any

def parse_financial_number(val_str: Any) -> Optional[float]:
    """
    Parses complex financial number strings into floats:
    - Standard: '13,125.00' -> 13125.0
    - Negative with parentheses: '(16,909)' -> -16909.0
    - Negative with minus: '-5.59' -> -5.59
    - Dash/nil: '-' -> 0.0
    - European decimal comma: '126,27' -> 126.27
    - OCR error where dot is used as thousands separator: '6.431,342,479' -> 6431342479.0
    """
    if val_str is None:
        return None
    if isinstance(val_str, (int, float)):
        return float(val_str)
    
    s = str(val_str).strip()
    if not s or s in ["-", "--", "—", "N/A", "n/a", "nil", "Nil"]:
        return 0.0

    is_neg = False
    if s.startswith("(") and s.endswith(")"):
        is_neg = True
        s = s[1:-1].strip()
    elif s.startswith("-"):
        is_neg = True
        s = s[1:].strip()

    # Clean currency symbols
    s = re.sub(r'[$€£₹¥]|RM|USD|INR|EUR', '', s).strip()

    # If dot used as thousands separator with comma e.g. 6.431,342,479 or 1.806,228
    if re.search(r'\d+\.\d{3},\d+', s):
        s = s.replace(".", "")
    elif re.search(r'^\d+\.\d{3},\d{3}$', s):
        s = s.replace(".", "").replace(",", "")

    # If single comma followed by 2 digits at the end and no dot: e.g. 126,27 -> 126.27
    if re.search(r'^\d+,\d{2}$', s):
        s = s.replace(",", ".")
    else:
        # Standard english: remove commas
        s = s.replace(",", "")

    s = s.replace(" ", "")
    try:
        val = float(s)
        return -val if is_neg else val
    except Exception:
        return None

def detect_currency(text: str) -> str:
    """
    Detects currency symbol or code from document text.
    """
    if not text:
        return "USD"
    if "₹" in text or "INR" in text or "Rupees" in text:
        return "INR"
    if "RM" in text or "Ringgit" in text:
        return "RM"
    if "€" in text or "EUR" in text:
        return "EUR"
    if "£" in text or "GBP" in text:
        return "GBP"
    if "$" in text or "USD" in text:
        return "USD"
    return "USD"
