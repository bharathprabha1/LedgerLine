
import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.transaction import (
    DepositRequest,
    TransactionResponse,
    TransferRequest,
    WithdrawalRequest,
)
from app.schemas.statement import (
    TransactionDetailResponse,
    TransactionHistoryResponse,
)
from app.services.transaction_service import (
    deposit_funds,
    transfer_funds,
    withdraw_funds,
)
from app.services.statement_service import (
    get_transaction_detail,
    get_transaction_history,
)


router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"],
)


def _get_transaction_response(result, operation: str):
    if result.status_code != status.HTTP_201_CREATED:
        raise HTTPException(
            status_code=result.status_code,
            detail=result.detail or f"{operation} was rejected.",
        )

    if result.transaction is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{operation} completed without a transaction record.",
        )

    return result.transaction


# ---------------------------------------------------------
# DEPOSIT
# ---------------------------------------------------------

@router.post(
    "/deposit",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_deposit(
    payload: DepositRequest,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=255,
        ),
    ],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = deposit_funds(
        db,
        current_user=current_user,
        account_id=payload.account_id,
        amount_paise=payload.amount_paise,
        description=payload.description,
        idempotency_key=idempotency_key,
    )

    return _get_transaction_response(result, "Deposit")


# ---------------------------------------------------------
# WITHDRAWAL
# ---------------------------------------------------------

@router.post(
    "/withdrawal",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_withdrawal(
    payload: WithdrawalRequest,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=255,
        ),
    ],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = withdraw_funds(
        db,
        current_user=current_user,
        account_id=payload.account_id,
        amount_paise=payload.amount_paise,
        description=payload.description,
        idempotency_key=idempotency_key,
    )

    return _get_transaction_response(result, "Withdrawal")


# ---------------------------------------------------------
# TRANSFER
# ---------------------------------------------------------

@router.post(
    "/transfer",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transfer(
    payload: TransferRequest,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=255,
        ),
    ],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = transfer_funds(
        db,
        current_user=current_user,
        source_account_id=payload.source_account_id,
        destination_account_id=payload.destination_account_id,
        amount_paise=payload.amount_paise,
        description=payload.description,
        idempotency_key=idempotency_key,
    )

    return _get_transaction_response(result, "Transfer")


# ---------------------------------------------------------
# TRANSACTION HISTORY
# ---------------------------------------------------------

@router.get(
    "",
    response_model=TransactionHistoryResponse,
)
def read_transaction_history(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_transaction_history(
        db,
        current_user=current_user,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------
# TRANSACTION DETAILS
# ---------------------------------------------------------

@router.get(
    "/{transaction_id}",
    response_model=TransactionDetailResponse,
)
def read_transaction_detail(
    transaction_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_transaction_detail(
        db,
        transaction_id=transaction_id,
        current_user=current_user,
    )
