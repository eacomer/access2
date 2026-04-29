"""add escalation resolution evidence

Revision ID: 6b8f8f8f0d12
Revises: 0a5f3c9d21b4
Create Date: 2026-04-23

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "6b8f8f8f0d12"
down_revision: Union[str, Sequence[str], None] = "0a5f3c9d21b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


resolution_reason_enum = postgresql.ENUM(
    "clinically_stable",
    "issue_addressed",
    "false_positive",
    "duplicate",
    "other",
    name="escalationresolutionreason",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    resolution_reason_enum.create(bind, checkfirst=True)

    op.add_column(
        "patient_escalations",
        sa.Column("resolution_reason", resolution_reason_enum, nullable=True),
    )
    op.add_column(
        "patient_escalations",
        sa.Column("resolution_outcome_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "patient_escalations",
        sa.Column("resolution_care_update_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "patient_escalations_resolution_outcome_id_fkey",
        "patient_escalations",
        "outcomes",
        ["resolution_outcome_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "patient_escalations_resolution_care_update_id_fkey",
        "patient_escalations",
        "care_updates",
        ["resolution_care_update_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_patient_escalations_resolution_outcome_id"),
        "patient_escalations",
        ["resolution_outcome_id"],
    )
    op.create_index(
        op.f("ix_patient_escalations_resolution_care_update_id"),
        "patient_escalations",
        ["resolution_care_update_id"],
    )

    op.add_column(
        "patient_escalation_status_events",
        sa.Column("resolution_reason", resolution_reason_enum, nullable=True),
    )
    op.add_column(
        "patient_escalation_status_events",
        sa.Column("resolution_outcome_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "patient_escalation_status_events",
        sa.Column("resolution_care_update_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "patient_escalation_status_events_resolution_outcome_id_fkey",
        "patient_escalation_status_events",
        "outcomes",
        ["resolution_outcome_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "patient_escalation_status_events_resolution_care_update_id_fkey",
        "patient_escalation_status_events",
        "care_updates",
        ["resolution_care_update_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_patient_escalation_status_events_resolution_outcome_id"),
        "patient_escalation_status_events",
        ["resolution_outcome_id"],
    )
    op.create_index(
        op.f("ix_patient_escalation_status_events_resolution_care_update_id"),
        "patient_escalation_status_events",
        ["resolution_care_update_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_patient_escalation_status_events_resolution_care_update_id"),
        table_name="patient_escalation_status_events",
    )
    op.drop_index(
        op.f("ix_patient_escalation_status_events_resolution_outcome_id"),
        table_name="patient_escalation_status_events",
    )
    op.drop_constraint(
        "patient_escalation_status_events_resolution_care_update_id_fkey",
        "patient_escalation_status_events",
        type_="foreignkey",
    )
    op.drop_constraint(
        "patient_escalation_status_events_resolution_outcome_id_fkey",
        "patient_escalation_status_events",
        type_="foreignkey",
    )
    op.drop_column("patient_escalation_status_events", "resolution_care_update_id")
    op.drop_column("patient_escalation_status_events", "resolution_outcome_id")
    op.drop_column("patient_escalation_status_events", "resolution_reason")

    op.drop_index(
        op.f("ix_patient_escalations_resolution_care_update_id"),
        table_name="patient_escalations",
    )
    op.drop_index(
        op.f("ix_patient_escalations_resolution_outcome_id"),
        table_name="patient_escalations",
    )
    op.drop_constraint(
        "patient_escalations_resolution_care_update_id_fkey",
        "patient_escalations",
        type_="foreignkey",
    )
    op.drop_constraint(
        "patient_escalations_resolution_outcome_id_fkey",
        "patient_escalations",
        type_="foreignkey",
    )
    op.drop_column("patient_escalations", "resolution_care_update_id")
    op.drop_column("patient_escalations", "resolution_outcome_id")
    op.drop_column("patient_escalations", "resolution_reason")

    bind = op.get_bind()
    resolution_reason_enum.drop(bind, checkfirst=True)
