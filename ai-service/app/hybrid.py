"""Hybrid recommendation scoring.

Per the SoAD thesis Ch.3.7:
    final_score = w1 * lstm + w2 * graph + w3 * rag

Where each component contributes a normalised score in [0, 1] per
candidate product. We min-max normalise within each source so that one
component cannot dominate just because it uses larger raw values."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import config
from .graph.queries import graph_recommend, user_history
from .lstm.inference import lstm_inference
from .rag.index import faiss_index


def _normalise(scores: Dict[int, float]) -> Dict[int, float]:
    if not scores:
        return {}
    values = list(scores.values())
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        return {k: 1.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


def hybrid_recommend(
    user_id: int,
    *,
    query: Optional[str] = None,
    top_k: int = 10,
    weights: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """Combine LSTM + Graph + RAG scores into a single ranked list.

    Args:
        user_id:  the customer id (resolved against Neo4j BOUGHT history).
        query:    optional natural-language hint for the RAG component.
                  If absent, RAG contributes 0 (LSTM + Graph only).
        top_k:    number of products to return.
        weights:  override the env-var defaults (w_lstm/w_graph/w_rag).
    """
    w = weights or {"lstm": config.W_LSTM, "graph": config.W_GRAPH, "rag": config.W_RAG}

    # ---- 1. Graph component ----
    graph_rows = graph_recommend(user_id, top_k=top_k * 4)
    graph_scores = {int(r["product_id"]): float(r["score"]) for r in graph_rows}
    name_lookup = {int(r["product_id"]): r.get("name", "") for r in graph_rows}

    # ---- 2. LSTM component ----
    history = user_history(user_id, limit=config.LSTM_SEQ_LENGTH)
    lstm_rows = lstm_inference.predict(history, top_k=top_k * 4)
    lstm_scores = {int(r["product_id"]): float(r["score"]) for r in lstm_rows}

    # ---- 3. RAG component (only if a query is provided) ----
    rag_scores = faiss_index.score_for(query) if query else {}

    # ---- normalise + combine ----
    g, l, r = _normalise(graph_scores), _normalise(lstm_scores), _normalise(rag_scores)
    candidates = set(g) | set(l) | set(r)
    blended: Dict[int, float] = {}
    for pid in candidates:
        blended[pid] = (
            w["lstm"]  * l.get(pid, 0.0) +
            w["graph"] * g.get(pid, 0.0) +
            w["rag"]   * r.get(pid, 0.0)
        )

    # Pull product names from FAISS catalogue if missing.
    for pid in candidates:
        if pid not in name_lookup:
            pos = faiss_index.id_to_pos.get(pid)
            if pos is not None:
                name_lookup[pid] = faiss_index.products[pos].get("name", "")

    ranked = sorted(blended.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
    return [
        {
            "product_id": pid,
            "name": name_lookup.get(pid, ""),
            "score": round(score, 4),
            "components": {
                "lstm":  round(l.get(pid, 0.0), 4),
                "graph": round(g.get(pid, 0.0), 4),
                "rag":   round(r.get(pid, 0.0), 4),
            },
        }
        for pid, score in ranked
    ]
