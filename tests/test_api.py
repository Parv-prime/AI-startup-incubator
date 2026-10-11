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


def test_liveness_endpoint_is_cheap_and_secret_free():
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_rate_limit_window():
    from app.security.rate_limit import check_rate_limit

    assert all(check_rate_limit("rl-user", 2, now=100.0 + i) for i in range(2))
    assert check_rate_limit("rl-user", 2, now=102.0) is False
    assert check_rate_limit("rl-user", 2, now=170.0) is True  # window has passed
    assert check_rate_limit("other", 0) is True  # 0 disables the throttle
