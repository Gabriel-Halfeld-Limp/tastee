import numpy as np
from power.models.electricity_models.network_models import *

class AC_PF:
    def __init__(self, network: Network):
        """
        Initializes the AC Power Flow class.
        """
        self.network = network # Network object

        # YBUS
        self.G = self.network.get_G() # Real part of YBUS
        self.B = self.network.get_B() # Imaginary part of YBUS

        # Number of buses
        self.nbus = len(self.network.buses)

        #Organize bus types:
        self.pq_buses = [bus for bus in self.network.buses if bus.bus_type == 'PQ'] # PQ buses
        self.pv_buses = [bus for bus in self.network.buses if bus.bus_type == 'PV'] # PV buses
        self.slack_bus = [bus for bus in self.network.buses if bus.bus_type == 'Slack'] # Slack bus

        # Bus Maps:
        self.bus_idx = {bus.id: i for i, bus in enumerate(self.network.buses)} # Bus Map, key: bus id, value: bus index
        self.pq_idx = [self.bus_idx[bus.id] for bus in self.pq_buses] # PQ buses
        self.pv_idx = [self.bus_idx[bus.id] for bus in self.pv_buses] # PV buses
        self.slack_idx = [self.bus_idx[bus.id] for bus in self.slack_bus] # Slack bus
        self.K = self.get_K_set() # K set: Set of buses connected to each bus including itself
        self.omega = self.get_omega_set() # Omega set: Set of buses connected to each bus excluding itself

        # Initialize voltage angles and magnitudes
        self.theta_0 = np.array([bus.theta_rad for bus in self.network.buses]) # Voltage angles
        self.V_0 = np.array([bus.v for bus in self.network.buses]) # Voltage magnitudes
        self.X_0 = np.concatenate((self.theta_0, self.V_0)) # State vector

        # Initialize P and Q
        self.P_esp = np.array([bus.p for bus in self.network.buses]) # Active power
        self.Q_esp = np.array([bus.q for bus in self.network.buses]) # Reactive power
        self.PQ_esp = np.concatenate((self.P_esp, self.Q_esp)) # Power vector

        # Initialize the final calculated vectors
        self.theta = np.zeros(self.nbus) # Voltage angles
        self.V_ = np.ones(self.nbus) # Voltage magnitudes

    
    def get_K_set(self):
        """
        Returns the K set, which is the set of buses connected to each bus.
        """
        K_set = {}
        for bus in self.network.buses:
            i = self.bus_idx[bus.id]
            connected_indices = {i}    #include the bus itself

            for line in self.network.lines:
                if line.from_bus.id == bus.id:
                    connected_indices.add(self.bus_idx[line.to_bus.id])
                elif line.to_bus.id == bus.id:
                    connected_indices.add(self.bus_idx[line.from_bus.id])
            K_set[i] = connected_indices
        return K_set

    def get_omega_set(self):
        """
        Returns the omega set, which is the set of buses connected to each bus, excluding itself.
        """
        omega_set = {}
        for bus in self.network.buses:
            i = self.bus_idx[bus.id]
            connected_indices = set()

            for line in self.network.lines:
                if line.from_bus.id == bus.id:
                    connected_indices.add(self.bus_idx[line.to_bus.id])
                elif line.to_bus.id == bus.id:
                    connected_indices.add(self.bus_idx[line.from_bus.id])
            omega_set[i] = connected_indices
        
        return omega_set

    # Method for power equations: It receives current V and theta for all buses and returns calculated P's and Q's.
    def pq_calc(self, theta, V):
        P = np.zeros(self.nbus)
        Q = np.zeros(self.nbus)
        for i in range(self.nbus):
            Vi = V[i]
            theta_i = theta[i]
            for j in self.K[i]:
                V_j = V[j]
                sin_diff = np.sin(theta_i - theta[j])
                cos_diff = np.cos(theta_i - theta[j])
                Gij = self.G[i, j]
                Bij = self.B[i, j]
                Vj = V[j]

                P[i] += Vi * Vj * (Gij * cos_diff + Bij * sin_diff)
                Q[i] += Vi * Vj * (Gij * sin_diff - Bij * cos_diff)
        return P, Q

    # Method for Power Mismatch:
    def power_mismatch(self, P, Q):
        dP = self.P_esp - P
        dQ = self.Q_esp - Q

        # Set the mismatch to zero for slack bus:
        for i in self.slack_idx:
            dP[i] = 0
            dQ[i] = 0

        # Set the Q mismatch to zero for PV buses:
        for i in self.pv_idx:
            dQ[i] = 0
        return dP, dQ


    def jacobian(self, theta, V, P, Q):
        n = self.nbus
        G = self.G
        B = self.B
        H = np.zeros((n, n)) # dP/dtheta
        N = np.zeros((n, n)) # dP/dV
        M = np.zeros((n, n)) # dQ/dtheta
        L = np.zeros((n, n)) # dQ/dV

        for i in range(n):
            V_i = V[i]
            theta_i = theta[i]
            B_ii = B[i, i]
            G_ii = G[i, i]
            P_i = P[i]
            Q_i = Q[i]
            for j in self.omega[i]:
                V_j = V[j]
                sin_diff = np.sin(theta_i - theta[j])
                cos_diff = np.cos(theta_i - theta[j])
                Gij = G[i, j]
                Bij = B[i, j]

                H[i, j] =  V_i * V_j * (Gij * sin_diff - Bij * cos_diff)
                N[i, j] = V_i * (Gij * cos_diff + Bij * sin_diff)
                M[i, j] = -V_i * V_j * (Gij * cos_diff + Bij * sin_diff)
                L[i, j] = V_i * (Gij * sin_diff - Bij * cos_diff)

            # Set the diagonal elements of H, N, M, and L
            H[i, i] = -V_i ** 2 * B_ii - Q_i
            N[i, i] = (P_i + V_i ** 2 * G_ii) / V_i
            M[i, i] = P_i - V_i ** 2 * G_ii
            L[i, i] = (Q_i - V_i ** 2 * B_ii) / V_i
            
        J = np.block([[H, N], [M, L]])

        for i in self.slack_idx:
            J[i, :] = 0   # P row equation set to zero
            J[i, i] = 1   # excpect the diagonal element, which is 1

            J[n + i, :] = 0 # Q row equation set to zero
            J[n + i, n + i] = 1 # except the diagonal element, which is 1
        
        for i in self.pv_idx:
            J[n + i, :] = 0 # Q row equation set to zero
            J[n + i, n + i] = 1 # except the diagonal element, which is 1
        
        return J

    def solve(self, tol_P = 1e-6, tol_Q = 1e-6, max_iter = 100, verbose = False):
        """
        Solves the power flow problem using the Newton-Raphson method.
        If verbose is True, prints detailed iteration information.
        """
        V = self.V_0
        theta = self.theta_0
            
        nbus = self.nbus

        for iter in range(max_iter):
            P, Q = self.pq_calc(theta, V)
            dP, dQ = self.power_mismatch(P, Q)
            dX = np.concatenate((dP, dQ))

            if verbose:
                print(f" \n=== Iteration {iter} === ")
                for i, bus in enumerate(self.network.buses):
                    print(f"{bus.name}: P = {P[i]:.4f}pu, Q = {Q[i]:.4f}pu, V = {V[i]:.4f}pu, theta = {np.rad2deg(theta[i]):.4f}°")
                    

            if np.linalg.norm(dP, np.inf)< tol_P and np.linalg.norm(dQ, np.inf) < tol_Q:
                print("Converged in", iter, "iterations.")
                break

            J = self.jacobian(theta, V, P, Q)
            dX = np.linalg.solve(J, dX)
            theta = theta + dX[:nbus]
            V = V + dX[nbus:]

        else:
            print("Failed to converge in", max_iter, "iterations.")

        # Atualize state variables
        self.V = V
        self.theta = np.rad2deg(theta)

    def _get_line_flows(self):
        """
        Calculate the line flows based on the solved voltage angles and magnitudes.
        Returns:
            flows (np.ndarray): Array of line flows in pu.
        """
        flows = []
        for line in self.network.lines:
            j = self.bus_idx[line.from_bus.id]
            i = self.bus_idx[line.to_bus.id]

            theta_i = np.deg2rad(self.theta[i])
            theta_j = np.deg2rad(self.theta[j])
            V_i = self.V[i]
            V_j = self.V[j]

            if line.reactance == 0:
                raise ValueError(f"Line {line.id} has zero reactance, cannot calculate flow.")
            
            #flow = (V_i * V_j * (self.G[i, j] * np.cos(theta_i - theta_j) + self.B[i, j] * np.sin(theta_i - theta_j)))
            flow = V_i**2 * self.G[i, j] - V_i * V_j * (self.G[i, j] * np.cos(theta_i - theta_j) + self.B[i, j] * np.sin(theta_i - theta_j))
            flows.append(flow)
        self.flows = np.array(flows)
        return self.flows

    def get_line_flows(self):
        """
        Calcula os fluxos de potência ativa Pij (de i para j) e Pji (de j para i) para cada linha.
        Retorna:
            flows_from (np.ndarray): Fluxos do lado from_bus (Pij).
            flows_to (np.ndarray): Fluxos do lado to_bus (Pji).
        """
        flows_from = []
        flows_to = []
        V = self.V
        theta = self.theta
        for line in self.network.lines:
            i = self.bus_idx[line.from_bus.id]
            j = self.bus_idx[line.to_bus.id]
            r = getattr(line, 'r', 0.0)
            x = getattr(line, 'x', 0.0)
            b_shunt = getattr(line, 'b_half', 0.0)
            z = r + 1j * x
            y = 1 / z if z != 0 else 0
            g = np.real(y)
            b = np.imag(y)

            Vi = V[i]
            Vj = V[j]
            thetai = np.deg2rad(theta[i])
            thetaj = np.deg2rad(theta[j])
            delta = thetai - thetaj

            # Fluxo de potência ativa de i para j (Pij)
            Pij = Vi**2 * g - Vi * Vj * (g * np.cos(delta) + b * np.sin(delta)) 

            # Fluxo de potência ativa de j para i (Pji)
            Pji = Vj**2 * g - Vj * Vi * (g * np.cos(-delta) + b * np.sin(-delta))

            flows_from.append(Pij)
            flows_to.append(Pji)
        return np.array(flows_from), np.array(flows_to)