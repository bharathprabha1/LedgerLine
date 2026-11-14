import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_trusted_origin_allows_cors_preflight(client):
    origin = settings.allowed_origins[0]

    response = client.options(
        "/api/v1/transactions/transfer",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": (
                "authorization,content-type,idempotency-key"
            ),
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin

    allowed_methods = response.headers[
        "access-control-allow-methods"
    ]

    assert "POST" in allowed_methods

    allowed_headers = response.headers[
        "access-control-allow-headers"
    ].lower()

    assert "authorization" in allowed_headers
    assert "content-type" in allowed_headers
    assert "idempotency-key" in allowed_headers


def test_untrusted_origin_is_rejected(client):
    origin = "https://untrusted.example"

    assert origin not in settings.allowed_origins

    response = client.options(
        "/api/v1/transactions/transfer",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_unsupported_method_is_rejected_by_cors(client):
    origin = settings.allowed_origins[0]

    response = client.options(
        "/api/v1/transactions/transfer",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "PUT",
        },
    )

    assert response.status_code == 400
