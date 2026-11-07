
import getpass
import sys

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal
from app.models.user import User
from app.models.enums import UserRole
from app.core.security import hash_password


def main():
    print("\n========== LedgerLine Admin Setup ==========\n")

    email = input("Admin email: ").strip().lower()
    full_name = input("Admin full name: ").strip()

    if not email or not full_name:
        print("Error: Name and email are required.")
        sys.exit(1)

    password = getpass.getpass("Admin password (minimum 12 characters): ")
    confirm_password = getpass.getpass("Confirm password: ")

    if len(password) < 12:
        print("Error: Password must contain at least 12 characters.")
        sys.exit(1)

    if password != confirm_password:
        print("Error: Passwords do not match.")
        sys.exit(1)

    db = SessionLocal()

    try:
        # Only allow the initial administrator to be bootstrapped.
        existing_admin = db.scalar(
            select(User.id).where(User.role == UserRole.ADMIN).limit(1)
        )

        if existing_admin:
            print("An administrator already exists.")
            print("No new administrator was created.")
            return

        existing_user = db.scalar(
            select(User.id).where(
                func.lower(User.email) == email
            ).limit(1)
        )

        if existing_user:
            print("Error: This email is already registered.")
            return

        admin = User(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        print("\nAdmin created successfully!")
        print("Name:", admin.full_name)
        print("Email:", admin.email)
        print("Role:", admin.role.value)
        print("Active:", admin.is_active)
        print("User ID:", admin.id)

    except IntegrityError:
        db.rollback()
        print("Error: Email already exists or a database constraint failed.")

    except Exception as error:
        db.rollback()
        print("Admin creation failed:", str(error))

    finally:
        db.close()


if __name__ == "__main__":
    main()
