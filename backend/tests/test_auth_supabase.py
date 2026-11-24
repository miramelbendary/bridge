"""Supabase token verification, tested with locally minted tokens.

These tests do not contact a real Supabase project (none is configured). They verify that BRIDGE
accepts correctly signed Supabase-style tokens and rejects everything else.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.main import create_app
from app.security import tokens
from tests.conftest import auth

SUPA_SECRET = "supabase-legacy-jwt-secret-for-tests-000000"
SUPA_URL = "https://demo-project.supabase.co"


def _claims(**overrides):
    now = datetime.now(UTC)
    claims = {
        "sub": str(uuid.uuid4()),
        "aud": "authenticated",
        "iss": f"{SUPA_URL}/auth/v1",
        "email": "Student@Uni.example.org",
        "role": "authenticated",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "user_metadata": {"role": "admin"},  # user-editable in Supabase: must be ignored
    }
    claims.update(overrides)
    return claims


@pytest.fixture
def supa_client(make_settings):
    app = create_app(
        make_settings(
            auth_provider="supabase", supabase_url=SUPA_URL, supabase_jwt_secret=SUPA_SECRET
        )
    )
    with TestClient(app) as c:
        yield c


def test_hs256_supabase_token_provisions_student(supa_client):
    token = jwt.encode(_claims(), SUPA_SECRET, algorithm="HS256")
    me = supa_client.get("/api/v1/users/me", headers=auth(token))
    assert me.status_code == 200, me.text
    assert me.json()["email"] == "student@uni.example.org"
    assert me.json()["role"] == "student"  # metadata role claim ignored
    # Second request reuses the same account.
    again = supa_client.get("/api/v1/users/me", headers=auth(token))
    assert again.json()["id"] == me.json()["id"]


def test_supabase_token_wrong_secret_or_audience_rejected(supa_client):
    bad_secret = jwt.encode(_claims(), "x" * 40, algorithm="HS256")
    bad_aud = jwt.encode(_claims(aud="anon"), SUPA_SECRET, algorithm="HS256")
    bad_iss = jwt.encode(_claims(iss="https://other.supabase.co/auth/v1"), SUPA_SECRET, "HS256")
    for t in (bad_secret, bad_aud, bad_iss):
        assert supa_client.get("/api/v1/users/me", headers=auth(t)).status_code == 401


def test_local_token_not_accepted_in_supabase_mode(supa_client):
    now = datetime.now(UTC)
    local = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "iss": "bridge-local",
            "aud": "bridge-api",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        SUPA_SECRET,
        algorithm="HS256",
    )
    assert supa_client.get("/api/v1/users/me", headers=auth(local)).status_code == 401


def test_supabase_identity_cannot_take_over_local_account(supa_client, create_user):
    create_user("owner@example.com")
    token = jwt.encode(_claims(email="owner@example.com"), SUPA_SECRET, algorithm="HS256")
    assert supa_client.get("/api/v1/users/me", headers=auth(token)).status_code == 403


def test_es256_token_verified_via_jwks(supa_client, monkeypatch):
    private_key = ec.generate_private_key(ec.SECP256R1())

    class FakeJWKSClient:
        def get_signing_key_from_jwt(self, _token):
            return type("Key", (), {"key": private_key.public_key()})()

    monkeypatch.setattr(tokens, "_jwks_client", lambda url: FakeJWKSClient())
    good = jwt.encode(_claims(), private_key, algorithm="ES256", headers={"kid": "k1"})
    assert supa_client.get("/api/v1/users/me", headers=auth(good)).status_code == 200

    other_key = ec.generate_private_key(ec.SECP256R1())
    forged = jwt.encode(_claims(), other_key, algorithm="ES256", headers={"kid": "k1"})
    assert supa_client.get("/api/v1/users/me", headers=auth(forged)).status_code == 401
