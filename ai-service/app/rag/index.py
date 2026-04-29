"""FAISS in-memory vector index over product descriptions.

Each product is embedded with sentence-transformers `all-MiniLM-L6-v2`
(384-dim) and stored in an `IndexFlatIP` on cosine-normalised vectors,
which is equivalent to cosine similarity search."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from .. import config

log = logging.getLogger("ai-service.rag.index")


class FaissProductIndex:
    def __init__(self):
        self.model: SentenceTransformer | None = None
        self.index: faiss.Index | None = None
        self.products: List[Dict[str, Any]] = []
        self.id_to_pos: Dict[int, int] = {}

    # ---------- bootstrap ----------

    def warmup(self, products: List[Dict[str, Any]]) -> bool:
        if not products:
            log.warning("FAISS warmup skipped — empty product list")
            return False

        log.info("Loading embedding model %s", config.EMBED_MODEL_NAME)
        self.model = SentenceTransformer(config.EMBED_MODEL_NAME)

        texts = [self._product_text(p) for p in products]
        log.info("Encoding %d product descriptions", len(texts))
        emb = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        emb = np.asarray(emb, dtype=np.float32)

        dim = emb.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(emb)

        self.products = products
        self.id_to_pos = {int(p["id"]): i for i, p in enumerate(products)}
        log.info("FAISS index ready (n=%d, dim=%d)", len(products), dim)
        return True

    @staticmethod
    def _product_text(p: Dict[str, Any]) -> str:
        ptype = p.get("product_type", "product")
        return (
            f"{ptype.upper()} | {p.get('name', '')} | "
            f"{p.get('description', '')} | "
            f"price={p.get('price', 0)}"
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
                "product_id": int(p["id"]),
                "name": p.get("name", ""),
                "price": float(p.get("price", 0)),
                "product_type": p.get("product_type", "book"),
                "score": float(score),
            })
        return results

    # ---------- score helper for hybrid ----------

    def score_for(self, query: str) -> Dict[int, float]:
        """Return a score map { product_id -> cosine_similarity } over the
        full catalogue. Used by hybrid scoring as the RAG component."""
        if self.index is None or self.model is None or not query:
            return {}
        q = self.model.encode([query], normalize_embeddings=True, show_progress_bar=False)
        scores, idxs = self.index.search(np.asarray(q, dtype=np.float32), len(self.products))
        return {
            int(self.products[pos]["id"]): float(score)
            for pos, score in zip(idxs[0].tolist(), scores[0].tolist())
            if 0 <= pos < len(self.products)
        }


faiss_index = FaissProductIndex()
