"""Generate synthetic user-behaviour sequences and train the LSTM.

Real production data does not exist (no event-tracking pipeline yet), so
we synthesise sequences with two patterns the model can learn:

  1. **Category affinity** — a user who has interacted with products in
     category C is likely to next pick another product in the same C.
  2. **Co-purchase signal** — items that appear together in the seed
     orders are linked: viewing one bumps the probability of the other.

This is honest about its purpose: it demonstrates the LSTM pipeline (data
→ tensor → train → save weights → infer) end-to-end, not state-of-the-art
recommendation accuracy."""
from __future__ import annotations

import logging
import random
from collections import defaultdict
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn

from .. import config
from .model import LSTMModel

log = logging.getLogger("ai-service.lstm.train")


def _seq_to_onehot(seq: Sequence[int], num_products: int, seq_length: int) -> np.ndarray:
    """Pad/truncate to seq_length, then one-hot encode each step."""
    seq = list(seq)[-seq_length:]
    while len(seq) < seq_length:
        seq.insert(0, 0)  # 0 = padding token (no real product uses index 0)
    arr = np.zeros((seq_length, num_products), dtype=np.float32)
    for t, prod_idx in enumerate(seq):
        if 0 <= prod_idx < num_products:
            arr[t, prod_idx] = 1.0
    return arr


def build_synthetic_dataset(
    products: List[Dict[str, Any]],
    orders: List[Dict[str, Any]],
    *,
    seq_length: int,
    num_examples: int = 600,
) -> Tuple[np.ndarray, np.ndarray, Dict[int, int], Dict[int, int]]:
    """Return (X, y, prod_id_to_idx, idx_to_prod_id).

    X has shape (num_examples, seq_length, num_products) — one-hot sequences.
    y has shape (num_examples,)                         — next-product index.
    """
    if not products:
        raise ValueError("Cannot train LSTM without product catalogue")

    # Map product ids → contiguous indices (0 reserved for padding).
    prod_id_to_idx: Dict[int, int] = {}
    idx_to_prod_id: Dict[int, int] = {}
    for i, p in enumerate(products, start=1):
        prod_id_to_idx[p["id"]] = i
        idx_to_prod_id[i] = p["id"]

    num_products = len(products) + 1  # +1 for padding

    # Index products by category to bias sampling toward category affinity.
    by_category: Dict[Any, List[int]] = defaultdict(list)
    for p in products:
        by_category[p.get("category_id")].append(prod_id_to_idx[p["id"]])

    # Co-purchase buckets from real orders.
    copurchase: Dict[int, List[int]] = defaultdict(list)
    for order in orders:
        items = order.get("items") or []
        idxs = [prod_id_to_idx[it["book_id"]] for it in items if it.get("book_id") in prod_id_to_idx]
        for a in idxs:
            for b in idxs:
                if a != b:
                    copurchase[a].append(b)

    rng = random.Random(42)
    X = np.zeros((num_examples, seq_length, num_products), dtype=np.float32)
    y = np.zeros((num_examples,), dtype=np.int64)

    cat_keys = list(by_category.keys())
    for n in range(num_examples):
        cat = rng.choice(cat_keys)
        pool = by_category[cat] or list(prod_id_to_idx.values())
        # Pick a recent context: 60% same-category, 40% co-purchase walk.
        if rng.random() < 0.6:
            ctx = [rng.choice(pool) for _ in range(seq_length)]
            target = rng.choice(pool)
        else:
            seed = rng.choice(pool)
            ctx = [seed]
            for _ in range(seq_length - 1):
                neighbours = copurchase.get(ctx[-1])
                ctx.append(rng.choice(neighbours) if neighbours else rng.choice(pool))
            neighbours = copurchase.get(ctx[-1])
            target = rng.choice(neighbours) if neighbours else rng.choice(pool)

        X[n] = _seq_to_onehot(ctx, num_products, seq_length)
        y[n] = target

    return X, y, prod_id_to_idx, idx_to_prod_id


def train(
    products: List[Dict[str, Any]],
    orders: List[Dict[str, Any]],
) -> Tuple[LSTMModel, Dict[int, int], Dict[int, int]]:
    """Train and persist the LSTM. Returns the model + id↔index maps."""
    X, y, prod_id_to_idx, idx_to_prod_id = build_synthetic_dataset(
        products, orders, seq_length=config.LSTM_SEQ_LENGTH
    )
    num_products = len(products) + 1

    device = torch.device("cpu")
    model = LSTMModel(num_products=num_products, hidden_dim=config.LSTM_HIDDEN_DIM).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=config.LSTM_LR)

    Xt = torch.from_numpy(X).to(device)
    yt = torch.from_numpy(y).to(device)

    model.train()
    for epoch in range(1, config.LSTM_EPOCHS + 1):
        optimizer.zero_grad()
        logits = model(Xt)
        loss = criterion(logits, yt)
        loss.backward()
        optimizer.step()
        if epoch % 5 == 0 or epoch == 1:
            log.info("LSTM epoch %02d/%d  loss=%.4f", epoch, config.LSTM_EPOCHS, loss.item())

    model.eval()
    torch.save(
        {
            "state_dict": model.state_dict(),
            "num_products": num_products,
            "hidden_dim": config.LSTM_HIDDEN_DIM,
            "seq_length": config.LSTM_SEQ_LENGTH,
            "prod_id_to_idx": prod_id_to_idx,
            "idx_to_prod_id": idx_to_prod_id,
        },
        config.LSTM_WEIGHTS_PATH,
    )
    log.info("Saved LSTM weights to %s", config.LSTM_WEIGHTS_PATH)
    return model, prod_id_to_idx, idx_to_prod_id
