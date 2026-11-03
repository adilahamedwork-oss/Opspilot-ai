from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_database_demo_returns_investigation():
    response = client.get("/incidents/demo/database")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "checkout-api"
    assert "database" in data["probable_root_cause"].lower()
    assert data["mode"] in ("rules", "ai")
    assert data["incident_id"]

def test_custom_incident():
    response = client.post("/incidents/investigate", json={
        "service": "test-api", "severity": "high",
        "description": "Test HTTP 500 failure",
        "logs": ["ERROR HTTP 500 internal server error"],
        "metrics": {"cpu_percent": 96}
    })
    assert response.status_code == 200
    assert response.json()["evidence"]
    assert response.json()["remediation"]

def test_unknown_demo():
    assert client.get("/incidents/demo/not-real").status_code == 404
