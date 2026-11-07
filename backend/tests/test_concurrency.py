
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import delete, select
from sqlalchemy.orm import sessionmaker

from app.models.account import Account
from app.models.audit_log import AuditLog
from app.models.enums import AccountStatus, TransactionStatus, UserRole
from app.models.idempotency import IdempotencyRecord
from app.models.ledger_entry import LedgerEntry
from app.models.transaction import LedgerTransaction
from app.models.user import User
from app.services.transaction_service import transfer_funds


def test_concurrent_transfers_cannot_overdraw(test_engine):
    suffix = uuid.uuid4().hex[:12]

    SessionFactory = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    source_owner_id = uuid.uuid4()
    destination_owner_id = uuid.uuid4()
    source_account_id = uuid.uuid4()
    destination_account_id = uuid.uuid4()

    # Create committed records visible to both worker sessions.
    with SessionFactory() as setup_db:
        source_owner = User(
            id=source_owner_id,
            full_name="Concurrent Source",
            email=f"concurrent-source-{suffix}@example.test",
            password_hash="test-only-password",
            role=UserRole.ACCOUNT_HOLDER,
            is_active=True,
        )

        destination_owner = User(
            id=destination_owner_id,
            full_name="Concurrent Destination",
            email=f"concurrent-destination-{suffix}@example.test",
            password_hash="test-only-password",
            role=UserRole.ACCOUNT_HOLDER,
            is_active=True,
        )

        source = Account(
            id=source_account_id,
            account_number=f"LLCS{suffix}",
            owner_id=source_owner_id,
            balance_paise=50_000,
            currency="INR",
            status=AccountStatus.ACTIVE,
            is_system=False,
        )

        destination = Account(
            id=destination_account_id,
            account_number=f"LLCD{suffix}",
            owner_id=destination_owner_id,
            balance_paise=0,
            currency="INR",
            status=AccountStatus.ACTIVE,
            is_system=False,
        )

        # Insert users first to satisfy account foreign keys.
        setup_db.add_all([
            source_owner,
            destination_owner,
        ])
        setup_db.flush()

        # Now insert accounts referencing the existing users.
        setup_db.add_all([
            source,
            destination,
        ])
        setup_db.commit()

    barrier = threading.Barrier(2)

    def perform_transfer(key):
        with SessionFactory() as worker_db:
            user = worker_db.get(User, source_owner_id)

            barrier.wait(timeout=10)

            return transfer_funds(
                worker_db,
                current_user=user,
                source_account_id=source_account_id,
                destination_account_id=destination_account_id,
                amount_paise=40_000,
                description="Concurrent transfer test",
                idempotency_key=key,
            )

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_a = executor.submit(
                perform_transfer,
                f"concurrent-a-{suffix}",
            )
            future_b = executor.submit(
                perform_transfer,
                f"concurrent-b-{suffix}",
            )

            result_a = future_a.result(timeout=30)
            result_b = future_b.result(timeout=30)

        results = [result_a, result_b]

        successful = [
            result for result in results
            if result.status_code == 201
        ]

        rejected = [
            result for result in results
            if result.status_code == 409
        ]

        assert len(successful) == 1
        assert len(rejected) == 1

        assert rejected[0].detail == "Insufficient funds."

        with SessionFactory() as verify_db:
            source = verify_db.get(Account, source_account_id)
            destination = verify_db.get(
                Account,
                destination_account_id,
            )

            assert source.balance_paise == 10_000
            assert destination.balance_paise == 40_000
            assert source.balance_paise >= 0

            transactions = verify_db.scalars(
                select(LedgerTransaction).where(
                    LedgerTransaction.source_account_id
                    == source_account_id
                )
            ).all()

            posted = [
                transaction for transaction in transactions
                if transaction.status == TransactionStatus.POSTED
            ]

            rejected_transactions = [
                transaction for transaction in transactions
                if transaction.status == TransactionStatus.REJECTED
            ]

            assert len(posted) == 1
            assert len(rejected_transactions) == 1

            entries = verify_db.scalars(
                select(LedgerEntry).where(
                    LedgerEntry.transaction_id == posted[0].id
                )
            ).all()

            assert len(entries) == 2

    finally:
        # Remove only records created by this test.
        with SessionFactory() as cleanup_db:
            transaction_ids = select(
                LedgerTransaction.id
            ).where(
                LedgerTransaction.initiated_by == source_owner_id
            )

            cleanup_db.execute(
                delete(LedgerEntry).where(
                    LedgerEntry.transaction_id.in_(transaction_ids)
                )
            )

            cleanup_db.execute(
                delete(IdempotencyRecord).where(
                    IdempotencyRecord.user_id == source_owner_id
                )
            )

            cleanup_db.execute(
                delete(AuditLog).where(
                    AuditLog.actor_id == source_owner_id
                )
            )

            cleanup_db.execute(
                delete(LedgerTransaction).where(
                    LedgerTransaction.initiated_by == source_owner_id
                )
            )

            cleanup_db.execute(
                delete(Account).where(
                    Account.id.in_([
                        source_account_id,
                        destination_account_id,
                    ])
                )
            )

            cleanup_db.execute(
                delete(User).where(
                    User.id.in_([
                        source_owner_id,
                        destination_owner_id,
                    ])
                )
            )

            cleanup_db.commit()
