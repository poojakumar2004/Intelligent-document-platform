import os
from typing import Tuple, Dict, Any
from PIL import Image
import pymupdf
from backend.app.core.config import settings
from backend.app.core.logging import logger

class DocumentValidationError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class DocumentValidationService:
    @staticmethod
    def validate_file(file_path: str, original_filename: str) -> Dict[str, Any]:
        """
        Validates file type, non-empty content, corruption, and max page limit (<=3).
        Returns a dict matching the specification:
        {
            "file_type": "application/pdf",
            "is_supported": True,
            "is_readable": True,
            "page_count": 1,
            "status": "PASS"
        }
        """
        if not os.path.exists(file_path):
            raise DocumentValidationError("FILE_NOT_FOUND", "Uploaded file does not exist on server.")

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise DocumentValidationError("EMPTY_FILE", "The uploaded file is empty (0 bytes).")

        # Check extension
        ext = original_filename.lower().split(".")[-1] if "." in original_filename else ""
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise DocumentValidationError(
                "UNSUPPORTED_FILE_TYPE",
                f"Only PDF / JPG / PNG documents are supported. Received file extension: .{ext}"
            )

        # Detect MIME type based on extension
        mime_map = {
            "pdf": "application/pdf",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png"
        }
        detected_mime = mime_map.get(ext, "application/octet-stream")

        page_count = 1
        is_readable = False

        if ext == "pdf":
            try:
                doc = pymupdf.open(file_path)
                page_count = len(doc)
                if page_count == 0:
                    raise DocumentValidationError("CORRUPTED_PDF", "PDF contains 0 pages or is corrupted.")
                
                # Verify readability of pages
                for page_idx in range(page_count):
                    _ = doc[page_idx].rect
                
                is_readable = True
                doc.close()
            except Exception as e:
                logger.error(f"Failed to read PDF {original_filename}: {str(e)}")
                raise DocumentValidationError("CORRUPTED_PDF", f"Cannot read or parse PDF: {str(e)}")

            if page_count > settings.MAX_PAGES:
                raise DocumentValidationError(
                    "PAGE_LIMIT_EXCEEDED",
                    f"Document exceeds the maximum allowed limit of {settings.MAX_PAGES} pages. Uploaded document has {page_count} pages."
                )

        else: # Image (JPG / PNG)
            try:
                with Image.open(file_path) as img:
                    img.verify() # Verify file integrity
                is_readable = True
                page_count = 1
            except Exception as e:
                logger.error(f"Failed to read image {original_filename}: {str(e)}")
                raise DocumentValidationError("CORRUPTED_IMAGE", f"Corrupted or unreadable image file: {str(e)}")

        result = {
            "file_type": detected_mime,
            "is_supported": True,
            "is_readable": is_readable,
            "page_count": page_count,
            "status": "PASS"
        }
        logger.info(f"File validation PASS for {original_filename}: {result}")
        return result
