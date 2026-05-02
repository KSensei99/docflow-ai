"""
Catalog Router
==============
POST /catalog/items       — add / upsert catalog items
GET  /catalog/items       — list all items
POST /catalog/search      — semantic search (test endpoint)
GET  /catalog/stats       — collection stats
DELETE /catalog/reset     — clear and rebuild
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.models.catalog import CatalogItem, CatalogMatchResult
from app.services.matcher import matcher

router = APIRouter(prefix="/catalog", tags=["Product Catalog"])

# In-memory catalog mirror (for listing)
_catalog: dict[str, CatalogItem] = {}


class SearchRequest(BaseModel):
    query: str
    top_k: int = 3


@router.post("/items", summary="Add items to product catalog")
async def add_items(items: list[CatalogItem]):
    """Embed and upsert product catalog items into Qdrant."""
    if not items:
        raise HTTPException(status_code=400, detail="Empty items list")

    matcher.upsert_catalog_items(items)

    for item in items:
        _catalog[item.id] = item

    return {"inserted": len(items), "total": matcher.catalog_count()}


@router.get("/items", response_model=list[CatalogItem])
async def list_items():
    """List all catalog items (in-memory mirror)."""
    return list(_catalog.values())


@router.post("/search", response_model=list[CatalogMatchResult])
async def semantic_search(req: SearchRequest):
    """Test semantic search against the catalog."""
    results = []
    for _ in range(req.top_k):
        match = matcher.match(req.query, top_k=req.top_k)
        if match:
            results.append(match)
            break
    return results


@router.get("/stats")
async def catalog_stats():
    return {
        "total_items": matcher.catalog_count(),
        "collection": matcher.client.get_collection(
            "product_catalog"
        ).model_dump() if matcher.catalog_count() > 0 else {}
    }


@router.delete("/reset")
async def reset_catalog():
    """Delete and recreate the Qdrant collection."""
    try:
        matcher.client.delete_collection("product_catalog")
    except Exception:
        pass
    matcher.init_collection()
    _catalog.clear()
    return {"status": "reset", "message": "Catalog cleared. Re-seed with POST /catalog/items"}
