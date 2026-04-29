"""LSTM next-product predictor.

Mirrors the architecture from the SoAD thesis Ch.3.4.2 sample:

    self.lstm = nn.LSTM(input_dim, hidden_dim, batch_first=True)
    self.fc   = nn.Linear(hidden_dim, output_dim)

Inputs are sequences of one-hot encoded product IDs (last K interactions);
outputs are logits over the product vocabulary."""
import torch
import torch.nn as nn


class LSTMModel(nn.Module):
    def __init__(self, num_products: int, hidden_dim: int = 64):
        super().__init__()
        self.num_products = num_products
        self.hidden_dim = hidden_dim
        # input_dim = num_products because each step is a one-hot vector of size N
        self.lstm = nn.LSTM(num_products, hidden_dim, batch_first=True)
        self.fc = nn.Linear(hidden_dim, num_products)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)
        out = out[:, -1, :]
        return self.fc(out)
