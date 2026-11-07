
import hashlib
import json
import secrets
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.audit_log import AuditLog
from app.models.enums import (
    AccountStatus,
    EntrySide,
    TransactionStatus,
    TransactionType,
    UserRole,
)
from app.models.idempotency import IdempotencyRecord
from app.models.ledger_entry import LedgerEntry
from app.models.transaction import LedgerTransaction
from app.models.user import User


TRANSFER_ENDPOINT = "/api/v1/transactions/transfer"
DEPOSIT_ENDPOINT = "/api/v1/transactions/deposit"
WITHDRAWAL_ENDPOINT = "/api/v1/transactions/withdrawal"

MAX_BIGINT = 9_223_372_036_854_775_807


@dataclass(frozen=True)
class TransferResult:
    transaction: LedgerTransaction | None
    status_code: int
    detail: str | None = None


def _request_hash(payload: dict) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _new_reference() -> str:
    return "LLTXN" + secrets.token_hex(12).upper()


def _claim_idempotency_key(
    db: Session,
    *,
    current_user: User,
    endpoint: str,
    idempotency_key: str,
    request_hash: str,
):
    """
    Atomically claim an idempotency key.

    Returns:
        (record, None) when newly claimed.
        (None, result) when an existing request must be replayed.
    """

    if not idempotency_key or not idempotency_key.strip():
        return None, TransferResult(
            transaction=None,
            status_code=400,
            detail="A valid Idempotency-Key header is required.",
        )

    claim = (
        insert(IdempotencyRecord)
        .values(
            id=uuid.uuid4(),
            user_id=current_user.id,
            endpoint=endpoint,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        .on_conflict_do_nothing(
            constraint="uq_idempotency_user_endpoint_key"
        )
        .returning(IdempotencyRecord.id)
    )

    claimed_id = db.execute(claim).scalar_one_or_none()

    if claimed_id is not None:
        record = db.get(IdempotencyRecord, claimed_id)
        return record, None

    existing = db.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.user_id == current_user.id,
            IdempotencyRecord.endpoint == endpoint,
            IdempotencyRecord.idempotency_key == idempotency_key,
        )
    )

    if existing is None:
        db.rollback()
        return None, TransferResult(
            transaction=None,
            status_code=409,
            detail="Unable to verify the idempotency request.",
        )

    if existing.request_hash != request_hash:
        db.commit()
        return None, TransferResult(
            transaction=None,
            status_code=409,
            detail="Idempotency key was already used for a different request.",
        )

    if existing.response_status is None:
        db.commit()
        return None, TransferResult(
            transaction=None,
            status_code=409,
            detail="The original request has no completed result.",
        )

    return None, existing


def _replay_existing_request(
    db: Session,
    *,
    current_user: User,
    existing: IdempotencyRecord,
    action: str,
    attempt_resource_type: str,
) -> TransferResult:
    transaction = (
        db.get(LedgerTransaction, existing.transaction_id)
        if existing.transaction_id
        else None
    )

    detail = None

    if existing.response_status != 201:
        resource_type = (
            "TRANSACTION" if transaction else attempt_resource_type
        )
        resource_id = (
            str(transaction.id)
            if transaction
            else str(existing.id)
        )

        audit = db.scalar(
            select(AuditLog)
            .where(
                AuditLog.actor_id == current_user.id,
                AuditLog.action == action,
                AuditLog.resource_type == resource_type,
                AuditLog.resource_id == resource_id,
                AuditLog.outcome == "REJECTED",
            )
            .order_by(AuditLog.created_at.desc())
            .limit(1)
        )

        detail = (
            audit.details.get("reason")
            if audit and audit.details
            else f"The original {action.lower()} was rejected."
        )

    response_status = existing.response_status
    db.commit()

    if transaction is not None:
        db.refresh(transaction)

    return TransferResult(
        transaction=transaction,
        status_code=response_status,
        detail=detail,
    )


