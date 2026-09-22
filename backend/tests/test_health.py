from fastapi.testclient import TestClient

def test_root_endpoint(app_client: TestClient) -> None:
    response = app_client.get("/")
    assert response.status_code == 200
    assert "name" in response.json()
    assert response.json()["name"] == "HealthNet"

def test_health_endpoint(app_client: TestClient) -> None:
    response = app_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "services" in data

def test_openapi_docs(app_client: TestClient) -> None:
    response = app_client.get("/docs")
    assert response.status_code == 200

def test_openapi_json(app_client: TestClient) -> None:
    response = app_client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "paths" in data
