from pydantic import BaseModel
from typing import Optional


class CatalogItem(BaseModel):
    id: str
    name: str
    description: str
    sku: Optional[str] = None
    category: Optional[str] = None
    unit_price: Optional[float] = None
    unit: Optional[str] = None   # "each", "kg", "hour", etc.

    def to_text(self) -> str:
        """Text used for embedding — richer = better semantic matching."""
        parts = [self.name]
        if self.description:
            parts.append(self.description)
        if self.sku:
            parts.append(f"SKU: {self.sku}")
        if self.category:
            parts.append(f"Category: {self.category}")
        return " | ".join(parts)


class CatalogMatchResult(BaseModel):
    catalog_item: CatalogItem
    similarity_score: float
    is_match: bool   # True if score >= threshold
