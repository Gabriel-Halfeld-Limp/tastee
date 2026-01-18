import pandas as pd
import torch
from torch.utils.data import Dataset
from typing import Sequence


class PowerDataset(Dataset):
    def __init__(self, df: pd.DataFrame, input_cols: Sequence[str], target_cols: Sequence[str]):
        self.df = df.reset_index(drop=True)
        self.input_cols = list(input_cols)
        self.target_cols = list(target_cols)

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.loc[idx]
        x = torch.tensor(row[self.input_cols].values, dtype=torch.float32)
        y = torch.tensor(row[self.target_cols].values, dtype=torch.float32)
        return x, y
