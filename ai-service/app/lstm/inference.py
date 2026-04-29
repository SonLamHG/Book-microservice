"""Stateful inference wrapper around the trained LSTMModel."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Sequence

import numpy as np
import torch

from .. import config
from .model import LSTMModel
from .train import train, _seq_to_onehot

log = logging.getLogger("ai-service.lstm.inference")


class LSTMInference:
    def __init__(self):
        self.model: LSTMModel | None = None
        self.num_products: int = 0
        self.seq_length: int = config.LSTM_SEQ_LENGTH
        self.prod_id_to_idx: Dict[int, int] = {}
        self.idx_to_prod_id: Dict[int, int] = {}

    # ---------- bootstrap ----------

    def warmup(
        self,
        products: List[Dict[str, Any]],
        orders: List[Dict[str, Any]],
        force_train: bool = False,
    ) -> bool:
        """Load saved weights, or train a fresh model if missing/forced.

        Returns True if the model is ready, False if no products were
        available (in which case the LSTM step contributes 0 to the
        hybrid score)."""
        if not products:
            log.warning("LSTM warmup skipped — no products in catalogue")
            return False

        if config.LSTM_WEIGHTS_PATH.exists() and not force_train:
            try:
                checkpoint = torch.load(config.LSTM_WEIGHTS_PATH, map_location="cpu", weights_only=False)
                # If catalogue size changed since last train, retrain.
                if checkpoint["num_products"] != len(products) + 1:
                    log.info("Catalogue size changed; retraining LSTM")
                    return self._train(products, orders)
                self.num_products = checkpoint["num_products"]
                self.seq_length = checkpoint["seq_length"]
                self.prod_id_to_idx = checkpoint["prod_id_to_idx"]
                self.idx_to_prod_id = checkpoint["idx_to_prod_id"]
                self.model = LSTMModel(self.num_products, checkpoint["hidden_dim"])
                self.model.load_state_dict(checkpoint["state_dict"])
                self.model.eval()
                log.info("Loaded LSTM weights for %d products", self.num_products - 1)
                return True
            except Exception as exc:
                log.warning("Failed to load LSTM weights (%s); retraining", exc)

        return self._train(products, orders)

    def _train(self, products, orders) -> bool:
        model, p2i, i2p = train(products, orders)
        self.model = model
        self.num_products = len(products) + 1
        self.prod_id_to_idx = p2i
        self.idx_to_prod_id = i2p
        return True

    # ---------- prediction ----------

    def predict(self, recent_product_ids: Sequence[int], top_k: int = 10) -> List[Dict[str, Any]]:
        """Given the user's last interactions, return [{product_id, score}, ...].

        If the model hasn't been warmed up or the user has no history, an
        empty list is returned — callers should treat that as a 0
        contribution to the hybrid score."""
        if self.model is None or not recent_product_ids:
            return []

        ctx_idx = [self.prod_id_to_idx.get(pid, 0) for pid in recent_product_ids]
        x = _seq_to_onehot(ctx_idx, self.num_products, self.seq_length)
        with torch.no_grad():
            logits = self.model(torch.from_numpy(x).unsqueeze(0))
            probs = torch.softmax(logits, dim=-1).squeeze(0).numpy()

        ranked = np.argsort(-probs)
        seen = set(ctx_idx)
        results: List[Dict[str, Any]] = []
        for idx in ranked:
            idx = int(idx)
            if idx == 0 or idx in seen:
                continue
            pid = self.idx_to_prod_id.get(idx)
            if pid is None:
                continue
            results.append({"product_id": pid, "score": float(probs[idx])})
            if len(results) >= top_k:
                break
        return results


# Singleton accessed by FastAPI lifespan + routes.
lstm_inference = LSTMInference()
