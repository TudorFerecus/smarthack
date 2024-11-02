import numpy as np
import pandas as pd
import random

# Load data from CSV files
def load_data():
    refineries = pd.read_csv("data/refineries.csv", sep=';').to_dict(orient='records')
    storage_tanks = pd.read_csv("data/tanks.csv", sep=';').to_dict(orient='records')
    customers = pd.read_csv("data/customers.csv", sep=';').to_dict(orient='records')
    connections = pd.read_csv("data/connections.csv", sep=';').to_dict(orient='records')
    demands = pd.read_csv("data/demands.csv", sep=';').to_dict(orient='records')
    teams = pd.read_csv("data/teams.csv", sep=';').to_dict(orient='records')
    
    return refineries, storage_tanks, customers, connections, demands, teams

# Initialize data
refineries, storage_tanks, customers, connections, demands, teams = load_data()

# Q-learning parameters
alpha = 0.1
gamma = 0.95
epsilon = 1.0
epsilon_decay = 0.99
min_epsilon = 0.01

# Initialize Q-table with a simplified shape based on unique indices
q_table = np.zeros((len(refineries) * len(storage_tanks) * len(customers), 42))

# Helper function to encode the state and action into a unique index
def encode_state(state):
    # Example: Combine stocks in refineries, storage tanks, and demands into a hashable state ID
    return hash(frozenset(state["refineries"].items())) % len(refineries)

def encode_action(action):
    # Example: Generate an index for the action based on its 'from' and 'to' attributes
    return hash((action["from"], action["to"], action["amount"])) % 42  # Adjust range if needed

# Reward function
def calculate_reward(action, penalties):
    base_reward = -action.get('cost', 0)
    penalty_cost = -sum(penalties)
    return base_reward + penalty_cost

# Initialize the state with refineries, storage tanks, and customer demands
def initialize_state():
    state = {
        "refineries": {refinery["id"]: refinery["initial_stock"] for refinery in refineries},
        "storage_tanks": {tank["id"]: tank["initial_stock"] for tank in storage_tanks},
        "customer_demands": {demand["customer_id"]: demand["quantity"] for demand in demands},
        "in_transit": []  # Movements in transit
    }
    return state

# Randomly choose an action based on the available connections and stock levels
def choose_random_action(state):
    from_node = random.choice(refineries + storage_tanks)
    to_node = random.choice(storage_tanks + customers)
    
    # Set max_amount to be the minimum of initial stock or a set limit (e.g., 100)
    max_amount = min(from_node.get("initial_stock", 0), 100)
    
    # Check if max_amount is less than 1, if so, skip action or handle accordingly
    if max_amount < 1:
        return choose_random_action(state)  # Recurse until we find a valid action

    action = {
        "from": from_node["id"],
        "to": to_node["id"],
        "amount": random.randint(1, max_amount)
    }
    return action

# Choose the best action based on the Q-table
def choose_best_action(state):
    # Placeholder implementation
    return choose_random_action(state)

# Find the connection details for the action
def get_connection_cost(action):
    for connection in connections:
        if connection["from_id"] == action["from"] and connection["to_id"] == action["to"]:
            cost = connection["distance"] * 0.01
            return cost
    return 0

# Environment Simulation Function
def take_action(state, action):
    new_state = state.copy()
    penalties = []

    # Calculate the cost of the action
    action['cost'] = get_connection_cost(action)

    # Update state based on action and calculate penalties

    return new_state, penalties

# Training loop
for episode in range(1000):
    state = initialize_state()
    total_reward = 0

    for day in range(42):
        if random.uniform(0, 1) < epsilon:
            action = choose_random_action(state)
        else:
            action = choose_best_action(state)

        new_state, penalties = take_action(state, action)
        reward = calculate_reward(action, penalties)

        # Encode state and action for Q-table access
        state_index = encode_state(state)
        action_index = encode_action(action)

        # Update Q-table
        q_table[state_index, action_index] = q_table[state_index, action_index] + alpha * (
            reward + gamma * np.max(q_table[encode_state(new_state), :]) - q_table[state_index, action_index]
        )

        state = new_state
        total_reward += reward

    epsilon = max(min_epsilon, epsilon * epsilon_decay)
    print(f"Episode {episode + 1}: Total Reward = {total_reward}")

print("Training complete.")
