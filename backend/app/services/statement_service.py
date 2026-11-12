
import uuid

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.enums import EntrySide, TransactionStatus, UserRole
from app.models.ledger_entry import LedgerEntry
from app.models.transaction import LedgerTransaction
from app.models.user import User
from app.schemas.statement import (
    AccountStatementResponse,
    StatementItem,
    TransactionHistoryItem,
)


def _can_view_transaction(
    transaction: LedgerTransaction,
    current_user: User,
    db: Session,
) -> bool:
    if current_user.role in {UserRole.ADMIN, UserRole.AUDITOR}:
        return True

    if current_user.role != UserRole.ACCOUNT_HOLDER:
        return False

    account_ids = [
        account_id
        for account_id in (
            transaction.source_account_id,
            transaction.destination_account_id,
        )
        if account_id is not None
    ]

    if not account_ids:
        return False

    owned_account = db.scalar(
        select(Account.id).where(
            Account.id.in_(account_ids),
            Account.owner_id == current_user.id,
            Account.is_system.is_(False),
        ).limit(1)
    )

    return owned_account is not None


def get_transaction_history(
    db: Session,
    *,
    current_user: User,
    limit: int = 20,
    offset: int = 0,
):
    query = select(LedgerTransaction)

    if current_user.role == UserRole.ACCOUNT_HOLDER:
        owned_account_ids = select(Account.id).where(
            Account.owner_id == current_user.id,
            Account.is_system.is_(False),
        )

        query = query.where(
            or_(
                LedgerTransaction.source_account_id.in_(owned_account_ids),
                LedgerTransaction.destination_account_id.in_(owned_account_ids),
            )
        )

    elif current_user.role not in {UserRole.ADMIN, UserRole.AUDITOR}:
        raise HTTPException(
            status_code=403,
            detail="You are not permitted to view transaction history.",
        )

    total = db.scalar(
        select(func.count()).select_from(query.subquery())
    ) or 0

    transactions = db.scalars(
        query.order_by(
            LedgerTransaction.created_at.desc(),
            LedgerTransaction.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    ).all()

    return {
        "items": transactions,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_transaction_detail(
    db: Session,
    *,
    transaction_id: uuid.UUID,
    current_user: User,
):
    transaction = db.get(LedgerTransaction, transaction_id)

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found.",
        )

    if not _can_view_transaction(transaction, current_user, db):
        raise HTTPException(
            status_code=404,
            detail="Transaction not found.",
        )

    return transaction


def get_account_statement(
    db: Session,
    *,
    account_id: uuid.UUID,
    current_user: User,
):
    account = db.get(Account, account_id)

    if account is None:
        raise HTTPException(
            status_code=404,
            detail="Account not found.",
        )

    if current_user.role == UserRole.ACCOUNT_HOLDER:
        if account.owner_id != current_user.id or account.is_system:
            raise HTTPException(
                status_code=404,
                detail="Account not found.",
            )

    elif current_user.role not in {UserRole.ADMIN, UserRole.AUDITOR}:
        raise HTTPException(
            status_code=403,
            detail="You are not permitted to view account statements.",
        )

    transactions = db.scalars(
        select(LedgerTransaction)
        .where(
            or_(
                LedgerTransaction.source_account_id == account_id,
                LedgerTransaction.destination_account_id == account_id,
            )
        )
        .order_by(
            LedgerTransaction.created_at.asc(),
            LedgerTransaction.id.asc(),
        )
    ).all()

    transaction_ids = [
        transaction.id for transaction in transactions
    ]

    entries = []

    if transaction_ids:
        entries = db.scalars(
            select(LedgerEntry)
            .where(
                LedgerEntry.account_id == account_id,
                LedgerEntry.transaction_id.in_(transaction_ids),
            )
            .order_by(
                LedgerEntry.created_at.asc(),
                LedgerEntry.id.asc(),
            )
        ).all()

    entries_by_transaction = {}

    for entry in entries:
        entries_by_transaction.setdefault(
            entry.transaction_id, []
        ).append(entry)

    # Customer accounts are credit-normal.
    # System settlement accounts are debit-normal.
    is_debit_normal = account.is_system

    running_balance = 0
    statement_items = []

    for transaction in transactions:
        debit_paise = 0
        credit_paise = 0

        for entry in entries_by_transaction.get(transaction.id, []):
            if entry.side == EntrySide.DEBIT:
                debit_paise += entry.amount_paise
            elif entry.side == EntrySide.CREDIT:
                credit_paise += entry.amount_paise

        if is_debit_normal:
            running_balance += debit_paise - credit_paise
        else:
            running_balance += credit_paise - debit_paise

        attempted_debit = 0
        attempted_credit = 0

        # Rejected attempts are visible but never change the balance.
        if transaction.status == TransactionStatus.REJECTED:
            if transaction.source_account_id == account_id:
                attempted_debit = transaction.amount_paise
            elif transaction.destination_account_id == account_id:
                attempted_credit = transaction.amount_paise

        statement_items.append(
            StatementItem(
                transaction_id=transaction.id,
                reference=transaction.reference,
                transaction_type=transaction.transaction_type,
                initiated_by=transaction.initiated_by,
                status=transaction.status,
                description=transaction.description,
                created_at=transaction.created_at,
                debit_paise=debit_paise,
                credit_paise=credit_paise,
                attempted_debit_paise=attempted_debit,
                attempted_credit_paise=attempted_credit,
                running_balance_paise=running_balance,
            )
        )

    return AccountStatementResponse(
        account_id=account.id,
        account_number=account.account_number,
        currency=account.currency,
        opening_balance_paise=0,
        closing_balance_paise=running_balance,
        items=statement_items,
    )
