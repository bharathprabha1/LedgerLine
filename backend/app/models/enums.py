from enum import Enum


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    ACCOUNT_HOLDER = "ACCOUNT_HOLDER"
    AUDITOR = "AUDITOR"


class AccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    CLOSED = "CLOSED"


class TransactionType(str, Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER = "TRANSFER"


class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    POSTED = "POSTED"
    REJECTED = "REJECTED"


class EntrySide(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"
