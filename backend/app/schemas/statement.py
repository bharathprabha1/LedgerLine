import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import TransactionStatus, TransactionType


class TransactionHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reference: str
    transaction_type: TransactionType
    status: TransactionStatus
    amount_paise: int
    source_account_id: uuid.UUID | None
    destination_account_id: uuid.UUID | None
    initiated_by: uuid.UUID
    description: str | None
    created_at: datetime


class TransactionHistoryResponse(BaseModel):
    items: list[TransactionHistoryItem]
    total: int
    limit: int
    offset: int


class TransactionDetailResponse(TransactionHistoryItem):
    pass


class StatementItem(BaseModel):
    transaction_id: uuid.UUID
    reference: str
    transaction_type: TransactionType
    status: TransactionStatus
    description: str | None
    created_at: datetime

    debit_paise: int
    credit_paise: int

    attempted_debit_paise: int
    attempted_credit_paise: int

    running_balance_paise: int


class AccountStatementResponse(BaseModel):
    account_id: uuid.UUID
    account_number: str
    currency: str
    opening_balance_paise: int
    closing_balance_paise: int
    items: list[StatementItem]