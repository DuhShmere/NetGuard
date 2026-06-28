from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

def test_list_devices_empty():
    res = client.get("/devices/")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_login_invalid():
    res = client.post("/auth/login", json={"username": "bad", "password": "wrong"})
    assert res.status_code == 401
