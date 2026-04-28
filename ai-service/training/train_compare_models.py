import json
import os
import random
from dataclasses import dataclass
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from torch.utils.data import DataLoader, Dataset

SEED = 42
SEQ_LEN = 3
EPOCHS = 16
BATCH_SIZE = 64
LR = 1e-3

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data_user500.csv"
ARTIFACT_DIR = ROOT / "artifacts"
PLOTS_DIR = ROOT / "plots"
MODEL_DIR = ROOT / "models"
for p in [ARTIFACT_DIR, PLOTS_DIR, MODEL_DIR]:
    p.mkdir(parents=True, exist_ok=True)

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)


@dataclass
class Encoders:
    product2idx: dict
    idx2product: dict
    action2idx: dict


class SequenceDataset(Dataset):
    def __init__(self, x_prod, x_act, y):
        self.x_prod = torch.tensor(x_prod, dtype=torch.long)
        self.x_act = torch.tensor(x_act, dtype=torch.long)
        self.y = torch.tensor(y, dtype=torch.long)

    def __len__(self):
        return len(self.y)

    def __getitem__(self, idx):
        return self.x_prod[idx], self.x_act[idx], self.y[idx]


class BaseSeqModel(nn.Module):
    def __init__(self, num_products, num_actions, product_emb_dim=16, action_emb_dim=8, hidden_dim=64):
        super().__init__()
        self.product_emb = nn.Embedding(num_products, product_emb_dim)
        self.action_emb = nn.Embedding(num_actions, action_emb_dim)
        self.input_dim = product_emb_dim + action_emb_dim
        self.hidden_dim = hidden_dim
        self.fc = nn.Linear(hidden_dim, num_products)

    def merge_inputs(self, x_prod, x_act):
        p = self.product_emb(x_prod)
        a = self.action_emb(x_act)
        return torch.cat([p, a], dim=-1)


class RNNModel(BaseSeqModel):
    def __init__(self, num_products, num_actions):
        super().__init__(num_products, num_actions)
        self.rnn = nn.RNN(self.input_dim, self.hidden_dim, batch_first=True)

    def forward(self, x_prod, x_act):
        x = self.merge_inputs(x_prod, x_act)
        out, _ = self.rnn(x)
        return self.fc(out[:, -1, :])


class LSTMModel(BaseSeqModel):
    def __init__(self, num_products, num_actions):
        super().__init__(num_products, num_actions)
        self.lstm = nn.LSTM(self.input_dim, self.hidden_dim, batch_first=True)

    def forward(self, x_prod, x_act):
        x = self.merge_inputs(x_prod, x_act)
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])


class BiLSTMModel(BaseSeqModel):
    def __init__(self, num_products, num_actions):
        super().__init__(num_products, num_actions)
        self.lstm = nn.LSTM(self.input_dim, self.hidden_dim, batch_first=True, bidirectional=True)
        self.fc = nn.Linear(self.hidden_dim * 2, self.fc.out_features)

    def forward(self, x_prod, x_act):
        x = self.merge_inputs(x_prod, x_act)
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])


def load_data(path: Path):
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values(["user_id", "timestamp"]).reset_index(drop=True)
    return df


def build_encoders(df: pd.DataFrame) -> Encoders:
    products = sorted(df["product_id"].unique().tolist())
    actions = sorted(df["action"].unique().tolist())
    product2idx = {p: i for i, p in enumerate(products)}
    idx2product = {i: p for p, i in product2idx.items()}
    action2idx = {a: i for i, a in enumerate(actions)}
    return Encoders(product2idx=product2idx, idx2product=idx2product, action2idx=action2idx)


def build_samples(df: pd.DataFrame, enc: Encoders, seq_len=SEQ_LEN):
    x_prod, x_act, y, ts = [], [], [], []

    for _, g in df.groupby("user_id", sort=False):
        g = g.sort_values("timestamp")
        p_seq = [enc.product2idx[v] for v in g["product_id"].tolist()]
        a_seq = [enc.action2idx[v] for v in g["action"].tolist()]
        t_seq = g["timestamp"].tolist()

        if len(g) <= seq_len:
            continue

        for i in range(seq_len, len(g)):
            x_prod.append(p_seq[i - seq_len : i])
            x_act.append(a_seq[i - seq_len : i])
            y.append(p_seq[i])
            ts.append(t_seq[i])

    arr_ts = pd.to_datetime(ts, utc=True)
    return np.array(x_prod), np.array(x_act), np.array(y), np.array(arr_ts)


