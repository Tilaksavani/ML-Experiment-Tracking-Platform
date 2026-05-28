from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_run():
    payload = {
        "name": "Unit Test Run",
        "task_type": "classification",
        "dataset": "unit-test-dataset",
        "model_name": "TestModel",
        "seed": 123,
        "config": {"epochs": 2},
    }
    response = client.post("/runs", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Unit Test Run"
    assert body["status"] == "created"
    assert body["config"]["epochs"] == 2
