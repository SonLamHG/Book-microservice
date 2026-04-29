"""Startup helpers. The service waits for backend dependencies to come up
(book-service for product list, neo4j for graph) before warming up the
LSTM, FAISS index and Neo4j seed graph."""
import logging
import time
from typing import List, Dict, Any

import requests

from . import config

log = logging.getLogger("ai-service.bootstrap")


def fetch_products(retries: int = 12, delay: float = 5.0) -> List[Dict[str, Any]]:
    """Pull the full product catalogue from book-service. We retry because
    book-service may not be ready yet during cold container start."""
    url = f"{config.BOOK_SERVICE_URL}/products/"
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                products = r.json()
                log.info("Fetched %d products from book-service", len(products))
                return products
        except requests.RequestException as exc:
            log.warning("book-service unreachable (attempt %d/%d): %s", attempt, retries, exc)
        time.sleep(delay)
    log.error("Could not reach book-service after %d attempts; returning empty catalogue", retries)
    return []


def fetch_orders() -> List[Dict[str, Any]]:
    """Pull existing orders so the LSTM and Neo4j see real co-purchase signal.
    Returns a flat list of orders, each with `customer_id` and `items`."""
    try:
        r = requests.get(f"{config.ORDER_SERVICE_URL}/orders/", timeout=5)
        if r.status_code == 200:
            orders = r.json()
            log.info("Fetched %d orders from order-service", len(orders))
            return orders
    except requests.RequestException as exc:
        log.warning("Could not fetch orders: %s", exc)
    return []
