"""add patient timeline read states

Revision ID: e1f3be20d3c1
Revises: 3e1d2b8328f4
Create Date: 2026-04-05

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "e1f3be20d3c1"
down_revision: Union[str, Sequence[str], None] = "3e1d2b8328f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "patient_timeline_read_states",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("last_read_event_id", sa.String(length=128), nullable=True),
        sa.Column("last_read_occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "patient_id",
            "user_id",
            name="uq_patient_timeline_read_states_scope",
        ),
    )
    op.create_index(
        op.f("ix_patient_timeline_read_states_organization_id"),
        "patient_timeline_read_states",
        ["organization_id"],
    )
    op.create_index(
        op.f("ix_patient_timeline_read_states_patient_id"),
        "patient_timeline_read_states",
        ["patient_id"],
    )
    op.create_index(
        op.f("ix_patient_timeline_read_states_user_id"),
        "patient_timeline_read_states",
        ["user_id"],
    )
    op.create_index(
        "ix_patient_timeline_read_states_patient_user",
        "patient_timeline_read_states",
        ["patient_id", "user_id"],
    )
    op.create_index(
        "ix_patient_timeline_read_states_org_user",
        "patient_timeline_read_states",
        ["organization_id", "user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_patient_timeline_read_states_org_user", table_name="patient_timeline_read_states")
    op.drop_index("ix_patient_timeline_read_states_patient_user", table_name="patient_timeline_read_states")
    op.drop_index(
        op.f("ix_patient_timeline_read_states_user_id"),
        table_name="patient_timeline_read_states",
    )
    op.drop_index(
        op.f("ix_patient_timeline_read_states_patient_id"),
        table_name="patient_timeline_read_states",
    )
    op.drop_index(
        op.f("ix_patient_timeline_read_states_organization_id"),
        table_name="patient_timeline_read_states",
    )
    op.drop_table("patient_timeline_read_states")
