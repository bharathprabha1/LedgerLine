ï»¿import uuid

import pytest
from fastapi import HTTPException

from app.models.account import Account
from app.models.enums import (
    AccountStatus,
    EntrySide,
    TransactionStatus,
    TransactionType,
    UserRole,
)
from app.models.ledger_entry import LedgerEntry
from app.models.transaction import LedgerTransaction
from app.models.user import User
from app.services.statement_service import (
    get_account_statement,
    get_transaction_detail,
    get_transaction_history,
)


def make_user(db, role=UserRole.ACCOUNT_HOLDER):
    suffix = uuid.uuid4().hex

    user = User(
        full_name="Statement Test User",
        email=f"statement-{suffix}@example.com",
        password_hash="test-only-password-hash",
        role=role,
        is_active=True,
    )

    db.add(user)
    db.flush()
    return user


def make_account(db, owner, *, balance=0, is_system=False):
    account = Account(
        account_number=f"LLSTMT{uuid.uuid4().hex[:12].upper()}",
        owner_id=owner.id,
        balance_paise=balance,
        currency="INR",
        status=AccountStatus.ACTIVE,
        is_system=is_system,
    )

    db.add(account)
    db.flush()
    return account


def make_transaction(
    db,
    *,
    initiated_by,
    transaction_type=TransactionType.TRANSFER,
    status=TransactionStatus.POSTED,
    amount=10_000,
    source=None,
    destination=None,
):
    transaction = LedgerTransaction(
        reference=f"STMT-{uuid.uuid4().hex}",
        transaction_type=transaction_type,
        status=status,
        amount_paise=amount,
        source_account_id=source.id if source else None,
        destination_account_id=destination.id if destination else None,
        initiated_by=initiated_by.id,
        description="Statement service test",
    )

    db.add(transaction)
    db.flush()
    return transaction


def make_entry(
    db,
    *,
    transaction,
    account,
    side,
    amount=10_000,
):
    entry = LedgerEntry(
        transaction_id=transaction.id,
        account_id=account.id,
        side=side,
        amount_paise=amount,
        currency="INR",
    )

    db.add(entry)
    db.flush()
    return entry


# ---------------------------------------------------------
# ACCOUNT STATEMENT
# ---------------------------------------------------------


def test_empty_account_statement(db):
    customer = make_user(db)
    account = make_account(db, customer)

    statement = get_account_statement(
        db,
        account_id=account.id,
        current_user=customer,
    )

    assert statement.account_id == account.id
    assert statement.account_number == account.account_number
    assert statement.currency == "INR"
    assert statement.opening_balance_paise == 0
    assert statement.closing_balance_paise == 0
    assert statement.items == []


def test_customer_statement_calculates_credit_normal_balance(db):
    customer = make_user(db)
    account = make_account(db, customer, balance=10_000)

    transaction = make_transaction(
        db,
        initiated_by=customer,
        transaction_type=TransactionType.DEPOSIT,
        destination=account,
    )

    make_entry(
        db,
        transaction=transaction,
        account=account,
        side=EntrySide.CREDIT,
        amount=10_000,
    )

    statement = get_account_statement(
        db,
        account_id=account.id,
        current_user=customer,
    )

    assert len(statement.items) == 1

    item = statement.items[0]
    assert item.credit_paise == 10_000
    assert item.debit_paise == 0
    assert item.running_balance_paise == 10_000

    assert statement.closing_balance_paise == 10_000


def test_customer_statement_calculates_debit_and_credit(db):
    customer = make_user(db)
    account = make_account(db, customer, balance=5_000)

    transaction = make_transaction(
        db,
        initiated_by=customer,
        transaction_type=TransactionType.TRANSFER,
        source=account,
    )

    make_entry(
        db,
        transaction=transaction,
        account=account,
        side=EntrySide.DEBIT,
        amount=5_000,
    )

    statement = get_account_statement(
        db,
        account_id=account.id,
        current_user=customer,
    )

    item = statement.items[0]

    assert item.debit_paise == 5_000
    assert item.credit_paise == 0
    assert item.running_balance_paise == -5_000
    assert statement.closing_balance_paise == -5_000


def test_rejected_transaction_is_visible_without_changing_balance(db):
    customer = make_user(db)
    account = make_account(db, customer, balance=50_000)

    transaction = make_transaction(
        db,
        initiated_by=customer,
        status=TransactionStatus.REJECTED,
        amount=60_000,
        source=account,
    )

    statement = get_account_statement(
        db,
        account_id=account.id,
        current_user=customer,
    )

    assert len(statement.items) == 1

    item = statement.items[0]

    assert item.status == TransactionStatus.REJECTED
    assert item.attempted_debit_paise == 60_000
    assert item.attempted_credit_paise == 0
    assert item.debit_paise == 0
    assert item.credit_paise == 0
    assert item.running_balance_paise == 0
    assert statement.closing_balance_paise == 0


