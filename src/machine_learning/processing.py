import pickle
from pathlib import Path
from typing import Tuple, Dict
import pandas as pd
from sklearn.preprocessing import StandardScaler


def fit_scalers(df: pd.DataFrame, input_cols, target_cols) -> Dict[str, StandardScaler]:
    scalers = {
        "input": StandardScaler(),
        "target": StandardScaler(),
    }
    scalers["input"].fit(df[input_cols])
    scalers["target"].fit(df[target_cols])
    return scalers


def transform(df: pd.DataFrame, scalers: Dict[str, StandardScaler], input_cols, target_cols) -> Tuple[pd.DataFrame, pd.DataFrame]:
    x = scalers["input"].transform(df[input_cols])
    y = scalers["target"].transform(df[target_cols])
    return pd.DataFrame(x, columns=input_cols), pd.DataFrame(y, columns[target_cols])


def inverse_targets(y_scaled, scalers: Dict[str, StandardScaler], target_cols):
    return scalers["target"].inverse_transform(y_scaled)


def save_scalers(scalers: Dict[str, StandardScaler], path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(scalers, f)


def load_scalers(path: str) -> Dict[str, StandardScaler]:
    with open(path, "rb") as f:
        return pickle.load(f)
