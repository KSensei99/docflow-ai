# DocFlow AI — Local Invoice Intelligence Pipeline

> Fully automated, cloud-free AI pipeline that extracts, structures, and routes supplier invoice data — no manual data entry, no cloud APIs, everything runs on your own machine.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat&logo=fastapi&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-black?style=flat)
![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-dc244c?style=flat)
![n8n](https://img.shields.io/badge/n8n-Automation-EA4B71?style=flat&logo=n8n&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker&logoColor=white)

---

## The Problem This Solves

Businesses receive supplier invoices in all formats — scanned PDFs, image files, Word documents. Manually reading them and typing the data into a system is slow, expensive, and error-prone.

**DocFlow AI automates the entire workflow:**

- Reads any invoice format automatically
- Extracts vendor name, dates, line items, totals, payment terms
- Matches each line item against your product catalog
- Scores its own confidence and flags uncertain extractions for human review
- Exports structured data to CSV or pushes it to your existing system via webhook
- Notifies your team on Slack in real time

Zero cloud API calls. Everything runs locally on your infrastructure.

---

## How It Works

```
Invoice uploaded (PDF / Image / Word)
         │
         ▼
┌─────────────────────────────────────────┐
│  Step 1 — OCR                           │
│  Tesseract + pdf2image + python-docx    │
│  → Extracts raw text from any format   │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Step 2 — LLM Extraction                │
│  Ollama running Qwen2.5 / Mistral       │
│  → Structures data into clean JSON     │
│  → vendor, date, line items, totals    │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Step 3 — Semantic Catalog Matching     │
│  Qdrant vector store + embeddings       │
│  → Matches line items to your catalog  │
│  → Works even with messy descriptions  │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Step 4 — Confidence Scoring            │
│  Multi-factor quality assessment        │
│  → Score ≥ 0.75 → auto-approved        │
│  → Score < 0.75 → flagged for review   │
└─────────────────────────────────────────┘
         │
         ▼
   CSV export + Webhook push + Slack alert
```

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| API & orchestration | FastAPI (Python 3.11) | Fast, async, auto-generates Swagger docs |
| OCR | Tesseract + pdf2image + python-docx | Handles scanned PDFs, images, and Word files |
| Local LLM | Ollama (Qwen2.5:7b / Mistral:7b) | Runs fully on-premise, no API costs |
| Vector search | Qdrant + sentence-transformers | Semantic catalog matching without cloud embeddings |
| Automation | n8n | Visual workflow: trigger → validate → notify → route |
| Infrastructure | Docker Compose | One command to start everything |
| Data models | Pydantic v2 | Strict typing and validation throughout |

---

## Features

- **Multi-format OCR** — digital PDFs (text layer), scanned PDFs (300 DPI OCR), PNG/JPG/TIFF images, Word documents
- **Structured extraction** — invoice number, vendor details, dates, line items, subtotal, tax, total, payment terms
- **Semantic matching** — fuzzy-matches line item descriptions to your product catalog even when wording differs
- **Confidence scoring** — 4-factor score combining LLM certainty, structural completeness, numeric consistency, and catalog match rate
- **Human-in-the-loop review** — low-confidence extractions go to a review queue with approve/reject/correct endpoints
- **Flexible output** — CSV files, webhook POST to any URL, or direct API response
- **n8n workflow** — import-ready workflow with Slack notifications for approvals and review alerts
- **Swap the model** — change one line in `.env` to use Mistral, LLaMA, or any Ollama-supported model
- **100% local** — no data ever leaves your server

---

## API Endpoints

| Method | Endpoint | What it does |
|--------|----------|-------------|
| `POST` | `/documents/upload` | Upload and process a document |
| `GET` | `/documents/` | List all processed documents |
| `GET` | `/documents/{id}` | Get result for a specific job |
| `GET` | `/documents/{id}/download/csv` | Download CSV export |
| `GET` | `/review/review-queue` | Get documents awaiting human review |
| `PATCH` | `/review/{id}/approve` | Approve a flagged extraction |
| `PATCH` | `/review/{id}/correct` | Submit corrected data |
| `POST` | `/catalog/items` | Add products to the catalog |
| `POST` | `/catalog/search` | Test semantic search |
| `GET` | `/health` | Check all services are running |

Full interactive docs available at `http://localhost:8000/docs` once running.

---

## Sample Output

Upload an invoice and get back structured JSON instantly:

```json
{
  "job_id": "a3f8b1c2-...",
  "filename": "supplier_invoice_nov.pdf",
  "review_status": "approved",
  "overall_confidence": 0.91,
  "invoice_data": {
    "vendor_name": "TechSupply Corp",
    "invoice_number": "INV-2024-00847",
    "invoice_date": "2024-11-15",
    "due_date": "2024-12-15",
    "total_amount": 2422.66,
    "currency": "USD",
    "line_items": [
      {
        "description": "USB-C Hub 7-in-1",
        "quantity": 5,
        "unit_price": 45.00,
        "total": 225.00,
        "matched_product_id": "IT-001",
        "matched_product_name": "USB-C Hub 7-in-1",
        "match_confidence": 0.98
      }
    ]
  },
  "field_confidences": {
    "vendor_name": 0.97,
    "total_amount": 0.95,
    "line_items": 0.89
  },
  "processing_time_ms": 4823
}
```

---

## Project Structure

```
docflow-ai/
├── app/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Settings via environment variables
│   ├── models/
│   │   ├── invoice.py           # Invoice, LineItem, ProcessingResult models
│   │   └── catalog.py           # CatalogItem, CatalogMatchResult models
│   ├── services/
│   │   ├── ocr.py               # OCR pipeline (Tesseract + pdf2image + docx)
│   │   ├── llm.py               # Ollama LLM client + extraction prompts
│   │   ├── matcher.py           # Qdrant semantic search
│   │   ├── extractor.py         # Pipeline orchestrator
│   │   ├── scorer.py            # Confidence scoring logic
│   │   └── exporter.py          # CSV + webhook output
│   └── routers/
│       ├── documents.py         # Upload and retrieval endpoints
│       ├── review.py            # Human-in-the-loop review endpoints
│       └── catalog.py           # Catalog management endpoints
├── n8n/
│   └── workflow.json            # Import-ready n8n automation workflow
├── scripts/
│   ├── seed_catalog.py          # Populate Qdrant with sample products
│   └── test_pipeline.py         # End-to-end pipeline test
├── docker-compose.yml           # All services: API + Ollama + Qdrant + n8n
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Quick Start

**Requirements:** Docker, Docker Compose, 8GB RAM minimum

```bash
# 1. Clone the repo
git clone https://github.com/KSensei99/docflow-ai.git
cd docflow-ai

# 2. Configure environment
cp .env.example .env

# 3. Start all services
docker compose up -d

# 4. Pull the LLM model (one-time, ~4GB download)
docker exec docflow-ollama ollama pull qwen2.5:7b

# 5. Seed the product catalog
python scripts/seed_catalog.py

# 6. Run the test
python scripts/test_pipeline.py
```

Then open **http://localhost:8000/docs** to see the full interactive API.

---

## Configuration

All settings are in `.env`:

```env
# LLM model — swap anytime without code changes
OLLAMA_MODEL=qwen2.5:7b       # or mistral:7b, llama3.2:3b, llama3.1:8b

# Confidence threshold — below this goes to human review
CONFIDENCE_THRESHOLD=0.75

# Optional: push results to your existing system
WEBHOOK_ENABLED=false
WEBHOOK_URL=https://your-system.com/api/invoices
```

---

## n8n Automation Workflow

Import `n8n/workflow.json` into your n8n instance for full automation:

- Receives document upload events via webhook
- Calls the DocFlow AI pipeline
- Routes by confidence score
- Sends Slack notification for auto-approved invoices
- Sends Slack alert with job ID for low-confidence invoices needing review
- Polls the review queue every 5 minutes and sends a summary

---

## Extending the Pipeline

This project is built to be extended:

- **More document types** — add a new method to `ocr.py`
- **Different LLM** — change `OLLAMA_MODEL` in `.env`
- **ERP integration** — add an endpoint in `exporter.py` that POSTs to your ERP
- **Persistent storage** — replace the in-memory store in `routers/documents.py` with Postgres or Redis
- **GPU acceleration** — uncomment the GPU section in `docker-compose.yml` for 10x faster inference

---

## License

MIT — free to use and modify.

---

*Built as a demonstration of local AI document processing. Stack: Python · FastAPI · Ollama · Qdrant · n8n · Docker*
