"""ai-service — FastAPI entry point.

Brings up:
  - LSTM model (loaded from disk or trained on synthetic data)
  - Neo4j Knowledge Graph (seeded from product-service + order-service)
  - FAISS RAG index (built from product descriptions)
  - Hybrid recommender (blends all three)

Endpoints:
  GET  /health
  GET  /recommend?user_id=&query=&top_k=
  POST /chatbot              { "query": "...", "top_k": 5 }
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import config
from app.bootstrap import fetch_orders, fetch_products
from app.graph.driver import close_driver
from app.graph.seed import seed_graph
from app.lstm.inference import lstm_inference
from app.rag.index import faiss_index
from app.routes.chatbot import router as chatbot_router
from app.routes.recommend import router as recommend_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("ai-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("=== ai-service warming up ===")

    products = fetch_products()
    orders = fetch_orders()

    if config.LSTM_TRAIN_AT_STARTUP:
        try:
            lstm_inference.warmup(products, orders, force_train=False)
        except Exception as exc:
            log.exception("LSTM warmup failed: %s", exc)

    if config.SEED_GRAPH_AT_STARTUP:
        try:
            seed_graph(products, orders)
        except Exception as exc:
            log.exception("Graph seed failed: %s", exc)

    if config.BUILD_FAISS_AT_STARTUP:
        try:
            faiss_index.warmup(products)
        except Exception as exc:
            log.exception("FAISS warmup failed: %s", exc)

    log.info("=== ai-service ready ===")
    yield

    log.info("=== ai-service shutting down ===")
    close_driver()


app = FastAPI(
    title="ai-service",
    description="LSTM + Neo4j Knowledge Graph + FAISS RAG hybrid recommender for the Bookstore Microservice platform.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(recommend_router, tags=["recommend"])
app.include_router(chatbot_router, tags=["chatbot"])


@app.get("/health", tags=["health"])
def health_check():
    return {
        "status": "healthy",
        "service": "ai-service",
        "lstm_loaded": lstm_inference.model is not None,
        "faiss_indexed": faiss_index.index is not None,
        "products_in_index": len(faiss_index.products),
    }
