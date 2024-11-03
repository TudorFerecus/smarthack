import time
import pandas as pd
from collections import defaultdict
from endpoints import start_session, end_session, play_round

# Define data structures
class Refinery:
    def __init__(self, id, name, capacity, max_output, production, overflow_penalty, underflow_penalty, over_output_penalty, production_cost, production_co2, initial_stock, node_type):
        self.id = id
        self.name = name
        self.capacity = capacity
        self.max_output = max_output
        self.production = production
        self.overflow_penalty = overflow_penalty
        self.underflow_penalty = underflow_penalty
        self.over_output_penalty = over_output_penalty
        self.production_cost = production_cost
        self.production_co2 = production_co2
        self.initial_stock = initial_stock
        self.node_type = node_type

class Tank:
    def __init__(self, id, name, capacity, max_input, max_output, overflow_penalty, underflow_penalty, over_input_penalty, over_output_penalty, initial_stock, node_type):
        self.id = id
        self.name = name
        self.capacity = capacity
        self.max_input = max_input
        self.max_output = max_output
        self.overflow_penalty = overflow_penalty
        self.underflow_penalty = underflow_penalty
        self.over_input_penalty = over_input_penalty
        self.over_output_penalty = over_output_penalty
        self.initial_stock = initial_stock
        self.node_type = node_type

class Customer:
    def __init__(self, id, name, max_input, over_input_penalty, late_delivery_penalty, early_delivery_penalty, node_type):
        self.id = id
        self.name = name
        self.max_input = max_input
        self.over_input_penalty = over_input_penalty
        self.late_delivery_penalty = late_delivery_penalty
        self.early_delivery_penalty = early_delivery_penalty
        self.node_type = node_type

class Connection:
    def __init__(self, from_id, to_id, distance, lead_time, max_capacity, connection_type, ratio):
        self.from_id = from_id
        self.to_id = to_id
        self.distance = distance
        self.lead_time = lead_time
        self.max_capacity = max_capacity
        self.connection_type = connection_type
        self.ratio = ratio

# Load data from CSV files
def load_data():
    connections = pd.read_csv('connections.csv', delimiter=';')
    customers = pd.read_csv('customers.csv', delimiter=';')
    refineries = pd.read_csv('refineries.csv', delimiter=';')
    tanks = pd.read_csv('tanks.csv', delimiter=';')

    return connections, customers, refineries, tanks

# Calculate transport ratios and build a graph
def build_graph(connections, refineries, tanks):
    transport_graph = defaultdict(list)
    for _, row in connections.iterrows():
        from_id = row['from_id']
        to_id = row['to_id']
        distance = row['distance']
        lead_time = row['lead_time_days']
        max_capacity = row['max_capacity']

        ratio = max_capacity / (lead_time * distance) if lead_time > 0 else 0
        transport_graph[from_id].append(Connection(from_id, to_id, distance, lead_time, max_capacity, row['connection_type'], ratio))

    return transport_graph

# Find the best transport connection based on the greedy ratio
def find_best_transport(node_id, transport_graph):
    best_connection = max(transport_graph.get(node_id, []), key=lambda conn: conn.ratio, default=None)
    return best_connection

# Process delivery requests for a specific day
def process_requests_for_day(customers, tanks, refineries, transport_graph, daily_demands, current_day):
    movements = []
    unfulfilled_demands = []

    for demand in daily_demands:
        print(f"Processing delivery request for customer ID {demand['customerId']}")

        # Find the customer based on customer_id
        customer = customers.get(demand['customerId'], None)
        if not customer:
            print(f"Customer with ID {demand['customerId']} not found.")
            continue

        # Check if the demand's time frame is valid
        if demand['startDay'] < demand['postDay'] + 3:
            print(f"Delivery cannot start before day {demand['postDay'] + 3}.")
            continue

        # Find the closest tank that can fulfill the request
        closest_tank_id = None
        best_ratio = -1
        for tank_id, tank in tanks.items():
            if tank.max_output >= demand['amount'] and tank.initial_stock > 0:
                best_transport = find_best_transport(tank_id, transport_graph)
                if best_transport and best_transport.ratio > best_ratio:
                    closest_tank_id = tank_id
                    best_ratio = best_transport.ratio

        if closest_tank_id:
            # Check if the tank can fulfill the request directly
            tank = tanks[closest_tank_id]
            quantity_to_deliver = min(demand['amount'], tank.initial_stock)

            # Check if the delivery will arrive within the correct timeframe
            if quantity_to_deliver > 0 and current_day + best_transport.lead_time >= demand['startDay'] and current_day + best_transport.lead_time <= demand['endDay']:
                print(f"Delivering {quantity_to_deliver} units from {tank.name} to {customer.name} on delivery day {current_day + best_transport.lead_time}.")
                tank.initial_stock -= quantity_to_deliver  # Update stock
                movements.append({"connectionId": best_transport.from_id, "amount": quantity_to_deliver})
            else:
                # print(f"{tank.name} does not have enough stock to fulfill the request or delivery is out of timeframe.")
                unfulfilled_demands.append(demand)
        else:
            unfulfilled_demands.append(demand)

    # Transport fuel from refineries to tanks to avoid overflow
    for refinery in refineries.values():
        if refinery.initial_stock > 0:
            best_transport = find_best_transport(refinery.id, transport_graph)
            if best_transport:
                for tank_id, tank in tanks.items():
                    if tank.capacity - tank.initial_stock > 0:
                        quantity_to_deliver = min(refinery.initial_stock, tank.capacity - tank.initial_stock, best_transport.max_capacity)

                        # Check if the delivery will arrive within the correct timeframe
                        if quantity_to_deliver > 0 and current_day + best_transport.lead_time <= 42:  # Ensure delivery is within the simulation period
                            print(f"Transporting {quantity_to_deliver} units from {refinery.name} to {tank.name} on delivery day {current_day + best_transport.lead_time}.")
                            refinery.initial_stock -= quantity_to_deliver  # Update stock
                            tank.initial_stock += quantity_to_deliver  # Update stock
                            movements.append({"connectionId": best_transport.from_id, "amount": quantity_to_deliver})

    return movements, unfulfilled_demands

# Main function
def main():
    connections, customers, refineries, tanks = load_data()
    
    # Convert refineries and tanks to dictionaries for easy access
    refineries_dict = {row['id']: Refinery(**row) for _, row in refineries.iterrows()}
    tanks_dict = {row['id']: Tank(**row) for _, row in tanks.iterrows()}
    
    # Convert customers to a dictionary for easy access
    customers_dict = {row['id']: Customer(**row) for _, row in customers.iterrows()}
    
    transport_graph = build_graph(connections, refineries_dict, tanks_dict)
    
    session_id = start_session()
    day = 0

    # Initial round 0
    print(f"\nDay {day + 1}")
    body = {"day": day, "movements": []}
    response = play_round(session_id, body)
    daily_demands = response.get("demand", [])
    unfulfilled_demands = daily_demands

    # Process subsequent rounds
    last_response = None
    for day in range(1, 43):
        print(f"\nDay {day + 1}")
        daily_demands = unfulfilled_demands
        movements, unfulfilled_demands = process_requests_for_day(customers_dict, tanks_dict, refineries_dict, transport_graph, daily_demands, day)
        body = {"day": day, "movements": movements}
        response = play_round(session_id, body)
        new_demands = response.get("demand", [])
        unfulfilled_demands.extend(new_demands)
        last_response = response
        time.sleep(1)  # Add delay to avoid hitting the API rate limit

    end_session(session_id)
    print(last_response)

if __name__ == "__main__":
    main()