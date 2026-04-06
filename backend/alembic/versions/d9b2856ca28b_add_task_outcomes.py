"""add intervention task outcomes

Revision ID: d9b2856ca28b
Revises: c9f8900f3f10
Create Date: 2026-04-05

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "d9b2856ca28b"
down_revision: Union[str, Sequence[str], None] = "c9f8900f3f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


outcome_status_enum = postgresql.ENUM(
    "successful",
    "unsuccessful",
    "no_response",
    "deferred",
    name="interventiontaskoutcomestatus",
)


def upgrade() -> None:
    bind = op.get_bind()
    outcome_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "intervention_task_outcomes",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("intervention_task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("escalation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("completed_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("completion_summary", sa.Text(), nullable=False),
        sa.Column("intervention_type", sa.String(length=128), nullable=False),
        sa.Column("outcome_status", outcome_status_enum, nullable=False),
        sa.Column("patient_response", sa.Text(), nullable=True),
        sa.Column(
            "follow_up_required",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("follow_up_notes", sa.Text(), nullable=True),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(["completed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["escalation_id"], ["patient_escalations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["intervention_task_id"], ["intervention_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("intervention_task_id", name="uq_task_outcome_task"),
    )
    op.create_index(
        op.f("ix_intervention_task_outcomes_organization_id"),
        "intervention_task_outcomes",
        ["organization_id"],
    )
    op.create_index(
        op.f("ix_intervention_task_outcomes_patient_id"),
        "intervention_task_outcomes",
        ["patient_id"],
    )
    op.create_index(
        op.f("ix_intervention_task_outcomes_escalation_id"),
        "intervention_task_outcomes",
        ["escalation_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_intervention_task_outcomes_escalation_id"),
        table_name="intervention_task_outcomes",
    )
    op.drop_index(
        op.f("ix_intervention_task_outcomes_patient_id"),
        table_name="intervention_task_outcomes",
    )
    op.drop_index(
        op.f("ix_intervention_task_outcomes_organization_id"),
        table_name="intervention_task_outcomes",
    )
    op.drop_table("intervention_task_outcomes")

    bind = op.get_bind()
    outcome_status_enum.drop(bind, checkfirst=True)