def split_by_time(x_prod, x_act, y, ts):
    idx = np.argsort(ts)
    x_prod, x_act, y = x_prod[idx], x_act[idx], y[idx]

    n = len(y)
    n_train = int(n * 0.7)
    n_val = int(n * 0.15)

    train = (x_prod[:n_train], x_act[:n_train], y[:n_train])
    val = (x_prod[n_train : n_train + n_val], x_act[n_train : n_train + n_val], y[n_train : n_train + n_val])
    test = (x_prod[n_train + n_val :], x_act[n_train + n_val :], y[n_train + n_val :])
    return train, val, test


def make_loader(data, shuffle=False):
    ds = SequenceDataset(*data)
    return DataLoader(ds, batch_size=BATCH_SIZE, shuffle=shuffle)


def evaluate(model, loader, criterion, device):
    model.eval()
    losses = []
    ys, preds, top3_ok = [], [], []

    with torch.no_grad():
        for x_prod, x_act, y in loader:
            x_prod, x_act, y = x_prod.to(device), x_act.to(device), y.to(device)
            logits = model(x_prod, x_act)
            loss = criterion(logits, y)
            losses.append(loss.item())

            prob = torch.softmax(logits, dim=1)
            pred = torch.argmax(prob, dim=1)
            top3 = torch.topk(prob, k=min(3, prob.shape[1]), dim=1).indices
            hit3 = (top3 == y.unsqueeze(1)).any(dim=1)

            ys.extend(y.cpu().numpy().tolist())
            preds.extend(pred.cpu().numpy().tolist())
            top3_ok.extend(hit3.cpu().numpy().astype(int).tolist())

    metrics = {
        "loss": float(np.mean(losses)) if losses else 0.0,
        "accuracy": float(accuracy_score(ys, preds)) if ys else 0.0,
        "macro_f1": float(f1_score(ys, preds, average="macro", zero_division=0)) if ys else 0.0,
        "recall_at_3": float(np.mean(top3_ok)) if top3_ok else 0.0,
        "y_true": ys,
        "y_pred": preds,
    }
    return metrics


def train_model(name, model, train_loader, val_loader, test_loader, device, num_products):
    model.to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)

    history = {
        "train_loss": [],
        "val_loss": [],
        "train_acc": [],
        "val_acc": [],
    }

    best_val_f1 = -1.0
    best_state = None

    for _ in range(EPOCHS):
        model.train()
        batch_losses = []
        ys, preds = [], []

        for x_prod, x_act, y in train_loader:
            x_prod, x_act, y = x_prod.to(device), x_act.to(device), y.to(device)
            optimizer.zero_grad()
            logits = model(x_prod, x_act)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()

            batch_losses.append(loss.item())
            pred = torch.argmax(logits, dim=1)
            ys.extend(y.detach().cpu().numpy().tolist())
            preds.extend(pred.detach().cpu().numpy().tolist())

        train_loss = float(np.mean(batch_losses)) if batch_losses else 0.0
        train_acc = float(accuracy_score(ys, preds)) if ys else 0.0

        val_metrics = evaluate(model, val_loader, criterion, device)

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_metrics["loss"])
        history["train_acc"].append(train_acc)
        history["val_acc"].append(val_metrics["accuracy"])

        if val_metrics["macro_f1"] > best_val_f1:
            best_val_f1 = val_metrics["macro_f1"]
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)

    test_metrics = evaluate(model, test_loader, criterion, device)

    cm = confusion_matrix(test_metrics["y_true"], test_metrics["y_pred"], labels=list(range(num_products)))
    cm_path = PLOTS_DIR / f"cm_{name}.png"
    plt.figure(figsize=(7, 6))
    plt.imshow(cm, cmap="Blues")
    plt.title(f"Confusion Matrix - {name}")
    plt.colorbar()
    threshold = cm.max() / 2 if cm.size else 0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            val = int(cm[i, j])
            color = "white" if val > threshold else "black"
            plt.text(j, i, str(val), ha="center", va="center", color=color, fontsize=8)
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.tight_layout()
    plt.savefig(cm_path)
    plt.close()

    model_path = MODEL_DIR / f"{name.lower()}.pt"
    torch.save(model.state_dict(), model_path)

    result = {
        "model": name,
        "history": history,
        "val_best_macro_f1": float(best_val_f1),
        "test": {
            "loss": test_metrics["loss"],
            "accuracy": test_metrics["accuracy"],
            "macro_f1": test_metrics["macro_f1"],
            "recall_at_3": test_metrics["recall_at_3"],
        },
        "artifacts": {
            "model_path": str(model_path),
            "confusion_matrix": str(cm_path),
        },
    }
    return result


