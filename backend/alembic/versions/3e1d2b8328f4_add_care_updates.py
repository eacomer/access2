"""add care updates

Revision ID: 3e1d2b8328f4
Revises: d9b2856ca28b
Create Date: 2026-04-05

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "3e1d2b8328f4"
down_revision: Union[str, Sequence[str], None] = "d9b2856ca28b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


care_update_type_enum = postgresql.ENUM(
    "outreach",
    "coordination",
    "education",
    "adherence",
    "follow_up",
    "other",
    name="careupdatetype",
)


def upgrade() -> None:
    bind = op.get_bind()
    care_update_type_enum.create(bind, checkfirst=True)

    op.create_table(
        "care_updates",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("escalation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("intervention_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "intervention_task_outcome_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("care_update_type", care_update_type_enum, nullable=False),
        sa.Column("summary", sa.String(length=512), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column(
            "occurred_at",
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
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["escalation_id"], ["patient_escalations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["intervention_task_id"], ["intervention_tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["intervention_task_outcome_id"],
            ["intervention_task_outcomes.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_care_updates_organization_id"),
        "care_updates",
        ["organization_id"],
    )
    op.create_index(
        op.f("ix_care_updates_patient_id"),
        "care_updates",
        ["patient_id"],
    )
    op.create_index(
        op.f("ix_care_updates_escalation_id"),
        "care_updates",
        ["escalation_id"],
    )
    op.create_index(
        op.f("ix_care_updates_intervention_task_id"),
        "care_updates",
        ["intervention_task_id"],
    )
    op.create_index(
        op.f("ix_care_updates_intervention_task_outcome_id"),
        "care_updates",
        ["intervention_task_outcome_id"],
    )
    op.create_index(
        "ix_care_updates_patient_occurred_at",
        "care_updates",
        ["patient_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_care_updates_patient_occurred_at", table_name="care_updates")
    op.drop_index(
        op.f("ix_care_updates_intervention_task_outcome_id"),
        table_name="care_updates",
    )
    op.drop_index(
        op.f("ix_care_updates_intervention_task_id"),
        table_name="care_updates",
    )
    op.drop_index(op.f("ix_care_updates_escalation_id"), table_name="care_updates")
    op.drop_index(op.f("ix_care_updates_patient_id"), table_name="care_updates")
    op.drop_index(op.f("ix_care_updates_organization_id"), table_name="care_updates")
    op.drop_table("care_updates")

    bind = op.get_bind()
    care_update_type_enum.drop(bind, checkfirst=True)
