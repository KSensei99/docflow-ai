"""
Seed Product Catalog
====================
Populates Qdrant with sample products so the semantic matcher
has something to match against. Run this before testing.

Usage:
    python scripts/seed_catalog.py
    python scripts/seed_catalog.py --url http://localhost:8000
"""

import sys
import json
import argparse
import urllib.request
import urllib.error

SAMPLE_CATALOG = [
    # Office Supplies
    {"id": "OFF-001", "name": "Copy Paper A4 500 sheets", "description": "White A4 80gsm copy paper, 500 sheets per ream", "sku": "CPY-A4-500", "category": "Office Supplies", "unit_price": 6.99, "unit": "ream"},
    {"id": "OFF-002", "name": "Ballpoint Pen Box Blue", "description": "Blue ballpoint pens, box of 50, medium tip", "sku": "PEN-BLUE-50", "category": "Office Supplies", "unit_price": 12.50, "unit": "box"},
    {"id": "OFF-003", "name": "Stapler Desktop Heavy Duty", "description": "Heavy duty desktop stapler, 50 sheet capacity", "sku": "STA-HD-01", "category": "Office Supplies", "unit_price": 18.99, "unit": "each"},
    {"id": "OFF-004", "name": "Sticky Notes 3x3 Yellow", "description": "Self-adhesive sticky notes, 3x3 inch, yellow, 100 sheets", "sku": "STK-3X3-YL", "category": "Office Supplies", "unit_price": 3.49, "unit": "pad"},
    {"id": "OFF-005", "name": "Printer Ink Cartridge Black", "description": "Black ink cartridge compatible with HP, Canon, Epson printers", "sku": "INK-BLK-01", "category": "Office Supplies", "unit_price": 22.00, "unit": "each"},

    # IT Equipment
    {"id": "IT-001", "name": "USB-C Hub 7-in-1", "description": "7-port USB-C hub with HDMI, USB 3.0, SD card reader, PD charging", "sku": "USB-HUB-7C", "category": "IT Equipment", "unit_price": 45.00, "unit": "each"},
    {"id": "IT-002", "name": "Wireless Keyboard and Mouse Combo", "description": "Wireless keyboard and mouse set, Bluetooth 5.0, rechargeable", "sku": "KB-MOUSE-WL", "category": "IT Equipment", "unit_price": 79.99, "unit": "set"},
    {"id": "IT-003", "name": "Monitor 27 inch Full HD", "description": "27-inch IPS full HD monitor, 75Hz, HDMI + DP, built-in speakers", "sku": "MON-27-FHD", "category": "IT Equipment", "unit_price": 249.00, "unit": "each"},
    {"id": "IT-004", "name": "External SSD 1TB Portable", "description": "1TB portable SSD, USB 3.2, 550MB/s read speed", "sku": "SSD-1TB-EXT", "category": "IT Equipment", "unit_price": 89.99, "unit": "each"},
    {"id": "IT-005", "name": "Ethernet Cable Cat6 5m", "description": "Cat6 ethernet patch cable, 5 meters, RJ45, gigabit", "sku": "ETH-CAT6-5M", "category": "IT Equipment", "unit_price": 7.99, "unit": "each"},

    # Professional Services
    {"id": "SVC-001", "name": "Software Development Consulting", "description": "Senior software development consulting services, hourly rate", "sku": "SVC-DEV-HR", "category": "Professional Services", "unit_price": 150.00, "unit": "hour"},
    {"id": "SVC-002", "name": "IT Support Monthly Retainer", "description": "Monthly IT support and maintenance retainer", "sku": "SVC-IT-MO", "category": "Professional Services", "unit_price": 500.00, "unit": "month"},
    {"id": "SVC-003", "name": "Cloud Migration Project", "description": "Full cloud infrastructure migration project, per project", "sku": "SVC-CLOUD-PRJ", "category": "Professional Services", "unit_price": 12000.00, "unit": "project"},
    {"id": "SVC-004", "name": "Data Analysis Report", "description": "Custom data analysis and business intelligence report", "sku": "SVC-DATA-RPT", "category": "Professional Services", "unit_price": 2500.00, "unit": "report"},

    # Facilities / Cleaning
    {"id": "FAC-001", "name": "Office Cleaning Service Monthly", "description": "Monthly office cleaning service, 5 days per week", "sku": "FAC-CLN-MO", "category": "Facilities", "unit_price": 800.00, "unit": "month"},
    {"id": "FAC-002", "name": "Coffee Beans 1kg Premium", "description": "Premium arabica coffee beans, 1kg bag", "sku": "FAC-COF-1KG", "category": "Facilities", "unit_price": 24.99, "unit": "kg"},
    {"id": "FAC-003", "name": "Hand Sanitizer 500ml", "description": "70% alcohol hand sanitizer gel, 500ml pump dispenser", "sku": "FAC-SAN-500", "category": "Facilities", "unit_price": 5.99, "unit": "bottle"},

    # Logistics / Shipping
    {"id": "LOG-001", "name": "Express Courier Delivery", "description": "Next-day express courier delivery service", "sku": "LOG-EXP-ND", "category": "Logistics", "unit_price": 25.00, "unit": "shipment"},
    {"id": "LOG-002", "name": "Freight Forwarding Service", "description": "International freight forwarding, air cargo", "sku": "LOG-FGHT-AIR", "category": "Logistics", "unit_price": 450.00, "unit": "shipment"},
    {"id": "LOG-003", "name": "Warehouse Storage Monthly", "description": "Warehouse pallet storage, per pallet per month", "sku": "LOG-WH-PLT", "category": "Logistics", "unit_price": 35.00, "unit": "pallet/month"},
]


def seed_catalog(base_url: str):
    print(f"\n🌱 Seeding catalog at {base_url}")
    print(f"   {len(SAMPLE_CATALOG)} products across 6 categories\n")

    data = json.dumps(SAMPLE_CATALOG).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/catalog/items",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read())
            print(f"✅ Seeded {result['inserted']} items. Total in catalog: {result['total']}")
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error {e.code}: {e.read().decode()}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    print("\n📦 Categories:")
    cats = {}
    for item in SAMPLE_CATALOG:
        cats[item["category"]] = cats.get(item["category"], 0) + 1
    for cat, count in sorted(cats.items()):
        print(f"   {cat}: {count} items")

    print("\n🔍 Test semantic search:")
    test_queries = ["printer paper", "web development hourly", "office cleaning"]
    for q in test_queries:
        search_data = json.dumps({"query": q, "top_k": 1}).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/catalog/search",
            data=search_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                matches = json.loads(response.read())
                if matches:
                    m = matches[0]
                    print(f'   "{q}" → {m["catalog_item"]["name"]} (score={m["similarity_score"]:.3f})')
        except Exception as e:
            print(f'   "{q}" → error: {e}')

    print("\n✨ Catalog ready! You can now upload invoices.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed DocFlow AI product catalog")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    args = parser.parse_args()
    seed_catalog(args.url)