def plot_curves(all_results):
    plt.figure(figsize=(11, 5))
    for r in all_results:
        plt.plot(r["history"]["train_loss"], label=f"{r['model']} train")
        plt.plot(r["history"]["val_loss"], linestyle="--", label=f"{r['model']} val")
    plt.title("Loss per Epoch")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "loss_curves.png")
    plt.close()

    plt.figure(figsize=(11, 5))
    for r in all_results:
        plt.plot(r["history"]["train_acc"], label=f"{r['model']} train")
        plt.plot(r["history"]["val_acc"], linestyle="--", label=f"{r['model']} val")
    plt.title("Accuracy per Epoch")
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy")
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "accuracy_curves.png")
    plt.close()


def plot_metric_bars(all_results):
    models = [r["model"] for r in all_results]
    acc = [r["test"]["accuracy"] for r in all_results]
    f1 = [r["test"]["macro_f1"] for r in all_results]
    r3 = [r["test"]["recall_at_3"] for r in all_results]

    x = np.arange(len(models))
    w = 0.25

    plt.figure(figsize=(9, 5))
    plt.bar(x - w, acc, width=w, label="Accuracy")
    plt.bar(x, f1, width=w, label="Macro F1")
    plt.bar(x + w, r3, width=w, label="Recall@3")
    plt.xticks(x, models)
    plt.ylim(0, 1)
    plt.title("Test Metrics Comparison")
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "metrics_bar.png")
    plt.close()


def choose_best(all_results):
    ranked = sorted(
        all_results,
        key=lambda r: (r["test"]["macro_f1"], r["test"]["recall_at_3"], r["test"]["accuracy"]),
        reverse=True,
    )
    return ranked[0]


def main():
    os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig"))

    df = load_data(DATA_PATH)
    enc = build_encoders(df)
    x_prod, x_act, y, ts = build_samples(df, enc)

    if len(y) < 100:
        raise RuntimeError("Dataset too small for stable comparison. Increase events.")

    train_data, val_data, test_data = split_by_time(x_prod, x_act, y, ts)
    train_loader = make_loader(train_data, shuffle=True)
    val_loader = make_loader(val_data, shuffle=False)
    test_loader = make_loader(test_data, shuffle=False)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    num_products = len(enc.product2idx)
    num_actions = len(enc.action2idx)

    models = [
        ("RNN", RNNModel(num_products=num_products, num_actions=num_actions)),
        ("LSTM", LSTMModel(num_products=num_products, num_actions=num_actions)),
        ("biLSTM", BiLSTMModel(num_products=num_products, num_actions=num_actions)),
    ]

    all_results = []
    for name, model in models:
        result = train_model(name, model, train_loader, val_loader, test_loader, device, num_products)
        all_results.append(result)

    plot_curves(all_results)
    plot_metric_bars(all_results)

    best = choose_best(all_results)

    summary = {
        "config": {
            "seed": SEED,
            "seq_len": SEQ_LEN,
            "epochs": EPOCHS,
            "batch_size": BATCH_SIZE,
            "lr": LR,
        },
        "data": {
            "rows": int(len(df)),
            "samples": int(len(y)),
            "num_products": int(num_products),
            "num_actions": int(num_actions),
            "train_samples": int(len(train_data[2])),
            "val_samples": int(len(val_data[2])),
            "test_samples": int(len(test_data[2])),
        },
        "results": all_results,
        "model_best": {
            "name": best["model"],
            "test": best["test"],
            "model_path": best["artifacts"]["model_path"],
            "why": "Highest test Macro F1 (tie-break by Recall@3, then Accuracy)",
        },
        "plots": {
            "loss_curves": str(PLOTS_DIR / "loss_curves.png"),
            "accuracy_curves": str(PLOTS_DIR / "accuracy_curves.png"),
            "metrics_bar": str(PLOTS_DIR / "metrics_bar.png"),
        },
    }

    with (ARTIFACT_DIR / "training_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    with (ARTIFACT_DIR / "model_best.txt").open("w", encoding="utf-8") as f:
        f.write(f"model_best={best['model']}\n")
        f.write(json.dumps(best["test"], ensure_ascii=False, indent=2))

    inference_bundle = {
        "model_best_name": best["model"],
        "model_best_filename": Path(best["artifacts"]["model_path"]).name,
        "seq_len": SEQ_LEN,
        "product_ids": [enc.idx2product[idx] for idx in sorted(enc.idx2product.keys())],
        "actions": [a for a, _ in sorted(enc.action2idx.items(), key=lambda kv: kv[1])],
    }
    with (ARTIFACT_DIR / "inference_bundle.json").open("w", encoding="utf-8") as f:
        json.dump(inference_bundle, f, ensure_ascii=False, indent=2)

    print("Training finished")
    print(f"model_best={best['model']}")
    print(json.dumps(best["test"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
