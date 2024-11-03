from pulp import LpProblem, LpMinimize, LpVariable, lpSum
import pandas as pd
from endpoints import start_session, end_session, play_round

# Load data function with CSV parsing
def load_data():
    refineries = pd.read_csv("data/refineries.csv", sep=';').to_dict(orient='records')
    storage_tanks = pd.read_csv("data/tanks.csv", sep=';').to_dict(orient='records') 
    customers = pd.read_csv("data/customers.csv", sep=';').to_dict(orient='records')
    connections = pd.read_csv("data/connections.csv", sep=';').to_dict(orient='records')
    demands = pd.read_csv("data/demands.csv", sep=';').to_dict(orient='records')
    teams = pd.read_csv("data/teams.csv", sep=';').to_dict(orient='records')
    return refineries, storage_tanks, customers, connections, demands, teams

# Initialize data
refineries, storages, clients, con, d, t = load_data()

# Define optimization problem base structure
problem = LpProblem("Fuel_Delivery_Optimization", LpMinimize)

# Start session
session_id = start_session()
client_response = play_round(session_id, {"day": 0, "movements": []})["demand"]

# Parameters for cost
PIPELINE = {"costPerDistanceAndVolume": 0.05, "co2PerDistanceAndVolume": 0.02, "overUsePenaltyPerVolume": 1.13}
TRUCK = {"costPerDistanceAndVolume": 0.42, "co2PerDistanceAndVolume": 0.31, "overUsePenaltyPerVolume": 0.73}

# Convert data into dictionaries for easy access
refineries_dict = {r["id"]: r for r in refineries}
storage_dict = {s["id"]: s for s in storages}
clients_dict = {c["id"]: c for c in clients}

# Define transport costs for existing connections
transport_cost = {}
existing_connections = []
for c in con:
    if c["from_id"] in refineries_dict and c["to_id"] in storage_dict:
        cost_per_distance = PIPELINE["costPerDistanceAndVolume"] if c["connection_type"] == "pipeline" else TRUCK["costPerDistanceAndVolume"]
        transport_cost[(c["from_id"], c["to_id"])] = c["distance"] * cost_per_distance
        existing_connections.append((c["from_id"], c["to_id"]))

# Initialize storage levels
for s in storage_dict.keys():
    storage_dict[s]["current_stock"] = storage_dict[s].get("initial_stock", 0)

# Loop over each day
for day in range(1, 43):
    # Fetch demand for the day
    client_demand = {c["customerId"]: c["amount"] for c in client_response}

    # Clear problem to re-add variables and constraints for the day
    problem = LpProblem("Fuel_Delivery_Optimization", LpMinimize)
    msg = {"day": day, "movements": []}

    # Define variables for production, storage, transport, delivery, and penalties
    production = LpVariable.dicts("Production", refineries_dict.keys(), lowBound=0)
    storage = LpVariable.dicts("Storage", storage_dict.keys(), lowBound=0)
    transport = LpVariable.dicts("Transport", existing_connections, lowBound=0)
    delivery = LpVariable.dicts("Delivery", [(s, c) for s in storage_dict.keys() for c in clients_dict.keys()], lowBound=0)
    unmet_demand_penalty = LpVariable.dicts("UnmetDemandPenalty", clients_dict.keys(), lowBound=0)

    # Objective function: prioritize delivery to clients and minimize unmet demand
    problem += (
        lpSum(transport[(r, s)] * transport_cost[(r, s)] for (r, s) in existing_connections) +
        lpSum(unmet_demand_penalty[c] * 10000000 for c in clients_dict.keys())  # Large penalty to prioritize delivery
    )

    # Constraints

    # 1. Production and Transport Constraints for Refineries
    for r in refineries_dict.keys():
        max_capacity = refineries_dict[r]["capacity"]
        max_output = refineries_dict[r]["max_output"]
        problem += production[r] <= max_capacity, f"ProductionCapacity_{r}"
        problem += lpSum(transport[(r, s)] for s in storage_dict if (r, s) in existing_connections) <= max_output, f"MaxOutput_{r}"

    # 2. Constraints for Storage Tanks
    for s in storage_dict.keys():
        max_capacity = storage_dict[s]["capacity"]
        max_input = storage_dict[s]["max_input"]
        max_output = storage_dict[s]["max_output"]
        current_stock = storage_dict[s]["current_stock"]
        problem += storage[s] <= max_capacity, f"StorageCapacity_{s}"
        inflow = lpSum(transport[(r, s)] for r in refineries_dict if (r, s) in existing_connections)
        problem += inflow <= max_input, f"MaxInput_{s}"
        outflow = lpSum(delivery[(s, c)] for c in clients_dict)
        problem += outflow <= max_output, f"MaxOutput_{s}"
        problem += storage[s] == current_stock + inflow - outflow, f"DailyStockBalance_{s}"

    # 3. Transport Capacity Constraints for Connections
    added_constraints = set()
    constraint_id = 0  # Inițializăm un contor pentru numele constrângerilor

    # 3. Transport Capacity Constraints for Connections
    for (r, s) in existing_connections:
        max_capacity = next(c["max_capacity"] for c in con if c["from_id"] == r and c["to_id"] == s)
        
        # Creăm un nume unic pentru constrângere
        constraint_name = f"ConnectionCapacity_{constraint_id}"
        constraint_id += 1  # Incrementăm contorul pentru a asigura unicitatea
        
        # Doar dacă constrângerea nu a fost deja adăugată
        if (r, s) not in added_constraints:
            problem += transport[(r, s)] <= max_capacity, constraint_name
            added_constraints.add((r, s))

    # 4. Daily client demand fulfillment with penalty for unmet demand
    for c in clients_dict.keys():
        if client_demand.get(c, 0) > 0:
            problem += (
                lpSum(delivery[(s, c)] for s in storage_dict) + unmet_demand_penalty[c] >= client_demand[c],
                f"ClientDemand_{c}"
            )

    # Solve the problem for the day
    problem.solve()

    # Collect and log results for the day's movements
    for v in problem.variables():
        test = v.name.replace("_", "-").split("',-'")
        if test[0].startswith("Transport"):
            test[0] = test[0].replace("Transport-('", "")
            test[1] = test[1].replace("')", "")
            for c in con:
                if c["from_id"] == test[0] and c["to_id"] == test[1] and v.varValue > 0:
                    msg["movements"].append({"connectionId": c["id"], "amount": v.varValue})
        elif test[0].startswith("Delivery"):
            test[0] = test[0].replace("Delivery-('", "")
            test[1] = test[1].replace("')", "")
            for c in con:
                if c["from_id"] == test[0] and c["to_id"] == test[1] and v.varValue > 0:
                    msg["movements"].append({"connectionId": c["id"], "amount": v.varValue})

    # Update storage levels based on the day's solution
    for s in storage_dict.keys():
        storage_dict[s]["current_stock"] = storage[s].varValue

    # Send the results to the session for the current day
    res = play_round(session_id, msg)
    print(f"Results for Day {day}:", res)

# End the session after 42 days
end_session()