from pathlib import Path
import pandas as pd
import numpy as np
import joblib
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import r2_score, mean_squared_error

class NeuralProxy118:
    def __init__(self):
        # Rede mais profunda para o IEEE 118
        self.pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('mlp', MLPRegressor(
                hidden_layer_sizes=(300, 300, 300), # 3 camadas ocultas
                activation='relu', 
                solver='adam', 
                max_iter=1000, 
                learning_rate_init=0.001,
                early_stopping=True,
                validation_fraction=0.1,
                verbose=True,
                random_state=42
            ))
        ])
        self.features = None
        self.targets = None

    def train_with_noise(self, train_path, test_path):
        print(f"--- Carregando Datasets ---\nTreino: {train_path}\nTeste: {test_path}")
        df_train = pd.read_parquet(train_path)
        df_test = pd.read_parquet(test_path)
        
        # Define Features (Input) e Targets (Output)
        self.features = [c for c in df_train.columns if c.startswith('input_')]
        self.targets = [c for c in df_train.columns if c.startswith('target_')]
        
        X_train = df_train[self.features]
        y_train = df_train[self.targets]
        
        X_test_clean = df_test[self.features]
        y_test = df_test[self.targets]
        
        print(f"Features: {len(self.features)} | Targets: {len(self.targets)}")
        print(f"Amostras Treino: {len(X_train)}")
        
        # --- 1. Treinamento (Dados Limpos) ---
        print("\n--- Iniciando Treinamento da RNA ---")
        self.pipeline.fit(X_train, y_train)
        
        # --- 2. Teste com Ruído (Slide 10) ---
        print("\n--- Aplicando Ruído de Medição (+/- 2%) no Teste ---")
        # Ruído uniforme entre -2% (-0.02) e +2% (+0.02)
        # X_noisy = X * (1 + r)
        noise = pd.DataFrame(
            np.random.uniform(-0.02, 0.02, X_test_clean.shape),
            columns=self.features,
            index=X_test_clean.index
        )
        X_test_noisy = X_test_clean * (1 + noise)
        
        # Inferência
        score = self.pipeline.score(X_test_noisy, y_test)
        print(f"R² Score (Teste Ruidoso): {score:.4f}")
        
        # Métricas Específicas
        y_pred = self.pipeline.predict(X_test_noisy)
        y_pred_df = pd.DataFrame(y_pred, columns=self.targets, index=y_test.index)
        
        # Erro Médio Quadrático para Deficit e Curtailment Total
        mse_def = mean_squared_error(y_test['target_Deficit_Total'], y_pred_df['target_Deficit_Total'])
        mse_pcw = mean_squared_error(y_test['target_PCW_Total'], y_pred_df['target_PCW_Total'])
        
        print(f"MSE Deficit Total: {mse_def:.6f}")
        print(f"MSE Curtailment Total: {mse_pcw:.6f}")
        
        self.save_model(save_dir=Path(train_path).resolve().parent)

    def save_model(self, filename="rna_118_model.pkl", save_dir=None):
        target_dir = Path(save_dir) if save_dir else Path.cwd()
        target_dir.mkdir(parents=True, exist_ok=True)
        model_path = target_dir / filename
        joblib.dump({'pipeline': self.pipeline, 'features': self.features, 'targets': self.targets}, model_path)
        print(f"Modelo salvo em {model_path}")

def find_latest_dataset(run_prefix: str = "dataset", base_dir: Path | None = None):
    base = base_dir or Path(__file__).resolve().parents[2] / "trabalhos_transmissao" / "trab_aula_11_RNA"
    if not base.exists():
        raise FileNotFoundError(f"Diretório base não encontrado: {base}")
    candidates = [d for d in base.iterdir() if d.is_dir() and d.name.startswith(run_prefix)]
    if not candidates:
        raise FileNotFoundError(f"Nenhum diretório encontrado em {base} com prefixo '{run_prefix}'")
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    train = next(latest.glob("*_train.parquet"), None)
    test = next(latest.glob("*_test.parquet"), None)
    if train is None or test is None:
        raise FileNotFoundError(f"Arquivos train/test não encontrados em {latest}")
    print(f"Usando último dataset em: {latest}")
    return train, test

if __name__ == "__main__":
    rna = NeuralProxy118()
    train_file, test_file = find_latest_dataset(run_prefix="dataset")
    rna.train_with_noise(train_file, test_file)