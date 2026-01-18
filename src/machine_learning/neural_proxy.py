# import pandas as pd
# import joblib
# import matplotlib.pyplot as plt
# import seaborn as sns

# from sklearn.neural_network import MLPRegressor
# from sklearn.compose import TransformedTargetRegressor
# from sklearn.preprocessing import StandardScaler
# from sklearn.pipeline import Pipeline
# from sklearn.model_selection import train_test_split
# from sklearn.metrics import r2_score, mean_squared_error

# class NeuralProxyAC:
#     def __init__(self, hidden_layers=(200, 200, 200), max_iter=1000):
#         """
#         Proxy Neural para emular o AC-OPF.
#         Usa um Multi-Layer Perceptron (MLP) para mapear (P_gen, P_load) -> (V, Theta, Q, Loading).
#         """
#         base_regressor = Pipeline([
#             ('scaler', StandardScaler()),
#             ('mlp', MLPRegressor(
#                 hidden_layer_sizes=hidden_layers,
#                 activation='relu',
#                 solver='adam',
#                 alpha=0.0001,
#                 batch_size='auto',
#                 learning_rate='adaptive',
#                 max_iter=max_iter,
#                 random_state=42,
#                 early_stopping=True,
#                 validation_fraction=0.1,
#                 verbose=True
#             ))
#         ])

#         # Escala alvos também para estabilizar o treino multi-saída
#         self.model = TransformedTargetRegressor(
#             regressor=base_regressor,
#             transformer=StandardScaler()
#         )
        
#         # Metadados para garantir que a ordem das colunas seja sempre a mesma
#         self.feature_names = None
#         self.target_names = None

#     def train(self, dataset_path="dataset_ac.parquet", test_size=0.2):
#         """
#         Carrega o Parquet, divide em Treino/Teste e treina a RNA.
#         """
#         print(f"--- Carregando Dataset: {dataset_path} ---")
#         df = pd.read_parquet(dataset_path)
        
#         # Separa Inputs (X) e Targets (Y) pelo prefixo da coluna
#         self.feature_names = [c for c in df.columns if c.startswith('input_')]
#         self.target_names = [c for c in df.columns if c.startswith('target_')]
        
#         X = df[self.feature_names]
#         y = df[self.target_names]
        
#         print(f"Entradas (X): {len(self.feature_names)} variáveis")
#         print(f"Saídas   (Y): {len(self.target_names)} variáveis")
#         print(f"Amostras Totais: {len(df)}")

#         # Divisão Treino (80%) vs Teste (20%)
#         X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)
        
#         print("\n--- Iniciando Treinamento da RNA ---")
#         self.model.fit(X_train, y_train)
        
#         print("\n--- Avaliação (Conjunto de Teste) ---")
#         score = self.model.score(X_test, y_test)
#         print(f"R² Score Global: {score:.4f} (1.0 é perfeito)")
        
#         # Salva automaticamente
#         self.save_model()
#         return score

#     def predict(self, input_dict):
#         """
#         Faz a inferência para um único ponto de operação.
#         Recebe um dicionário com os valores de input e retorna os valores previstos.
#         """
#         if self.feature_names is None:
#             raise ValueError("O modelo precisa ser treinado ou carregado antes de usar.")

#         # Converte dict para DataFrame garantindo a ordem das colunas
#         df_in = pd.DataFrame([input_dict])
        
#         # Preenche colunas faltantes com 0 (robustez) e reordena
#         df_in = df_in.reindex(columns=self.feature_names, fill_value=0)
        
#         # Predição (retorna matriz, pegamos a primeira linha)
#         y_pred_array = self.model.predict(df_in)[0]
        
#         # Reconstrói o dicionário com os nomes das saídas
#         return dict(zip(self.target_names, y_pred_array))

#     def save_model(self, filename="ac_proxy_model.pkl"):
#         """Salva o modelo treinado + scalers em disco."""
#         joblib.dump({
#             'model': self.model,
#             'features': self.feature_names,
#             'targets': self.target_names
#         }, filename)
#         print(f"Modelo salvo em: {filename}")

