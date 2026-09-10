from typing import Optional, Dict, Any, List
from pydantic import BaseModel

class ExtractedField(BaseModel):
    value: Any
    confidence: Optional[float] = 0.95
    page_number: Optional[int] = 1
    source_text: Optional[str] = None

class LineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None
    vat_rate: Optional[str] = None

class ValidationCheck(BaseModel):
    name: str
    period: Optional[str] = None
    formula: str
    operands: Dict[str, Optional[float]]
    calculated_value: Optional[float] = None
    reported_value: Optional[float] = None
    variance: Optional[float] = 0.0
    status: str # PASS, FAIL, NOT_APPLICABLE
    message: Optional[str] = None

class ValidationSummary(BaseModel):
    checks: List[ValidationCheck]
    overall_status: str
    issues: List[str] = []
