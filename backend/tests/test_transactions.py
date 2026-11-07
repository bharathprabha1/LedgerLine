
from sqlalchemy import func, select

from app.models.audit_log import AuditLog
from app.models.enums import (
    AccountStatus,
    EntrySide,
    TransactionStatus,
)
from app.models.ledger_entry import LedgerEntry
from app.models.transaction import LedgerTransaction
from app.services.transaction_service import (
    MAX_BIGINT,
    transfer_funds,
)


def make_transfer(db, accounts, key, amount=10_000):
    return transfer_funds(
        db,
        current_user=accounts["source_owner"],
        source_account_id=accounts["source"].id,
        destination_account_id=accounts["destination"].id,
        amount_paise=amount,
        description="Automated transfer test",
        idempotency_key=key,
    )


# --------------------------------------------------
# 1. Successful transfer
# --------------------------------------------------

def test_successful_transfer(db, transfer_accounts):
    accounts = transfer_accounts

    result = make_transfer(
        db,
        accounts,
        "success-test-001",
    )

    assert result.status_code == 201
    assert result.transaction is not None
    assert result.transaction.status == TransactionStatus.POSTED

    db.refresh(accounts["source"])
    db.refresh(accounts["destination"])

    assert accounts["source"].balance_paise == 40_000
    assert accounts["destination"].balance_paise == 10_000

    entries = db.scalars(
        select(LedgerEntry).where(
            LedgerEntry.transaction_id == result.transaction.id
        )
    ).all()

    assert len(entries) == 2

    debit_entries = [
        entry for entry in entries
        if entry.side == EntrySide.DEBIT
    ]

    credit_entries = [
        entry for entry in entries
        if entry.side == EntrySide.CREDIT
    ]

    assert len(debit_entries) == 1
    assert len(credit_entries) == 1

    assert debit_entries[0].amount_paise == 10_000
    assert credit_entries[0].amount_paise == 10_000

    audit = db.scalar(
        select(AuditLog).where(
            AuditLog.resource_id == str(result.transaction.id),
            AuditLog.action == "TRANSFER",
            AuditLog.outcome == "SUCCESS",
        )
    )

    assert audit is not None


# --------------------------------------------------
# 2. Insufficient funds
# --------------------------------------------------

def test_insufficient_funds_is_recorded(db, transfer_accounts):
    accounts = transfer_accounts

    result = make_transfer(
        db,
        accounts,
        "insufficient-test-001",
        amount=100_000,
    )

    assert result.status_code == 409
    assert result.transaction is not None
    assert result.transaction.status == TransactionStatus.REJECTED
    assert result.detail == "Insufficient funds."

    db.refresh(accounts["source"])
    db.refresh(accounts["destination"])

    assert accounts["source"].balance_paise == 50_000
    assert accounts["destination"].balance_paise == 0

    entries = db.scalar(
        select(func.count(LedgerEntry.id)).where(
            LedgerEntry.transaction_id == result.transaction.id
        )
    )

    assert entries == 0

    rejected_audit = db.scalar(
        select(AuditLog).where(
            AuditLog.resource_id == str(result.transaction.id),
            AuditLog.action == "TRANSFER",
            AuditLog.outcome == "REJECTED",
        )
    )

    assert rejected_audit is not None


# --------------------------------------------------
# 3. Successful request idempotency
# --------------------------------------------------

def test_successful_request_is_idempotent(db, transfer_accounts):
    accounts = transfer_accounts

    first = make_transfer(
        db,
        accounts,
        "idempotent-test-001",
    )

    second = make_transfer(
        db,
        accounts,
        "idempotent-test-001",
    )

    assert first.status_code == 201
    assert second.status_code == 201

    assert first.transaction.id == second.transaction.id

    db.refresh(accounts["source"])
    db.refresh(accounts["destination"])

    # The transfer must happen only once.
    assert accounts["source"].balance_paise == 40_000
    assert accounts["destination"].balance_paise == 10_000


# --------------------------------------------------
# 4. Same key with different payload
# --------------------------------------------------