#     def load_model(self, filename="ac_proxy_model.pkl"):
#         """Carrega um modelo do disco."""
#         data = joblib.load(filename)
#         self.model = data['model']
#         self.feature_names = data['features']
#         self.target_names = data['targets']
#         print(f"Modelo carregado de: {filename}")

# if __name__ == "__main__":
#     # Treina diretamente usando o dataset gerado pelo data_gen
#     proxy = NeuralProxyAC(hidden_layers=(200, 200, 200), max_iter=1000)
#     proxy.train(dataset_path="teste_dataset.parquet", test_size=0.2)import pandas as pd
import joblib
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
import pandas as pd

class NeuralProxyAC:
    def __init__(self, hidden_layers=(256, 256, 256, 256), max_iter=2000):
        """
        Versão Tunada para Fluxo de Potência AC.
        Mudanças:
        - Mais camadas (Deep Learning) para capturar a não-linearidade do AC.
        - Taxa de aprendizado menor para evitar oscilação.
        - Mais paciência (n_iter_no_change).
        """
        self.pipeline = Pipeline([
            ('scaler', StandardScaler()), # Essencial para normalizar V(1.0) e P(100.0)
            ('mlp', MLPRegressor(
                hidden_layer_sizes=hidden_layers, # 4 camadas de 256 neurônios
                activation='relu',      
                solver='adam',          
                alpha=1e-5,             # Regularização leve
                batch_size=64,          # Lotes menores as vezes ajudam a generalizar melhor
                learning_rate_init=0.0005, # <--- O SEGREDO: Mais lento (era 0.001)
                max_iter=max_iter,
                random_state=42,
                early_stopping=True,    
                validation_fraction=0.1,
                n_iter_no_change=50,    # <--- PACIÊNCIA: Espera 50 épocas antes de desistir
                verbose=True            
            ))
        ])
        
        self.feature_names = None
        self.target_names = None

    def train(self, dataset_path="dataset_ac.parquet", test_size=0.15):
        print(f"--- Carregando Dataset: {dataset_path} ---")
        df = pd.read_parquet(dataset_path)
        
        self.feature_names = [c for c in df.columns if c.startswith('input_')]
        self.target_names = [c for c in df.columns if c.startswith('target_')]
        
        X = df[self.feature_names]
        y = df[self.target_names]
        
        print(f"Dataset Shape: {X.shape}")

        # Aumentamos um pouco o conjunto de treino (deixando 15% pra teste)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)
        
        print("\n--- Iniciando Treinamento (Deep MLP) ---")
        self.pipeline.fit(X_train, y_train)
        
        print("\n--- Avaliação Final ---")
        score = self.pipeline.score(X_test, y_test)
        print(f"R² Score (Teste): {score:.5f}")
        
        self.save_model()
        return score

    def predict(self, input_dict):
        # (Código de predição igual ao anterior)
        if self.feature_names is None:
            raise ValueError("Modelo não carregado.")
        df_in = pd.DataFrame([input_dict])
        df_in = df_in.reindex(columns=self.feature_names, fill_value=0)
        y_pred = self.pipeline.predict(df_in)[0]
        return dict(zip(self.target_names, y_pred))

    def save_model(self, filename="ac_proxy_model.pkl"):
        joblib.dump({'pipeline': self.pipeline, 'features': self.feature_names, 'targets': self.target_names}, filename)
        print(f"Modelo salvo em: {filename}")

    def load_model(self, filename="ac_proxy_model.pkl"):
        data = joblib.load(filename)
        self.pipeline = data['pipeline']
        self.feature_names = data['features']
        self.target_names = data['targets']

if __name__ == "__main__":
    # Atalho pra treinar direto se rodar o arquivo
    net = NeuralProxyAC()
    net.train("teste_dataset.parquet")