def _record_rejection(
    db: Session,
    *,
    current_user: User,
    idempotency_record: IdempotencyRecord,
    status_code: int,
    reason: str,
    source_account_id: uuid.UUID,
    destination_account_id: uuid.UUID,
    amount_paise: int,
    description: str | None,
    accounts_exist: bool,
) -> TransferResult:
    """
    Persist a rejected transfer attempt without changing balances
    or creating ledger entries.
    """

    transaction = None

    if accounts_exist:
        transaction = LedgerTransaction(
            reference=_new_reference(),
            transaction_type=TransactionType.TRANSFER,
            status=TransactionStatus.REJECTED,
            amount_paise=amount_paise,
            source_account_id=source_account_id,
            destination_account_id=destination_account_id,
            initiated_by=current_user.id,
            description=description,
        )
        db.add(transaction)
        db.flush()

    resource_type = (
        "TRANSACTION" if transaction else "TRANSFER_ATTEMPT"
    )
    resource_id = (
        str(transaction.id)
        if transaction
        else str(idempotency_record.id)
    )

    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="TRANSFER",
            resource_type=resource_type,
            resource_id=resource_id,
            outcome="REJECTED",
            details={
                "reason": reason,
                "http_status": status_code,
                "source_account_id": str(source_account_id),
                "destination_account_id": str(destination_account_id),
                "amount_paise": amount_paise,
            },
        )
    )

    idempotency_record.transaction_id = (
        transaction.id if transaction else None
    )
    idempotency_record.response_status = status_code

    db.commit()

    if transaction is not None:
        db.refresh(transaction)

    return TransferResult(
        transaction=transaction,
        status_code=status_code,
        detail=reason,
    )


