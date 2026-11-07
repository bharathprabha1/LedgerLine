
import uuid

from sqlalchemy import select, text

from app.db.session import SessionLocal
from app.models.account import Account
from app.models.audit_log import AuditLog
from app.models.enums import AccountStatus, UserRole
from app.models.user import User


SETTLEMENT_ACCOUNT_NUMBER = "LLSYS0000000001"


def initialize_settlement_account():
    with SessionLocal() as db:
        try:
            with db.begin():
                # Prevent simultaneous initialization.
                db.execute(
                    text("SELECT pg_advisory_xact_lock(:lock_id)"),
                    {"lock_id": 741202612},
                )

                existing = db.scalar(
                    select(Account)
                    .where(
                        Account.account_number
                        == SETTLEMENT_ACCOUNT_NUMBER
                    )
                    .with_for_update()
                )

                if existing:
                    if not existing.is_system:
                        raise RuntimeError(
                            "The reserved settlement account number "
                            "is already used by a non-system account."
                        )

                    print("Settlement account already exists.")
                    print(f"Account number: {existing.account_number}")
                    print(f"System account: {existing.is_system}")
                    print(f"Balance: {existing.balance_paise} paise")
                    return

                admin = db.scalar(
                    select(User)
                    .where(
                        User.role == UserRole.ADMIN,
                        User.is_active.is_(True),
                    )
                    .order_by(User.created_at)
                    .limit(1)
                )

                if admin is None:
                    raise RuntimeError(
                        "No active administrator found."
                    )

                account = Account(
                    id=uuid.uuid4(),
                    account_number=SETTLEMENT_ACCOUNT_NUMBER,
                    owner_id=admin.id,
                    balance_paise=0,
                    currency="INR",
                    status=AccountStatus.ACTIVE,
                    is_system=True,
                )

                db.add(account)
                db.flush()

                db.add(
                    AuditLog(
                        actor_id=admin.id,
                        action="SYSTEM_ACCOUNT_CREATED",
                        resource_type="ACCOUNT",
                        resource_id=str(account.id),
                        outcome="SUCCESS",
                        details={
                            "account_number": SETTLEMENT_ACCOUNT_NUMBER,
                            "account_type": "SETTLEMENT",
                            "initial_balance_paise": 0,
                        },
                    )
                )

            print("\nSettlement account created successfully.")
            print(f"Account number: {SETTLEMENT_ACCOUNT_NUMBER}")
            print("System account: True")
            print("Initial balance: ₹0.00")
            print(f"Administrator: {admin.email}")

        except Exception:
            raise


if __name__ == "__main__":
    initialize_settlement_account()
