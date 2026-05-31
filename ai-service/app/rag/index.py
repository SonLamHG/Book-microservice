"""FAISS in-memory vector index over the on-disk product corpus
`ai-service/data/product_corpus.jsonl`.

Each product is embedded with sentence-transformers `all-MiniLM-L6-v2`
(384-dim) and stored in an `IndexFlatIP` on cosine-normalised vectors —
equivalent to cosine similarity search.

The corpus file is the source-of-truth for product metadata used by the
RAG pipeline; products fetched from product-service at runtime are
normalised into the same shape before indexing."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from .. import config
from ..datasets import load_product_corpus

log = logging.getLogger("ai-service.rag.index")


def _normalise(p: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce either product_corpus.jsonl or product-service JSON shape
    into a single unified dict."""
    pid = p.get("product_id", p.get("id"))
    return {
        "id":           int(pid) if pid is not None else None,
        "name":         p.get("name", ""),
        "price":        float(p.get("price", 0) or 0),
        "description":  p.get("description", ""),
        "product_type": p.get("type") or p.get("product_type", "book"),
        "category":     p.get("category", ""),
        "author":       p.get("brand_or_author", ""),
        "keywords":     p.get("keywords", []) or [],
    }


class FaissProductIndex:
    def __init__(self):
        self.model: SentenceTransformer | None = None
        self.index: faiss.Index | None = None
        self.products: List[Dict[str, Any]] = []
        self.id_to_pos: Dict[int, int] = {}

    # ---------- bootstrap ----------

    def warmup(self, products: List[Dict[str, Any]] | None = None) -> bool:
        """Build the index. If `products` is empty, fall back to the
        hand-curated on-disk corpus (product_corpus.jsonl)."""
        if not products:
            products = load_product_corpus()
            log.info("Falling back to on-disk corpus (%d items)", len(products))
        if not products:
            log.warning("FAISS warmup skipped — empty product list")
            return False

        normalised = [_normalise(p) for p in products if p]
        normalised = [p for p in normalised if p["id"] is not None]

        log.info("Loading embedding model %s", config.EMBED_MODEL_NAME)
        self.model = SentenceTransformer(config.EMBED_MODEL_NAME)

        texts = [self._product_text(p) for p in normalised]
        log.info("Encoding %d product descriptions", len(texts))
        emb = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        emb = np.asarray(emb, dtype=np.float32)

        dim = emb.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(emb)

        self.products = normalised
        self.id_to_pos = {p["id"]: i for i, p in enumerate(normalised)}
        log.info("FAISS index ready (n=%d, dim=%d)", len(normalised), dim)
        return True

    @staticmethod
    def _product_text(p: Dict[str, Any]) -> str:
        """Rich text used for embedding: name, type, category, brand,
        description, keywords. Keywords carry strong semantic signal so
        they're included verbatim."""
        keywords = " ".join(p.get("keywords", []))
        return (
            f"{p['product_type'].upper()} | {p['name']} | "
            f"category: {p['category']} | by: {p['author']} | "
            f"price: {p['price']} | "
            f"{p['description']} | "
            f"keywords: {keywords}"
        )

    # ---------- search ----------

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if self.index is None or self.model is None or not query:
            return []
        q = self.model.encode([query], normalize_embeddings=True, show_progress_bar=False)
        scores, idxs = self.index.search(np.asarray(q, dtype=np.float32), top_k)

        results: List[Dict[str, Any]] = []
        for pos, score in zip(idxs[0].tolist(), scores[0].tolist()):
            if pos < 0 or pos >= len(self.products):
                continue
            p = self.products[pos]
            results.append({
                "product_id":   p["id"],
                "name":         p["name"],
                "price":        p["price"],
                "product_type": p["product_type"],
                "score":        float(score),
            })
        return results

    # ---------- score helper for hybrid ----------

    def score_for(self, query: str) -> Dict[int, float]:
        if self.index is None or self.model is None or not query:
            return {}
        q = self.model.encode([query], normalize_embeddings=True, show_progress_bar=False)
        scores, idxs = self.index.search(np.asarray(q, dtype=np.float32), len(self.products))
        return {
            self.products[pos]["id"]: float(score)
            for pos, score in zip(idxs[0].tolist(), scores[0].tolist())
            if 0 <= pos < len(self.products)
        }


faiss_index = FaissProductIndex()
