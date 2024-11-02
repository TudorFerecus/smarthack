import pulp
import pandas as pd


def load_data():
    refineries = pd.read_csv("data/refineries.csv", sep=';').to_dict(orient='records')
    storage_tanks = pd.read_csv("data/tanks.csv", sep=';').to_dict(orient='records')
    customers = pd.read_csv("data/customers.csv", sep=';').to_dict(orient='records')
    connections = pd.read_csv("data/connections.csv", sep=';').to_dict(orient='records')
    demands = pd.read_csv("data/demands.csv", sep=';').to_dict(orient='records')
    teams = pd.read_csv("data/teams.csv", sep=';').to_dict(orient='records')
    
    return refineries, storage_tanks, customers, connections, demands, teams


# Create a LP minimization problem