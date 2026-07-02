"""CNN+LSTM flow classifier (thesis architecture).

Tabular flow features are treated as a length-`num_features` sequence with a
single channel: Conv1D extracts local feature interactions, the LSTM models
them as a sequence, then dense layers classify. Matches the thesis spec
(Conv1D -> LSTM -> Dense -> Softmax), parameterised for any feature/class count.
"""
from __future__ import annotations

import torch
import torch.nn as nn


class CNNLSTM(nn.Module):
    def __init__(
        self,
        num_features: int,
        num_classes: int,
        conv_filters: int = 64,
        lstm_hidden: int = 128,
        dense_hidden: int = 64,
        dropout: float = 0.3,
    ):
        super().__init__()
        self.num_features = num_features
        self.num_classes = num_classes

        # Treat the feature vector as a 1-channel sequence of length num_features.
        self.conv = nn.Sequential(
            nn.Conv1d(1, conv_filters, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.BatchNorm1d(conv_filters),
        )
        # LSTM consumes the conv feature-map as a sequence of length num_features,
        # each step a conv_filters-dim vector.
        self.lstm = nn.LSTM(
            input_size=conv_filters,
            hidden_size=lstm_hidden,
            batch_first=True,
        )
        self.head = nn.Sequential(
            nn.Linear(lstm_hidden, dense_hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(dense_hidden, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, num_features) -> (batch, 1, num_features)
        x = x.unsqueeze(1)
        x = self.conv(x)                 # (batch, conv_filters, num_features)
        x = x.transpose(1, 2)            # (batch, num_features, conv_filters)
        out, (h_n, _) = self.lstm(x)     # h_n: (1, batch, lstm_hidden)
        last = h_n[-1]                   # (batch, lstm_hidden)
        return self.head(last)           # logits (batch, num_classes)


def build_model(cfg, num_features: int, num_classes: int) -> CNNLSTM:
    m = cfg.model
    return CNNLSTM(
        num_features=num_features,
        num_classes=num_classes,
        conv_filters=m.conv_filters,
        lstm_hidden=m.lstm_hidden,
        dense_hidden=m.dense_hidden,
        dropout=m.dropout,
    )
