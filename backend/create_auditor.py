
from getpass import getpass

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.models.user import User


def create_auditor():
    print("\n========== LEDGERLINE AUDITOR SETUP ==========\n")

    full_name = input("Auditor full name: ").strip()
    if len(full_name) < 2 or len(full_name) > 120:
        raise SystemExit("Name must contain between 2 and 120 characters.")

    email = input("Auditor email: ").strip().lower()

    try:
        email = validate_email(
            email,
            check_deliverability=False,
        ).normalized.lower()
    except EmailNotValidError:
        raise SystemExit("Invalid email address.")

    password = getpass("Temporary auditor password: ")
    if len(password) < 12 or len(password) > 128:
        raise SystemExit("Password must contain 12 to 128 characters.")

    confirm = getpass("Confirm password: ")
    if password != confirm:
        raise SystemExit("Passwords do not match.")

    with SessionLocal() as db:
        with db.begin():
            existing = db.scalar(
                select(User).where(User.email == email)
            )

            if existing:
                raise SystemExit("This email is already registered.")

            auditor = User(
                full_name=full_name,
                email=email,
                password_hash=hash_password(password),
                role=UserRole.AUDITOR,
                is_active=True,
            )

            db.add(auditor)
            db.flush()

            print("\nAUDITOR ACCOUNT CREATED SUCCESSFULLY.")
            print(f"Name: {full_name}")
            print(f"Email: {email}")
            print("Role: AUDITOR")
            print("Status: ACTIVE")


if __name__ == "__main__":
    create_auditor()
