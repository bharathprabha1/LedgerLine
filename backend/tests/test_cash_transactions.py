
import uuid

from sqlalchemy import select

from app.models.account import Account
from app.models.audit_log import AuditLog
from app.models.enums import (
    AccountStatus,
    EntrySide,
    TransactionStatus,
    TransactionType,
)
from app.models.idempotency import IdempotencyRecord
from app.models.ledger_entry import LedgerEntry
from app.models.transaction import LedgerTransaction
from app.services.transaction_service import (
    deposit_funds,
    withdraw_funds,
)


def create_settlement_account(db, owner, balance_paise=100_000):
    """Create an isolated system settlement account for a test."""

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


def get_transaction_entries(db, transaction_id):
    return db.scalars(
        select(LedgerEntry).where(
            LedgerEntry.transaction_id == transaction_id
        )
    ).all()


def test_successful_deposit(db, transfer_accounts):
    source_owner = transfer_accounts["source_owner"]
    customer = transfer_accounts["source"]

    settlement = create_settlement_account(db, source_owner)

    result = deposit_funds(
        db,
        current_user=source_owner,
        account_id=customer.id,
        amount_paise=20_000,
        description="Test deposit",
        idempotency_key="deposit-success-001",
    )

    assert result.status_code == 201
    assert result.transaction is not None
    assert result.transaction.transaction_type == TransactionType.DEPOSIT
    assert result.transaction.status == TransactionStatus.POSTED

    db.refresh(customer)
    db.refresh(settlement)

    assert customer.balance_paise == 70_000
    assert settlement.balance_paise == 120_000

    entries = get_transaction_entries(db, result.transaction.id)

    assert len(entries) == 2

    debit = next(entry for entry in entries if entry.side == EntrySide.DEBIT)
    credit = next(entry for entry in entries if entry.side == EntrySide.CREDIT)

    assert debit.account_id == settlement.id
    assert credit.account_id == customer.id
    assert debit.amount_paise == 20_000
    assert credit.amount_paise == 20_000

    audit = db.scalar(
        select(AuditLog).where(
            AuditLog.resource_id == str(result.transaction.id),
            AuditLog.action == "DEPOSIT",
            AuditLog.outcome == "SUCCESS",
        )
    )

    assert audit is not None


def test_successful_withdrawal(db, transfer_accounts):
    source_owner = transfer_accounts["source_owner"]
    customer = transfer_accounts["source"]

    settlement = create_settlement_account(db, source_owner)

    result = withdraw_funds(
        db,
        current_user=source_owner,
        account_id=customer.id,
        amount_paise=20_000,
        description="Test withdrawal",
        idempotency_key="withdraw-success-001",
    )

    assert result.status_code == 201
    assert result.transaction is not None
    assert result.transaction.transaction_type == TransactionType.WITHDRAWAL
    assert result.transaction.status == TransactionStatus.POSTED

    db.refresh(customer)
    db.refresh(settlement)

    assert customer.balance_paise == 30_000
    assert settlement.balance_paise == 80_000

    entries = get_transaction_entries(db, result.transaction.id)

    assert len(entries) == 2

    debit = next(entry for entry in entries if entry.side == EntrySide.DEBIT)
    credit = next(entry for entry in entries if entry.side == EntrySide.CREDIT)

    assert debit.account_id == customer.id
    assert credit.account_id == settlement.id
    assert debit.amount_paise == 20_000
    assert credit.amount_paise == 20_000


def test_withdrawal_insufficient_customer_funds(db, transfer_accounts):
    source_owner = transfer_accounts["source_owner"]
    customer = transfer_accounts["source"]

    settlement = create_settlement_account(db, source_owner)

    result = withdraw_funds(
        db,
        current_user=source_owner,
        account_id=customer.id,
        amount_paise=60_000,
        description="Excess withdrawal",
        idempotency_key="withdraw-insufficient-001",
    )

    assert result.status_code == 409
    assert result.detail == "Insufficient funds."
    assert result.transaction is not None
    assert result.transaction.status == TransactionStatus.REJECTED

    db.refresh(customer)
    db.refresh(settlement)

    assert customer.balance_paise == 50_000
    assert settlement.balance_paise == 100_000

    entries = get_transaction_entries(db, result.transaction.id)
    assert len(entries) == 0


def test_withdrawal_insufficient_settlement_funds(db, transfer_accounts):
    source_owner = transfer_accounts["source_owner"]
    customer = transfer_accounts["source"]

    settlement = create_settlement_account(
        db,
        source_owner,
        balance_paise=1_000,
    )

    result = withdraw_funds(
        db,
        current_user=source_owner,
        account_id=customer.id,
        amount_paise=5_000,
        description="Withdrawal exceeding settlement funds",
        idempotency_key="withdraw-settlement-001",
    )

    assert result.status_code == 409
    assert result.detail == "Insufficient settlement funds."
    assert result.transaction is not None
    assert result.transaction.status == TransactionStatus.REJECTED

    db.refresh(customer)
    db.refresh(settlement)

    assert customer.balance_paise == 50_000
    assert settlement.balance_paise == 1_000

    entries = get_transaction_entries(db, result.transaction.id)
    assert len(entries) == 0


