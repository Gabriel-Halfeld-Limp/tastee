import torch
import pandas as pd
from pathlib import Path
from typing import Sequence
from .architectures import MLP
from .processing import load_scalers, inverse_targets


class SurrogatePredictor:
    def __init__(self, model_path: str, scalers_path: str, device: str = None):
        ckpt = torch.load(model_path, map_location="cpu")
        self.input_cols = ckpt["input_cols"]
        self.target_cols = ckpt["target_cols"]
        self.model = MLP(len(self.input_cols), len(self.target_cols))
        self.model.load_state_dict(ckpt["model_state_dict"])
        self.model.eval()
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.scalers = load_scalers(scalers_path)

    def predict(self, df_inputs: pd.DataFrame) -> pd.DataFrame:
        x_scaled = self.scalers["input"].transform(df_inputs[self.input_cols])
        x_tensor = torch.tensor(x_scaled, dtype=torch.float32, device=self.device)
        with torch.no_grad():
            y_scaled = self.model(x_tensor).cpu().numpy()
        y = inverse_targets(y_scaled, self.scalers, self.target_cols)
        return pd.DataFrame(y, columns=self.target_cols)

    def predict_single(self, x: Sequence[float]) -> pd.Series:
        df = pd.DataFrame([x], columns=self.input_cols)
        return self.predict(df).iloc[0]
