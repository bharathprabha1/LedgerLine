import uuid

import pytest
from sqlalchemy import select
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.main import app
from app.models.account import Account
from app.models.audit_log import AuditLog
from app.models.enums import (
    AccountStatus,
    TransactionStatus,
    TransactionType,
    UserRole,
)
from app.models.transaction import LedgerTransaction
from app.models.user import User


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def create_test_user(
    db,
    *,
    role=UserRole.ACCOUNT_HOLDER,
    is_active=True,
):
    suffix = uuid.uuid4().hex

    user = User(
        full_name="API Test User",
        email=f"api-{suffix}@example.com",
        password_hash=hash_password("TestPassword@2026"),
        role=role,
        is_active=is_active,
    )

    db.add(user)
    db.flush()

    return user


def create_auth_headers(user):
    token = create_access_token(
        user_id=user.id,
        role=user.role.value,
        token_version=user.token_version,
    )

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def customer(db):
    return create_test_user(db)


@pytest.fixture
def admin(db):
    return create_test_user(db, role=UserRole.ADMIN)


@pytest.fixture
def inactive_customer(db):
    return create_test_user(db, is_active=False)


@pytest.fixture
def customer_account(db, customer):
    account = Account(
        account_number=f"LLTEST{uuid.uuid4().hex[:12]}",
        owner_id=customer.id,
        balance_paise=0,
        currency="INR",
        status=AccountStatus.ACTIVE,
        is_system=False,
    )

    db.add(account)
    db.flush()

    return account


# ---------------------------------------------------------
# AUTHENTICATION
# ---------------------------------------------------------


def test_missing_token_returns_401(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_invalid_token_returns_401(client):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )

    assert response.status_code == 401


