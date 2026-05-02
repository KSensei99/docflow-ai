"""
Semantic Matcher — Qdrant + Sentence Transformers
==================================================
Embeds extracted line item descriptions and finds the closest
matching products in the catalog using cosine similarity.

All embeddings are computed locally (no cloud API calls).
"""

from typing import Optional
from loguru import logger

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.models.catalog import CatalogItem, CatalogMatchResult


VECTOR_DIM = 384  # all-MiniLM-L6-v2 output dimension
SIMILARITY_THRESHOLD = 0.65  # cosine score → is_match


class SemanticMatcher:
    """Manages the Qdrant product catalog and performs semantic search."""

    def __init__(self):
        self._client: Optional[QdrantClient] = None
        self._model: Optional[SentenceTransformer] = None

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(
                host=settings.qdrant_host, port=settings.qdrant_port
            )
        return self._client

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info(f"Loading embedding model: {settings.embedding_model}")
            self._model = SentenceTransformer(settings.embedding_model)
        return self._model

    # ── Catalog Management ────────────────────────────────────────────────────

    def init_collection(self):
        """Create Qdrant collection if it doesn't exist."""
        existing = [c.name for c in self.client.get_collections().collections]
        if settings.qdrant_collection not in existing:
            self.client.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
            )
            logger.info(f"Created Qdrant collection: {settings.qdrant_collection}")
        else:
            count = self.client.count(settings.qdrant_collection).count
            logger.info(f"Qdrant collection ready: {count} catalog items")

    def upsert_catalog_items(self, items: list[CatalogItem]):
        """Embed and upsert products into Qdrant."""
        self.init_collection()

        texts = [item.to_text() for item in items]
        embeddings = self.model.encode(texts, show_progress_bar=True)

        points = [
            PointStruct(
                id=abs(hash(item.id)) % (2**31),  # Qdrant needs uint32 id
                vector=embedding.tolist(),
                payload={
                    "item_id": item.id,
                    "name": item.name,
                    "description": item.description,
                    "sku": item.sku,
                    "category": item.category,
                    "unit_price": item.unit_price,
                    "unit": item.unit,
                },
            )
            for item, embedding in zip(items, embeddings)
        ]

        self.client.upsert(collection_name=settings.qdrant_collection, points=points)
        logger.info(f"Upserted {len(points)} catalog items to Qdrant")

    def catalog_count(self) -> int:
        try:
            return self.client.count(settings.qdrant_collection).count
        except Exception:
            return 0

    # ── Semantic Search ───────────────────────────────────────────────────────

    def match(self, query: str, top_k: int = 1) -> CatalogMatchResult | None:
        """
        Find the best matching catalog item for a line item description.
        Returns None if catalog is empty or no close match found.
        """
        if self.catalog_count() == 0:
            return None

        vector = self.model.encode([query])[0].tolist()

        results = self.client.search(
            collection_name=settings.qdrant_collection,
            query_vector=vector,
            limit=top_k,
            with_payload=True,
        )

        if not results:
            return None

        best = results[0]
        score = float(best.score)

        item = CatalogItem(
            id=best.payload["item_id"],
            name=best.payload["name"],
            description=best.payload.get("description", ""),
            sku=best.payload.get("sku"),
            category=best.payload.get("category"),
            unit_price=best.payload.get("unit_price"),
            unit=best.payload.get("unit"),
        )

        return CatalogMatchResult(
            catalog_item=item,
            similarity_score=round(score, 4),
            is_match=score >= SIMILARITY_THRESHOLD,
        )

    def match_batch(self, queries: list[str]) -> list[CatalogMatchResult | None]:
        """Match multiple line items efficiently."""
        return [self.match(q) for q in queries]


matcher = SemanticMatcher()
