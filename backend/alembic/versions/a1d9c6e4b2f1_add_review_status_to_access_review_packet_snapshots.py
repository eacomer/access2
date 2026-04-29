"""add review status to access review packet snapshots

Revision ID: a1d9c6e4b2f1
Revises: f0b3a7c91d44
Create Date: 2026-04-24

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a1d9c6e4b2f1"
down_revision: Union[str, Sequence[str], None] = "f0b3a7c91d44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


review_status_enum = postgresql.ENUM(
    "pending_review",
    "approved",
    "rejected",
    name="accessreviewpacketsnapshotreviewstatus",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    review_status_enum.create(bind, checkfirst=True)

    op.add_column(
        "access_review_packet_snapshots",
        sa.Column(
            "review_status",
            review_status_enum,
            nullable=False,
            server_default="pending_review",
        ),
    )
    op.add_column(
        "access_review_packet_snapshots",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "access_review_packet_snapshots",
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "access_review_packet_snapshots",
        sa.Column("review_note", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "access_review_packet_snapshots_reviewed_by_user_id_fkey",
        "access_review_packet_snapshots",
        "users",
        ["reviewed_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_access_review_packet_snapshots_reviewed_by_user_id"),
        "access_review_packet_snapshots",
        ["reviewed_by_user_id"],
    )

    op.alter_column(
        "access_review_packet_snapshots",
        "review_status",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_access_review_packet_snapshots_reviewed_by_user_id"),
        table_name="access_review_packet_snapshots",
    )
    op.drop_constraint(
        "access_review_packet_snapshots_reviewed_by_user_id_fkey",
        "access_review_packet_snapshots",
        type_="foreignkey",
    )
    op.drop_column("access_review_packet_snapshots", "review_note")
    op.drop_column("access_review_packet_snapshots", "reviewed_by_user_id")
    op.drop_column("access_review_packet_snapshots", "reviewed_at")
    op.drop_column("access_review_packet_snapshots", "review_status")

    bind = op.get_bind()
    review_status_enum.drop(bind, checkfirst=True)
