import os
import shutil
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.repositories.document_repository import DocumentRepository
from backend.app.services.document_service import DocumentService
from backend.app.services.document_validation_service import DocumentValidationError
from backend.app.schemas.document import ProcessedDocumentResponse, DocumentListItem, HealthResponse

router = APIRouter(tags=["documents"])

@router.get("/health", response_model=HealthResponse)
def health_check():
    """
    Health check endpoint for deployed environment monitoring.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.VERSION
    }

@router.post("/documents/process")
async def process_document(
    file: UploadFile = File(..., description="Document file (PDF, JPG, PNG)"),
    document_type: str = Form(..., description="Type of document: invoice | balance_sheet | profit_and_loss | cash_flow_statement")
):
    """
    Upload and process a PDF / JPG / PNG document.
    Performs file validation, OCR, field & table extraction, and financial validation.
    """
    original_filename = file.filename or "uploaded_document"
    logger.info(f"Received upload: {original_filename}, declared type: {document_type}")

    # Save uploaded file temporarily
    temp_path = os.path.join(settings.UPLOAD_DIR, original_filename)
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "FILE_SAVE_ERROR", "message": "Failed to save uploaded file to disk."}}
        )

    try:
        result = DocumentService.process_document(
            file_path=temp_path,
            original_filename=original_filename,
            document_type=document_type
        )
        return JSONResponse(status_code=status.HTTP_200_OK, content=result)
    except DocumentValidationError as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": e.code, "message": e.message}}
        )
    except Exception as e:
        logger.exception(f"Unexpected error processing {original_filename}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": "INTERNAL_PROCESSING_ERROR", "message": f"Processing failure: {str(e)}"}}
        )

@router.get("/documents", response_model=List[DocumentListItem])
def list_documents():
    """
    List all processed documents with metadata for the frontend dashboard.
    """
    docs = DocumentRepository.list_all()
    items = []
    for d in docs:
        items.append({
            "id": d.id or 0,
            "document_name": d.document_name,
            "document_type": d.document_type,
            "processing_status": d.processing_status,
            "overall_confidence": d.overall_confidence,
            "page_count": d.file_validation.get("page_count", 1),
            "created_at": d.created_at
        })
    return items

@router.get("/documents/{document_name}")
def get_document_by_name(document_name: str):
    """
    Retrieve the latest structured JSON result for a given document/file name.
    """
    doc = DocumentRepository.get_by_name(document_name)
    if not doc:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "DOCUMENT_NOT_FOUND", "message": f"No processed record found for '{document_name}'."}}
        )
    return {
        "document_name": doc.document_name,
        "document_type": doc.document_type,
        "processing_status": doc.processing_status,
        "overall_confidence": doc.overall_confidence,
        "file_validation": doc.file_validation,
        "extracted_data": doc.extracted_data,
        "validation": doc.validation,
        "processing_metadata": doc.processing_metadata
    }