def transfer_funds(
    db: Session,
    *,
    current_user: User,
    source_account_id: uuid.UUID,
    destination_account_id: uuid.UUID,
    amount_paise: int,
    description: str | None,
    idempotency_key: str,
) -> TransferResult:

    if not idempotency_key or not idempotency_key.strip():
        return TransferResult(
            transaction=None,
            status_code=400,
            detail="A valid Idempotency-Key header is required.",
        )

    payload = {
        "source_account_id": str(source_account_id),
        "destination_account_id": str(destination_account_id),
        "amount_paise": amount_paise,
        "description": description,
    }
    request_hash = _request_hash(payload)

    try:
        idempotency_record, existing = _claim_idempotency_key(
            db,
            current_user=current_user,
            endpoint=TRANSFER_ENDPOINT,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )

        if existing is not None:
            if isinstance(existing, TransferResult):
                return existing

            return _replay_existing_request(
                db,
                current_user=current_user,
                existing=existing,
                action="TRANSFER",
                attempt_resource_type="TRANSFER_ATTEMPT",
            )

        if idempotency_record is None:
            return TransferResult(
                transaction=None,
                status_code=409,
                detail="Unable to claim the idempotency key.",
            )

        if current_user.role != UserRole.ACCOUNT_HOLDER:
            return _record_rejection(
                db,
                current_user=current_user,
                idempotency_record=idempotency_record,
                status_code=403,
                reason="Only account holders can initiate transfers.",
                source_account_id=source_account_id,
                destination_account_id=destination_account_id,
                amount_paise=amount_paise,
                description=description,
                accounts_exist=False,
            )

        account_ids = sorted(
            {source_account_id, destination_account_id},
            key=str,
        )

        locked_accounts = db.scalars(
            select(Account)
            .where(Account.id.in_(account_ids))
            .order_by(Account.id)
            .with_for_update()
        ).all()

        accounts = {
            account.id: account
            for account in locked_accounts
        }

        source = accounts.get(source_account_id)
        destination = accounts.get(destination_account_id)

        if source is None or destination is None:
            return _record_rejection(
                db,
                current_user=current_user,
                idempotency_record=idempotency_record,
                status_code=404,
                reason="Source or destination account not found.",
                source_account_id=source_account_id,
                destination_account_id=destination_account_id,
                amount_paise=amount_paise,
                description=description,
                accounts_exist=False,
            )

        if source_account_id == destination_account_id:
            return _record_rejection(
                db,
                current_user=current_user,
                idempotency_record=idempotency_record,
                status_code=400,
                reason="Source and destination accounts must differ.",
                source_account_id=source_account_id,
                destination_account_id=destination_account_id,
                amount_paise=amount_paise,
                description=description,
                accounts_exist=True,
            )

        if source.owner_id != current_user.id:
            return _record_rejection(
                db,
                current_user=current_user,
                idempotency_record=idempotency_record,
                status_code=403,
                reason="You cannot transfer from an account you do not own.",
                source_account_id=source_account_id,
                destination_account_id=destination_account_id,
                amount_paise=amount_paise,
                description=description,
                accounts_exist=True,
            )

        if source.is_system or destination.is_system:
            return _record_rejection(
                db,
                current_user=current_user,
                idempotency_record=idempotency_record,
                status_code=400,
                reason="System accounts cannot be used for customer transfers.",
                source_account_id=source_account_id,
                destination_account_id=destination_account_id,
                amount_paise=amount_paise,
                description=description,
                accounts_exist=True,
            )

        destination_owner = db.get(User, destination.owner_id)

        if (
            destination_owner is None
            or not destination_owner.is_active
            or destination_owner.role != UserRole.ACCOUNT_HOLDER
        ):
            return _record_rejection(
                db,
                current_user=current_user,
                idempotency_record=idempotency_record,
                status_code=409,
                reason="Destination account owner is not eligible to receive transfers.",
                source_account_id=source_account_id,
                destination_account_id=destination_account_id,
                amount_paise=amount_paise,
                description=description,
                accounts_exist=True,
            )

        if (
            source.status != AccountStatus.ACTIVE
            or destination.status != AccountStatus.ACTIVE
        ):
            return _record_rejection(
                db,
                current_user=current_user,
                idempotency_record=idempotency_record,
                status_code=409,
                reason="Both accounts must be active.",
                source_account_id=source_account_id,
                destination_account_id=destination_account_id,
                amount_paise=amount_paise,
                description=description,
                accounts_exist=True,
            )

        if source.currency != destination.currency:
            return _record_rejection(
                db,
                current_user=current_user,
                idempotency_record=idempotency_record,
                status_code=400,
                reason="Account currencies must match.",
                source_account_id=source_account_id,
                destination_account_id=destination_account_id,
                amount_paise=amount_paise,
                description=description,
                accounts_exist=True,
            )

        if amount_paise <= 0 or amount_paise > MAX_BIGINT:
            return _record_rejection(
                db,
                current_user=current_user,
                idempotency_record=idempotency_record,
                status_code=400,
                reason="Transfer amount is outside the permitted range.",
                source_account_id=source_account_id,
                destination_account_id=destination_account_id,
                amount_paise=amount_paise,
                description=description,
                accounts_exist=True,
            )

        if source.balance_paise < amount_paise:
            return _record_rejection(
                db,
                current_user=current_user,
                idempotency_record=idempotency_record,
                status_code=409,
                reason="Insufficient funds.",
                source_account_id=source_account_id,
                destination_account_id=destination_account_id,
                amount_paise=amount_paise,
                description=description,
                accounts_exist=True,
            )

        if destination.balance_paise > MAX_BIGINT - amount_paise:
            return _record_rejection(
                db,
                current_user=current_user,
                idempotency_record=idempotency_record,
                status_code=409,
                reason="Destination account balance limit would be exceeded.",
                source_account_id=source_account_id,
                destination_account_id=destination_account_id,
                amount_paise=amount_paise,
                description=description,
                accounts_exist=True,
            )

        transaction = LedgerTransaction(
            reference=_new_reference(),
            transaction_type=TransactionType.TRANSFER,
            status=TransactionStatus.POSTED,
            amount_paise=amount_paise,
            source_account_id=source.id,
            destination_account_id=destination.id,
            initiated_by=current_user.id,
            description=description,
        )

        db.add(transaction)
        db.flush()

        db.add_all([
            LedgerEntry(
                transaction_id=transaction.id,
                account_id=source.id,
                side=EntrySide.DEBIT,
                amount_paise=amount_paise,
                currency=source.currency,
            ),
            LedgerEntry(
                transaction_id=transaction.id,
                account_id=destination.id,
                side=EntrySide.CREDIT,
                amount_paise=amount_paise,
                currency=destination.currency,
            ),
        ])

        source.balance_paise -= amount_paise
        destination.balance_paise += amount_paise

        db.add(
            AuditLog(
                actor_id=current_user.id,
                action="TRANSFER",
                resource_type="TRANSACTION",
                resource_id=str(transaction.id),
                outcome="SUCCESS",
                details={
                    "source_account_id": str(source.id),
                    "destination_account_id": str(destination.id),
                    "amount_paise": amount_paise,
                    "currency": source.currency,
                },
            )
        )

        idempotency_record.transaction_id = transaction.id
        idempotency_record.response_status = 201

        db.commit()
        db.refresh(transaction)

        return TransferResult(
            transaction=transaction,
            status_code=201,
        )

    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------
