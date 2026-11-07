
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AccountStatus


class AccountCreate(BaseModel):
    owner_id: uuid.UUID


class AccountStatusUpdate(BaseModel):
    status: AccountStatus


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_number: str
    owner_id: uuid.UUID
    balance_paise: int
    currency: str
    status: AccountStatus
    created_at: datetime
