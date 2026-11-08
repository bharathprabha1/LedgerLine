
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.account import Account
from app.models.enums import AccountStatus, UserRole
from app.models.user import User
from app.schemas.account import (
    AccountCreate,
    AccountResponse,
    AccountStatusUpdate,
)
from app.schemas.statement import AccountStatementResponse
from app.services.account_service import (
    change_account_status,
    create_account,
    record_audit_event,
)
from app.services.statement_service import get_account_statement


router = APIRouter(
    prefix="/accounts",
    tags=["Accounts"],
)


# ---------------------------------------------------------
# RESPONSE MODELS
# ---------------------------------------------------------

class AccountHolderOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str


class TransferRecipientResponse(BaseModel):
    id: uuid.UUID
    account_number: str
    holder_name: str
    currency: str


# ---------------------------------------------------------
# CREATE ACCOUNT - ADMIN ONLY
# ---------------------------------------------------------

@router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_account(
    payload: AccountCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    owner = db.scalar(
        select(User).where(
            User.id == payload.owner_id,
            User.is_active.is_(True),
        )
    )

    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active account holder not found.",
        )

    if owner.role != UserRole.ACCOUNT_HOLDER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Accounts can only be created for account holders.",
        )

    return create_account(db, owner.id)


# ---------------------------------------------------------
# LIST ACCOUNTS
# ---------------------------------------------------------

@router.get(
    "",
    response_model=list[AccountResponse],
)
def list_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Account).order_by(
        Account.created_at.desc()
    )

    # Customers can only see their own non-system accounts.
    if current_user.role == UserRole.ACCOUNT_HOLDER:
        query = query.where(
            Account.owner_id == current_user.id,
            Account.is_system.is_(False),
        )

    return db.scalars(query).all()


# ---------------------------------------------------------
# LIST ELIGIBLE ACCOUNT HOLDERS - ADMIN ONLY
# ---------------------------------------------------------

@router.get(
    "/eligible-holders",
    response_model=list[AccountHolderOption],
)
def list_eligible_account_holders(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Return active account holders for the admin account
    creation dropdown.

    Only administrators can access this endpoint.
    """

    holders = db.scalars(
        select(User)
        .where(
            User.role == UserRole.ACCOUNT_HOLDER,
            User.is_active.is_(True),
        )
        .order_by(
            User.full_name.asc(),
            User.email.asc(),
        )
    ).all()

    return holders


# ---------------------------------------------------------
# TRANSFER RECIPIENT LOOKUP - ACCOUNT HOLDERS
# ---------------------------------------------------------

@router.get(
    "/recipient-lookup",
    response_model=TransferRecipientResponse,
)
def lookup_transfer_recipient(
    account_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Look up an eligible transfer recipient using an exact
    account number.

    Only authenticated account holders can use this endpoint.
    Recipient balances and private information are not exposed.
    """

    if current_user.role != UserRole.ACCOUNT_HOLDER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Only account holders can look up "
                "transfer recipients."
            ),
        )

    normalized_number = account_number.strip()

    if not normalized_number or len(normalized_number) > 64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid account number.",
        )

    account = db.scalar(
        select(Account).where(
            Account.account_number == normalized_number,
            Account.is_system.is_(False),
            Account.status == AccountStatus.ACTIVE,
        )
    )

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Eligible recipient account not found.",
        )

    owner = db.get(User, account.owner_id)

    if (
        owner is None
        or not owner.is_active
        or owner.role != UserRole.ACCOUNT_HOLDER
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Eligible recipient account not found.",
        )

    if account.owner_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot transfer money to your own account.",
        )

    return TransferRecipientResponse(
        id=account.id,
        account_number=account.account_number,
        holder_name=owner.full_name,
        currency=account.currency,
    )


# ---------------------------------------------------------
# ACCOUNT STATEMENT
# ---------------------------------------------------------

@router.get(
    "/{account_id}/statement",
    response_model=AccountStatementResponse,
)
def read_account_statement(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_account_statement(
        db,
        account_id=account_id,
        current_user=current_user,
    )


# ---------------------------------------------------------
# GET ACCOUNT DETAILS
# ---------------------------------------------------------

@router.get(
    "/{account_id}",
    response_model=AccountResponse,
)
def get_account(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Account).where(
        Account.id == account_id
    )

    # Hide system accounts and other customers' accounts.
    if current_user.role == UserRole.ACCOUNT_HOLDER:
        query = query.where(
            Account.owner_id == current_user.id,
            Account.is_system.is_(False),
        )

    account = db.scalar(query)

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )

    return account


# ---------------------------------------------------------
# UPDATE ACCOUNT STATUS - ADMIN ONLY
# ---------------------------------------------------------

@router.patch(
    "/{account_id}/status",
    response_model=AccountResponse,
)
def update_account_status(
    account_id: uuid.UUID,
    payload: AccountStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    request_id = request.headers.get("X-Request-ID")

    ip_address = (
        request.client.host
        if request.client
        else None
    )

    # Record denied attempts for non-administrators.
    if current_user.role != UserRole.ADMIN:
        record_audit_event(
            actor_id=current_user.id,
            action="ACCOUNT_STATUS_CHANGE",
            resource_type="ACCOUNT",
            resource_id=str(account_id),
            outcome="DENIED",
            details={
                "requested_status": payload.status.value,
                "reason": "Administrator access required",
                "actor_role": current_user.role.value,
            },
            request_id=request_id,
            ip_address=ip_address,
        )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )

    # System account status is protected.
    target_account = db.scalar(
        select(Account).where(
            Account.id == account_id
        )
    )

    if target_account is not None and target_account.is_system:
        record_audit_event(
            actor_id=current_user.id,
            action="ACCOUNT_STATUS_CHANGE",
            resource_type="ACCOUNT",
            resource_id=str(account_id),
            outcome="REJECTED",
            details={
                "requested_status": payload.status.value,
                "reason": "System account status is protected.",
            },
            request_id=request_id,
            ip_address=ip_address,
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "System account status cannot be changed "
                "through this endpoint."
            ),
        )

    return change_account_status(
        db,
        account_id=account_id,
        requested_status=payload.status,
        actor_id=current_user.id,
        request_id=request_id,
        ip_address=ip_address,
    )
