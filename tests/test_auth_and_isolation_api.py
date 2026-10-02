"""API-level auth + multi-project isolation tests (spec section 47).

Uses a throwaway SQLite file per test via DATABASE_URL so these never touch
the real dev Postgres database and don't require Ollama to be running
(no endpoint here exercises the chat/orchestrator path).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.app import create_app
from app.config.settings import get_settings


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


def _signup(client: TestClient, email: str = "ada@example.com", password: str = "hunter2pass"):
    return client.post(
        "/api/v1/auth/signup",
        json={"name": "Ada Lovelace", "email": email, "password": password},
    )


def _auth_headers(client: TestClient, email: str = "ada@example.com", password: str = "hunter2pass") -> dict:
    res = _signup(client, email, password)
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------------------------- auth


def test_signup_succeeds(client: TestClient):
    res = _signup(client)
    assert res.status_code == 201
    body = res.json()
    assert "access_token" in body
    assert body["user"]["email"] == "ada@example.com"
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]


def test_duplicate_signup_fails(client: TestClient):
    _signup(client)
    res = _signup(client)
    assert res.status_code == 409


def test_login_succeeds(client: TestClient):
    _signup(client)
    res = client.post(
        "/api/v1/auth/login", json={"email": "ada@example.com", "password": "hunter2pass"}
    )
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_login_invalid_password_fails(client: TestClient):
    _signup(client)
    res = client.post(
        "/api/v1/auth/login", json={"email": "ada@example.com", "password": "wrong-password"}
    )
    assert res.status_code == 401


def test_unauthorized_request_is_rejected(client: TestClient):
    res = client.get("/api/v1/projects")
    assert res.status_code == 401


def test_me_returns_current_user(client: TestClient):
    headers = _auth_headers(client)
    res = client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["email"] == "ada@example.com"


# ----------------------------------------------------------------- projects


def test_user_can_create_and_list_projects(client: TestClient):
    headers = _auth_headers(client)
    res = client.post("/api/v1/projects", json={"name": "SafePlate"}, headers=headers)
    assert res.status_code == 201
    project_id = res.json()["id"]

    res = client.get("/api/v1/projects", headers=headers)
    assert res.status_code == 200
    names = [p["name"] for p in res.json()]
    assert "SafePlate" in names
    assert res.json()[0]["id"] == project_id


def test_user_can_update_own_project(client: TestClient):
    headers = _auth_headers(client)
    project_id = client.post("/api/v1/projects", json={"name": "SafePlate"}, headers=headers).json()["id"]

    res = client.put(
        "/api/v1/projects/{}".format(project_id), json={"industry": "FoodTech"}, headers=headers
    )
    assert res.status_code == 200
    assert res.json()["industry"] == "FoodTech"


def test_user_can_archive_own_project(client: TestClient):
    headers = _auth_headers(client)
    project_id = client.post("/api/v1/projects", json={"name": "SafePlate"}, headers=headers).json()["id"]

    res = client.put(
        "/api/v1/projects/{}".format(project_id), json={"archived": True}, headers=headers
    )
    assert res.status_code == 200
    assert res.json()["archived"] is True

    res = client.get("/api/v1/projects", headers=headers)
    assert project_id not in [p["id"] for p in res.json()]


# ------------------------------------------------------- cross-user isolation


def test_user_cannot_access_another_users_project(client: TestClient):
    headers_a = _auth_headers(client, email="ada@example.com")
    project_a = client.post(
        "/api/v1/projects", json={"name": "SafePlate"}, headers=headers_a
    ).json()["id"]

    headers_b = _auth_headers(client, email="bo@example.com")

    res = client.get(f"/api/v1/projects/{project_a}", headers=headers_b)
    assert res.status_code == 403

    res = client.put(
        f"/api/v1/projects/{project_a}", json={"name": "Hijacked"}, headers=headers_b
    )
    assert res.status_code == 403

    res = client.delete(f"/api/v1/projects/{project_a}", headers=headers_b)
    assert res.status_code == 403


def test_user_cannot_list_conversations_of_unowned_project(client: TestClient):
    headers_a = _auth_headers(client, email="ada@example.com")
    project_a = client.post(
        "/api/v1/projects", json={"name": "SafePlate"}, headers=headers_a
    ).json()["id"]
    client.post(f"/api/v1/projects/{project_a}/conversations", json={}, headers=headers_a)

    headers_b = _auth_headers(client, email="bo@example.com")
    res = client.get(f"/api/v1/projects/{project_a}/conversations", headers=headers_b)
    assert res.status_code == 403


def test_conversation_and_messages_isolated_across_projects(client: TestClient):
    headers = _auth_headers(client)
    project_a = client.post(
        "/api/v1/projects", json={"name": "SafePlate"}, headers=headers
    ).json()["id"]
    project_b = client.post(
        "/api/v1/projects", json={"name": "AI Tutoring Platform"}, headers=headers
    ).json()["id"]

    conv_a = client.post(
        f"/api/v1/projects/{project_a}/conversations", json={}, headers=headers
    ).json()["id"]
    conv_b = client.post(
        f"/api/v1/projects/{project_b}/conversations", json={}, headers=headers
    ).json()["id"]

    convos_a = client.get(f"/api/v1/projects/{project_a}/conversations", headers=headers).json()
    convos_b = client.get(f"/api/v1/projects/{project_b}/conversations", headers=headers).json()

    assert [c["id"] for c in convos_a] == [conv_a]
    assert [c["id"] for c in convos_b] == [conv_b]


def test_conversation_not_accessible_by_wrong_id(client: TestClient):
    headers = _auth_headers(client)
    res = client.get("/api/v1/conversations/conv_does_not_exist", headers=headers)
    assert res.status_code == 404


# -------------------------------------------------------------- persistence


def test_data_persists_across_new_client_against_same_db(tmp_path, monkeypatch):
    db_path = tmp_path / "persist.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()

    with TestClient(create_app()) as first:
        headers = _auth_headers(first)
        project_id = first.post(
            "/api/v1/projects", json={"name": "SafePlate"}, headers=headers
        ).json()["id"]

    # Simulate a backend restart: fresh app instance, same sqlite file on disk.
    get_settings.cache_clear()
    with TestClient(create_app()) as second:
        login = second.post(
            "/api/v1/auth/login", json={"email": "ada@example.com", "password": "hunter2pass"}
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        res = second.get("/api/v1/projects", headers=headers)
        assert res.status_code == 200
        assert any(p["id"] == project_id for p in res.json())

    get_settings.cache_clear()