def test_authenticated_user_can_access_profile(client, customer):
    response = client.get(
        "/api/v1/auth/me",
        headers=create_auth_headers(customer),
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(customer.id)
    assert response.json()["role"] == "ACCOUNT_HOLDER"



def test_customer_can_update_own_profile(client, customer):
    response = client.patch(
        "/api/v1/auth/me",
        headers=create_auth_headers(customer),
        json={
            "full_name": "Updated Customer Name",
            "email": "updated-customer@example.com",
        },
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated Customer Name"
    assert response.json()["email"] == "updated-customer@example.com"
    assert response.json()["id"] == str(customer.id)


def test_customer_cannot_use_another_users_email(
    client,
    customer,
    admin,
):
    response = client.patch(
        "/api/v1/auth/me",
        headers=create_auth_headers(customer),
        json={"email": admin.email},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "This email is already registered"


def test_unauthenticated_user_cannot_update_profile(client):
    response = client.patch(
        "/api/v1/auth/me",
        json={"full_name": "Unauthorized Update"},
    )

    assert response.status_code == 401


def test_customer_can_update_only_full_name(client, customer):
    original_email = customer.email

    response = client.patch(
        "/api/v1/auth/me",
        headers=create_auth_headers(customer),
        json={"full_name": "Name Only Update"},
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Name Only Update"
    assert response.json()["email"] == original_email


def test_customer_can_change_own_password(client, customer, db):
    old_password = "TestPassword@2026"
    new_password = "NewSecurePassword@2026"

    response = client.patch(
        "/api/v1/auth/change-password",
        headers=create_auth_headers(customer),
        json={
            "current_password": old_password,
            "new_password": new_password,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Password changed successfully. Please log in again."
    }

    db.refresh(customer)
    assert verify_password(new_password, customer.password_hash)
    assert not verify_password(old_password, customer.password_hash)


def test_password_change_invalidates_old_access_token(
    client,
    customer,
):
    old_password = "TestPassword@2026"
    new_password = "NewSecurePassword@2026"
    old_headers = create_auth_headers(customer)

    change_response = client.patch(
        "/api/v1/auth/change-password",
        headers=old_headers,
        json={
            "current_password": old_password,
            "new_password": new_password,
        },
    )

    assert change_response.status_code == 200

    old_token_response = client.get(
        "/api/v1/auth/me",
        headers=old_headers,
    )
    assert old_token_response.status_code == 401

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": customer.email,
            "password": new_password,
        },
    )
    assert login_response.status_code == 200

    new_headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }
    new_token_response = client.get(
        "/api/v1/auth/me",
        headers=new_headers,
    )

    assert new_token_response.status_code == 200
    assert new_token_response.json()["id"] == str(customer.id)


def test_password_change_rejects_incorrect_current_password(
    client,
    customer,
    db,
):
    original_hash = customer.password_hash

    response = client.patch(
        "/api/v1/auth/change-password",
        headers=create_auth_headers(customer),
        json={
            "current_password": "IncorrectPassword@2026",
            "new_password": "NewSecurePassword@2026",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Current password is incorrect"

    db.refresh(customer)
    assert customer.password_hash == original_hash


def test_password_change_rejects_reusing_current_password(
    client,
    customer,
    db,
):
    original_hash = customer.password_hash

    response = client.patch(
        "/api/v1/auth/change-password",
        headers=create_auth_headers(customer),
        json={
            "current_password": "TestPassword@2026",
            "new_password": "TestPassword@2026",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "New password must be different from the current password"
    )

    db.refresh(customer)
    assert customer.password_hash == original_hash


def test_unauthenticated_user_cannot_change_password(client):
    response = client.patch(
        "/api/v1/auth/change-password",
        json={
            "current_password": "TestPassword@2026",
            "new_password": "NewSecurePassword@2026",
        },
    )

    assert response.status_code == 401


def test_password_change_rejects_new_password_shorter_than_12_characters(
    client,
    customer,
):
    response = client.patch(
        "/api/v1/auth/change-password",
        headers=create_auth_headers(customer),
        json={
            "current_password": "TestPassword@2026",
            "new_password": "Short@123",
        },
    )

    assert response.status_code == 422


def test_inactive_user_cannot_access_protected_route(
    client,
    inactive_customer,
):
    response = client.get(
        "/api/v1/auth/me",
        headers=create_auth_headers(inactive_customer),
    )

    assert response.status_code == 401


def test_registration_assigns_account_holder_role(client):
    email = f"register-{uuid.uuid4().hex}@example.com"

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "New API Customer",
            "email": email,
            "password": "StrongPassword@2026",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == email
    assert response.json()["role"] == "ACCOUNT_HOLDER"
    assert "password_hash" not in response.json()


def test_duplicate_registration_returns_409(client):
    email = f"duplicate-{uuid.uuid4().hex}@example.com"

    payload = {
        "full_name": "Duplicate Test User",
        "email": email,
        "password": "StrongPassword@2026",
    }

    first_response = client.post(
        "/api/v1/auth/register",
        json=payload,
    )

    second_response = client.post(
        "/api/v1/auth/register",
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_invalid_login_returns_401(client, customer):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": customer.email,
            "password": "WrongPassword@2026",
        },
    )

    assert response.status_code == 401


def test_inactive_user_login_returns_403(client, inactive_customer):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": inactive_customer.email,
            "password": "TestPassword@2026",
        },
    )

    assert response.status_code == 403


# ---------------------------------------------------------
# ACCOUNT AUTHORIZATION
# ---------------------------------------------------------


def test_customer_can_view_own_account(
    client,
    customer,
    customer_account,
):
    response = client.get(
        f"/api/v1/accounts/{customer_account.id}",
        headers=create_auth_headers(customer),
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(customer_account.id)


def test_customer_cannot_view_another_customers_account(
    client,
    customer,
    transfer_accounts,
):
    other_account = transfer_accounts["source"]

    response = client.get(
        f"/api/v1/accounts/{other_account.id}",
        headers=create_auth_headers(customer),
    )

    assert response.status_code == 404


def test_customer_cannot_create_account(
    client,
    customer,
):
    response = client.post(
        "/api/v1/accounts",
        headers=create_auth_headers(customer),
        json={"owner_id": str(customer.id)},
    )

    assert response.status_code == 403


def test_admin_can_create_account(
    client,
    db,
    admin,
    customer,
):
    response = client.post(
        "/api/v1/accounts",
        headers=create_auth_headers(admin),
        json={"owner_id": str(customer.id)},
    )

    assert response.status_code == 201
    assert response.json()["owner_id"] == str(customer.id)
    assert response.json()["balance_paise"] == 0


def test_customer_status_change_is_denied_and_audited(
    client,
    customer,
    customer_account,
    monkeypatch,
):
    recorded_events = []

    def fake_record_audit_event(**kwargs):
        recorded_events.append(kwargs)

    monkeypatch.setattr(
        "app.api.v1.accounts.record_audit_event",
        fake_record_audit_event,
    )

    response = client.patch(
        f"/api/v1/accounts/{customer_account.id}/status",
        headers={
            **create_auth_headers(customer),
            "X-Request-ID": "api-test-request-001",
        },
        json={"status": "FROZEN"},
    )

    assert response.status_code == 403
    assert len(recorded_events) == 1

    event = recorded_events[0]

    assert event["actor_id"] == customer.id
    assert event["action"] == "ACCOUNT_STATUS_CHANGE"
    assert event["outcome"] == "DENIED"
    assert event["request_id"] == "api-test-request-001"


# ---------------------------------------------------------
# TRANSACTION AND STATEMENT PRIVACY
# ---------------------------------------------------------


def test_customer_cannot_view_another_customers_transaction(
    client,
    customer,
    transfer_accounts,
    db,
):
    source = transfer_accounts["source"]

    transaction = LedgerTransaction(
        reference=f"API-{uuid.uuid4().hex}",
        transaction_type=TransactionType.TRANSFER,
        status=TransactionStatus.POSTED,
        amount_paise=1000,
        source_account_id=source.id,
        destination_account_id=transfer_accounts["destination"].id,
        initiated_by=source.owner_id,
        description="API privacy test",
    )

    db.add(transaction)
    db.flush()

    response = client.get(
        f"/api/v1/transactions/{transaction.id}",
        headers=create_auth_headers(customer),
    )

    assert response.status_code == 404


def test_customer_cannot_view_another_customers_statement(
    client,
    customer,
    transfer_accounts,
):
    other_account = transfer_accounts["source"]

    response = client.get(
        f"/api/v1/accounts/{other_account.id}/statement",
        headers=create_auth_headers(customer),
    )

    assert response.status_code == 404


def test_transaction_history_requires_authentication(client):
    response = client.get("/api/v1/transactions")

    assert response.status_code == 401


def test_customer_history_does_not_expose_other_customers_transactions(
    client,
    customer,
    transfer_accounts,
    db,
):
    source = transfer_accounts["source"]

    transaction = LedgerTransaction(
        reference=f"API-{uuid.uuid4().hex}",
        transaction_type=TransactionType.TRANSFER,
        status=TransactionStatus.POSTED,
        amount_paise=1000,
        source_account_id=source.id,
        destination_account_id=transfer_accounts["destination"].id,
        initiated_by=source.owner_id,
        description="Private transaction",
    )

    db.add(transaction)
    db.flush()

    response = client.get(
        "/api/v1/transactions",
        headers=create_auth_headers(customer),
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert response.json()["items"] == []


# ---------------------------------------------------------
# AUDITOR AND ACCOUNT STATUS SECURITY
# ---------------------------------------------------------


@pytest.fixture
def auditor(db):
    return create_test_user(db, role=UserRole.AUDITOR)


def test_auditor_can_view_accounts(
    client,
    auditor,
    transfer_accounts,
):
    response = client.get(
        "/api/v1/accounts",
        headers=create_auth_headers(auditor),
    )

    assert response.status_code == 200

    returned_ids = {
        item["id"] for item in response.json()
    }

    assert str(transfer_accounts["source"].id) in returned_ids
    assert str(transfer_accounts["destination"].id) in returned_ids


def test_auditor_cannot_change_account_status(
    client,
    auditor,
    customer_account,
    monkeypatch,
):
    recorded_events = []

    def fake_record_audit_event(**kwargs):
        recorded_events.append(kwargs)

    monkeypatch.setattr(
        "app.api.v1.accounts.record_audit_event",
        fake_record_audit_event,
    )

    response = client.patch(
        f"/api/v1/accounts/{customer_account.id}/status",
        headers=create_auth_headers(auditor),
        json={"status": "FROZEN"},
    )

    assert response.status_code == 403
    assert len(recorded_events) == 1
    assert recorded_events[0]["actor_id"] == auditor.id
    assert recorded_events[0]["outcome"] == "DENIED"


def test_admin_can_freeze_active_account_and_audit_success(
    client,
    db,
    admin,
    customer_account,
):
    response = client.patch(
        f"/api/v1/accounts/{customer_account.id}/status",
        headers=create_auth_headers(admin),
        json={"status": "FROZEN"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "FROZEN"

    audit_event = db.scalar(
        select(AuditLog).where(
            AuditLog.actor_id == admin.id,
            AuditLog.action == "ACCOUNT_STATUS_CHANGE",
            AuditLog.resource_id == str(customer_account.id),
            AuditLog.outcome == "SUCCESS",
        )
    )

    assert audit_event is not None
    assert audit_event.details["previous_status"] == "ACTIVE"
    assert audit_event.details["new_status"] == "FROZEN"


def test_admin_cannot_change_system_account_status(
    client,
    admin,
    db,
    monkeypatch,
):
    system_account = Account(
        account_number=f"LLSYS{uuid.uuid4().hex[:12]}",
        owner_id=admin.id,
        balance_paise=0,
        currency="INR",
        status=AccountStatus.ACTIVE,
        is_system=True,
    )

    db.add(system_account)
    db.flush()

    recorded_events = []

    def fake_record_audit_event(**kwargs):
        recorded_events.append(kwargs)

    monkeypatch.setattr(
        "app.api.v1.accounts.record_audit_event",
        fake_record_audit_event,
    )

    response = client.patch(
        f"/api/v1/accounts/{system_account.id}/status",
        headers=create_auth_headers(admin),
        json={"status": "FROZEN"},
    )

    assert response.status_code == 409
    assert len(recorded_events) == 1
    assert recorded_events[0]["outcome"] == "REJECTED"


def test_admin_cannot_close_account_with_nonzero_balance(
    client,
    admin,
    customer_account,
    monkeypatch,
):
    customer_account.balance_paise = 5000

    recorded_events = []

    def fake_record_audit_event(**kwargs):
        recorded_events.append(kwargs)

    monkeypatch.setattr(
        "app.services.account_service.record_audit_event",
        fake_record_audit_event,
    )

    response = client.patch(
        f"/api/v1/accounts/{customer_account.id}/status",
        headers=create_auth_headers(admin),
        json={"status": "CLOSED"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "An account with a non-zero balance cannot be closed."
    )
    assert len(recorded_events) == 1
    assert recorded_events[0]["outcome"] == "REJECTED"


def test_admin_cannot_reopen_closed_account(
    client,
    admin,
    customer_account,
    monkeypatch,
):
    customer_account.status = AccountStatus.CLOSED

    recorded_events = []

    def fake_record_audit_event(**kwargs):
        recorded_events.append(kwargs)

    monkeypatch.setattr(
        "app.services.account_service.record_audit_event",
        fake_record_audit_event,
    )

    response = client.patch(
        f"/api/v1/accounts/{customer_account.id}/status",
        headers=create_auth_headers(admin),
        json={"status": "ACTIVE"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Requested account status transition is not allowed."
    )
    assert len(recorded_events) == 1
    assert recorded_events[0]["outcome"] == "REJECTED"


# ---------------------------------------------------------
# MISSING ACCOUNT STATUS SECURITY
# ---------------------------------------------------------


def test_admin_status_change_for_missing_account_is_audited(
    client,
    admin,
    monkeypatch,
):
    recorded_events = []
    missing_account_id = uuid.uuid4()

    def fake_record_audit_event(**kwargs):
        recorded_events.append(kwargs)

    # change_account_status calls record_audit_event from account_service.
    monkeypatch.setattr(
        "app.services.account_service.record_audit_event",
        fake_record_audit_event,
    )

    response = client.patch(
        f"/api/v1/accounts/{missing_account_id}/status",
        headers=create_auth_headers(admin),
        json={"status": "FROZEN"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Account not found."

    assert len(recorded_events) == 1

    event = recorded_events[0]

    assert event["actor_id"] == admin.id
    assert event["action"] == "ACCOUNT_STATUS_CHANGE"
    assert event["resource_type"] == "ACCOUNT"
    assert event["resource_id"] == str(missing_account_id)
    assert event["outcome"] == "REJECTED"
    assert event["details"]["requested_status"] == "FROZEN"
    assert event["details"]["reason"] == "Account not found"


# ---------------------------------------------------------
# ADDITIONAL AUDITOR AUTHORIZATION TESTS
# ---------------------------------------------------------


def create_auditor_test_transaction(db, transfer_accounts):
    """Create a posted transaction for auditor read-access tests."""

    transaction = LedgerTransaction(
        reference=f"AUDIT-{uuid.uuid4().hex}",
        transaction_type=TransactionType.TRANSFER,
        status=TransactionStatus.POSTED,
        amount_paise=5000,
        source_account_id=transfer_accounts["source"].id,
        destination_account_id=transfer_accounts["destination"].id,
        initiated_by=transfer_accounts["source_owner"].id,
        description="Auditor authorization test",
    )

    db.add(transaction)
    db.flush()

    return transaction


def test_auditor_can_view_transaction_history(
    client,
    db,
    auditor,
    transfer_accounts,
):
    transaction = create_auditor_test_transaction(
        db, transfer_accounts
    )

    response = client.get(
        "/api/v1/transactions",
        headers=create_auth_headers(auditor),
    )

    assert response.status_code == 200
    assert str(transaction.id) in str(response.json())


def test_auditor_can_view_transaction_details(
    client,
    db,
    auditor,
    transfer_accounts,
):
    transaction = create_auditor_test_transaction(
        db, transfer_accounts
    )

    response = client.get(
        f"/api/v1/transactions/{transaction.id}",
        headers=create_auth_headers(auditor),
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(transaction.id)


def test_auditor_can_view_customer_account_statement(
    client,
    db,
    auditor,
    transfer_accounts,
):
    create_auditor_test_transaction(db, transfer_accounts)
    account = transfer_accounts["source"]

    response = client.get(
        f"/api/v1/accounts/{account.id}/statement",
        headers=create_auth_headers(auditor),
    )

    assert response.status_code == 200


def test_auditor_cannot_create_account(
    client,
    auditor,
    transfer_accounts,
):
    response = client.post(
        "/api/v1/accounts",
        headers=create_auth_headers(auditor),
        json={
            "owner_id": str(
                transfer_accounts["source_owner"].id
            )
        },
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    ("endpoint", "payload_factory"),
    [
        (
            "/api/v1/transactions/deposit",
            lambda accounts: {
                "account_id": str(accounts["source"].id),
                "amount_paise": 1000,
                "description": "Auditor deposit denial test",
            },
        ),
        (
            "/api/v1/transactions/withdrawal",
            lambda accounts: {
                "account_id": str(accounts["source"].id),
                "amount_paise": 1000,
                "description": "Auditor withdrawal denial test",
            },
        ),
        (
            "/api/v1/transactions/transfer",
            lambda accounts: {
                "source_account_id": str(accounts["source"].id),
                "destination_account_id": str(
                    accounts["destination"].id
                ),
                "amount_paise": 1000,
                "description": "Auditor transfer denial test",
            },
        ),
    ],
)
def test_auditor_cannot_initiate_financial_transactions(
    client,
    auditor,
    transfer_accounts,
    endpoint,
    payload_factory,
):
    response = client.post(
        endpoint,
        headers={
            **create_auth_headers(auditor),
            "Idempotency-Key": str(uuid.uuid4()),
        },
        json=payload_factory(transfer_accounts),
    )

    assert response.status_code == 403


# ---------------------------------------------------------
# RECIPIENT LOOKUP RATE-LIMIT API SECURITY TESTS
# ---------------------------------------------------------


def test_account_holder_can_lookup_eligible_recipient(
    client,
    db,
    customer,
):
    recipient = create_test_user(db)

    recipient_account = Account(
        account_number=f"LLTEST{uuid.uuid4().hex[:12]}",
        owner_id=recipient.id,
        balance_paise=50000,
        currency="INR",
        status=AccountStatus.ACTIVE,
        is_system=False,
    )

    db.add(recipient_account)
    db.flush()

    response = client.get(
        "/api/v1/accounts/recipient-lookup",
        params={"account_number": recipient_account.account_number},
        headers=create_auth_headers(customer),
    )

    assert response.status_code == 200
    assert response.json()["account_number"] == recipient_account.account_number
    assert response.json()["holder_name"] == recipient.full_name
    assert "balance_paise" not in response.json()


def test_unknown_recipient_lookups_are_rate_limited(
    client,
    customer,
):
    headers = create_auth_headers(customer)

    for _ in range(10):
        response = client.get(
            "/api/v1/accounts/recipient-lookup",
            params={"account_number": "LLUNKNOWN000001"},
            headers=headers,
        )

        assert response.status_code == 404

    response = client.get(
        "/api/v1/accounts/recipient-lookup",
        params={"account_number": "LLUNKNOWN000002"},
        headers=headers,
    )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"


def test_invalid_account_number_attempts_are_rate_limited(
    client,
    customer,
):
    headers = create_auth_headers(customer)

    for _ in range(10):
        response = client.get(
            "/api/v1/accounts/recipient-lookup",
            params={"account_number": ""},
            headers=headers,
        )

        assert response.status_code == 400

    response = client.get(
        "/api/v1/accounts/recipient-lookup",
        params={"account_number": ""},
        headers=headers,
    )

    assert response.status_code == 429


def test_recipient_lookup_limits_are_independent_per_user(
    client,
    db,
    customer,
):
    second_customer = create_test_user(db)

    first_headers = create_auth_headers(customer)
    second_headers = create_auth_headers(second_customer)

    for _ in range(10):
        response = client.get(
            "/api/v1/accounts/recipient-lookup",
            params={"account_number": "LLUNKNOWN000003"},
            headers=first_headers,
        )

        assert response.status_code == 404

    # A second customer has an independent rate-limit counter.
    second_response = client.get(
        "/api/v1/accounts/recipient-lookup",
        params={"account_number": "LLUNKNOWN000004"},
        headers=second_headers,
    )

    assert second_response.status_code == 404

    # The first customer is now rate-limited.
    first_response = client.get(
        "/api/v1/accounts/recipient-lookup",
        params={"account_number": "LLUNKNOWN000005"},
        headers=first_headers,
    )

    assert first_response.status_code == 429
