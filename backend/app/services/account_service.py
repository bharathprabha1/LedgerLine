
import secrets
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.account import Account
from app.models.audit_log import AuditLog
from app.models.enums import AccountStatus


def generate_account_number() -> str:
    """Generate a 14-character account number."""
    return "LL" + str(secrets.randbelow(10**12)).zfill(12)


def create_account(db: Session, owner_id: uuid.UUID):
    """Create an account with a unique generated account number."""

    for attempt in range(5):
        account = Account(
            account_number=generate_account_number(),
            owner_id=owner_id,
            balance_paise=0,
            currency="INR",
            status=AccountStatus.ACTIVE,
        )

        db.add(account)

        try:
            db.commit()
            db.refresh(account)
            return account

        except IntegrityError as error:
            db.rollback()

            # Retry only when the account-number unique index collided.
            original_error = error.orig
            diagnostic = getattr(original_error, "diag", None)
            constraint_name = getattr(
                diagnostic, "constraint_name", None
            )

            if constraint_name != "ix_accounts_account_number":
                raise

            if attempt == 4:
                raise

    raise RuntimeError("Unable to generate a unique account number.")


def record_audit_event(
    *,
    actor_id: uuid.UUID,
    action: str,
    resource_type: str,
    resource_id: str | None,
    outcome: str,
    details: dict | None = None,
    request_id: str | None = None,
    ip_address: str | None = None,
):
    """
    Write an audit event in its own transaction.

    Used for refused operations so that their audit records
    survive rollback of the business transaction.
    """

    with SessionLocal() as audit_db:
        audit_db.add(
            AuditLog(
                actor_id=actor_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                outcome=outcome,
                details=details,
                request_id=request_id,
                ip_address=ip_address,
            )
        )
        audit_db.commit()


def change_account_status(
    db: Session,
    *,
    account_id: uuid.UUID,
    requested_status: AccountStatus,
    actor_id: uuid.UUID,
    request_id: str | None = None,
    ip_address: str | None = None,
):
    """Change account status with row locking and audit logging."""

    action = "ACCOUNT_STATUS_CHANGE"

    # Lock the account row to prevent simultaneous status changes.
    account = db.scalar(
        select(Account)
        .where(Account.id == account_id)
        .with_for_update()
    )

    if account is None:
        record_audit_event(
            actor_id=actor_id,
            action=action,
            resource_type="ACCOUNT",
            resource_id=str(account_id),
            outcome="REJECTED",
            details={
                "requested_status": requested_status.value,
                "reason": "Account not found",
            },
            request_id=request_id,
            ip_address=ip_address,
        )

        raise HTTPException(
            status_code=404,
            detail="Account not found.",
        )

    current_status = account.status

    # Validate permitted status transitions.
    allowed_transitions = {
        AccountStatus.ACTIVE: {
            AccountStatus.FROZEN,
            AccountStatus.CLOSED,
        },
        AccountStatus.FROZEN: {
            AccountStatus.ACTIVE,
            AccountStatus.CLOSED,
        },
        AccountStatus.CLOSED: set(),
    }

    if requested_status not in allowed_transitions[current_status]:
        reason = "Requested account status transition is not allowed."

        record_audit_event(
            actor_id=actor_id,
            action=action,
            resource_type="ACCOUNT",
            resource_id=str(account.id),
            outcome="REJECTED",
            details={
                "previous_status": current_status.value,
                "requested_status": requested_status.value,
                "reason": reason,
            },
            request_id=request_id,
            ip_address=ip_address,
        )

        raise HTTPException(
            status_code=409,
            detail=reason,
        )

    # An account cannot be closed with a non-zero balance.
    if (
        requested_status == AccountStatus.CLOSED
        and account.balance_paise != 0
    ):
        reason = "An account with a non-zero balance cannot be closed."

        record_audit_event(
            actor_id=actor_id,
            action=action,
            resource_type="ACCOUNT",
            resource_id=str(account.id),
            outcome="REJECTED",
            details={
                "previous_status": current_status.value,
                "requested_status": requested_status.value,
                "reason": reason,
                "balance_paise": account.balance_paise,
            },
            request_id=request_id,
            ip_address=ip_address,
        )

        raise HTTPException(
            status_code=409,
            detail=reason,
        )

    # Update account and successful audit record atomically.
    account.status = requested_status

    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            resource_type="ACCOUNT",
            resource_id=str(account.id),
            outcome="SUCCESS",
            request_id=request_id,
            ip_address=ip_address,
            details={
                "previous_status": current_status.value,
                "new_status": requested_status.value,
            },
        )
    )

    db.commit()
    db.refresh(account)

    return account
