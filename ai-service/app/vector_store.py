from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass

import numpy as np

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover - optional runtime dependency
    faiss = None


@dataclass
class VectorSearchResult:
    product_id: int
    score: float
    reason: str


def _normalize_vi(text: str) -> str:
    text = (text or "").lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokenize(text: str) -> list[str]:
    norm = _normalize_vi(text)
    return [tok for tok in norm.split(" ") if tok]


class VectorProductStore:
    """
    Lightweight vector store for product semantic retrieval.
    Uses FAISS when available; falls back to NumPy cosine search.
    """

    def __init__(self, dim: int = 384):
        self.dim = dim
        self._index = None
        self._ids: list[int] = []
        self._matrix: np.ndarray | None = None
        self._signature = ""

    @property
    def faiss_enabled(self) -> bool:
        return faiss is not None

    def _text_for_product(self, p: dict) -> str:
        category = (p.get("category") or {}).get("name") or ""
        name = str(p.get("name") or "")
        desc = str(p.get("description") or "")
        return f"{name}. {desc}. Danh muc {category}."

    def _signature_for_products(self, products: list[dict]) -> str:
        # Minimal deterministic signature to avoid rebuilding on every query.
        base = "|".join(
            f"{int(p.get('id', 0))}:{str(p.get('name', ''))}:{str(p.get('updated_at', ''))}"
            for p in sorted(products, key=lambda x: int(x.get("id", 0)))
        )
        return hashlib.sha1(base.encode("utf-8")).hexdigest()

    def _embed(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        tokens = _tokenize(text)
        if not tokens:
            return vec

        for token in tokens:
            # Two hashed projections per token for sparse semantic signal.
            h1 = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            h2 = int(hashlib.sha1(token.encode("utf-8")).hexdigest(), 16)
            i1 = h1 % self.dim
            i2 = h2 % self.dim
            vec[i1] += 1.0
            vec[i2] += 0.5

        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        return vec

    def _build_embeddings(self, products: list[dict]) -> np.ndarray:
        emb = np.vstack([self._embed(self._text_for_product(p)) for p in products]).astype(np.float32)
        return emb

    def ensure_index(self, products: list[dict]) -> None:
        sig = self._signature_for_products(products)
        if sig == self._signature and self._matrix is not None:
            return

        if not products:
            self._index = None
            self._matrix = None
            self._ids = []
            self._signature = sig
            return

        self._ids = [int(p["id"]) for p in products]
        self._matrix = self._build_embeddings(products)
        self._signature = sig

        if faiss is not None:
            idx = faiss.IndexFlatIP(self.dim)
            idx.add(self._matrix)
            self._index = idx
        else:
            self._index = None

    def search(
        self,
        *,
        query: str,
        products: list[dict],
        top_k: int = 10,
        category: str | None = None,
        budget: float | None = None,
    ) -> list[VectorSearchResult]:
        if not query.strip():
            return []

        self.ensure_index(products)
        if self._matrix is None or not self._ids:
            return []

        qv = self._embed(query).reshape(1, -1)

        if self._index is not None:
            k = min(max(top_k * 3, top_k), len(self._ids))
            scores, indices = self._index.search(qv, k)
            raw = [(int(self._ids[i]), float(s)) for i, s in zip(indices[0], scores[0]) if i >= 0]
        else:
            sims = (self._matrix @ qv.T).reshape(-1)
            order = np.argsort(-sims)[: min(max(top_k * 3, top_k), len(self._ids))]
            raw = [(int(self._ids[i]), float(sims[i])) for i in order]

        by_id = {int(p["id"]): p for p in products if "id" in p}
        q_tokens = set(_tokenize(query))
        out: list[VectorSearchResult] = []

        for pid, score in raw:
            p = by_id.get(pid)
            if not p:
                continue
            p_cat = ((p.get("category") or {}).get("slug") or "").strip()
            p_price = p.get("price")

            if category and p_cat != category:
                continue
            if budget is not None and p_price is not None and float(p_price) > budget:
                continue

            name_tokens = set(_tokenize(str(p.get("name") or "")))
            token_overlap = len(q_tokens & name_tokens)
            rerank = score + (0.15 * token_overlap)
            reason = "khớp ngữ nghĩa từ vector search"
            if token_overlap > 0:
                reason = "khớp ngữ nghĩa + từ khóa trong tên"
            out.append(VectorSearchResult(product_id=pid, score=float(rerank), reason=reason))

            if len(out) >= top_k:
                break

        return out