def test_rejected_destination_transaction_shows_attempted_credit(db):
    customer = make_user(db)
    account = make_account(db, customer)

    make_transaction(
        db,
        initiated_by=customer,
        status=TransactionStatus.REJECTED,
        amount=15_000,
        destination=account,
    )

    statement = get_account_statement(
        db,
        account_id=account.id,
        current_user=customer,
    )

    item = statement.items[0]

    assert item.attempted_credit_paise == 15_000
    assert item.attempted_debit_paise == 0
    assert item.running_balance_paise == 0


def test_system_account_uses_debit_normal_balance(db):
    admin = make_user(db, UserRole.ADMIN)
    system_account = make_account(
        db,
        admin,
        is_system=True,
        balance=12_000,
    )

    transaction = make_transaction(
        db,
        initiated_by=admin,
        transaction_type=TransactionType.DEPOSIT,
        destination=system_account,
    )

    make_entry(
        db,
        transaction=transaction,
        account=system_account,
        side=EntrySide.DEBIT,
        amount=12_000,
    )

    statement = get_account_statement(
        db,
        account_id=system_account.id,
        current_user=admin,
    )

    item = statement.items[0]

    assert item.debit_paise == 12_000
    assert item.credit_paise == 0
    assert item.running_balance_paise == 12_000
    assert statement.closing_balance_paise == 12_000


def test_customer_cannot_view_system_account_statement(db):
    admin = make_user(db, UserRole.ADMIN)
    customer = make_user(db)

    system_account = make_account(
        db,
        admin,
        is_system=True,
    )

    with pytest.raises(HTTPException) as exc:
        get_account_statement(
            db,
            account_id=system_account.id,
            current_user=customer,
        )

    assert exc.value.status_code == 404


def test_customer_cannot_view_another_users_statement(db):
    owner = make_user(db)
    other_customer = make_user(db)

    account = make_account(db, owner)

    with pytest.raises(HTTPException) as exc:
        get_account_statement(
            db,
            account_id=account.id,
            current_user=other_customer,
        )

    assert exc.value.status_code == 404


def test_missing_account_statement_returns_404(db):
    customer = make_user(db)

    with pytest.raises(HTTPException) as exc:
        get_account_statement(
            db,
            account_id=uuid.uuid4(),
            current_user=customer,
        )

    assert exc.value.status_code == 404


# ---------------------------------------------------------
# TRANSACTION HISTORY AND DETAIL
# ---------------------------------------------------------


def test_admin_can_view_all_transaction_history(db):
    admin = make_user(db, UserRole.ADMIN)
    first_owner = make_user(db)
    second_owner = make_user(db)

    first_account = make_account(db, first_owner)
    second_account = make_account(db, second_owner)

    make_transaction(
        db,
        initiated_by=first_owner,
        source=first_account,
    )

    make_transaction(
        db,
        initiated_by=second_owner,
        source=second_account,
    )

    history = get_transaction_history(
        db,
        current_user=admin,
    )

    assert history["total"] == 2
    assert len(history["items"]) == 2


def test_auditor_can_view_all_transaction_history(db):
    auditor = make_user(db, UserRole.AUDITOR)
    owner = make_user(db)
    account = make_account(db, owner)

    make_transaction(
        db,
        initiated_by=owner,
        source=account,
    )

    history = get_transaction_history(
        db,
        current_user=auditor,
    )

    assert history["total"] == 1
    assert len(history["items"]) == 1


def test_customer_history_pagination(db):
    customer = make_user(db)
    account = make_account(db, customer)

    for _ in range(3):
        make_transaction(
            db,
            initiated_by=customer,
            source=account,
        )

    first_page = get_transaction_history(
        db,
        current_user=customer,
        limit=2,
        offset=0,
    )

    second_page = get_transaction_history(
        db,
        current_user=customer,
        limit=2,
        offset=2,
    )

    assert first_page["total"] == 3
    assert len(first_page["items"]) == 2
    assert first_page["limit"] == 2
    assert first_page["offset"] == 0

    assert second_page["total"] == 3
    assert len(second_page["items"]) == 1
    assert second_page["offset"] == 2


def test_transaction_detail_is_available_to_admin(db):
    admin = make_user(db, UserRole.ADMIN)
    owner = make_user(db)
    account = make_account(db, owner)

    transaction = make_transaction(
        db,
        initiated_by=owner,
        source=account,
    )

    result = get_transaction_detail(
        db,
        transaction_id=transaction.id,
        current_user=admin,
    )

    assert result.id == transaction.id


def test_transaction_detail_returns_404_for_missing_id(db):
    admin = make_user(db, UserRole.ADMIN)

    with pytest.raises(HTTPException) as exc:
        get_transaction_detail(
            db,
            transaction_id=uuid.uuid4(),
            current_user=admin,
        )

    assert exc.value.status_code == 404
