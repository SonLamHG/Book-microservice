import json
from pathlib import Path

import torch
import torch.nn as nn
from sqlalchemy import desc, select


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


MODEL_FACTORY = {
    "RNN": RNNModel,
    "LSTM": LSTMModel,
    "biLSTM": BiLSTMModel,
}


class SequenceRecommender:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.ready = False
        self.model_name = None
        self.seq_len = 3
        self.product2idx = {}
        self.idx2product = {}
        self.action2idx = {}
        self.default_action_idx = 0
        self.model = None
        self.device = torch.device("cpu")
        self._load()

    def _load(self):
        bundle_path = self.base_dir / "training" / "artifacts" / "inference_bundle.json"
        models_dir = self.base_dir / "training" / "models"
        if not bundle_path.exists() or not models_dir.exists():
            return

        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        self.model_name = bundle["model_best_name"]
        self.seq_len = int(bundle["seq_len"])

        product_ids = [int(v) for v in bundle["product_ids"]]
        actions = [str(v) for v in bundle["actions"]]

        self.product2idx = {pid: idx for idx, pid in enumerate(product_ids)}
        self.idx2product = {idx: pid for pid, idx in self.product2idx.items()}
        self.action2idx = {a: idx for idx, a in enumerate(actions)}
        self.default_action_idx = self.action2idx.get("click", 0)

        model_cls = MODEL_FACTORY.get(self.model_name)
        if model_cls is None:
            return

        model = model_cls(num_products=len(product_ids), num_actions=len(actions))
        model_path = models_dir / bundle["model_best_filename"]
        state = torch.load(model_path, map_location=self.device)
        model.load_state_dict(state)
        model.eval()

        self.model = model
        self.ready = True

    def predict_scores(self, db, behavior_model, user_id: int):
        if not self.ready:
            return {}

        events = db.scalars(
            select(behavior_model)
            .where(behavior_model.user_id == user_id, behavior_model.product_id.is_not(None))
            .order_by(desc(behavior_model.timestamp))
            .limit(100)
        ).all()

        ordered = list(reversed(events))
        seq_prod = []
        seq_act = []
        for e in ordered:
            pid = int(e.product_id)
            if pid not in self.product2idx:
                continue
            a_idx = self.action2idx.get(str(e.action).lower(), self.default_action_idx)
            seq_prod.append(self.product2idx[pid])
            seq_act.append(a_idx)

        if len(seq_prod) < self.seq_len:
            return {}

        seq_prod = seq_prod[-self.seq_len :]
        seq_act = seq_act[-self.seq_len :]

        x_prod = torch.tensor([seq_prod], dtype=torch.long)
        x_act = torch.tensor([seq_act], dtype=torch.long)

        with torch.no_grad():
            logits = self.model(x_prod, x_act)
            probs = torch.softmax(logits, dim=1)[0].cpu().tolist()

        return {self.idx2product[idx]: float(score) for idx, score in enumerate(probs)}
