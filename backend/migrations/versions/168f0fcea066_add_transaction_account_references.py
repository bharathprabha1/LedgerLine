
"""add transaction account references

Revision ID: 168f0fcea066
Revises: 530904edf36a
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "168f0fcea066"
down_revision: Union[str, Sequence[str], None] = "530904edf36a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("source_account_id", sa.UUID(), nullable=True),
    )

    op.add_column(
        "transactions",
        sa.Column("destination_account_id", sa.UUID(), nullable=True),
    )

    op.create_index(
        "ix_transactions_source_account_id",
        "transactions",
        ["source_account_id"],
        unique=False,
    )

    op.create_index(
        "ix_transactions_destination_account_id",
        "transactions",
        ["destination_account_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_transactions_source_account_id_accounts",
        "transactions",
        "accounts",
        ["source_account_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_foreign_key(
        "fk_transactions_destination_account_id_accounts",
        "transactions",
        "accounts",
        ["destination_account_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_transactions_destination_account_id_accounts",
        "transactions",
        type_="foreignkey",
    )

    op.drop_constraint(
        "fk_transactions_source_account_id_accounts",
        "transactions",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_transactions_destination_account_id",
        table_name="transactions",
    )

    op.drop_index(
        "ix_transactions_source_account_id",
        table_name="transactions",
    )

    op.drop_column("transactions", "destination_account_id")
    op.drop_column("transactions", "source_account_id")
