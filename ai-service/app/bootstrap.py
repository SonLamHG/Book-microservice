"""Startup helpers.

Each AI component now has an on-disk dataset as its primary input
(see ai-service/data/). The bootstrap step still tries product-service
and order-service first so the runtime view stays fresh, but every
component can fall back to the on-disk source if the REST call fails."""
import logging
import time
from typing import List, Dict, Any

import requests

from . import config
from .datasets import load_product_corpus

log = logging.getLogger("ai-service.bootstrap")


def _normalize(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """product-service returns {"id": ...}; product_corpus.jsonl uses
    "product_id". Make every entry expose BOTH keys so downstream
    modules (LSTM train, Neo4j seed, FAISS index) don't have to branch."""
    for p in products:
        if "product_id" not in p and "id" in p:
            p["product_id"] = p["id"]
        elif "id" not in p and "product_id" in p:
            p["id"] = p["product_id"]
    return products


def fetch_products(retries: int = 12, delay: float = 5.0) -> List[Dict[str, Any]]:
    """Try product-service first; on failure fall back to the
    hand-curated product_corpus.jsonl committed in the repo."""
    url = f"{config.PRODUCT_SERVICE_URL}/products/"
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                products = r.json()
                log.info("Fetched %d products from product-service", len(products))
                return _normalize(products)
        except requests.RequestException as exc:
            log.warning("product-service unreachable (attempt %d/%d): %s", attempt, retries, exc)
        time.sleep(delay)
    log.error("Could not reach product-service after %d attempts; using on-disk corpus",
              retries)
    return _normalize(load_product_corpus())


def fetch_orders() -> List[Dict[str, Any]]:
    """Kept for compatibility with earlier call sites. Orders are no
    longer the source of training signal — that role belongs to
    user_behavior.csv now — but other callers (e.g. main.py logging)
    still want a list."""
    try:
        r = requests.get(f"{config.ORDER_SERVICE_URL}/orders/", timeout=5)
        if r.status_code == 200:
            orders = r.json()
            log.info("Fetched %d orders from order-service", len(orders))
            return orders
    except requests.RequestException as exc:
        log.warning("Could not fetch orders: %s", exc)
    return []
