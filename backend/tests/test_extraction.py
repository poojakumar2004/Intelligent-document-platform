import os
import tempfile
import unittest
import pymupdf
from PIL import Image
from backend.app.services.document_validation_service import DocumentValidationService, DocumentValidationError

class TestDocumentValidation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        for f in os.listdir(self.temp_dir):
            try:
                os.remove(os.path.join(self.temp_dir, f))
            except Exception:
                pass
        try:
            os.rmdir(self.temp_dir)
        except Exception:
            pass

    def test_valid_pdf_validation(self):
        # Create a 1-page valid PDF
        pdf_path = os.path.join(self.temp_dir, "test.pdf")
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Test invoice content")
        doc.save(pdf_path)
        doc.close()

        val = DocumentValidationService.validate_file(pdf_path, "test.pdf")
        self.assertEqual(val["status"], "PASS")
        self.assertEqual(val["file_type"], "application/pdf")
        self.assertEqual(val["page_count"], 1)
        self.assertTrue(val["is_supported"])
        self.assertTrue(val["is_readable"])

    def test_valid_image_validation(self):
        img_path = os.path.join(self.temp_dir, "test.jpg")
        img = Image.new("RGB", (100, 100), color="white")
        img.save(img_path)

        val = DocumentValidationService.validate_file(img_path, "test.jpg")
        self.assertEqual(val["status"], "PASS")
        self.assertEqual(val["file_type"], "image/jpeg")
        self.assertEqual(val["page_count"], 1)

    def test_unsupported_extension(self):
        txt_path = os.path.join(self.temp_dir, "notes.txt")
        with open(txt_path, "w") as f:
            f.write("Some text file")

        with self.assertRaises(DocumentValidationError) as ctx:
            DocumentValidationService.validate_file(txt_path, "notes.txt")
        self.assertEqual(ctx.exception.code, "UNSUPPORTED_FILE_TYPE")

    def test_empty_file_rejected(self):
        empty_path = os.path.join(self.temp_dir, "empty.pdf")
        with open(empty_path, "wb") as f:
            pass

        with self.assertRaises(DocumentValidationError) as ctx:
            DocumentValidationService.validate_file(empty_path, "empty.pdf")
        self.assertEqual(ctx.exception.code, "EMPTY_FILE")

    def test_page_limit_exceeded(self):
        # Create a 4-page PDF (> 3 pages)
        pdf_path = os.path.join(self.temp_dir, "multi.pdf")
        doc = pymupdf.open()
        for i in range(4):
            p = doc.new_page()
            p.insert_text((50, 50), f"Page {i+1}")
        doc.save(pdf_path)
        doc.close()

        with self.assertRaises(DocumentValidationError) as ctx:
            DocumentValidationService.validate_file(pdf_path, "multi.pdf")
        self.assertEqual(ctx.exception.code, "PAGE_LIMIT_EXCEEDED")

if __name__ == "__main__":
    unittest.main()
