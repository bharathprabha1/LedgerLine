ï»¿import uuid

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.account import Account
from app.models.enums import AccountStatus, UserRole
from app.models.user import User


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()



@pytest.fixture
def customer(db):
    user = User(
        full_name="Transaction API Test User",
        email=f"transaction-api-{uuid.uuid4().hex}@example.com",
        password_hash="test-only-password-hash",
        role=UserRole.ACCOUNT_HOLDER,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user

def create_auth_headers(user):
    token = create_access_token(
        user_id=user.id,
        role=user.role.value,
    )
    return {"Authorization": f"Bearer {token}"}


def create_settlement_account(db, owner, balance_paise=100_000):
    settlement = Account(
        account_number=f"LLSYS{uuid.uuid4().hex[:12].upper()}",
        owner_id=owner.id,
        balance_paise=balance_paise,
        currency="INR",
        status=AccountStatus.ACTIVE,
        is_system=True,
    )
    db.add(settlement)
    db.flush()
    return settlement


# ---------------------------------------------------------
# SUCCESSFUL TRANSACTION API REQUESTS
# ---------------------------------------------------------


def test_deposit_endpoint_success(client, db, transfer_accounts):
    owner = transfer_accounts["source_owner"]
    account = transfer_accounts["source"]
    settlement = create_settlement_account(db, owner)

    response = client.post(
        "/api/v1/transactions/deposit",
        headers={
            **create_auth_headers(owner),
            "Idempotency-Key": "api-deposit-success-001",
        },
        json={
            "account_id": str(account.id),
            "amount_paise": 10_000,
            "description": "API deposit test",
        },
    )

    assert response.status_code == 201
    assert response.json()["transaction_type"] == "DEPOSIT"
    assert response.json()["status"] == "POSTED"
    assert response.json()["amount_paise"] == 10_000

    db.refresh(account)
    db.refresh(settlement)

    assert account.balance_paise == 60_000
    assert settlement.balance_paise == 110_000


def test_withdrawal_endpoint_success(client, db, transfer_accounts):
    owner = transfer_accounts["source_owner"]
    account = transfer_accounts["source"]
    settlement = create_settlement_account(db, owner)

    response = client.post(
        "/api/v1/transactions/withdrawal",
        headers={
            **create_auth_headers(owner),
            "Idempotency-Key": "api-withdraw-success-001",
        },
        json={
            "account_id": str(account.id),
            "amount_paise": 10_000,
            "description": "API withdrawal test",
        },
    )

    assert response.status_code == 201
    assert response.json()["transaction_type"] == "WITHDRAWAL"
    assert response.json()["status"] == "POSTED"
    assert response.json()["amount_paise"] == 10_000

    db.refresh(account)
    db.refresh(settlement)

    assert account.balance_paise == 40_000
    assert settlement.balance_paise == 90_000


def test_transfer_endpoint_success(client, db, transfer_accounts):
    owner = transfer_accounts["source_owner"]
    source = transfer_accounts["source"]
    destination = transfer_accounts["destination"]

    response = client.post(
        "/api/v1/transactions/transfer",
        headers={
            **create_auth_headers(owner),
            "Idempotency-Key": "api-transfer-success-001",
        },
        json={
            "source_account_id": str(source.id),
            "destination_account_id": str(destination.id),
            "amount_paise": 10_000,
            "description": "API transfer test",
        },
    )

    assert response.status_code == 201
    assert response.json()["transaction_type"] == "TRANSFER"
    assert response.json()["status"] == "POSTED"
    assert response.json()["amount_paise"] == 10_000

    db.refresh(source)
    db.refresh(destination)

    assert source.balance_paise == 40_000
    assert destination.balance_paise == 10_000


# ---------------------------------------------------------
# IDEMPOTENCY HEADER VALIDATION
# ---------------------------------------------------------


def test_deposit_requires_idempotency_key(
    client,
    transfer_accounts,
):
    owner = transfer_accounts["source_owner"]
    account = transfer_accounts["source"]

    response = client.post(
        "/api/v1/transactions/deposit",
        headers=create_auth_headers(owner),
        json={
            "account_id": str(account.id),
            "amount_paise": 1_000,
        },
    )

    assert response.status_code == 422


def test_deposit_rejects_empty_idempotency_key(
    client,
    transfer_accounts,
):
    owner = transfer_accounts["source_owner"]
    account = transfer_accounts["source"]

    response = client.post(
        "/api/v1/transactions/deposit",
        headers={
            **create_auth_headers(owner),
            "Idempotency-Key": "",
        },
        json={
            "account_id": str(account.id),
            "amount_paise": 1_000,
        },
    )

    assert response.status_code == 422


def test_deposit_rejects_oversized_idempotency_key(
    client,
    transfer_accounts,
):
    owner = transfer_accounts["source_owner"]
    account = transfer_accounts["source"]

    response = client.post(
        "/api/v1/transactions/deposit",
        headers={
            **create_auth_headers(owner),
            "Idempotency-Key": "x" * 256,
        },
        json={
            "account_id": str(account.id),
            "amount_paise": 1_000,
        },
    )

    assert response.status_code == 422


# ---------------------------------------------------------
# REQUEST BODY VALIDATION
# ---------------------------------------------------------


@pytest.mark.parametrize("amount", [0, -1])
def test_deposit_rejects_nonpositive_amount(
    client,
    transfer_accounts,
    amount,
):
    owner = transfer_accounts["source_owner"]
    account = transfer_accounts["source"]

    response = client.post(
        "/api/v1/transactions/deposit",
        headers={
            **create_auth_headers(owner),
            "Idempotency-Key": f"api-invalid-deposit-{amount}",
        },
        json={
            "account_id": str(account.id),
            "amount_paise": amount,
        },
    )

    assert response.status_code == 422


def test_withdrawal_rejects_negative_amount(
    client,
    transfer_accounts,
):
    owner = transfer_accounts["source_owner"]
    account = transfer_accounts["source"]

    response = client.post(
        "/api/v1/transactions/withdrawal",
        headers={
            **create_auth_headers(owner),
            "Idempotency-Key": "api-invalid-withdrawal-001",
        },
        json={
            "account_id": str(account.id),
            "amount_paise": -100,
        },
    )

    assert response.status_code == 422


def test_transfer_rejects_zero_amount(
    client,
    transfer_accounts,
):
    owner = transfer_accounts["source_owner"]

    response = client.post(
        "/api/v1/transactions/transfer",
        headers={
            **create_auth_headers(owner),
            "Idempotency-Key": "api-invalid-transfer-001",
        },
        json={
            "source_account_id": str(transfer_accounts["source"].id),
            "destination_account_id": str(
                transfer_accounts["destination"].id
            ),
            "amount_paise": 0,
        },
    )

    assert response.status_code == 422


def test_deposit_rejects_invalid_account_uuid(
    client,
    transfer_accounts,
):
    owner = transfer_accounts["source_owner"]

    response = client.post(
        "/api/v1/transactions/deposit",
        headers={
            **create_auth_headers(owner),
            "Idempotency-Key": "api-invalid-uuid-001",
        },
        json={
            "account_id": "not-a-valid-uuid",
            "amount_paise": 1_000,
        },
    )

    assert response.status_code == 422


# ---------------------------------------------------------
# REJECTED TRANSACTION API REQUESTS
# ---------------------------------------------------------


def test_withdrawal_endpoint_returns_insufficient_funds(
    client,
    db,
    transfer_accounts,
):
    owner = transfer_accounts["source_owner"]
    account = transfer_accounts["source"]
    create_settlement_account(db, owner)

    response = client.post(
        "/api/v1/transactions/withdrawal",
        headers={
            **create_auth_headers(owner),
            "Idempotency-Key": "api-withdraw-insufficient-001",
        },
        json={
            "account_id": str(account.id),
            "amount_paise": 60_000,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Insufficient funds."

    db.refresh(account)
    assert account.balance_paise == 50_000


def test_transfer_endpoint_returns_insufficient_funds(
    client,
    transfer_accounts,
):
    owner = transfer_accounts["source_owner"]

    response = client.post(
        "/api/v1/transactions/transfer",
        headers={
            **create_auth_headers(owner),
            "Idempotency-Key": "api-transfer-insufficient-001",
        },
        json={
            "source_account_id": str(transfer_accounts["source"].id),
            "destination_account_id": str(
                transfer_accounts["destination"].id
            ),
            "amount_paise": 100_000,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Insufficient funds."


# ---------------------------------------------------------
# TRANSACTION HISTORY AND DETAIL VALIDATION
# ---------------------------------------------------------


@pytest.mark.parametrize(
    ("query", "expected_status"),
    [
        ("?limit=0", 422),
        ("?limit=101", 422),
        ("?offset=-1", 422),
    ],
)
def test_transaction_history_rejects_invalid_pagination(
    client,
    customer,
    query,
    expected_status,
):
    response = client.get(
        f"/api/v1/transactions{query}",
        headers=create_auth_headers(customer),
    )

    assert response.status_code == expected_status


def test_transaction_detail_rejects_invalid_uuid(
    client,
    customer,
):
    response = client.get(
        "/api/v1/transactions/not-a-valid-uuid",
        headers=create_auth_headers(customer),
    )

    assert response.status_code == 422


def test_transaction_detail_returns_404_for_missing_transaction(
    client,
    customer,
):
    response = client.get(
        f"/api/v1/transactions/{uuid.uuid4()}",
        headers=create_auth_headers(customer),
    )

    assert response.status_code == 404
