from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class FileValidationDetail(BaseModel):
    file_type: str
    is_supported: bool
    is_readable: bool
    page_count: int
    status: str

class ProcessingMetadata(BaseModel):
    ocr_used: bool = True
    ocr_engine: Optional[str] = "PyMuPDF+OCR.Space"
    processed_at: str
    processing_time_ms: int

class ProcessedDocumentResponse(BaseModel):
    document_name: str
    document_type: str
    processing_status: str
    overall_confidence: Optional[float] = None
    file_validation: FileValidationDetail
    extracted_data: Dict[str, Any]
    validation: Dict[str, Any]
    processing_metadata: ProcessingMetadata

class DocumentListItem(BaseModel):
    id: int
    document_name: str
    document_type: str
    processing_status: str
    overall_confidence: Optional[float] = None
    page_count: Optional[int] = 1
    created_at: str

class HealthResponse(BaseModel):
    status: str = "healthy"
    timestamp: str
    version: str = "1.0.0"

class ErrorDetail(BaseModel):
    code: str
    message: str

class ErrorResponse(BaseModel):
    error: ErrorDetail