def test_deposit_to_another_users_account_is_rejected(db, transfer_accounts):
    source_owner = transfer_accounts["source_owner"]
    destination = transfer_accounts["destination"]

    settlement = create_settlement_account(db, source_owner)

    result = deposit_funds(
        db,
        current_user=source_owner,
        account_id=destination.id,
        amount_paise=10_000,
        description="Unauthorized deposit",
        idempotency_key="deposit-unauthorized-001",
    )

    assert result.status_code == 403
    assert result.detail == "You cannot transact using an account you do not own."
    assert result.transaction is None

    db.refresh(destination)
    db.refresh(settlement)

    assert destination.balance_paise == 0
    assert settlement.balance_paise == 100_000


def test_deposit_to_frozen_account_is_rejected(db, transfer_accounts):
    source_owner = transfer_accounts["source_owner"]
    customer = transfer_accounts["source"]

    settlement = create_settlement_account(db, source_owner)

    customer.status = AccountStatus.FROZEN
    db.flush()

    result = deposit_funds(
        db,
        current_user=source_owner,
        account_id=customer.id,
        amount_paise=10_000,
        description="Deposit to frozen account",
        idempotency_key="deposit-frozen-001",
    )

    assert result.status_code == 409
    assert result.detail == "Customer account must be active."
    assert result.transaction is None

    db.refresh(customer)
    db.refresh(settlement)

    assert customer.balance_paise == 50_000
    assert settlement.balance_paise == 100_000


def test_deposit_request_is_idempotent(db, transfer_accounts):
    source_owner = transfer_accounts["source_owner"]
    customer = transfer_accounts["source"]

    settlement = create_settlement_account(db, source_owner)

    arguments = {
        "current_user": source_owner,
        "account_id": customer.id,
        "amount_paise": 10_000,
        "description": "Idempotent deposit",
        "idempotency_key": "deposit-idempotent-001",
    }

    first_result = deposit_funds(db, **arguments)
    second_result = deposit_funds(db, **arguments)

    assert first_result.status_code == 201
    assert second_result.status_code == 201

    assert first_result.transaction.id == second_result.transaction.id

    db.refresh(customer)
    db.refresh(settlement)

    assert customer.balance_paise == 60_000
    assert settlement.balance_paise == 110_000

    transactions = db.scalars(
        select(LedgerTransaction).where(
            LedgerTransaction.initiated_by == source_owner.id,
            LedgerTransaction.transaction_type == TransactionType.DEPOSIT,
        )
    ).all()

    assert len(transactions) == 1


def test_withdrawal_request_is_idempotent(db, transfer_accounts):
    source_owner = transfer_accounts["source_owner"]
    customer = transfer_accounts["source"]

    settlement = create_settlement_account(db, source_owner)

    arguments = {
        "current_user": source_owner,
        "account_id": customer.id,
        "amount_paise": 10_000,
        "description": "Idempotent withdrawal",
        "idempotency_key": "withdraw-idempotent-001",
    }

    first_result = withdraw_funds(db, **arguments)
    second_result = withdraw_funds(db, **arguments)

    assert first_result.status_code == 201
    assert second_result.status_code == 201

    assert first_result.transaction.id == second_result.transaction.id

    db.refresh(customer)
    db.refresh(settlement)

    assert customer.balance_paise == 40_000
    assert settlement.balance_paise == 90_000

    transactions = db.scalars(
        select(LedgerTransaction).where(
            LedgerTransaction.initiated_by == source_owner.id,
            LedgerTransaction.transaction_type == TransactionType.WITHDRAWAL,
        )
    ).all()

    assert len(transactions) == 1


def test_deposit_same_key_different_amount_is_rejected(db, transfer_accounts):
    source_owner = transfer_accounts["source_owner"]
    customer = transfer_accounts["source"]

    settlement = create_settlement_account(db, source_owner)

    first_result = deposit_funds(
        db,
        current_user=source_owner,
        account_id=customer.id,
        amount_paise=10_000,
        description="First deposit",
        idempotency_key="deposit-different-payload-001",
    )

    second_result = deposit_funds(
        db,
        current_user=source_owner,
        account_id=customer.id,
        amount_paise=20_000,
        description="Different amount",
        idempotency_key="deposit-different-payload-001",
    )

    assert first_result.status_code == 201
    assert second_result.status_code == 409
    assert second_result.detail == (
        "Idempotency key was already used for a different request."
    )

    db.refresh(customer)
    db.refresh(settlement)

    assert customer.balance_paise == 60_000
    assert settlement.balance_paise == 110_000


def test_rejected_withdrawal_request_is_idempotent(db, transfer_accounts):
    source_owner = transfer_accounts["source_owner"]
    customer = transfer_accounts["source"]

    settlement = create_settlement_account(db, source_owner)

    arguments = {
        "current_user": source_owner,
        "account_id": customer.id,
        "amount_paise": 60_000,
        "description": "Rejected withdrawal",
        "idempotency_key": "withdraw-rejected-idempotent-001",
    }

    first_result = withdraw_funds(db, **arguments)
    second_result = withdraw_funds(db, **arguments)

    assert first_result.status_code == 409
    assert second_result.status_code == 409

    assert first_result.detail == "Insufficient funds."
    assert second_result.detail == "Insufficient funds."

    assert first_result.transaction.id == second_result.transaction.id

    db.refresh(customer)
    db.refresh(settlement)

    assert customer.balance_paise == 50_000
    assert settlement.balance_paise == 100_000

    transactions = db.scalars(
        select(LedgerTransaction).where(
            LedgerTransaction.initiated_by == source_owner.id,
            LedgerTransaction.transaction_type == TransactionType.WITHDRAWAL,
        )
    ).all()

    assert len(transactions) == 1

    entries = get_transaction_entries(db, first_result.transaction.id)
    assert len(entries) == 0
