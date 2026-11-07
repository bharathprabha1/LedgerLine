
from getpass import getpass

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import func, select, text

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.models.user import User


def get_admin_details():
    print("\n========== LEDGERLINE ADMIN BOOTSTRAP ==========\n")

    full_name = input("Administrator full name: ").strip()

    if len(full_name) < 2 or len(full_name) > 120:
        raise SystemExit("Name must contain between 2 and 120 characters.")

    email = input("Administrator email: ").strip().lower()

    try:
        email = validate_email(
            email,
            check_deliverability=False,
        ).normalized.lower()
    except EmailNotValidError:
        raise SystemExit("Please enter a valid email address.")

    password = getpass("Administrator password: ")

    if len(password) < 12 or len(password) > 128:
        raise SystemExit("Password must contain 12 to 128 characters.")

    confirm_password = getpass("Confirm administrator password: ")

    if password != confirm_password:
        raise SystemExit("Passwords do not match.")

    return full_name, email, password


def bootstrap_admin():
    full_name, email, password = get_admin_details()

    with SessionLocal() as db:
        try:
            with db.begin():

                # Serialize simultaneous bootstrap attempts.
                db.execute(
                    text("SELECT pg_advisory_xact_lock(:lock_id)"),
                    {"lock_id": 741202611},
                )

                admin_count = db.scalar(
                    select(func.count(User.id)).where(
                        User.role == UserRole.ADMIN
                    )
                )

                if admin_count > 0:
                    raise RuntimeError(
                        "An administrator already exists. "
                        "Initial bootstrap is not allowed again."
                    )

                existing_user = db.scalar(
                    select(User).where(User.email == email)
                )

                if existing_user:
                    raise RuntimeError(
                        "This email is already registered. "
                        "Choose another email address."
                    )

                admin = User(
                    full_name=full_name,
                    email=email,
                    password_hash=hash_password(password),
                    role=UserRole.ADMIN,
                    is_active=True,
                )

                db.add(admin)
                db.flush()

            print("\nADMIN ACCOUNT CREATED SUCCESSFULLY.")
            print(f"Name: {full_name}")
            print(f"Email: {email}")
            print("Role: ADMIN")
            print("Status: ACTIVE")

        except RuntimeError as error:
            raise SystemExit(f"\nBOOTSTRAP FAILED: {error}")


if __name__ == "__main__":
    bootstrap_admin()
