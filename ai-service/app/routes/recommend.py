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
):
    items = hybrid_recommend(user_id=user_id, query=query, top_k=top_k)
    return {
        "user_id": user_id,
        "query": query,
        "recommendations": items,
    }
