"""Thin wrapper around neo4j.GraphDatabase that retries until the database
accepts connections (Neo4j takes ~10s to come up in docker-compose)."""
import logging
import time
from typing import Optional

from neo4j import Driver, GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

from .. import config

log = logging.getLogger("ai-service.graph")

_driver: Optional[Driver] = None


def get_driver(retries: int = 24, delay: float = 5.0) -> Optional[Driver]:
    """Return a singleton Bolt driver, blocking until Neo4j is reachable."""
    global _driver
    if _driver is not None:
        return _driver

    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            drv = GraphDatabase.driver(
                config.NEO4J_URI,
                auth=(config.NEO4J_USER, config.NEO4J_PASSWORD),
            )
            drv.verify_connectivity()
            _driver = drv
            log.info("Connected to Neo4j at %s", config.NEO4J_URI)
            return _driver
        except (ServiceUnavailable, AuthError, OSError) as exc:
            last_exc = exc
            log.warning("Neo4j unavailable (attempt %d/%d): %s", attempt, retries, exc)
            time.sleep(delay)

    log.error("Could not connect to Neo4j after %d attempts: %s", retries, last_exc)
    return None


def close_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
