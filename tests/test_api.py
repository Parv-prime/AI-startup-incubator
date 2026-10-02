from fastapi.testclient import TestClient

from app.api.app import create_app
from app.config.settings import get_settings


def test_health_endpoint(monkeypatch):
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert "model_runtime" in body
    assert "status" in body
