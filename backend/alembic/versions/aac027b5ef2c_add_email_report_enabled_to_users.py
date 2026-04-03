"""add email_report_enabled to users

Revision ID: aac027b5ef2c
Revises: 72d5415bc297
Create Date: 2026-04-03 02:14:53.213599

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "aac027b5ef2c"
down_revision: Union[str, None] = "72d5415bc297"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "email_report_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "email_report_enabled")
