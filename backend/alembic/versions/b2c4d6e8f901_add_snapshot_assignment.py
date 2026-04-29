"""add snapshot assignment

Revision ID: b2c4d6e8f901
Revises: a1d9c6e4b2f1
Create Date: 2026-04-24 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "b2c4d6e8f901"
down_revision = "a1d9c6e4b2f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "access_review_packet_snapshots",
        sa.Column("assigned_reviewer_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f("ix_access_review_packet_snapshots_assigned_reviewer_user_id"),
        "access_review_packet_snapshots",
        ["assigned_reviewer_user_id"],
        unique=False,
    )
    op.create_foreign_key(
        "access_review_packet_snapshots_assigned_reviewer_user_id_fkey",
        "access_review_packet_snapshots",
        "users",
        ["assigned_reviewer_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "access_review_packet_snapshots_assigned_reviewer_user_id_fkey",
        "access_review_packet_snapshots",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_access_review_packet_snapshots_assigned_reviewer_user_id"),
        table_name="access_review_packet_snapshots",
    )
    op.drop_column("access_review_packet_snapshots", "assigned_reviewer_user_id")
