import requests

API_KEY = "7bcd6334-bc2e-4cbf-b9d4-61cb9e868869"
BASE_URL = "http://localhost:8080/api/v1"

def start_session():
    response = requests.post(f"{BASE_URL}/session/start", headers={"API-KEY": API_KEY}, json={})
    return response.text.strip()  # Extract the session ID directly from the response body

def end_session(session_id):
    response = requests.post(f"{BASE_URL}/session/end", headers={"API-KEY": API_KEY}, json={})
    return response.json()

def play_round(session_id, body):
    response = requests.post(f"{BASE_URL}/play/round", headers={"API-KEY": API_KEY, "SESSION-ID": session_id}, json=body)
    return response.json()