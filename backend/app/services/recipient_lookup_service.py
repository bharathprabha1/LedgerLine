
import uuid
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import Interval, Integer, case, func, literal
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.recipient_lookup_limit import RecipientLookupLimit


MAX_LOOKUPS = 10
WINDOW_SECONDS = 60


def enforce_recipient_lookup_limit(
    db: Session,
    user_id: uuid.UUID,
) -> None:
    """
    Allow 10 recipient lookup attempts per user per 60 seconds.

    Uses an atomic PostgreSQL upsert so simultaneous requests
    cannot bypass the limit across application workers.

    Retry-After is calculated using the database clock and
    reports the remaining time in the current rate-limit window.
    """

    window_duration = literal(
        timedelta(seconds=WINDOW_SECONDS),
        type_=Interval(),
    )

    window_expired = (
        RecipientLookupLimit.window_started_at
        <= func.now() - window_duration
    )

    statement = insert(RecipientLookupLimit).values(
        user_id=user_id,
        window_started_at=func.now(),
        request_count=1,
    )

    statement = statement.on_conflict_do_update(
        index_elements=[
            RecipientLookupLimit.user_id,
        ],
        set_={
            "window_started_at": case(
                (window_expired, func.now()),
                else_=RecipientLookupLimit.window_started_at,
            ),
            "request_count": case(
                (window_expired, 1),
                else_=RecipientLookupLimit.request_count + 1,
            ),
        },
    )

    remaining_seconds = (
        func.greatest(
            1,
            func.ceil(
                func.extract(
                    "epoch",
                    RecipientLookupLimit.window_started_at
                    + window_duration
                    - func.now(),
                )
            ),
        )
        .cast(Integer)
        .label("retry_after_seconds")
    )

    statement = statement.returning(
        RecipientLookupLimit.request_count,
        remaining_seconds,
    )

    try:
        result = db.execute(statement).one()
        request_count = result[0]
        retry_after_seconds = result[1]

        db.commit()

    except Exception:
        db.rollback()
        raise

    if request_count > MAX_LOOKUPS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Too many recipient lookup attempts. "
                "Please try again after the indicated time."
            ),
            headers={
                "Retry-After": str(retry_after_seconds),
            },
        )
