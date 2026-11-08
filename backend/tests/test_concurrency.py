
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import delete, select
from sqlalchemy.orm import sessionmaker

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
from app.services.transaction_service import (
    transfer_funds,
    withdraw_funds,
)


def cleanup_test_records(
    SessionFactory,
    source_owner_id,
    destination_owner_id,
    source_account_id,
    destination_account_id,
    settlement_account_id=None,
):
    """Remove only records created by an individual concurrency test."""

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

        account_ids = [
            source_account_id,
            destination_account_id,
        ]

        if settlement_account_id is not None:
            account_ids.append(settlement_account_id)

        cleanup_db.execute(
            delete(Account).where(
                Account.id.in_(account_ids)
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


def create_concurrency_test_accounts(
    SessionFactory,
    suffix,
    source_owner_id,
    destination_owner_id,
    source_account_id,
    destination_account_id,
):
    """Create isolated, committed accounts for concurrency tests."""

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

        setup_db.add_all([
            source_owner,
            destination_owner,
        ])
        setup_db.flush()

        setup_db.add_all([
            source,
            destination,
        ])

        setup_db.commit()


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

    create_concurrency_test_accounts(
        SessionFactory,
        suffix,
        source_owner_id,
        destination_owner_id,
        source_account_id,
        destination_account_id,
    )

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
        cleanup_test_records(
            SessionFactory,
            source_owner_id,
            destination_owner_id,
            source_account_id,
            destination_account_id,
        )


def test_concurrent_duplicate_transfer_is_processed_once(test_engine):
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

    create_concurrency_test_accounts(
        SessionFactory,
        suffix,
        source_owner_id,
        destination_owner_id,
        source_account_id,
        destination_account_id,
    )

    barrier = threading.Barrier(2)
    shared_key = f"concurrent-duplicate-{suffix}"

    def perform_transfer():
        with SessionFactory() as worker_db:
            user = worker_db.get(User, source_owner_id)

            barrier.wait(timeout=10)

            return transfer_funds(
                worker_db,
                current_user=user,
                source_account_id=source_account_id,
                destination_account_id=destination_account_id,
                amount_paise=10_000,
                description="Concurrent duplicate transfer test",
                idempotency_key=shared_key,
            )

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_a = executor.submit(perform_transfer)
            future_b = executor.submit(perform_transfer)

            result_a = future_a.result(timeout=30)
            result_b = future_b.result(timeout=30)

        # Both identical requests must succeed.
        assert result_a.status_code == 201
        assert result_b.status_code == 201

        # Both requests must return the same transaction.
        assert result_a.transaction is not None
        assert result_b.transaction is not None

        assert result_a.transaction.id == result_b.transaction.id

        with SessionFactory() as verify_db:
            source = verify_db.get(Account, source_account_id)
            destination = verify_db.get(
                Account,
                destination_account_id,
            )

            # Money must move only once.
            assert source.balance_paise == 40_000
            assert destination.balance_paise == 10_000

            transactions = verify_db.scalars(
                select(LedgerTransaction).where(
                    LedgerTransaction.source_account_id
                    == source_account_id
                )
            ).all()

            assert len(transactions) == 1

            transaction = transactions[0]

            assert transaction.id == result_a.transaction.id
            assert transaction.status == TransactionStatus.POSTED

            entries = verify_db.scalars(
                select(LedgerEntry).where(
                    LedgerEntry.transaction_id == transaction.id
                )
            ).all()

            # Exactly one debit and one credit.
            assert len(entries) == 2
            assert sum(
                entry.amount_paise for entry in entries
            ) == 20_000

            idempotency_records = verify_db.scalars(
                select(IdempotencyRecord).where(
                    IdempotencyRecord.user_id == source_owner_id,
                    IdempotencyRecord.idempotency_key == shared_key,
                )
            ).all()

            assert len(idempotency_records) == 1

            success_audits = verify_db.scalars(
                select(AuditLog).where(
                    AuditLog.actor_id == source_owner_id,
                    AuditLog.action == "TRANSFER",
                    AuditLog.outcome == "SUCCESS",
                )
            ).all()

            assert len(success_audits) == 1

    finally:
        cleanup_test_records(
            SessionFactory,
            source_owner_id,
            destination_owner_id,
            source_account_id,
            destination_account_id,
        )


def test_concurrent_withdrawals_cannot_overdraw(test_engine):
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
    settlement_account_id = uuid.uuid4()

    create_concurrency_test_accounts(
        SessionFactory,
        suffix,
        source_owner_id,
        destination_owner_id,
        source_account_id,
        destination_account_id,
    )

    # Create an isolated system settlement account.
    with SessionFactory() as setup_db:
        settlement = Account(
            id=settlement_account_id,
            account_number=f"LLSYS{suffix.upper()}",
            owner_id=source_owner_id,
            balance_paise=100_000,
            currency="INR",
            status=AccountStatus.ACTIVE,
            is_system=True,
        )

        setup_db.add(settlement)
        setup_db.commit()

    barrier = threading.Barrier(2)

    def perform_withdrawal(key):
        with SessionFactory() as worker_db:
            user = worker_db.get(User, source_owner_id)

            barrier.wait(timeout=10)

            return withdraw_funds(
                worker_db,
                current_user=user,
                account_id=source_account_id,
                amount_paise=30_000,
                description="Concurrent withdrawal test",
                idempotency_key=key,
            )

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_a = executor.submit(
                perform_withdrawal,
                f"withdraw-a-{suffix}",
            )

            future_b = executor.submit(
                perform_withdrawal,
                f"withdraw-b-{suffix}",
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
            customer = verify_db.get(
                Account,
                source_account_id,
            )

            settlement = verify_db.get(
                Account,
                settlement_account_id,
            )

            # Only one withdrawal must be applied.
            assert customer.balance_paise == 20_000
            assert settlement.balance_paise == 70_000

            # Neither account may become negative.
            assert customer.balance_paise >= 0
            assert settlement.balance_paise >= 0

            transactions = verify_db.scalars(
                select(LedgerTransaction).where(
                    LedgerTransaction.source_account_id
                    == source_account_id,
                    LedgerTransaction.transaction_type
                    == TransactionType.WITHDRAWAL,
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

            # One debit from customer and one credit to settlement.
            assert len(entries) == 2

            debit = next(
                entry for entry in entries
                if entry.side == EntrySide.DEBIT
            )

            credit = next(
                entry for entry in entries
                if entry.side == EntrySide.CREDIT
            )

            assert debit.account_id == source_account_id
            assert credit.account_id == settlement_account_id

            assert debit.amount_paise == 30_000
            assert credit.amount_paise == 30_000

            assert sum(
                entry.amount_paise for entry in entries
            ) == 60_000

            success_audits = verify_db.scalars(
                select(AuditLog).where(
                    AuditLog.actor_id == source_owner_id,
                    AuditLog.action == "WITHDRAWAL",
                    AuditLog.outcome == "SUCCESS",
                )
            ).all()

            rejected_audits = verify_db.scalars(
                select(AuditLog).where(
                    AuditLog.actor_id == source_owner_id,
                    AuditLog.action == "WITHDRAWAL",
                    AuditLog.outcome == "REJECTED",
                )
            ).all()

            assert len(success_audits) == 1
            assert len(rejected_audits) == 1

    finally:
        cleanup_test_records(
            SessionFactory,
            source_owner_id,
            destination_owner_id,
            source_account_id,
            destination_account_id,
            settlement_account_id,
        )
