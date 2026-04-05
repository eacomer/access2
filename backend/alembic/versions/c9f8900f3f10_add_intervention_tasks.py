"""add intervention tasks table

Revision ID: c9f8900f3f10
Revises: c8a2f8c20bde
Create Date: 2026-04-05

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c9f8900f3f10"
down_revision: Union[str, Sequence[str], None] = "c8a2f8c20bde"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


task_status_enum = postgresql.ENUM(
    "open",
    "in_progress",
    "completed",
    "cancelled",
    name="interventiontaskstatus",
    create_type=False,
)

task_priority_enum = postgresql.ENUM(
    "low",
    "medium",
    "high",
    "urgent",
    name="interventiontaskpriority",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    task_status_enum.create(bind, checkfirst=True)
    task_priority_enum.create(bind, checkfirst=True)

    op.create_table(
        "intervention_tasks",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enrollment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("escalation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", task_status_enum, server_default="open", nullable=False),
        sa.Column(
            "priority",
            task_priority_enum,
            server_default="medium",
            nullable=False,
        ),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("completion_note", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["completed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["enrollment_id"], ["patient_enrollments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["escalation_id"], ["patient_escalations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_intervention_tasks_organization_id"),
        "intervention_tasks",
        ["organization_id"],
    )
    op.create_index(
        op.f("ix_intervention_tasks_patient_id"),
        "intervention_tasks",
        ["patient_id"],
    )
    op.create_index(
        op.f("ix_intervention_tasks_enrollment_id"),
        "intervention_tasks",
        ["enrollment_id"],
    )
    op.create_index(
        op.f("ix_intervention_tasks_escalation_id"),
        "intervention_tasks",
        ["escalation_id"],
    )
    op.create_index(
        op.f("ix_intervention_tasks_assigned_user_id"),
        "intervention_tasks",
        ["assigned_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_intervention_tasks_assigned_user_id"),
        table_name="intervention_tasks",
    )
    op.drop_index(
        op.f("ix_intervention_tasks_escalation_id"),
        table_name="intervention_tasks",
    )
    op.drop_index(
        op.f("ix_intervention_tasks_enrollment_id"),
        table_name="intervention_tasks",
    )
    op.drop_index(
        op.f("ix_intervention_tasks_patient_id"),
        table_name="intervention_tasks",
    )
    op.drop_index(
        op.f("ix_intervention_tasks_organization_id"),
        table_name="intervention_tasks",
    )
    op.drop_table("intervention_tasks")

    bind = op.get_bind()
    task_priority_enum.drop(bind, checkfirst=True)
    task_status_enum.drop(bind, checkfirst=True)
