
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TransactionStatus, TransactionType


MAX_AMOUNT_PAISE = 9_223_372_036_854_775_807


class DepositRequest(BaseModel):
    account_id: uuid.UUID
    amount_paise: int = Field(gt=0, le=MAX_AMOUNT_PAISE)
    description: str | None = Field(default=None, max_length=500)


class WithdrawalRequest(BaseModel):
    account_id: uuid.UUID
    amount_paise: int = Field(gt=0, le=MAX_AMOUNT_PAISE)
    description: str | None = Field(default=None, max_length=500)


class TransferRequest(BaseModel):
    source_account_id: uuid.UUID
    destination_account_id: uuid.UUID
    amount_paise: int = Field(gt=0, le=MAX_AMOUNT_PAISE)
    description: str | None = Field(default=None, max_length=500)


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reference: str
    transaction_type: TransactionType
    status: TransactionStatus
    amount_paise: int
    initiated_by: uuid.UUID
    description: str | None
    created_at: datetime
