# DocFlow AI — Local Invoice Intelligence Pipeline

> **Fully local, cloud-free AI pipeline** for automated invoice processing.
> OCR → LLM extraction → semantic catalog matching → confidence scoring → human-in-the-loop review.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)
![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-orange)
![Qdrant](https://img.shields.io/badge/Qdrant-Vector_Store-red)
![n8n](https://img.shields.io/badge/n8n-Workflow_Automation-purple)

---

## What This Does

Suppliers send invoices in all formats — scanned PDFs, image files, Word documents. Manually keying them into your system is slow and error-prone.

DocFlow AI automates the entire workflow:

```
Invoice (PDF/Image/DOCX)
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  1. OCR Extraction          Tesseract + pdf2image            │
│     → Raw text from any document type                        │
│                                                               │
│  2. LLM Structured Parsing  Ollama (Qwen2.5 / Mistral)       │
│     → Vendor, date, line items, totals, payment terms        │
│                                                               │
│  3. Semantic Catalog Match  Qdrant + sentence-transformers    │
│     → Each line item matched against your product catalog    │
│                                                               │
│  4. Confidence Scoring      Multi-factor quality assessment  │
│     → Auto-approve or flag for human review                  │
│                                                               │
│  5. Output                  CSV + webhook + review queue      │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
n8n Workflow → Slack notifications → Review queue → ERP/CSV export
```

**No data ever leaves your infrastructure.** Zero cloud API calls.

---

## Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   n8n        │    │  FastAPI     │    │  Ollama      │    │  Qdrant      │
│  :5678       │───▶│   :8000      │───▶│  :11434      │    │  :6333       │
│  Automation  │    │  Pipeline    │    │  Local LLM   │    │  Vector DB   │
│  & Routing   │    │  Orchestr.   │◀───│  Qwen2.5 7B  │◀───│  Embeddings  │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                           │
                    ┌──────┴──────┐
                    │  Tesseract  │
                    │    OCR      │
                    └─────────────┘
```

All services run in Docker Compose on your local machine or server.

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API** | FastAPI + Python 3.11 | REST API, pipeline orchestration |
| **OCR** | Tesseract + pdf2image + python-docx | Text extraction from any doc type |
| **LLM** | Ollama (Qwen2.5:7b / Mistral:7b) | Structured data extraction via NLP |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2) | Local vector embeddings |
| **Vector Store** | Qdrant | Semantic catalog matching |
| **Automation** | n8n | Trigger, validate, notify, route |
| **Validation** | Pydantic v2 | Strict data models + type safety |

---

## Quick Start

### Prerequisites
- Docker + Docker Compose
- 8GB RAM minimum (16GB recommended for 7B models)
- ~10GB disk for model weights

### 1. Clone and configure

```bash
git clone https://github.com/yourname/docflow-ai
cd docflow-ai
cp .env.example .env
```

### 2. Start all services

```bash
docker compose up -d
```

Services starting:
- **API** → http://localhost:8000
- **Qdrant** → http://localhost:6333
- **Ollama** → http://localhost:11434
- **n8n** → http://localhost:5678

### 3. Pull the LLM model

```bash
docker exec docflow-ollama ollama pull qwen2.5:7b
```

> Want a smaller/faster model? Try `llama3.2:3b` (~2GB, faster) or `mistral:7b` (~4GB, excellent accuracy).

### 4. Seed the product catalog

```bash
python scripts/seed_catalog.py
```

This loads 20 sample products into Qdrant across 6 categories. Replace with your real catalog.

### 5. Test the full pipeline

```bash
python scripts/test_pipeline.py
```

Expected output:
```
📤 Uploading: test_invoice.txt
📋 PIPELINE RESULTS
  Job ID:         a3f8b1c2-...
  Status:         approved
  Confidence:     91.0%
  Processing:     4823ms

📄 EXTRACTED INVOICE DATA:
  Vendor:         TechSupply Corp
  Invoice #:      INV-2024-00847
  Total:          USD 2422.66

🛒 LINE ITEMS (5):
  1. USB-C Hub 7-in-1                      → ✅ matched: USB-C Hub 7-in-1 (98%)
  2. Wireless Keyboard and Mouse Combo     → ✅ matched: Wireless Keyboard... (95%)
  ...
```

---

## API Reference

Interactive docs available at **http://localhost:8000/docs**

### Upload & Process

```bash
# Process a PDF invoice
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@invoice.pdf"
```

Response:
```json
{
  "job_id": "a3f8b1c2-...",
  "filename": "invoice.pdf",
  "review_status": "approved",
  "overall_confidence": 0.91,
  "invoice_data": {
    "vendor_name": "TechSupply Corp",
    "invoice_number": "INV-2024-00847",
    "invoice_date": "2024-11-15",
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

### Review Queue (HITL)

```bash
# Get documents flagged for review
curl http://localhost:8000/review-queue

# Approve a document after review
curl -X PATCH http://localhost:8000/review/a3f8b1c2/approve \
  -H "Content-Type: application/json" \
  -d '{"reviewed_by": "john.doe"}'

# Submit corrections
curl -X PATCH http://localhost:8000/review/a3f8b1c2/correct \
  -H "Content-Type: application/json" \
  -d '{"reviewed_by": "john.doe", "corrected_data": {...}}'
```

### Catalog Management

```bash
# Add your product catalog
curl -X POST http://localhost:8000/catalog/items \
  -H "Content-Type: application/json" \
  -d '[{"id":"P001","name":"Widget A","description":"Premium widget","unit_price":9.99}]'

# Test semantic matching
curl -X POST http://localhost:8000/catalog/search \
  -H "Content-Type: application/json" \
  -d '{"query": "printer paper A4", "top_k": 3}'
```

### Download CSV

```bash
curl http://localhost:8000/documents/a3f8b1c2/download/csv -o invoice.csv
```

---

## n8n Automation Workflow

Import `n8n/workflow.json` into your n8n instance:

1. Go to http://localhost:5678 (admin / docflow123)
2. New Workflow → Import from JSON
3. Paste contents of `n8n/workflow.json`
4. Update Slack webhook URLs
5. Activate

**What the workflow does:**

```
Webhook (receives doc upload event)
    │
    ▼
Validate Input
    │
    ▼
DocFlow API: Process Document
    │
    ▼
Route by Confidence
    │
    ├── High confidence → Download CSV → Slack: "Auto-approved ✅"
    │
    └── Low confidence → Slack: "Needs review ⚠️" (with job ID + link)

+ Scheduled every 5 min:
    Poll review queue → Slack summary if items pending
```

---

## Supported Document Types

| Format | Method | Notes |
|--------|--------|-------|
| Digital PDF | Text layer extraction | Fast, high accuracy |
| Scanned PDF | Tesseract OCR (300 DPI) | Works on most scans |
| PNG / JPG / TIFF | Tesseract OCR | Grayscale preprocessing |
| Word (.docx) | python-docx | Preserves tables |

---

## Confidence Scoring

The pipeline scores each extraction on 4 dimensions:

| Factor | Weight | What it measures |
|--------|--------|-----------------|
| LLM self-score | 40% | Model's own uncertainty estimate |
| Structural completeness | 25% | Required fields present |
| Numeric consistency | 20% | Line items sum = subtotal, subtotal + tax = total |
| Catalog match rate | 15% | % of line items matched in catalog |

**Routing:**
- Score ≥ 0.75 → **Auto-approved**, CSV exported, team notified
- Score < 0.75 → **Flagged for review**, reviewer notified via Slack

---

## Swapping the LLM

Change the model in `.env`:

```bash
OLLAMA_MODEL=mistral:7b         # Good balance of speed + accuracy
OLLAMA_MODEL=llama3.2:3b        # Fastest, works on 8GB RAM
OLLAMA_MODEL=llama3.1:8b        # High accuracy, needs 16GB RAM
OLLAMA_MODEL=qwen2.5:7b         # Best for structured extraction (default)
```

Then pull it:
```bash
docker exec docflow-ollama ollama pull mistral:7b
```

---

## Replacing In-Memory Storage

The default in-memory store is for demo purposes. For production:

```python
# app/routers/documents.py
# Replace _results dict with:

# Redis
import redis
r = redis.Redis()
r.set(result.job_id, result.model_dump_json())

# Postgres (with SQLAlchemy)
# MongoDB (with motor)
# SQLite (lightweight)
```

---

## Production Notes

- **GPU:** Uncomment the GPU section in `docker-compose.yml` for 10x faster inference
- **Model size:** 7B models run fine on CPU, just slower (~30-60s per invoice)
- **Scaling:** Add multiple API replicas behind a load balancer
- **Auth:** Add API key middleware to FastAPI before exposing publicly
- **Storage:** Swap in-memory store for Postgres/Redis for persistence
- **ERP integration:** Add exporter route that POSTs structured JSON to your ERP webhook

---

## Project Structure

```
docflow-ai/
├── app/
│   ├── main.py              # FastAPI app + lifespan
│   ├── config.py            # Settings (Pydantic)
│   ├── models/
│   │   ├── invoice.py       # ProcessingResult, InvoiceData, LineItem
│   │   └── catalog.py       # CatalogItem, CatalogMatchResult
│   ├── services/
│   │   ├── ocr.py           # Tesseract + pdf2image + python-docx
│   │   ├── llm.py           # Ollama HTTP client, prompt templates
│   │   ├── matcher.py       # Qdrant CRUD + semantic search
│   │   ├── extractor.py     # Pipeline orchestrator
│   │   ├── scorer.py        # Multi-factor confidence scoring
│   │   └── exporter.py      # CSV + webhook output
│   └── routers/
│       ├── documents.py     # Upload, list, download endpoints
│       ├── review.py        # HITL approve/reject/correct
│       └── catalog.py       # Catalog CRUD + search
├── n8n/
│   └── workflow.json        # Import into n8n
├── scripts/
│   ├── seed_catalog.py      # Load sample products into Qdrant
│   └── test_pipeline.py     # End-to-end pipeline test
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## License

MIT