# DEPOSIT AND WITHDRAWAL HELPERS
# ---------------------------------------------------------

def _record_cash_rejection(
    db: Session,
    *,
    current_user: User,
    idempotency_record: IdempotencyRecord,
    transaction_type: TransactionType,
    action: str,
    status_code: int,
    reason: str,
    source_account_id: uuid.UUID | None,
    destination_account_id: uuid.UUID | None,
    amount_paise: int,
    description: str | None,
    accounts_exist: bool,
) -> TransferResult:
    """
    Record a rejected deposit or withdrawal.

    A rejected transaction is created only when both account
    references are valid. Otherwise, the attempt is recorded
    in the audit log without transaction account references.
    """

    transaction = None

    if accounts_exist:
        transaction = LedgerTransaction(
            reference=_new_reference(),
            transaction_type=transaction_type,
            status=TransactionStatus.REJECTED,
            amount_paise=amount_paise,
            source_account_id=source_account_id,
            destination_account_id=destination_account_id,
            initiated_by=current_user.id,
            description=description,
        )
        db.add(transaction)
        db.flush()

    resource_type = (
        "TRANSACTION" if transaction else "CASH_ATTEMPT"
    )
    resource_id = (
        str(transaction.id)
        if transaction
        else str(idempotency_record.id)
    )

    db.add(
        AuditLog(
            actor_id=current_user.id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome="REJECTED",
            details={
                "reason": reason,
                "http_status": status_code,
                "amount_paise": amount_paise,
                "source_account_id": (
                    str(source_account_id)
                    if source_account_id else None
                ),
                "destination_account_id": (
                    str(destination_account_id)
                    if destination_account_id else None
                ),
            },
        )
    )

    idempotency_record.transaction_id = (
        transaction.id if transaction else None
    )
    idempotency_record.response_status = status_code

    db.commit()

    if transaction is not None:
        db.refresh(transaction)

    return TransferResult(
        transaction=transaction,
        status_code=status_code,
        detail=reason,
    )


