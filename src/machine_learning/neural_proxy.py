import json
import pandas as pd
import numpy as np
import joblib
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

class OPFNeuralProxy:
    def __init__(self, hidden_layers=(300, 300, 300)):
        self.pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('mlp', MLPRegressor(
                hidden_layer_sizes=hidden_layers,
                activation='relu',
                solver='adam',
                max_iter=2000,
                learning_rate_init=0.0005, 
                alpha=0.01,
                early_stopping=True,
                validation_fraction=0.1,
                random_state=42,
                verbose=True
            ))
        ])
        self.input_cols = []
        self.target_cols = []

    def _flatten_json(self, json_path):
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        flat_data = []
        for sample in data:
            row = {}
            inputs = sample['inputs']
            outputs = sample['outputs']
            
            # --- INPUTS ---
            for k, v in inputs['thermal_gen_pu'].items(): row[f'in_gen_{k}'] = v
            for k, v in inputs['wind_available_pu'].items(): row[f'in_wind_{k}'] = v
            for k, v in inputs['load_required'].items():
                row[f'in_load_P_{k}'] = v['p_pu']
                row[f'in_load_Q_{k}'] = v['q_pu']

            # --- OUTPUTS ---
            # Dicionários Padrão
            if 'wind_curtailment_pu' in outputs:
                for k, v in outputs['wind_curtailment_pu'].items(): row[f'out_curt_{k}'] = v
            if 'load_deficit_pu' in outputs:
                for k, v in outputs['load_deficit_pu'].items(): row[f'out_def_{k}'] = v
            if 'bus_voltage_pu' in outputs:
                for k, v in outputs['bus_voltage_pu'].items(): row[f'out_v_{k}'] = v
            
            # Reativos (Qg) - O que faltava mostrar!
            if 'thermal_gen_q_pu' in outputs:
                for k, v in outputs['thermal_gen_q_pu'].items(): row[f'out_gen_Q_{k}'] = v

            # Carregamento (Escalar)
            for key, val in outputs.items():
                if key.startswith('line_loading_'):
                    clean_name = key.replace('line_loading_', '').replace('_pu', '')
                    row[f'out_loading_{clean_name}'] = val
            
            flat_data.append(row)
            
        df = pd.DataFrame(flat_data)
        return df, [c for c in df.columns if c.startswith('in_')], [c for c in df.columns if c.startswith('out_')]

    def train(self, train_file):
        print(f"--- Carregando TREINO: {train_file} ---")
        df_train, self.input_cols, self.target_cols = self._flatten_json(train_file)
        print(f"Amostras: {len(df_train)} | Inputs: {len(self.input_cols)} | Targets: {len(self.target_cols)}")
        
        self.pipeline.fit(df_train[self.input_cols], df_train[self.target_cols])
        print("Treinamento Concluído.")
        
        joblib.dump(self.pipeline, 'rna_proxy_model.pkl')
        joblib.dump({'input': self.input_cols, 'target': self.target_cols}, 'rna_cols.pkl')

    def evaluate(self, test_file):
        print(f"\n--- Avaliando no Teste: {test_file} ---")
        df_test, _, _ = self._flatten_json(test_file)
        
        # Alinha colunas (preenche faltantes com 0)
        for col in self.input_cols + self.target_cols:
            if col not in df_test.columns: df_test[col] = 0.0
            
        y_true = df_test[self.target_cols]
        y_pred = pd.DataFrame(self.pipeline.predict(df_test[self.input_cols]), columns=self.target_cols, index=df_test.index)
        
        print(f"MSE Global: {mean_squared_error(y_true, y_pred):.6f}")
        
        # --- Categorias de Métricas ---
        def_cols = [c for c in self.target_cols if 'out_def_' in c]
        load_cols = [c for c in self.target_cols if 'out_loading_' in c]
        volt_cols = [c for c in self.target_cols if 'out_v_' in c]
        q_cols = [c for c in self.target_cols if 'out_gen_Q_' in c] # Identifica colunas de Q

        if def_cols: print(f"R² Déficit: {r2_score(y_true[def_cols], y_pred[def_cols]):.5f}")
        if load_cols: print(f"MAE Carregamento: {mean_absolute_error(y_true[load_cols], y_pred[load_cols]):.4f}")
        if volt_cols: print(f"MAE Tensão: {mean_absolute_error(y_true[volt_cols], y_pred[volt_cols]):.4f}")
        if q_cols: 
            # Reativos costumam ter comportamento difícil, MAE é melhor que R2
            print(f"MAE Reativos (Qg): {mean_absolute_error(y_true[q_cols], y_pred[q_cols]):.4f}")

        # --- Visualização de Amostra ---
        # Prioridade para mostrar: Déficit > Sobrecarga > Aleatório
        is_critical = (y_true[def_cols].sum(axis=1) > 0.01)
        if load_cols: is_critical |= (y_true[load_cols].max(axis=1) > 0.95)
        
        idx = y_true[is_critical].index[0] if is_critical.any() else df_test.index[0]
        
        print(f"\n--- Detalhes da Amostra #{idx} ---")
        print(f"{'Target':<30} | {'Real':<10} | {'Predito':<10} | {'Erro':<10}")
        print("-" * 65)
        
        def print_row(cols, threshold=1e-3):
            for col in cols:
                real, pred = y_true.loc[idx, col], y_pred.loc[idx, col]
                if abs(real) > threshold or abs(real - pred) > threshold:
                    print(f"{col:<30} | {real:.4f}     | {pred:.4f}     | {abs(real-pred):.4f}")

        print(">>> DÉFICIT E CURTAILMENT")
        print_row(def_cols)
        print_row([c for c in self.target_cols if 'out_curt_' in c])
        
        if q_cols:
            print("-" * 65)
            print(">>> GERAÇÃO REATIVA (PU) [Qg]")
            # Mostra só os que estão gerando/absorvendo algo relevante (> 0.01 pu)
            print_row(q_cols, threshold=0.01)

        if load_cols:
            print("-" * 65)
            print(">>> CARREGAMENTO LINHAS (%)")
            # Top 3 mais carregadas
            top_loaded = y_true.loc[idx, load_cols].sort_values(ascending=False).head(3).index
            print_row(top_loaded, threshold=0.0)

        if volt_cols:
            print("-" * 65)
            print(">>> TENSÕES (PU) [Desvios > 0.01]")
            bad_volts = [c for c in volt_cols if abs(y_true.loc[idx, c] - 1.0) > 0.01]
            print_row(bad_volts, threshold=0.0)

if __name__ == "__main__":
    rna = OPFNeuralProxy()
    rna.train("data_train_b6l8.json")
    rna.evaluate("data_test_b6l8.json")