def test_same_key_with_different_payload_is_rejected(
    db,
    transfer_accounts,
):
    accounts = transfer_accounts

    first = make_transfer(
        db,
        accounts,
        "different-payload-test-001",
        amount=10_000,
    )

    second = make_transfer(
        db,
        accounts,
        "different-payload-test-001",
        amount=20_000,
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.transaction is None

    db.refresh(accounts["source"])
    db.refresh(accounts["destination"])

    assert accounts["source"].balance_paise == 40_000
    assert accounts["destination"].balance_paise == 10_000


# --------------------------------------------------
# 5. Rejected request idempotency
# --------------------------------------------------

def test_rejected_request_is_idempotent(db, transfer_accounts):
    accounts = transfer_accounts

    first = make_transfer(
        db,
        accounts,
        "rejected-replay-test-001",
        amount=100_000,
    )

    second = make_transfer(
        db,
        accounts,
        "rejected-replay-test-001",
        amount=100_000,
    )

    assert first.status_code == 409
    assert second.status_code == 409

    assert first.transaction is not None
    assert second.transaction is not None

    assert first.transaction.id == second.transaction.id

    db.refresh(accounts["source"])

    assert accounts["source"].balance_paise == 50_000


# --------------------------------------------------
# 6. Account ownership security
# --------------------------------------------------

def test_cannot_transfer_from_another_users_account(
    db,
    transfer_accounts,
):
    accounts = transfer_accounts

    result = transfer_funds(
        db,
        current_user=accounts["destination_owner"],
        source_account_id=accounts["source"].id,
        destination_account_id=accounts["destination"].id,
        amount_paise=10_000,
        description="Ownership security test",
        idempotency_key="ownership-test-001",
    )

    assert result.status_code == 403
    assert result.transaction is not None
    assert result.transaction.status == TransactionStatus.REJECTED

    db.refresh(accounts["source"])
    db.refresh(accounts["destination"])

    assert accounts["source"].balance_paise == 50_000
    assert accounts["destination"].balance_paise == 0


# --------------------------------------------------
# 7. Frozen account rejection
# --------------------------------------------------

def test_frozen_account_cannot_transfer(
    db,
    transfer_accounts,
):
    accounts = transfer_accounts

    accounts["source"].status = AccountStatus.FROZEN
    db.flush()

    result = make_transfer(
        db,
        accounts,
        "frozen-account-test-001",
    )

    assert result.status_code == 409
    assert result.transaction is not None
    assert result.transaction.status == TransactionStatus.REJECTED

    db.refresh(accounts["source"])
    db.refresh(accounts["destination"])

    assert accounts["source"].balance_paise == 50_000
    assert accounts["destination"].balance_paise == 0


# --------------------------------------------------
# 8. System account rejection
# --------------------------------------------------

def test_system_account_cannot_be_used_for_transfer(
    db,
    transfer_accounts,
):
    accounts = transfer_accounts

    accounts["destination"].is_system = True
    db.flush()

    result = make_transfer(
        db,
        accounts,
        "system-account-test-001",
    )

    assert result.status_code == 400
    assert result.transaction is not None
    assert result.transaction.status == TransactionStatus.REJECTED

    db.refresh(accounts["source"])
    db.refresh(accounts["destination"])

    assert accounts["source"].balance_paise == 50_000
    assert accounts["destination"].balance_paise == 0


# --------------------------------------------------
# 9. Destination balance overflow rejection
# --------------------------------------------------

def test_destination_balance_overflow_is_rejected(
    db,
    transfer_accounts,
):
    accounts = transfer_accounts

    accounts["destination"].balance_paise = MAX_BIGINT - 5_000
    db.flush()

    result = make_transfer(
        db,
        accounts,
        "balance-overflow-test-001",
        amount=10_000,
    )

    assert result.status_code == 409
    assert result.transaction is not None
    assert result.transaction.status == TransactionStatus.REJECTED

    db.refresh(accounts["source"])
    db.refresh(accounts["destination"])

    assert accounts["source"].balance_paise == 50_000
    assert (
        accounts["destination"].balance_paise
        == MAX_BIGINT - 5_000
    )
