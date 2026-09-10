import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.document import DocumentModel
from backend.app.repositories.document_repository import DocumentRepository
from backend.app.services.document_validation_service import DocumentValidationService, DocumentValidationError
from backend.app.services.ocr_service import OCRService
from backend.app.services.extraction_service import ExtractionService
from backend.app.services.financial_validation_service import FinancialValidationService

class DocumentService:
    @staticmethod
    def process_document(file_path: str, original_filename: str, document_type: str) -> Dict[str, Any]:
        start_time = time.time()
        now_str = datetime.now(timezone.utc).isoformat()
        logger.info(f"Starting processing for document: {original_filename} (Type: {document_type})")

        # Step 1: Document Validation
        try:
            file_val = DocumentValidationService.validate_file(file_path, original_filename)
        except DocumentValidationError as e:
            # Save failed record if possible
            elapsed_ms = int((time.time() - start_time) * 1000)
            failed_response = {
                "document_name": original_filename,
                "document_type": document_type,
                "processing_status": "FAILED",
                "overall_confidence": 0.0,
                "file_validation": {
                    "file_type": "unknown",
                    "is_supported": False,
                    "is_readable": False,
                    "page_count": 0,
                    "status": "FAILED"
                },
                "extracted_data": {},
                "validation": {
                    "checks": [],
                    "overall_status": "FAIL",
                    "issues": [f"{e.code}: {e.message}"]
                },
                "processing_metadata": {
                    "ocr_used": False,
                    "ocr_engine": "None",
                    "processed_at": now_str,
                    "processing_time_ms": elapsed_ms
                }
            }
            # Re-raise so controller returns proper HTTP status
            raise e

        # Step 2: OCR and Text Extraction
        page_texts, page_images, ocr_engine = OCRService.extract_document_pages(file_path, original_filename)

        # Step 3: Field & Table Extraction
        extracted_data, confidence = ExtractionService.extract(document_type, page_texts, page_images)

        # Step 4: Financial Validation
        validation_result = FinancialValidationService.validate_document(document_type, extracted_data)

        # Step 5: Overall Processing Status
        # PASS if file validation passes and financial validation does not fail catastrophically
        processing_status = "PASS" if file_val.get("status") == "PASS" else "FAILED"
        if validation_result.get("overall_status") == "FAIL":
            # Document processed but has financial variances
            processing_status = "PASS" # As per specs: document was successfully processed and returned with calculation issues

        elapsed_ms = int((time.time() - start_time) * 1000)

        metadata = {
            "ocr_used": True,
            "ocr_engine": ocr_engine,
            "processed_at": now_str,
            "processing_time_ms": elapsed_ms
        }

        # Persist to database
        doc_model = DocumentModel(
            id=None,
            document_name=original_filename,
            document_type=document_type,
            processing_status=processing_status,
            overall_confidence=confidence,
            file_validation=file_val,
            extracted_data=extracted_data,
            validation=validation_result,
            processing_metadata=metadata,
            created_at=now_str,
            updated_at=now_str
        )
        saved_doc = DocumentRepository.save_or_update(doc_model)

        response = {
            "document_name": saved_doc.document_name,
            "document_type": saved_doc.document_type,
            "processing_status": saved_doc.processing_status,
            "overall_confidence": saved_doc.overall_confidence,
            "file_validation": saved_doc.file_validation,
            "extracted_data": saved_doc.extracted_data,
            "validation": saved_doc.validation,
            "processing_metadata": saved_doc.processing_metadata
        }
        logger.info(f"Finished processing {original_filename} in {elapsed_ms}ms with status {processing_status}")
        return response
