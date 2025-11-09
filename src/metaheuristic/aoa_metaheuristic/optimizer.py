import numpy as np
from typing import Callable, Optional, Tuple
import matplotlib.pyplot as plt
import os
import time


class AOA:
    """
    Arithmetic Optimization Algorithm (AOA) - Versão orientada a objetos.

    Parâmetros:
        fitness_func: Função objetivo.
        dim: Dimensão do problema.
        ub: Limite superior (escalar ou array).
        lb: Limite inferior (escalar ou array).
        pop_start: População inicial (opcional).
        pop_size: Tamanho da população.
        max_iter: Número máximo de iterações.
        seed: Semente do gerador aleatório.
        alpha, mu, mop_max, mop_min: Parâmetros do AOA.

    Exemplo:
        aoa = AOA_3(fitness_func, dim=10, ub=5, lb=-5)
        best_fit, best_sol, curve = aoa.solve()
    """
    def __init__(
        self,
        fitness_func: Callable,
        dim: int,
        ub,
        lb,
        pop_start: Optional[np.ndarray] = None,
        pop_size: int = 30,
        max_iter: int = 100,
        seed: Optional[int] = 10,
        alpha: float = 5,
        mu: float = 0.499,
        mop_max: float = 1,
        mop_min: float = 0.2,
    ):
        # RNG
        self.rng = np.random.default_rng(seed)
        self.pop_size = int(pop_size)
        self.dim = int(dim)
        self.lb = np.full(self.dim, lb, dtype=float) if np.isscalar(lb) or np.array(lb).size == 1 else np.array(lb, dtype=float)
        self.ub = np.full(self.dim, ub, dtype=float) if np.isscalar(ub) or np.array(ub).size == 1 else np.array(ub, dtype=float)

        if pop_start is not None:
            self.pop = np.array(pop_start, dtype=float)
        else:
            self.pop = self.rng.random((self.pop_size, self.dim)) * (self.ub - self.lb) + self.lb

        # Problem
        self.fitness_func = fitness_func

        # Optimizer params
        self.max_iter = int(max_iter)
        self.alpha = float(alpha)
        self.mu = float(mu)
        self.mop_max = float(mop_max)
        self.mop_min = float(mop_min)
        self.eps = np.finfo(float).eps

        #

    
    def _eval(self, x: np.ndarray) -> float:
        try:
            return float(self.fitness_func(x))
        except Exception:
            return float(self.fitness_func(x.tolist()))
    
    def _div(self, pop_best, mop, constant):
        return pop_best / (mop + self.eps) * constant
    
    def _mult(self, pop_best, mop, constant):
        return pop_best * mop * constant
    
    def _sum(self, pop_best, mop, constant):
        return pop_best + mop * constant
    
    def _sub(self, pop_best, mop, constant):
        return pop_best - mop * constant
    
    def _mop(self, iter):
        return 1 - ((iter) ** (1 / self.alpha) / (self.max_iter) ** (1 / self.alpha))
    
    def _moa(self, iter):
        return self.mop_min + iter * ((self.mop_max - self.mop_min) / self.max_iter)

    def solve(self, verbose: bool = True) -> Tuple[float, np.ndarray, np.ndarray]:
        """
        Executa o algoritmo AOA.
        Retorna: melhor fitness, melhor solução, curva de convergência.
        """
        pop = np.copy(self.pop)
        pop_new = np.empty_like(pop)
        fitness = np.array([self._eval(ind) for ind in pop])
        fitness_best = np.min(fitness)
        pop_best = np.copy(pop[np.argmin(fitness)])
        conv_curve = np.zeros(self.max_iter)        

        for iter in range(1, self.max_iter + 1):
            mop = self._mop(iter)
            moa = self._moa(iter)
            for i in range(self.pop_size):
                for j in range(self.dim):
                    r1 = self.rng.random()
                    constant = (self.ub[j] - self.lb[j]) * self.mu + self.lb[j]
                    if r1 < moa:
                        r2 = self.rng.random()
                        if r2 > 0.5:
                            pop_new[i, j] = self._div(pop_best[j], mop, constant)
                        else:
                            pop_new[i, j] = self._mult(pop_best[j], mop, constant)
                    else:
                        r3 = self.rng.random()
                        if r3 > 0.5:
                            pop_new[i, j] = self._sub(pop_best[j], mop, constant)
                        else:
                            pop_new[i, j] = self._sum(pop_best[j], mop, constant)

                # Correção de limites
                pop_new[i, :] = np.clip(pop_new[i, :], self.lb, self.ub)

            print(f"Rodando iteração:{iter}")
            fitness_new = np.array([self._eval(ind) for ind in pop_new])

            improved = fitness_new < fitness
            pop[improved] = pop_new[improved]
            fitness[improved] = fitness_new[improved]

            if np.min(fitness) < fitness_best:
                fitness_best = np.min(fitness)
                pop_best = np.copy(pop[np.argmin(fitness)])

            conv_curve[iter - 1] = fitness_best
            if verbose and iter % 1 == 0:
                print(f"At iteration {iter} the best solution fitness is {fitness_best}")
            self.conv_curve = conv_curve

        return float(fitness_best), pop_best, conv_curve
    
    def plot_convergence(self, save_path: Optional[str] = None, title: str = "Curva de Convergência"):
        """
        Plota ou salva a curva de convergência da metaheurística.
        Rode o método solve primeiro.

        Parâmetros:
            save_path: se fornecido, salva o gráfico nesse caminho em vez de mostrar.
            title: título do gráfico (opcional)
        """
        if self.conv_curve is None:
            raise ValueError("Nenhuma curva de convergência carregada. Rode solve() primeiro.")

        plt.figure(figsize=(8, 5))
        plt.plot(self.conv_curve, marker='o', markersize=3)
        plt.title(title)
        plt.xlabel("Iteração")
        plt.ylabel("Melhor Fitness")
        plt.grid(True)

        if save_path is not None:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            plt.savefig(save_path)
            plt.close()  # fecha o plot para não mostrar
            print(f"Gráfico salvo em: {save_path}")
        else:
            plt.show()
    
    def solve_with_time(self, verbose: bool = True) -> Tuple[float, np.ndarray, np.ndarray, float]:
        """
        Executa o algoritmo AOA e mede o tempo de execução.
        Retorna: melhor fitness, melhor solução, curva de convergência, tempo (segundos).
        """
        start_time = time.perf_counter()
        best_fit, best_sol, conv_curve = self.solve(verbose=verbose)
        elapsed_time = time.perf_counter() - start_time
        return best_fit, best_sol, conv_curve, elapsed_time