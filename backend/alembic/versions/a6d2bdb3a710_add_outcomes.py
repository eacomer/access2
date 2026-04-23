"""add outcomes

Revision ID: a6d2bdb3a710
Revises: b7e81e8b3a21
Create Date: 2026-04-23

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a6d2bdb3a710"
down_revision: Union[str, Sequence[str], None] = "b7e81e8b3a21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


outcome_type_enum = postgresql.ENUM(
    "bp",
    "a1c",
    "weight",
    "adherence",
    "checkin_status",
    name="outcometype",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    outcome_type_enum.create(bind, checkfirst=True)

    op.create_table(
        "outcomes",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("intervention_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("type", outcome_type_enum, nullable=False),
        sa.Column("metric_name", sa.String(length=128), nullable=False),
        sa.Column("value_numeric", sa.Float(), nullable=True),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "value_numeric IS NOT NULL OR value_text IS NOT NULL",
            name="ck_outcomes_value_present",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["intervention_task_id"], ["intervention_tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["signal_id"], ["patient_signals.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_outcomes_organization_id"), "outcomes", ["organization_id"])
    op.create_index(op.f("ix_outcomes_patient_id"), "outcomes", ["patient_id"])
    op.create_index(op.f("ix_outcomes_intervention_task_id"), "outcomes", ["intervention_task_id"])
    op.create_index(op.f("ix_outcomes_signal_id"), "outcomes", ["signal_id"])
    op.create_index("ix_outcomes_patient_observed_at", "outcomes", ["patient_id", "observed_at"])


def downgrade() -> None:
    op.drop_index("ix_outcomes_patient_observed_at", table_name="outcomes")
    op.drop_index(op.f("ix_outcomes_signal_id"), table_name="outcomes")
    op.drop_index(op.f("ix_outcomes_intervention_task_id"), table_name="outcomes")
    op.drop_index(op.f("ix_outcomes_patient_id"), table_name="outcomes")
    op.drop_index(op.f("ix_outcomes_organization_id"), table_name="outcomes")
    op.drop_table("outcomes")

    bind = op.get_bind()
    outcome_type_enum.drop(bind, checkfirst=True)
