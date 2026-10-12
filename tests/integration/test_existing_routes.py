"""Testes reais dos endpoints que já existem no projeto recebido."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_home():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "APeX-API"

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_duckdb():
    response = client.get("/test/duckdb")
    assert response.status_code == 200
    assert response.json()["result"] == 42

def test_openapi():
    response = client.get("/openapi.json")
    assert response.status_code == 200
