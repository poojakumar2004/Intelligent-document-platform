import os
import io
import time
from typing import List, Dict, Any, Tuple
import pymupdf
from PIL import Image
import requests
from backend.app.core.config import settings
from backend.app.core.logging import logger

class OCRService:
    @staticmethod
    def extract_document_pages(file_path: str, original_filename: str) -> Tuple[List[str], List[str], str]:
        """
        Processes a PDF or image file.
        Returns:
            (page_texts, page_image_paths, engine_used)
        """
        ext = original_filename.lower().split(".")[-1] if "." in original_filename else ""
        page_texts: List[str] = []
        page_image_paths: List[str] = []
        engine_used = "PyMuPDF-Text"

        temp_dir = os.path.join(settings.UPLOAD_DIR, "renders")
        os.makedirs(temp_dir, exist_ok=True)

        if ext == "pdf":
            doc = pymupdf.open(file_path)
            has_native_text = False

            # Check if native text exists in PDF
            raw_texts = []
            for i, page in enumerate(doc):
                t = page.get_text()
                raw_texts.append(t.strip())
                if len(t.strip()) > 50:
                    has_native_text = True

            if has_native_text:
                page_texts = raw_texts
                engine_used = "PyMuPDF-Native"
                # Still render images for preview
                for i, page in enumerate(doc):
                    pix = page.get_pixmap(dpi=150)
                    img_path = os.path.join(temp_dir, f"{os.path.basename(file_path)}_p{i+1}.png")
                    pix.save(img_path)
                    page_image_paths.append(img_path)
            else:
                # Scanned PDF: Render pages to images, then OCR
                logger.info(f"PDF {original_filename} has no embedded text; rendering pages to OCR.")
                for i, page in enumerate(doc):
                    pix = page.get_pixmap(dpi=150)
                    img_path = os.path.join(temp_dir, f"{os.path.basename(file_path)}_p{i+1}.png")
                    pix.save(img_path)
                    page_image_paths.append(img_path)

                    page_text, engine = OCRService._ocr_image_file(img_path)
                    page_texts.append(page_text)
                    engine_used = engine
            doc.close()

        else: # JPG / PNG image
            page_image_paths.append(file_path)
            page_text, engine = OCRService._ocr_image_file(file_path)
            page_texts.append(page_text)
            engine_used = engine

        logger.info(f"OCR extracted {len(page_texts)} pages using engine '{engine_used}'.")
        return page_texts, page_image_paths, engine_used

    @staticmethod
    def _ocr_image_file(image_path: str) -> Tuple[str, str]:
        """
        Runs OCR on an image file using OCR.space or fallback.
        """
        # Try OCR.space API
        ocr_key = settings.OCR_SPACE_API_KEY or "helloworld"
        try:
            url = "https://api.ocr.space/parse/image"
            with open(image_path, "rb") as f:
                resp = requests.post(
                    url,
                    files={"file": (os.path.basename(image_path), f, "image/jpeg")},
                    data={
                        "apikey": ocr_key,
                        "language": "eng",
                        "isTable": True,
                        "scale": True,
                        "detectOrientation": True
                    },
                    timeout=25
                )
            if resp.status_code == 200:
                data = resp.json()
                parsed_results = data.get("ParsedResults", [])
                if parsed_results and len(parsed_results) > 0:
                    text = parsed_results[0].get("ParsedText", "").strip()
                    if text:
                        logger.info(f"OCR.Space successfully parsed {image_path} (length: {len(text)})")
                        return text, "OCR.Space-API"
        except Exception as e:
            logger.warning(f"OCR.space request failed or timed out: {str(e)}")

        return "", "None"
