"""Train the LSTM next-product predictor on the real on-disk dataset
`ai-service/data/user_behavior.csv`.

Pipeline:
  1. Load the behaviour log (load_user_behavior).
  2. Group events by user, ordered by timestamp.
  3. For each user sequence of length N ≥ seq_length+1, emit sliding-
     window samples X[t-seq_length : t-1] → y[t].
  4. One-hot encode each product id; train an LSTMModel (nn.LSTM + nn.Linear).
  5. Persist weights to data/lstm_weights.pt.

This is the canonical training entry point — synthetic generation has
been removed. If the behaviour CSV is missing or yields too few samples,
training is skipped and the LSTM contributes 0 to the hybrid score (the
graph + RAG components still work)."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn

from .. import config
from ..datasets import (
    behavior_sequences_per_user,
    load_product_corpus,
    load_user_behavior,
)
from .model import LSTMModel

log = logging.getLogger("ai-service.lstm.train")


def _seq_to_onehot(seq: Sequence[int], num_products: int, seq_length: int) -> np.ndarray:
    """Pad/truncate to seq_length, one-hot encode each step.
    Index 0 is reserved for the padding token."""
    seq = list(seq)[-seq_length:]
    while len(seq) < seq_length:
        seq.insert(0, 0)
    arr = np.zeros((seq_length, num_products), dtype=np.float32)
    for t, prod_idx in enumerate(seq):
        if 0 <= prod_idx < num_products:
            arr[t, prod_idx] = 1.0
    return arr


def build_dataset_from_behavior(
    products: List[Dict[str, Any]],
    behavior_rows: List[Dict[str, Any]],
    *,
    seq_length: int,
) -> Tuple[np.ndarray, np.ndarray, Dict[int, int], Dict[int, int]]:
    """Build (X, y, prod_id_to_idx, idx_to_prod_id) from the real
    user-behaviour log using a sliding window.

    Each user's chronologically sorted product sequence yields
    (len(seq) - seq_length) training samples.
    """
    if not products:
        raise ValueError("Cannot train LSTM without product catalogue")
    if not behavior_rows:
        raise ValueError("Cannot train LSTM without behaviour log")

    # Contiguous indices, 0 reserved for padding. Accept both REST shape
    # ({id}) and corpus shape (post-normalisation also {id}).
    prod_id_to_idx: Dict[int, int] = {}
    idx_to_prod_id: Dict[int, int] = {}
    for i, p in enumerate(products, start=1):
        pid = p.get("id", p.get("product_id"))
        if pid is None:
            continue
        prod_id_to_idx[int(pid)] = i
        idx_to_prod_id[i] = int(pid)
    num_products = len(products) + 1

    seqs = behavior_sequences_per_user(behavior_rows)

    X_list: List[np.ndarray] = []
    y_list: List[int] = []
    for uid, seq in seqs.items():
        idx_seq = [prod_id_to_idx.get(pid, 0) for pid in seq]
        idx_seq = [i for i in idx_seq if i != 0]  # drop unknown products
        if len(idx_seq) < seq_length + 1:
            # Pad-then-predict: even a short sequence can produce one sample.
            target = idx_seq[-1]
            ctx = idx_seq[:-1]
            X_list.append(_seq_to_onehot(ctx, num_products, seq_length))
            y_list.append(target)
            continue
        # Sliding window
        for t in range(seq_length, len(idx_seq)):
            ctx = idx_seq[t - seq_length : t]
            target = idx_seq[t]
            X_list.append(_seq_to_onehot(ctx, num_products, seq_length))
            y_list.append(target)

    if not X_list:
        raise ValueError("Behaviour log yielded zero training samples")

    X = np.stack(X_list, axis=0)
    y = np.asarray(y_list, dtype=np.int64)
    log.info("LSTM training set: %d samples, %d users, %d products",
             len(X_list), len(seqs), len(products))
    return X, y, prod_id_to_idx, idx_to_prod_id


def train(
    products: List[Dict[str, Any]] | None = None,
    orders: List[Dict[str, Any]] | None = None,    # kept for backward compat — ignored
) -> Tuple[LSTMModel, Dict[int, int], Dict[int, int]]:
    """Train and persist the LSTM.

    `products` is preferred from caller (typically fetched from
    product-service); falls back to the on-disk product_corpus.jsonl
    if not provided.  `orders` is accepted for backward compatibility
    with earlier call sites but no longer used — sequences come from
    user_behavior.csv now.
    """
    if not products:
        products = load_product_corpus()

    behavior_rows = load_user_behavior()
    X, y, prod_id_to_idx, idx_to_prod_id = build_dataset_from_behavior(
        products, behavior_rows, seq_length=config.LSTM_SEQ_LENGTH
    )
    num_products = len(products) + 1

    device = torch.device("cpu")
    model = LSTMModel(num_products=num_products, hidden_dim=config.LSTM_HIDDEN_DIM).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=config.LSTM_LR)

    # Mini-batch training: one-hot tensors are large (N x seq_len x num_products),
    # so a single full-batch forward would allocate gigabytes of activations.
    # torch.from_numpy shares memory with X, and we slice per batch so only one
    # batch worth of one-hot is materialised on the autograd tape at a time.
    Xt = torch.from_numpy(X)
    yt = torch.from_numpy(y)
    n_samples = Xt.shape[0]
    batch_size = config.LSTM_BATCH_SIZE

    model.train()
    for epoch in range(1, config.LSTM_EPOCHS + 1):
        perm = torch.randperm(n_samples)
        epoch_loss = 0.0
        n_batches = 0
        for start in range(0, n_samples, batch_size):
            idx = perm[start:start + batch_size]
            xb = Xt[idx].to(device)
            yb = yt[idx].to(device)
            optimizer.zero_grad()
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            n_batches += 1
        if epoch % 5 == 0 or epoch == 1:
            log.info("LSTM epoch %02d/%d  loss=%.4f",
                     epoch, config.LSTM_EPOCHS, epoch_loss / max(n_batches, 1))

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


def main() -> int:
    """Offline training entry point (`make train-ai` → `python -m app.lstm.train`).

    Loads the on-disk product corpus + behaviour log, trains the LSTM, and
    persists weights to config.LSTM_WEIGHTS_PATH. Returns non-zero if no
    weights were produced so callers/CI can detect failure."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    train()
    if not config.LSTM_WEIGHTS_PATH.exists():
        log.error("Training finished but no weights file at %s", config.LSTM_WEIGHTS_PATH)
        return 1
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
