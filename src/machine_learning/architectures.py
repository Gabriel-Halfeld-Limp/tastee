import torch
import torch.nn as nn
from typing import Sequence


class MLP(nn.Module):
    def __init__(self, input_dim: int, output_dim: int, hidden_layers: Sequence[int] = (256, 256), activation: str = "relu"):
        super().__init__()
        acts = {"relu": nn.ReLU, "tanh": nn.Tanh}
        act_cls = acts.get(activation, nn.ReLU)

        layers = []
        prev = input_dim
        for h in hidden_layers:
            layers.append(nn.Linear(prev, h))
            layers.append(act_cls())
            prev = h
        layers.append(nn.Linear(prev, output_dim))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)