def _process_cash_operation(
    db: Session,
    *,
    current_user: User,
    account_id: uuid.UUID,
    amount_paise: int,
    description: str | None,
    idempotency_key: str,
    is_deposit: bool,
) -> TransferResult:

    action = "DEPOSIT" if is_deposit else "WITHDRAWAL"

    transaction_type = (
        TransactionType.DEPOSIT
        if is_deposit
        else TransactionType.WITHDRAWAL
    )

    endpoint = (
        DEPOSIT_ENDPOINT
        if is_deposit
        else WITHDRAWAL_ENDPOINT
    )

    try:
        payload = {
            "account_id": str(account_id),
            "amount_paise": amount_paise,
            "description": description,
        }

        request_hash = _request_hash(payload)

        idempotency_record, existing = _claim_idempotency_key(
            db,
            current_user=current_user,
            endpoint=endpoint,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )

        if existing is not None:
            if isinstance(existing, TransferResult):
                return existing

            return _replay_existing_request(
                db,
                current_user=current_user,
                existing=existing,
                action=action,
                attempt_resource_type="CASH_ATTEMPT",
            )

        if idempotency_record is None:
            return TransferResult(
                transaction=None,
                status_code=409,
                detail="Unable to claim the idempotency key.",
            )

        if current_user.role != UserRole.ACCOUNT_HOLDER:
            return _record_cash_rejection(
                db,
                current_user=current_user,
                idempotency_record=idempotency_record,
                transaction_type=transaction_type,
                action=action,
                status_code=403,
                reason="Only account holders can initiate this operation.",
                source_account_id=None,
                destination_account_id=None,
                amount_paise=amount_paise,
                description=description,
                accounts_exist=False,
            )

        if amount_paise <= 0 or amount_paise > MAX_BIGINT:
            return _record_cash_rejection(
                db,
                current_user=current_user,
                idempotency_record=idempotency_record,
                transaction_type=transaction_type,
                action=action,
                status_code=400,
                reason="Transaction amount is outside the permitted range.",
                source_account_id=None,
                destination_account_id=None,
                amount_paise=amount_paise,
                description=description,
                accounts_exist=False,
            )

        # Lock the customer account and settlement account together.
        # Consistent ordering reduces deadlock risk.
        locked_accounts = db.scalars(
            select(Account)
            .where(
                (Account.id == account_id)
                | (Account.is_system.is_(True))
            )
            .order_by(Account.id)
            .with_for_update()
        ).all()

        customer_account = next(
            (
                account for account in locked_accounts
                if account.id == account_id and not account.is_system
            ),
            None,
        )

        system_accounts = [
            account
            for account in locked_accounts
            if account.is_system
        ]

        settlement_account = (
            system_accounts[0]
            if len(system_accounts) == 1
            else None
        )

        if customer_account is None:
            return _record_cash_rejection(
                db,
                current_user=current_user,
                idempotency_record=idempotency_record,
                transaction_type=transaction_type,
                action=action,
                status_code=404,
                reason="Customer account not found.",
                source_account_id=None,
                destination_account_id=None,
                amount_paise=amount_paise,
                description=description,
                accounts_exist=False,
            )

        if customer_account.owner_id != current_user.id:
            return _record_cash_rejection(
                db,
                current_user=current_user,
                idempotency_record=idempotency_record,
                transaction_type=transaction_type,
                action=action,
                status_code=403,
                reason="You cannot transact using an account you do not own.",
                source_account_id=None,
                destination_account_id=None,
                amount_paise=amount_paise,
                description=description,
                accounts_exist=False,
            )

        if customer_account.status != AccountStatus.ACTIVE:
            return _record_cash_rejection(
                db,
                current_user=current_user,
                idempotency_record=idempotency_record,
                transaction_type=transaction_type,
                action=action,
                status_code=409,
                reason="Customer account must be active.",
                source_account_id=None,
                destination_account_id=None,
                amount_paise=amount_paise,
                description=description,
                accounts_exist=False,
            )

        if settlement_account is None:
            return _record_cash_rejection(
                db,
                current_user=current_user,
                idempotency_record=idempotency_record,
                transaction_type=transaction_type,
                action=action,
                status_code=503,
                reason="System settlement account is unavailable.",
                source_account_id=None,
                destination_account_id=None,
                amount_paise=amount_paise,
                description=description,
                accounts_exist=False,
            )

        if settlement_account.status != AccountStatus.ACTIVE:
            return _record_cash_rejection(
                db,
                current_user=current_user,
                idempotency_record=idempotency_record,
                transaction_type=transaction_type,
                action=action,
                status_code=503,
                reason="System settlement account is not active.",
                source_account_id=None,
                destination_account_id=None,
                amount_paise=amount_paise,
                description=description,
                accounts_exist=False,
            )

        if customer_account.currency != settlement_account.currency:
            return _record_cash_rejection(
                db,
                current_user=current_user,
                idempotency_record=idempotency_record,
                transaction_type=transaction_type,
                action=action,
                status_code=409,
                reason="Customer and settlement account currencies do not match.",
                source_account_id=None,
                destination_account_id=None,
                amount_paise=amount_paise,
                description=description,
                accounts_exist=False,
            )

        # Deposit:
        #   DEBIT settlement account
        #   CREDIT customer account
        #
        # Withdrawal:
        #   DEBIT customer account
        #   CREDIT settlement account

        if is_deposit:
            source = settlement_account
            destination = customer_account
        else:
            source = customer_account
            destination = settlement_account

        if is_deposit:
            if (
                settlement_account.balance_paise
                > MAX_BIGINT - amount_paise
                or customer_account.balance_paise
                > MAX_BIGINT - amount_paise
            ):
                return _record_cash_rejection(
                    db,
                    current_user=current_user,
                    idempotency_record=idempotency_record,
                    transaction_type=transaction_type,
                    action=action,
                    status_code=409,
                    reason="Account balance limit would be exceeded.",
                    source_account_id=source.id,
                    destination_account_id=destination.id,
                    amount_paise=amount_paise,
                    description=description,
                    accounts_exist=True,
                )

        else:
            if customer_account.balance_paise < amount_paise:
                return _record_cash_rejection(
                    db,
                    current_user=current_user,
                    idempotency_record=idempotency_record,
                    transaction_type=transaction_type,
                    action=action,
                    status_code=409,
                    reason="Insufficient funds.",
                    source_account_id=source.id,
                    destination_account_id=destination.id,
                    amount_paise=amount_paise,
                    description=description,
                    accounts_exist=True,
                )

            if settlement_account.balance_paise < amount_paise:
                return _record_cash_rejection(
                    db,
                    current_user=current_user,
                    idempotency_record=idempotency_record,
                    transaction_type=transaction_type,
                    action=action,
                    status_code=409,
                    reason="Insufficient settlement funds.",
                    source_account_id=source.id,
                    destination_account_id=destination.id,
                    amount_paise=amount_paise,
                    description=description,
                    accounts_exist=True,
                )

        transaction = LedgerTransaction(
            reference=_new_reference(),
            transaction_type=transaction_type,
            status=TransactionStatus.POSTED,
            amount_paise=amount_paise,
            source_account_id=source.id,
            destination_account_id=destination.id,
            initiated_by=current_user.id,
            description=description,
        )

        db.add(transaction)
        db.flush()

        db.add_all([
            LedgerEntry(
                transaction_id=transaction.id,
                account_id=source.id,
                side=EntrySide.DEBIT,
                amount_paise=amount_paise,
                currency=source.currency,
            ),
            LedgerEntry(
                transaction_id=transaction.id,
                account_id=destination.id,
                side=EntrySide.CREDIT,
                amount_paise=amount_paise,
                currency=destination.currency,
            ),
        ])

        # Stored balance convention:
        # System asset account increases on debit.
        # Customer liability account increases on credit.
        if is_deposit:
            settlement_account.balance_paise += amount_paise
            customer_account.balance_paise += amount_paise
        else:
            customer_account.balance_paise -= amount_paise
            settlement_account.balance_paise -= amount_paise

        db.add(
            AuditLog(
                actor_id=current_user.id,
                action=action,
                resource_type="TRANSACTION",
                resource_id=str(transaction.id),
                outcome="SUCCESS",
                details={
                    "source_account_id": str(source.id),
                    "destination_account_id": str(destination.id),
                    "customer_account_id": str(customer_account.id),
                    "settlement_account_id": str(settlement_account.id),
                    "amount_paise": amount_paise,
                    "currency": customer_account.currency,
                },
            )
        )

        idempotency_record.transaction_id = transaction.id
        idempotency_record.response_status = 201

        db.commit()
        db.refresh(transaction)

        return TransferResult(
            transaction=transaction,
            status_code=201,
        )

    except Exception:
        db.rollback()
        raise


def deposit_funds(
    db: Session,
    *,
    current_user: User,
    account_id: uuid.UUID,
    amount_paise: int,
    description: str | None,
    idempotency_key: str,
) -> TransferResult:
    return _process_cash_operation(
        db,
        current_user=current_user,
        account_id=account_id,
        amount_paise=amount_paise,
        description=description,
        idempotency_key=idempotency_key,
        is_deposit=True,
    )


def withdraw_funds(
    db: Session,
    *,
    current_user: User,
    account_id: uuid.UUID,
    amount_paise: int,
    description: str | None,
    idempotency_key: str,
) -> TransferResult:
    return _process_cash_operation(
        db,
        current_user=current_user,
        account_id=account_id,
        amount_paise=amount_paise,
        description=description,
        idempotency_key=idempotency_key,
        is_deposit=False,
    )
