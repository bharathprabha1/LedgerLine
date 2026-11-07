
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.account import Account
from app.models.enums import AccountStatus, UserRole
from app.models.user import User


@pytest.fixture(scope="session")
def test_engine():
    # Derive the test URL without modifying the application's .env.
    test_url = make_url(settings.database_url).set(
        database="ledgerline_test_db"
    )

    if test_url.database != "ledgerline_test_db":
        raise RuntimeError("Refusing to run tests outside the test database.")

    engine = create_engine(
        test_url,
        pool_pre_ping=True,
    )

    with engine.connect() as connection:
        database_name = connection.scalar(
            text("SELECT current_database()")
        )

        if database_name != "ledgerline_test_db":
            engine.dispose()
            raise RuntimeError(
                "Test database safety check failed."
            )

        version_exists = connection.scalar(
            text(
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'alembic_version'"
                ")"
            )
        )

        if not version_exists:
            engine.dispose()
            raise RuntimeError(
                "Test database migrations have not been applied."
            )

    yield engine
    engine.dispose()


@pytest.fixture
def db(test_engine):
    connection = test_engine.connect()
    outer_transaction = connection.begin()

    session = Session(
        bind=connection,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        session.close()

        if outer_transaction.is_active:
            outer_transaction.rollback()

        connection.close()


@pytest.fixture
def transfer_accounts(db):
    suffix = uuid.uuid4().hex[:12]

    source_owner = User(
        full_name="Source Test User",
        email=f"source-{suffix}@example.test",
        password_hash="test-only-password-hash",
        role=UserRole.ACCOUNT_HOLDER,
        is_active=True,
    )

    destination_owner = User(
        full_name="Destination Test User",
        email=f"destination-{suffix}@example.test",
        password_hash="test-only-password-hash",
        role=UserRole.ACCOUNT_HOLDER,
        is_active=True,
    )

    db.add_all([source_owner, destination_owner])
    db.flush()

    source = Account(
        account_number=f"LLTEST{suffix}",
        owner_id=source_owner.id,
        balance_paise=50_000,
        currency="INR",
        status=AccountStatus.ACTIVE,
        is_system=False,
    )

    destination = Account(
        account_number=f"LLTEST{uuid.uuid4().hex[:12]}",
        owner_id=destination_owner.id,
        balance_paise=0,
        currency="INR",
        status=AccountStatus.ACTIVE,
        is_system=False,
    )

    db.add_all([source, destination])
    db.flush()

    return {
        "source_owner": source_owner,
        "destination_owner": destination_owner,
        "source": source,
        "destination": destination,
    }
