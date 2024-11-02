from pulp import LpProblem, LpMinimize, LpVariable, lpSum
import pandas as pd
from endpoints import start_session, end_session, play_round

def load_data():
    refineries = pd.read_csv("data/refineries.csv", sep=';').to_dict(orient='records')
    storage_tanks = pd.read_csv("data/tanks.csv", sep=';').to_dict(orient='records')
    customers = pd.read_csv("data/customers.csv", sep=';').to_dict(orient='records')
    connections = pd.read_csv("data/connections.csv", sep=';').to_dict(orient='records')
    demands = pd.read_csv("data/demands.csv", sep=';').to_dict(orient='records')
    teams = pd.read_csv("data/teams.csv", sep=';').to_dict(orient='records')
    
    return refineries, storage_tanks, customers, connections, demands, teams

refineries, storages, clients, con, d, t = load_data()

# Definim problema de optimizare ca problemă de minimizare a costului
problem = LpProblem("Fuel_Delivery_Optimization", LpMinimize)

session_id = start_session()
print(session_id)

client_response = play_round(session_id, {"day": 0, "movements": []})

print(client_response)


end_session()
exit()
# # Parametri exemplu
# refineries = [(r1.id) for r1 in r]  # rafinării
# storages = []    # rezervoare intermediare
# clients = ["C1", "C2"]     # clienți
# days = range(1, 8)         # o săptămână (pentru simplificare)

# # Capacități, cerințe și costuri exemplu
# production_capacity = {"R1": 100, "R2": 120}  # capacitate producție pe rafinărie
# storage_capacity = {"S1": 200, "S2": 150}     # capacitate maximă de stocare
# client_demand = {"C1": 70, "C2": 80}          # cererea zilnică a clienților
# transport_cost = {("R1", "S1"): 10, ("R1", "S2"): 12, ("S1", "C1"): 8, ("S2", "C2"): 9}  # cost de transport
# emission_cost = {"R1": 5, "R2": 4}            # costul emisiilor la pornire

# Variabile de decizie

PIPELINE = {"costPerDistanceAndVolume": 0.05, "co2PerDistanceAndVolume": 0.02, "overUsePenaltyPerVolume": 1.13}
TRUCK = {"costPerDistanceAndVolume": 0.42, "co2PerDistanceAndVolume": 0.31, "overUsePenaltyPerVolume": 0.73}


refineries_dict = {r["id"]: r for r in refineries}
storage_dict = {s["id"]: s for s in storages}
clients_dict = {c["id"]: c for c in clients}
emission_cost = {r["id"]: r["production_co2"] for r in refineries}
production_capacity = {r["id"]: r["production"] for r in refineries}
storage_capacity = {s["id"]: s["capacity"] for s in storages}
client_demand = {c["id"]: c["demand"] for c in clients}

transport_cost = {}
for c in con:
    if c["from_id"] in refineries_dict and c["to_id"] in storage_dict:
        transport_cost[(c["from_id"], c["to_id"])] = c["distance"] * PIPELINE["costPerDistanceAndVolume"]


production = LpVariable.dicts("Production", refineries_dict, lowBound=0)
storage = LpVariable.dicts("Storage", storage_dict, lowBound=0)
transport = LpVariable.dicts("Transport", [(r, s) for r in refineries_dict.keys for s in storage_dict.keys], lowBound=0)
delivery = LpVariable.dicts("Delivery", [(s, c) for s in storage_dict.keys for c in clients_dict.keys], lowBound=0)

problem += (
    lpSum(transport[(r, s)] * transport_cost.get((r, s), 0) for r in refineries_dict.keys for s in storage_dict.keys) +
    lpSum(production[r] * emission_cost[r] for r in refineries_dict.keys)
)

# Constrângeri

# 1. Producția la rafinării să fie sub capacitatea maximă
for r in refineries:
    problem += production[r] <= production_capacity[r], f"ProductionCapacity_{r}"

# 2. Capacitatea de stocare la rezervoare să nu fie depășită
for s in storages:
    problem += storage[s] <= storage_capacity[s], f"StorageCapacity_{s}"

# 3. Cererea zilnică a clienților trebuie să fie satisfăcută
for c in clients:
    problem += lpSum(delivery[(s, c)] for s in storage_dict.keys) >= client_demand[c], f"ClientDemand_{c}"

# 4. Conservarea fluxului între rafinării, rezervoare și clienți
for s in storages:
    inflow = lpSum(transport[(r, s)] for r in refineries)
    outflow = lpSum(delivery[(s, c)] for c in clients)
    problem += inflow - outflow == storage[s], f"FlowConservation_{s}"

# 5. Transportul să fie limitat la cantitățile produse
for r in refineries:
    problem += lpSum(transport[(r, s)] for s in storages) <= production[r], f"TransportLimit_{r}"

# Rezolvarea problemei
problem.solve()

# Afișarea rezultatelor
for v in problem.variables():
    print(f"{v.name} = {v.varValue}")