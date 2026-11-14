
import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        payload = decode_access_token(credentials.credentials)

        # Validate the subject claim before UUID conversion.
        subject = payload.get("sub")

        if not isinstance(subject, str) or not subject:
            raise unauthorized

        user_id = uuid.UUID(subject)

        # Validate the token version claim.
        token_version = payload["token_version"]

        if type(token_version) is not int or token_version < 0:
            raise unauthorized

    except (
        jwt.InvalidTokenError,
        ValueError,
        KeyError,
        TypeError,
    ):
        raise unauthorized

    # Load the user from the database.
    user = db.scalar(
        select(User).where(User.id == user_id)
    )

    # Reject missing users, inactive users, and revoked tokens.
    if (
        user is None
        or not user.is_active
        or user.token_version != token_version
    ):
        raise unauthorized

    return user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )

    return current_user


def require_auditor(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.AUDITOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Auditor access required",
        )

    return current_user


def require_admin_or_auditor(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role not in {
        UserRole.ADMIN,
        UserRole.AUDITOR,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator or auditor access required",
        )

    return current_user
