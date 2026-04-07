"""add escalation sla due timestamp

Revision ID: b7e81e8b3a21
Revises: f4fa50a6c98b
Create Date: 2026-04-06
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7e81e8b3a21"
down_revision: Union[str, Sequence[str], None] = "f4fa50a6c98b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "patient_escalations",
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("patient_escalations", "sla_due_at")
