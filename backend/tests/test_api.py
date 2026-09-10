import io
import unittest
import pymupdf
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import init_db

class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def test_health_endpoint(self):
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("timestamp", data)
        self.assertIn("version", data)

    def test_list_documents(self):
        resp = self.client.get("/api/v1/documents")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)

    def test_get_nonexistent_document(self):
        resp = self.client.get("/api/v1/documents/non_existent_doc_12345.pdf")
        self.assertEqual(resp.status_code, 404)
        data = resp.json()
        self.assertEqual(data["error"]["code"], "DOCUMENT_NOT_FOUND")

    def test_process_unsupported_file(self):
        file_content = b"Some random text content"
        files = {"file": ("bad_file.txt", io.BytesIO(file_content), "text/plain")}
        data = {"document_type": "invoice"}
        resp = self.client.post("/api/v1/documents/process", files=files, data=data)
        self.assertEqual(resp.status_code, 400)
        res_json = resp.json()
        self.assertIn("error", res_json)
        self.assertEqual(res_json["error"]["code"], "UNSUPPORTED_FILE_TYPE")

    def test_process_valid_document_flow(self):
        # Create a small valid PDF in-memory
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Invoice no: INV-TEST-99\nTotal: 1000.00\nSubtotal: 1000.00")
        pdf_bytes = doc.tobytes()
        doc.close()

        files = {"file": ("test_invoice_flow.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        data = {"document_type": "invoice"}
        resp = self.client.post("/api/v1/documents/process", files=files, data=data)
        self.assertEqual(resp.status_code, 200)
        res_json = resp.json()
        self.assertEqual(res_json["document_name"], "test_invoice_flow.pdf")
        self.assertEqual(res_json["document_type"], "invoice")
        self.assertEqual(res_json["file_validation"]["status"], "PASS")
        self.assertIn("extracted_data", res_json)
        self.assertIn("validation", res_json)

        # Verify retrieval by document name
        get_resp = self.client.get("/api/v1/documents/test_invoice_flow.pdf")
        self.assertEqual(get_resp.status_code, 200)
        get_json = get_resp.json()
        self.assertEqual(get_json["document_name"], "test_invoice_flow.pdf")

if __name__ == "__main__":
    unittest.main()
