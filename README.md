# 🧠 Intelligent Document Extraction, Validation & API Platform

[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg?style=flat&logo=FastAPI)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=flat&logo=python)](https://www.python.org/)

An end-to-end, production-ready AI-powered document intelligence platform that ingests native and scanned financial documents (Invoices, Balance Sheets, Profit & Loss Statements, and Cash Flow Statements), validates file constraints, performs OCR and complete structured field/table extraction with evidence grounding, verifies domain-specific financial calculations, persists records in a persistent ACID database, and surfaces results via an interactive dashboard and OpenAPI-compliant REST APIs.

---
## Demo Video

https://github.com/user-attachments/assets/c05c01de-76a0-4442-8534-0f1791c0b4cf

## 🏗️ Overview & Architecture

The platform is designed around a decoupled, 6-tier pipeline to guarantee high availability, testability, and strict financial auditability:

```text
📄 Upload Document
        │
        ▼
🛡️ Validate File
        │
        ▼
🔍 OCR & PDF Parsing
        │
        ▼
🤖 AI Information Extraction
        │
        ▼
🎯 Evidence Grounding
        │
        ▼
🧮 Financial Validation
        │
        ▼
💾 Store Results
        │
        ▼
🌐 Dashboard • REST API • Swagger
```


![Architecture Diagram](docs/architecture.png)

### ✨ Architecture Highlights

1. **🛡️ Input Validation Layer**: Guards downstream compute by checking file integrity (`PIL.verify()`, PyMuPDF bounding box read), non-empty payloads, allowed MIME extensions (`.pdf`, `.jpg`, `.jpeg`, `.png`), and page count constraints ($\le 3$ pages).
2. **🔍 Dual-Tier OCR**: Automatically detects native PDF vector text or seamlessly rasterizes scanned pages at 150 DPI for OCR.Space / Gemini Vision processing.
3. **🎯 Evidence Grounding**: Binds every critical financial figure to a concrete `source_text` excerpt and `page_number` for audit verification.
4. **🧮 Financial Validation Engine**: Performs independent mathematical checks for all supported financial document types with configurable numerical tolerance ($\pm 0.05$).

---

## 🛠️ Technology Stack & Rationale

| 🏷️ **Component** | ⚙️ **Technology** | 💡 **Rationale** |
|:-----------------|:------------------|:-----------------|
| 🚀 **Backend Framework** | **FastAPI** | High-performance asynchronous REST framework with native OpenAPI 3.0 (Swagger UI at `/docs`), Pydantic data validation, and multipart form support. |
| 📄 **Document Processing** | **PyMuPDF (fitz)** | High-speed, robust PDF parsing and rasterization without requiring external C/C++ dependencies like Poppler. |
| 🔍 **OCR Service** | **OCR.Space REST API** | Free-tier cloud OCR engine providing high-precision table extraction without requiring system-level Tesseract installations. |
| 🤖 **Multimodal Vision** | **Google Gemini 2.5 Flash** | Integrated via `google-genai` for zero-shot structured financial extraction on complex, degraded layouts. |
| 💾 **Persistence** | **SQLite 3** | Zero-configuration, ACID-compliant database ideal for containerized deployments and evaluator test runs without external DB provisioning. |
| 🎨 **Frontend** | **Jinja2 + HTML5 / CSS3 / Vanilla JS** | Lightweight, zero-build-step responsive UI with status badges, formula breakdown cards, and raw JSON copy/export features. |
| 🧪 **Testing** | **unittest & pytest** | Comprehensive unit and integration test coverage for validation formulas, edge cases, and API routes. |
```
```

## 🌍 Deployed URLs & Public Repository

| 🔗 Resource | 🌐 URL |
| :--- | :--- |
| **Public GitHub Repository** | [https://github.com/PoojaKumar2004/intelligent-document-platform](https://github.com/PoojaKumar2004/intelligent-document-platform)
| **Live Deployed Frontend** | [`https://intelligent-document-platform-lk0l.onrender.com/`](https://intelligent-document-platform-lk0l.onrender.com/)
| **Live Backend API Base** | [`https://intelligent-document-platform.onrender.com/api/v1`](https://intelligent-document-platform-lk0l.onrender.com/api/v1)` |
| **Interactive Swagger Docs** | [`https://intelligent-document-platform.onrender.com/docs`](https://intelligent-document-platform-lk0l.onrender.com/docs)
| **System Health Endpoint** | [`https://intelligent-document-platform.onrender.com/api/v1/health`](https://intelligent-document-platform-lk0l.onrender.com/api/v1/health)


## 🚀 Local Setup & Quickstart

### 📋 Prerequisites
- 🐍 Python 3.10, 3.11, 3.12, 3.13, or 3.14
- 🌿 Git

### ⚡ Installation Steps

```bash
# 1. Clone the repository
git clone https://github.com/PoojaKumar2004/intelligent-document-platform.git
cd intelligent-document-platform

# 2. Create and activate a virtual environment
python -m venv venv

# On Windows
.\venv\Scripts\activate

# On Linux/macOS
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env

# 5. Start the platform server
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --reload
```

Open your browser at `http://localhost:8001/` to access the Dashboard, or `http://localhost:80001docs` to test via Swagger UI.

## 🔑 Environment Variables (`.env.example`)

| 🔑 Variable | 📌 Default | 📝 Description |
| :--- | :--- | :--- |
| `PORT` | `8000` | Port for the web and API server. |
| `DATABASE_PATH` | `documents.db` | Path to persistent SQLite database file. |
| `UPLOAD_DIR` | `uploads` | Directory for staging uploaded documents. |
| `MAX_PAGES` | `3` | Maximum allowed page count per document. |
| `FINANCIAL_TOLERANCE` | `0.05` | Numerical variance threshold for rounding reconciliations. |
| `OCR_SPACE_API_KEY` | `helloworld` | Free OCR.Space API key (obtain free key at ocr.space). |
| `GEMINI_API_KEY` | `""` | Optional Google Gemini API key for multimodal vision extraction. |


## 📡 API Reference & Request Examples

### 📤 Process Document (`POST /api/v1/documents/process`)
Accepts multipart form upload with `file` and `document_type` (`invoice`, `balance_sheet`, `profit_and_loss`, `cash_flow_statement`).

**URL Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents/process" \
  -F "file=@sample_invoice.pdf" \
  -F "document_type=invoice"
```

**Response (HTTP 200 OK):**
```json
{
  "document_name": "sample_invoice.pdf",
  "document_type": "invoice",
  "processing_status": "PASS",
  "overall_confidence": 0.96,
  "file_validation": {
    "file_type": "application/pdf",
    "is_supported": true,
    "is_readable": true,
    "page_count": 1,
    "status": "PASS"
  },
  "extracted_data": {
    "invoice_number": { "value": "INV-23891", "confidence": 0.98, "page_number": 1, "evidence": { "source_text": "Invoice no: INV-23891", "page_number": 1 } },
    "subtotal": { "value": 12500.00, "confidence": 0.98, "page_number": 1 },
    "tax_amount": { "value": 625.00, "confidence": 0.97, "page_number": 1 },
    "discount": { "value": 0.00, "confidence": 0.95, "page_number": 1 },
    "total_amount": { "value": 13125.00, "confidence": 0.99, "page_number": 1 },
    "line_items": [
      { "description": "Consulting Service", "quantity": 1, "unit_price": 12500.00, "amount": 12500.00 }
    ]
  },
  "validation": {
    "checks": [
      {
        "name": "invoice_total_check",
        "formula": "subtotal + tax_amount - discount",
        "operands": { "subtotal": 12500.00, "tax_amount": 625.00, "discount": 0.00 },
        "calculated_value": 13125.00,
        "reported_value": 13125.00,
        "variance": 0.00,
        "status": "PASS",
        "message": "Calculation matches reported value."
      }
    ],
    "overall_status": "PASS",
    "issues": []
  },
  "processing_metadata": {
    "ocr_used": true,
    "ocr_engine": "OCR.Space-API",
    "processed_at": "2026-09-10T12:00:00Z",
    "processing_time_ms": 2840
  }
}
```

### 📥 Retrieve Latest Document by Name (`GET /api/v1/documents/{document_name}`)
```bash
curl -X GET "http://localhost:8000/api/v1/documents/sample_invoice.pdf"
```

### 📃 List All Processed Documents (`GET /api/v1/documents`)
```bash
curl -X GET "http://localhost:8000/api/v1/documents"
```

### ❤️ Health Check (`GET /api/v1/health`)
```bash
curl -X GET "http://localhost:8000/api/v1/health"
```
**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-09-10T12:00:00Z",
  "version": "1.0.0"
}
```

---

## 🧮 Financial Validation Rules & Numerical Tolerance

The platform enforces the accounting reconciliation formulas specified in Section 4.4:

### 🧾 Invoices
- **Line Item Check**: $\text{Quantity} \times \text{Unit Price} \approx \text{Line Total}$ (evaluated per line).
- **Line Item Sum**: $\sum \text{Line Totals} \approx \text{Reported Subtotal / Total}$.
- **Invoice Total**: $\text{Subtotal} + \text{Tax Amount} - \text{Discount} \approx \text{Total Amount}$.
- **Cash & Change**: $\text{Cash Paid} - \text{Total Amount} \approx \text{Change}$ (e.g. retail receipts).

### 🏦 Balance Sheets
- **Fundamental Accounting Equation**: $\text{Total Capital \ Liabilities} \approx \text{Total Assets}$.
- **Liabilities Component Check**: $\text{Capital} + \text{Reserves} + \text{Minority Interest} + \text{Deposits} + \text{Borrowings} + \text{Other Liabilities} \approx \text{Total Liabilities}$.
- **Assets Component Check**: $\text{Cash/RBI} + \text{Bank Balances} + \text{Investments} + \text{Advances} + \text{Fixed Assets} + \text{Other Assets} \approx \text{Total Assets}$.
- *Multi-Period*: Validated independently for each comparative financial year/period present.

### 📈 Profit & Loss Statements
- **Income Reconciliation**: $\text{Interest Earned} + \text{Other Income} \approx \text{Total Income}$.
- **Expenditure Reconciliation**: $\text{Interest Expended} + \text{Operating Expenses} + \text{Provisions} \approx \text{Total Expenditure}$.
- **Net Operating Profit**: $\text{Total Income} - \text{Total Expenditure} \approx \text{Net Profit Before Minority Interest}$.
- **Group Attributable Profit**: $\text{Net Profit} - \text{Minority Interest} + \text{Associates Profit} \approx \text{Consolidated Net Profit}$.
- **Appropriations**: $\text{Group Profit} + \text{Balance Brought Forward} + \text{Amalgamation} \approx \text{Total Available for Appropriation}$.

### 💰 Cash Flow Statements
- **Net Cash Change**: $\text{Operating CF} + \text{Investing CF} + \text{Financing CF} + \text{FX Adjustment} + \text{Amalgamation} \approx \text{Net Increase in Cash}$.
- **Closing Cash Balance:** `Opening Cash + Net Increase in Cash ≈ Closing Cash & Cash Equivalents`
- **Sign Convention**: Negative / outflow values denoted by parentheses `(x)` or `-` are correctly parsed as negative floats.

### ⚖️ Tolerance & Missing Field Rule
- **Tolerance**: Defaults to $\pm 0.05$ to prevent false failures caused by rounding fractions of a cent/paisa.
- **Null Handling**: If a required operand is absent from the document, the check status is strictly set to `NOT_APPLICABLE` rather than fabricating numbers.

---

## 🎯 Confidence Scoring & Evidence Grounding

- **📌 Grounding**: For key fields, the JSON response includes an `evidence` object containing `source_text` (verbatim string from the source) and `page_number`.
- **📊 Confidence Metric**: Confidence scores range from `0.0` to `1.0`:
  - `0.98 - 0.99`: Exact regex/table pattern match with high OCR character fidelity.
  - `0.94 - 0.97`: Standard parsed value with valid contextual grounding.
  - `< 0.90`: Low-confidence or ambiguous matches (visually flagged on the dashboard).

---

## 🧪 Testing

Run all tests:

```bash
python -m unittest discover backend/tests
```

Or using PyTest:

```bash
pytest backend/tests/ -v
```

### ✅ Test Breakdown

| Test File | Description |
|-----------|-------------|
| `test_validation.py` | Validates invoice calculations, Balance Sheet reconciliation, Profit & Loss formulas, Cash Flow equations, and negative value handling. |
| `test_extraction.py` | Tests document validation, supported PDF/JPG formats, OCR pipeline, and unsupported file rejection. |
| `test_api.py` | Tests `/api/v1/health`, `/api/v1/documents/process`, document retrieval, listing APIs, and error responses. |

---

## 📂 Sample Outputs

The `sample_outputs/` directory contains verified JSON outputs generated by the platform.

| File | Description |
|------|-------------|
| `sample_invoice_result.json` | Invoice extraction with line items, taxes, totals, and validation. |
| `sample_balance_sheet_result.json` | Multi-period Balance Sheet extraction with reconciliation results. |
| `sample_profit_and_loss_result.json` | Profit & Loss statement extraction with financial validation. |
| `sample_cash_flow_result.json` | Cash Flow statement extraction with operating, investing, financing, and closing balance validation. |
| `sample_validation_failure_result.json` | Example output showing mathematical validation failure. |
| `sample_unsupported_file_error.json` | Standardized API response for unsupported file formats. |

---

## 🚧 Known Limitations

| Limitation | Description |
|-----------|-------------|
| ⏳ Synchronous Processing | OCR processing for large multi-page documents typically requires 4–8 seconds and is optimized for evaluation workloads. |
| 🗄 SQLite Database | SQLite is ideal for local deployments but is not intended for high-concurrency distributed production systems. |
| 📁 Local File Storage | Uploaded documents and rendered previews are temporarily stored on local disk during processing. |

---

## 🚀 Future Production Improvements

- ⚡ Implement asynchronous processing using Celery/ARQ with Redis or RabbitMQ.
- ☁️ Store documents in cloud object storage such as AWS S3 or Google Cloud Storage.
- 🗄 Migrate from SQLite to PostgreSQL for enterprise-scale deployments.
- 🤖 Integrate layout-aware document AI models (LayoutLMv3, Donut, or fine-tuned Gemini) for enhanced extraction accuracy.

---

## Sample Screenshot

<img width="1836" height="912" alt="Screenshot 2026-09-10 220340" src="https://github.com/user-attachments/assets/0f5ddac2-08ce-44e5-a639-1787aef2f327" />

<img width="1510" height="912" alt="Screenshot 2026-09-10 220400" src="https://github.com/user-attachments/assets/e6da3004-c571-4234-85ba-cb9c536d62e3" />

<img width="1846" height="872" alt="Screenshot 2026-09-10 220432" src="https://github.com/user-attachments/assets/aedbfc96-0d94-4db4-94b9-10f955f9a027" />

<img width="1649" height="904" alt="Screenshot 2026-09-10 220459" src="https://github.com/user-attachments/assets/8c1b0525-9d1a-4b17-a865-89a44e3ef37c" />

<img width="1513" height="907" alt="Screenshot 2026-09-10 220513" src="https://github.com/user-attachments/assets/78cd503b-3b10-4303-98b6-fbddd28ae5bb" />

<img width="1469" height="894" alt="Screenshot 2026-09-10 220536" src="https://github.com/user-attachments/assets/030a900e-2769-420b-88a8-5f815c9c15bb" />

## 🤖 AI Tools Used

The following AI-assisted development tools were used during implementation in accordance with the internship guidelines:

- Google DeepMind Antigravity / Gemini
- Boilerplate code generation
- Pydantic schema drafting
- Mathematical edge-case test generation
- Documentation refinement
- PyMuPDF-based PDF visualization support
