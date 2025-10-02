import numpy as np
from power.models.electricity_models.network_models import *

class DC_PF:
    def __init__(self, network: Network):

        network.ACtoDC()  # Convert AC network to DC
        self.network = network

        # Identify buses by index
        self.bus_idx = {bus.id: i for i, bus in enumerate(network.buses)}

        # Identify bus types by index
        self.slack_idx = next(i for i, bus in enumerate(network.buses) if bus.bus_type == 'Slack')

        # Active power vector
        self.P = np.array([bus.p for bus in network.buses])

        # Reduced admittance matrix and power vector
        B = network.get_B()
        B_red = np.delete(B, self.slack_idx, axis=0)
        self.B_red = -1*np.delete(B_red, self.slack_idx, axis=1)
        self.P_red = np.delete(self.P, self.slack_idx)

    def get_line_flows(self):
        """
        Calculate the line flows based on the DC power flow solution.
        Returns:
            line_flows (np.ndarray): The calculated line flows for each line in the network.
        """

        # Ensure the DC power flow has been solved
        if not hasattr(self, 'theta_rad'):
            raise ValueError("DC power flow has not been solved yet. Call solve() first.")

        flows = []
        for line in self.network.lines:
            i = self.bus_idx[line.from_bus.id]
            j = self.bus_idx[line.to_bus.id]

            theta_i = self.theta_rad[i]
            theta_j = self.theta_rad[j]

            if line.reactance == 0:
                raise ValueError(f"Line {line.id} has zero reactance, cannot calculate flow.")
            
            flow = (theta_i - theta_j) / line.reactance
            flows.append(flow)
        self.flows = np.array(flows)
        
        return self.flows

    def solve(self):
        """
        Solve the DC power flow problem.
        """
        # Solve B_red * theta_red = P_red
        theta = np.linalg.solve(self.B_red, self.P_red)

        # Reinsert slack angle (theta = 0) into full vector
        theta = np.insert(theta, self.slack_idx, 0)

        # Store solution
        self.theta_rad = theta
        self.theta_deg = np.rad2deg(theta)

        return self.theta_deg

    def print_results(self):
        """
        Print the results of the DC power flow solution.
        """

        if not hasattr(self, 'theta_deg'):
            self.solve()
        if not hasattr(self, 'flows'):
            self.get_line_flows()

        print("-" * 40)
        print("DC Power Flow Results:")
        print("-" * 40)

        for bus, theta in zip(self.network.buses, self.theta_deg):
            print(f"{bus.name}: Angle = {theta:.4f}°")
        print("-" * 40)

        print("🔌 Line Flows (in pu):")
        print("-" * 40)
        for line, flow in zip(self.network.lines, self.flows):
            print(f"{line.name} ({line.from_bus.name} -> {line.to_bus.name}): Flow = {flow:.4f} pu")
    