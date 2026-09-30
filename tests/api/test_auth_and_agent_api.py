from __future__ import annotations

import os

from fastapi.testclient import TestClient

from app.api.app import create_app


def test_register_login_and_me():
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

    client = TestClient(create_app())

    registered = client.post(
        "/auth/register",
        json={
            "email": "demo@example.com",
            "password": "password123",
        },
    )

    assert registered.status_code == 201

    login = client.post(
        "/auth/login",
        json={
            "email": "demo@example.com",
            "password": "password123",
        },
    )

    assert login.status_code == 200

    token = login.json()["access_token"]

    me = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me.status_code == 200
    assert me.json()["email"] == "demo@example.com"