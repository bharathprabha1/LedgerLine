
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.models.recipient_lookup_limit import RecipientLookupLimit
from app.services.recipient_lookup_service import (
    MAX_LOOKUPS,
    WINDOW_SECONDS,
    enforce_recipient_lookup_limit,
)


def test_first_ten_lookup_attempts_are_allowed(db, transfer_accounts):
    user = transfer_accounts["source_owner"]

    for _ in range(MAX_LOOKUPS):
        enforce_recipient_lookup_limit(db, user.id)

    record = db.get(RecipientLookupLimit, user.id)

    assert record is not None
    assert record.request_count == MAX_LOOKUPS


def test_eleventh_lookup_attempt_is_rejected(db, transfer_accounts):
    user = transfer_accounts["source_owner"]

    for _ in range(MAX_LOOKUPS):
        enforce_recipient_lookup_limit(db, user.id)

    with pytest.raises(HTTPException) as exc_info:
        enforce_recipient_lookup_limit(db, user.id)

    assert exc_info.value.status_code == 429

    retry_after = int(exc_info.value.headers["Retry-After"])
    assert 1 <= retry_after <= WINDOW_SECONDS

    record = db.get(RecipientLookupLimit, user.id)
    assert record.request_count == MAX_LOOKUPS + 1


def test_different_users_have_independent_limits(db, transfer_accounts):
    first_user = transfer_accounts["source_owner"]
    second_user = transfer_accounts["destination_owner"]

    for _ in range(MAX_LOOKUPS):
        enforce_recipient_lookup_limit(db, first_user.id)

    # The second user must still be allowed their first lookup.
    enforce_recipient_lookup_limit(db, second_user.id)

    first_record = db.get(RecipientLookupLimit, first_user.id)
    second_record = db.get(RecipientLookupLimit, second_user.id)

    assert first_record.request_count == MAX_LOOKUPS
    assert second_record.request_count == 1


def test_lookup_limit_resets_after_window_expires(db, transfer_accounts):
    user = transfer_accounts["source_owner"]

    for _ in range(MAX_LOOKUPS):
        enforce_recipient_lookup_limit(db, user.id)

    record = db.get(RecipientLookupLimit, user.id)

    record.window_started_at = (
        datetime.now(timezone.utc)
        - timedelta(seconds=WINDOW_SECONDS + 1)
    )
    db.commit()

    enforce_recipient_lookup_limit(db, user.id)

    db.refresh(record)

    assert record.request_count == 1
