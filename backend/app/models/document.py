from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

@dataclass
class DocumentModel:
    id: Optional[int]
    document_name: str
    document_type: str
    processing_status: str
    overall_confidence: Optional[float]
    file_validation: Dict[str, Any]
    extracted_data: Dict[str, Any]
    validation: Dict[str, Any]
    processing_metadata: Dict[str, Any]
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
