import argparse
import math
import torch
from torch.utils.data import DataLoader, random_split
from pathlib import Path
from typing import Dict, Sequence
import pandas as pd
from .dataset import PowerDataset
from .architectures import MLP
from .processing import fit_scalers, transform, save_scalers


def train_model(
    df: pd.DataFrame,
    input_cols: Sequence[str],
    target_cols: Sequence[str],
    hidden_layers=(256, 256),
    batch_size: int = 64,
    max_epochs: int = 50,
    lr: float = 1e-3,
    weight_decay: float = 0.0,
    val_split: float = 0.1,
    test_split: float = 0.1,
    device: str = None,
    out_dir: str = "artifacts/mlp",
) -> Dict[str, float]:
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    scalers = fit_scalers(df, input_cols, target_cols)
    X_scaled, y_scaled = transform(df, scalers, input_cols, target_cols)
    ds = PowerDataset(pd.concat([X_scaled, y_scaled], axis=1), input_cols, target_cols)

    n_total = len(ds)
    n_val = int(n_total * val_split)
    n_test = int(n_total * test_split)
    n_train = n_total - n_val - n_test
    train_ds, val_ds, test_ds = random_split(ds, [n_train, n_val, n_test])

    loaders = {
        "train": DataLoader(train_ds, batch_size=batch_size, shuffle=True),
        "val": DataLoader(val_ds, batch_size=batch_size, shuffle=False),
        "test": DataLoader(test_ds, batch_size=batch_size, shuffle=False),
    }

    model = MLP(len(input_cols), len(target_cols), hidden_layers=hidden_layers).to(device)
    optim = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    loss_fn = torch.nn.MSELoss()

    best_val = math.inf
    best_path = out / "best_model.pth"

    for epoch in range(max_epochs):
        model.train()
        train_loss = 0.0
        for xb, yb in loaders["train"]:
            xb, yb = xb.to(device), yb.to(device)
            optim.zero_grad()
            pred = model(xb)
            loss = loss_fn(pred, yb)
            loss.backward()
            optim.step()
            train_loss += loss.item() * xb.size(0)
        train_loss /= len(loaders["train"].dataset)

        # Validação
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for xb, yb in loaders["val"]:
                xb, yb = xb.to(device), yb.to(device)
                pred = model(xb)
                loss = loss_fn(pred, yb)
                val_loss += loss.item() * xb.size(0)
        val_loss /= max(1, len(loaders["val"].dataset))

        if val_loss < best_val:
            best_val = val_loss
            torch.save({"model_state_dict": model.state_dict(), "input_cols": input_cols, "target_cols": target_cols}, best_path)
            save_scalers(scalers, out / "scalers.pkl")

        print(f"Epoch {epoch+1}/{max_epochs} - train {train_loss:.4f} - val {val_loss:.4f}")

    # Avalia teste
    test_loss = 0.0
    model.load_state_dict(torch.load(best_path)["model_state_dict"])
    model.eval()
    with torch.no_grad():
        for xb, yb in loaders["test"]:
            xb, yb = xb.to(device), yb.to(device)
            pred = model(xb)
            loss = loss_fn(pred, yb)
            test_loss += loss.item() * xb.size(0)
    test_loss /= max(1, len(loaders["test"].dataset))

    return {"best_val_loss": best_val, "test_loss": test_loss, "model_path": str(best_path), "scalers_path": str(out / "scalers.pkl")}


def _parse_args():
    p = argparse.ArgumentParser(description="Train MLP surrogate for AC state estimation")
    p.add_argument("--data", type=str, required=True, help="Path to parquet/csv dataset")
    p.add_argument("--out", type=str, default="artifacts/mlp", help="Output directory")
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--weight-decay", type=float, default=0.0)
    p.add_argument("--hidden", type=int, nargs="*", default=[256, 256])
    p.add_argument("--val-split", type=float, default=0.1)
    p.add_argument("--test-split", type=float, default=0.1)
    p.add_argument("--input-cols", type=str, nargs="+", required=True)
    p.add_argument("--target-cols", type=str, nargs="+", required=True)
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    if args.data.endswith(".parquet"):
        df = pd.read_parquet(args.data)
    else:
        df = pd.read_csv(args.data)

    metrics = train_model(
        df,
        input_cols=args.input_cols,
        target_cols=args.target_cols,
        hidden_layers=args.hidden,
        batch_size=args.batch_size,
        max_epochs=args.epochs,
        lr=args.lr,
        weight_decay=args.weight_decay,
        val_split=args.val_split,
        test_split=args.test_split,
        out_dir=args.out,
    )
    print("Treino finalizado:", metrics)
