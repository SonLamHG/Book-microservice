"""GET /recommend?user_id=&query=&top_k= endpoint."""
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..hybrid import hybrid_recommend

router = APIRouter()


class ScoreComponents(BaseModel):
    lstm: float
    graph: float
    rag: float


class Recommendation(BaseModel):
    product_id: int
    name: str
    score: float
    components: ScoreComponents


class RecommendResponse(BaseModel):
    user_id: int
    query: Optional[str]
    recommendations: list[Recommendation]


@router.get("/recommend", response_model=RecommendResponse)
def recommend(
    user_id: int = Query(..., ge=1, description="Customer id"),
    query: Optional[str] = Query(None, description="Optional NL hint for the RAG component"),
    top_k: int = Query(10, ge=1, le=50),
    w_lstm:  Optional[float] = Query(None, ge=0.0, le=1.0, description="Override LSTM weight"),
    w_graph: Optional[float] = Query(None, ge=0.0, le=1.0, description="Override Graph weight"),
    w_rag:   Optional[float] = Query(None, ge=0.0, le=1.0, description="Override RAG weight"),
):
    weights = None
    if any(w is not None for w in (w_lstm, w_graph, w_rag)):
        from .. import config
        weights = {
            "lstm":  w_lstm  if w_lstm  is not None else config.W_LSTM,
            "graph": w_graph if w_graph is not None else config.W_GRAPH,
            "rag":   w_rag   if w_rag   is not None else config.W_RAG,
        }
    items = hybrid_recommend(user_id=user_id, query=query, top_k=top_k, weights=weights)
    return {
        "user_id": user_id,
        "query": query,
        "recommendations": items,
    }
