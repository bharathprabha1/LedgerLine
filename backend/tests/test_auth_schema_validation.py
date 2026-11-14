
import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    PasswordChangeRequest,
    UserProfileUpdate,
    UserRegister,
)


def test_registration_rejects_whitespace_only_name():
    with pytest.raises(ValidationError):
        UserRegister(
            full_name="       ",
            email="test@example.com",
            password="SecurePassword123",
        )


def test_registration_rejects_whitespace_only_password():
    with pytest.raises(ValidationError):
        UserRegister(
            full_name="Test User",
            email="test@example.com",
            password="            ",
        )


def test_profile_update_rejects_whitespace_only_name():
    with pytest.raises(ValidationError):
        UserProfileUpdate(
            full_name="       ",
        )


def test_password_change_rejects_whitespace_only_new_password():
    with pytest.raises(ValidationError):
        PasswordChangeRequest(
            current_password="OldSecurePassword123",
            new_password="            ",
        )


def test_registration_accepts_valid_passphrase_with_spaces():
    user = UserRegister(
        full_name="  Test User  ",
        email="test@example.com",
        password="correct horse battery staple",
    )

    assert user.full_name == "Test User"
    assert user.password == "correct horse battery staple"


def test_password_change_accepts_valid_passphrase_with_spaces():
    request = PasswordChangeRequest(
        current_password="OldSecurePassword123",
        new_password="new secure passphrase 2026",
    )

    assert request.new_password == "new secure passphrase 2026"
