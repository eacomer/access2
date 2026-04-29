"""add access review packet snapshots

Revision ID: f0b3a7c91d44
Revises: 6b8f8f8f0d12
Create Date: 2026-04-24

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f0b3a7c91d44"
down_revision: Union[str, Sequence[str], None] = "6b8f8f8f0d12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "access_review_packet_snapshots",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("review_readiness_status", sa.String(length=64), nullable=False),
        sa.Column("packet_json", sa.JSON(), nullable=False),
        sa.Column("packet_markdown", sa.Text(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_access_review_packet_snapshots_organization_id"),
        "access_review_packet_snapshots",
        ["organization_id"],
    )
    op.create_index(
        op.f("ix_access_review_packet_snapshots_patient_id"),
        "access_review_packet_snapshots",
        ["patient_id"],
    )
    op.create_index(
        "ix_access_review_packet_snapshots_patient_generated_at",
        "access_review_packet_snapshots",
        ["patient_id", "generated_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_access_review_packet_snapshots_patient_generated_at",
        table_name="access_review_packet_snapshots",
    )
    op.drop_index(
        op.f("ix_access_review_packet_snapshots_patient_id"),
        table_name="access_review_packet_snapshots",
    )
    op.drop_index(
        op.f("ix_access_review_packet_snapshots_organization_id"),
        table_name="access_review_packet_snapshots",
    )
    op.drop_table("access_review_packet_snapshots")
