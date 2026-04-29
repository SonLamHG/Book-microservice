"""POST /chatbot endpoint — RAG retrieve + LLM generate."""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..rag.chatbot import answer

router = APIRouter()


class ChatbotRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(5, ge=1, le=20)


class RetrievedProduct(BaseModel):
    product_id: int
    name: str
    price: float
    product_type: str
    score: float


class ChatbotResponse(BaseModel):
    query: str
    response: str
    retrieved: List[RetrievedProduct]
    llm_used: bool


@router.post("/chatbot", response_model=ChatbotResponse)
def chatbot(req: ChatbotRequest):
    return answer(req.query, top_k=req.top_k)
