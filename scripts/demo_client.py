import time
import requests

API = "http://localhost:8000"

run = requests.post(f"{API}/runs/demo/start?task_type=classification", timeout=10).json()
print("Started:", run["id"])

for _ in range(8):
    detail = requests.get(f"{API}/runs/{run['id']}", timeout=10).json()
    metrics = requests.get(f"{API}/runs/{run['id']}/metrics", timeout=10).json()
    print(detail["status"], "metrics:", len(metrics))
    if detail["status"] in {"completed", "failed"}:
        break
    time.sleep(1)
