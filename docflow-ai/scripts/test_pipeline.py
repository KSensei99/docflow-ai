"""
Test Pipeline
=============
Creates a sample invoice text file and tests the full pipeline.
Run after seeding the catalog.

Usage:
    python scripts/test_pipeline.py
    python scripts/test_pipeline.py --url http://localhost:8000
"""

import sys
import json
import time
import argparse
import urllib.request
import urllib.error
from pathlib import Path


SAMPLE_INVOICE_TEXT = """
INVOICE

TechSupply Corp
123 Business Park, Suite 400
San Francisco, CA 94107
billing@techsupply.com

BILL TO:
Acme Corp Ltd
456 Corporate Blvd
New York, NY 10001

Invoice Number: INV-2024-00847
Invoice Date: 2024-11-15
Due Date: 2024-12-15
Payment Terms: Net 30

DESCRIPTION                          QTY    UNIT PRICE    TOTAL
----------------------------------------------------------------------
USB-C Hub 7-in-1                      5       $45.00      $225.00
Wireless Keyboard and Mouse Combo     3       $79.99      $239.97
Copy Paper A4 500 sheets             10        $6.99       $69.90
Monitor 27 inch Full HD               2      $249.00      $498.00
Software Development Consulting       8      $150.00    $1,200.00
----------------------------------------------------------------------

Subtotal:                                              $2,232.87
Tax (8.5%):                                              $189.79
----------------------------------------------------------------------
TOTAL DUE:                                             $2,422.66
Currency: USD

Payment Method: Bank Transfer
Bank: First National Bank
Account: **** **** 4892
Routing: 021000021

Notes: Thank you for your business. Please reference invoice number on payment.
Late payments subject to 1.5% monthly interest.
"""


def create_test_file() -> Path:
    """Create a sample invoice text file for testing."""
    test_path = Path("/tmp/test_invoice.txt")
    test_path.write_text(SAMPLE_INVOICE_TEXT)
    print(f"✅ Created test invoice: {test_path}")
    return test_path


def upload_and_process(base_url: str, file_path: Path) -> dict:
    """Upload the test file to DocFlow AI."""
    print(f"\n📤 Uploading: {file_path.name}")

    with open(file_path, "rb") as f:
        file_content = f.read()

    boundary = b"----TestBoundary12345"
    body = (
        b"------TestBoundary12345\r\n"
        b'Content-Disposition: form-data; name="file"; filename="test_invoice.txt"\r\n'
        b"Content-Type: text/plain\r\n\r\n"
        + file_content
        + b"\r\n------TestBoundary12345--\r\n"
    )

    req = urllib.request.Request(
        f"{base_url}/documents/upload",
        data=body,
        headers={"Content-Type": "multipart/form-data; boundary=----TestBoundary12345"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as e:
        print(f"❌ Upload error {e.code}: {e.read().decode()}")
        sys.exit(1)


def print_results(result: dict):
    inv = result.get("invoice_data", {})
    routing = result.get("routing", {})

    print("\n" + "="*60)
    print("📋 PIPELINE RESULTS")
    print("="*60)
    print(f"  Job ID:         {result['job_id']}")
    print(f"  File:           {result['filename']}")
    print(f"  Status:         {result['review_status']}")
    print(f"  Confidence:     {result['overall_confidence']:.1%}")
    print(f"  OCR Engine:     {result['ocr_engine']}")
    print(f"  LLM Model:      {result['llm_model']}")
    print(f"  Processing:     {result['processing_time_ms']}ms")

    print("\n📄 EXTRACTED INVOICE DATA:")
    print(f"  Vendor:         {inv.get('vendor_name', 'N/A')}")
    print(f"  Invoice #:      {inv.get('invoice_number', 'N/A')}")
    print(f"  Date:           {inv.get('invoice_date', 'N/A')}")
    print(f"  Due Date:       {inv.get('due_date', 'N/A')}")
    print(f"  Subtotal:       {inv.get('currency', 'USD')} {inv.get('subtotal', 'N/A')}")
    print(f"  Tax:            {inv.get('tax', 'N/A')}")
    print(f"  Total:          {inv.get('currency', 'USD')} {inv.get('total_amount', 'N/A')}")

    line_items = inv.get("line_items", [])
    if line_items:
        print(f"\n🛒 LINE ITEMS ({len(line_items)}):")
        for i, item in enumerate(line_items, 1):
            match_info = ""
            if item.get("matched_product_name"):
                match_info = f" → ✅ matched: {item['matched_product_name']} ({item['match_confidence']:.0%})"
            elif item.get("match_confidence", 0) > 0:
                match_info = f" → ⚠️ no match ({item['match_confidence']:.0%})"
            print(f"  {i}. {item['description'][:50]:<50} {item.get('total', '')}{match_info}")

    confidences = result.get("field_confidences", {})
    if confidences:
        print("\n📊 FIELD CONFIDENCES:")
        for field, score in sorted(confidences.items(), key=lambda x: -x[1]):
            bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
            flag = "⚠️ " if score < 0.6 else "   "
            print(f"  {flag}{field:<25} {bar} {score:.0%}")

    if result.get("review_notes"):
        print(f"\n💬 Review Notes: {result['review_notes']}")

    print("\n" + "="*60)


def main(base_url: str):
    # Health check
    print(f"🏥 Checking DocFlow AI at {base_url}...")
    try:
        with urllib.request.urlopen(f"{base_url}/health", timeout=5) as r:
            health = json.loads(r.read())
            print(f"   API: {health['api']} | Ollama: {health['ollama']} | Catalog: {health['catalog_items']} items")
    except Exception as e:
        print(f"❌ Cannot reach API: {e}")
        sys.exit(1)

    if health.get("catalog_items", 0) == 0:
        print("\n⚠️  Catalog is empty! Run first: python scripts/seed_catalog.py")

    # Create + upload test invoice
    test_file = create_test_file()
    result = upload_and_process(base_url, test_file)
    print_results(result)

    print(f"\n📥 Download CSV: {base_url}/documents/{result['job_id']}/download/csv")
    print(f"🔍 API Docs:     {base_url}/docs\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test DocFlow AI pipeline")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    args = parser.parse_args()
    main(args.url)
