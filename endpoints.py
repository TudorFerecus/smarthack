import requests
import time

def start_session():
    x = requests.post('http://localhost:8081/api/v1/session/start', headers={"API-KEY": "7bcd6334-bc2e-4cbf-b9d4-61cb9e868869"}, json={})
    return x.text

def end_session():
    x = requests.post('http://localhost:8081/api/v1/session/end', headers={"API-KEY": "7bcd6334-bc2e-4cbf-b9d4-61cb9e868869"}, json={}).json()
    return x

def play_round(session_id, body):
    x = requests.post('http://localhost:8081/api/v1/round/play', headers={"API-KEY": "7bcd6334-bc2e-4cbf-b9d4-61cb9e868869", "SESSION-ID": session_id}, json={body}).json()
    return x


