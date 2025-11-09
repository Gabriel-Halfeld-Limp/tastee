from power import Network, ThermalGenerator, BusType
import numpy as np
import pulp as pl
# from opf_linear.utils.extr_and_save import extract_and_save_results

class LinearDispatch:
    def __init__(self, net: Network):
        """
        Inicializa e constrói o problema de despacho econômico linear para uma dada rede.
        """
        self.net = net
        self.problem = None

        # Initializing losses on each bus:
        for b in self.net.buses:
            b.loss = 0

        # RNG da classe
        self.rng = np.random.default_rng(seed=42)
    # ----------------------------------------------------------------OBJECTIVE FUNCTIONS------------------------------------------------------------------------------------#
    def _fob_linear_econ_dispatch(self):
        """Define a função objetivo do problema (minimizar custo total)."""

        thermal_generators = [g for g in self.net.generators if isinstance(g, ThermalGenerator)]
        thermal_cost = pl.lpSum([g.cost_b_pu * g.p_var for g in thermal_generators])
        generation_cost = thermal_cost
        shedding_cost = pl.lpSum([l.cost_shed_pu * l.p_shed_var for l in self.net.loads if hasattr(l, 'p_shed_var')])
        self.problem += generation_cost + shedding_cost, "Min_Total_System_Cost"
    
    def _fob_min_loss(self):
        self.problem += pl.lpSum([g.p_var for g in self.net.generators]), "Min_Loss"
    
    def _fob_transmission_cost(self):
        self._update_flow_sign()
        self.problem += pl.lpSum([l.flow_sign * l.flow_max_pu * l.flow_var for l in self.net.lines]), "Min_Transmission_Cost"

    # ----------------------------------------------------------------CREATE VARIABLES------------------------------------------------------------------------------------#
    def _create_theta_variable(self):
        # Ângulo das Barras
        for b in self.net.buses:
                if b.btype == BusType.SLACK:
                    b.theta_var = pl.LpVariable(f"Theta{b.id}")
                    self.problem += b.theta_var <=  0, f"Constraint_Theta_{b.id}_Upper"
                    self.problem += b.theta_var >= 0, f"Constraint_Theta_{b.id}_Lower"
                    b.theta_var.setInitialValue(0)   
                else:
                    b.theta_var = pl.LpVariable(f"Theta{b.id}")
                    self.problem += b.theta_var <=  np.pi, f"Constraint_Theta_{b.id}_Upper"
                    self.problem += b.theta_var >= -np.pi, f"Constraint_Theta_{b.id}_Lower"
                    b.theta_var.setInitialValue(0)   

    def _create_flow_variable(self):
        for line in self.net.lines:
            line.flow_var = pl.LpVariable(f"Flow_{line.id}")
            self.problem += line.flow_var <=  line.flow_max_pu, f"Constraint_Flow_{line.id}_Upper"
            self.problem += line.flow_var >= -line.flow_max_pu, f"Constraint_Flow_{line.id}_Lower"
            self.problem += line.flow_var == ((line.from_bus.theta_var - line.to_bus.theta_var) / line.x_pu), f"Constraint_Flow_{line.id}"
    
    def _create_generation_variable(self):
        for g in self.net.generators:
            g.p_var = pl.LpVariable(f"P{g.id}")
            self.problem += g.p_var <= g.p_max_pu, f"Constraint_P{g.id}_Upper"
            self.problem += g.p_var >= g.p_min_pu, f"Constraint_P{g.id}_Lower"

    def _create_load_shed_variable(self):
        for l in self.net.loads:
            l.p_shed_var = pl.LpVariable(f"L_shed{l.id}")
            self.problem += l.p_shed_var <= l.p_pu,       f"Constraint_P_Shed{l.id}_Upper"
            self.problem += l.p_shed_var >= 0,         f"Constraint_P_Shed{l.id}_Lower"

    # ----------------------------------------------------------------CREATE CONSTRAINTS------------------------------------------------------------------------------------#
    def _nodal_power_balance(self):
        for b in self.net.buses:
            generation = pl.lpSum([g.p_var for g in b.generators])
            load = sum([l.p_pu for l in b.loads]) + b.loss
            load_shed = pl.lpSum([l.p_shed_var for l in b.loads])
            flow_in = pl.lpSum([(l.from_bus.theta_var - b.theta_var) / l.x_pu for l in self.net.lines if l.to_bus == b])
            flow_out = pl.lpSum([(b.theta_var - l.to_bus.theta_var) / l.x_pu for l in self.net.lines if l.from_bus == b])
            self.problem += generation + load_shed + flow_in - flow_out == load, f"B{b.id}_Power_Balance"

    # ----------------------------------------------------------------UTILS------------------------------------------------------------------------------------------------#

    def _update_losses(self):
        """
        Calcula as perdas com base nos ângulos da solução atual e as atualiza nas barras.
        Retorna o valor total das perdas calculadas.
        """
        current_total_loss = 0
        # 1. Zera as perdas da iteração anterior em todas as barras
        for b in self.net.buses:
            b.loss = 0

        # 2. Calcula e distribui as novas perdas
        for l in self.net.lines:
            r = l.r_pu
            x = l.x_pu
            # Evita divisão por zero se a linha não tiver impedância
            g_series = r / (r**2 + x**2) if (r**2 + x**2) > 0 else 0
            
            # .value() é um alias para .varValue, mais limpo de ler
            dtheta = l.from_bus.theta_var.value() - l.to_bus.theta_var.value()
            
            line_loss = g_series * (dtheta ** 2)
            l.loss = line_loss
            current_total_loss += line_loss
            
            # Atribui metade da perda para cada barra da linha
            l.from_bus.loss += line_loss / 2
            l.to_bus.loss += line_loss / 2
            
        return current_total_loss

    def _update_flow_sign(self):
        for line in self.net.lines:
            if line.from_bus.theta_var.value() > line.to_bus.theta_var.value(): # Fluxo de "FROM" para "TO"
                line.flow_sign = 1
            elif line.from_bus.theta_var.value() < line.to_bus.theta_var.value(): #Fluxo de "TO" para "FROM"
                line.flow_sign = -1
            elif line.from_bus.theta_var.value() == line.to_bus.theta_var.value(): #Fluxo 0
                line.flow_sign = 0
            else:
                raise ValueError(f"Fluxo não foi corretamente calculado, o sentido do fluxo não é negativo, nem positivo, nem zero")
    

    
    # ----------------------------------------------------------------SOLVING----------------------------------------------------------------------------------------------#
    
    def solve_loss(self, iter_max=100, max_tol=1e-6, min_losses=False):
        """
        Resolve o despacho econômico de forma iterativa para incluir as perdas da rede.
        """
        # print("Iniciando Despacho Econômico Linear com Perdas...")

        # 1. Construir o modelo base FORA do loop
        self.problem = pl.LpProblem("Linear_Economic_Dispatch", pl.LpMinimize)
        self._create_theta_variable()
        self._create_flow_variable()
        self._create_generation_variable()
        self._create_load_shed_variable()
        if not min_losses:
            self._fob_linear_econ_dispatch()
        else:
            self._fob_min_loss()
        self._nodal_power_balance() 

        prev_total_loss = 0

        for i in range(1, iter_max + 1):
            # 2. Resolver o problema atual
            # self.problem.solve()
            self.problem.solve(pl.PULP_CBC_CMD(msg=False))
            if self.problem.status != pl.LpStatusOptimal:
                print(f"ERRO: Solução ótima não encontrada na iteração {i}.")
                return (pl.LpStatus[self.problem.status], None, None)

            # 3. Calcular novas perdas e verificar convergência
            current_total_loss = self._update_losses()
            loss_diff = abs(current_total_loss - prev_total_loss)
            # print(f"Iteração {i}: Perdas Totais = {current_total_loss:.6f} pu | Diferença = {loss_diff:.6f}")
            if loss_diff <= max_tol:
                # print(f"\nConvergência atingida na iteração {i}!")
                break    
            # 4. Preparar para a próxima iteração
            prev_total_loss = current_total_loss
            
            # Remove as restrições de balanço de potência antigas
            for b in self.net.buses:
                constraint_name = f"B{b.id}_Power_Balance"
                self.problem.constraints.pop(constraint_name)
            
            # Adiciona as novas restrições de balanço com as perdas atualizadas
            self._nodal_power_balance()
        else: # Este `else` pertence ao `for`, executando se o loop terminar sem `break`
            print(f"\nAviso: Convergência não atingida após {iter_max} iterações.")

        final_cost = pl.value(self.problem.objective)
        
        return (pl.LpStatus[self.problem.status], final_cost, current_total_loss)
    
    def solve_transmission(self):
        """
        Otimização de Custo de Transmissão com injeções de potência fixas.
        Objetivo: Obter os coeficientes de Lagrange (preços-sombra) das restrições.
        """
        print("\n" + "="*80)
        print("OTIMIZAÇÃO DE CUSTO DE TRANSMISSÃO")
        print("="*80)

        #1) Resolvendo o Problema com Perdas
        print("Passo 1: Resolvendo o Despacho Econômico com Perdas para fixar a geração...")
        status, _, _ = self.solve_loss()
        
        if status != 'Optimal':
            print("[ERRO] O despacho econômico inicial falhou. Abortando a otimização de transmissão.")
            return None, None     
        
        #2) Construir o Problema de Custo de Transmissão
        self.problem = pl.LpProblem("Transmission_Cost_Optimization", pl.LpMinimize)
        self._create_theta_variable()
        self._create_flow_variable()
        # 3. Balanço nodal COM VALORES FIXOS
        for b in self.net.buses:
            generation = sum([g.p_var.value() for g in b.generators])
            demand = sum([l.p_pu for l in b.loads]) + b.loss
            flow_out = pl.lpSum([l.flow_var for l in self.net.lines if l.from_bus == b])
            flow_in = pl.lpSum([l.flow_var for l in self.net.lines if l.to_bus == b])
            self.problem += flow_in - flow_out == demand - generation

        self._fob_transmission_cost()
        self.problem.solve()

        return extract_and_save_results(self.problem, self.net, "resultados_transmissao.json")
if __name__ == "__main__":
    from power.systems.b6l8 import B6L8
    from power.systems.ieee118 import IEEE118
    print("oi")
    net = IEEE118()
    solver = LinearDispatch(net)
    solver.solve_loss()


