"""add patient signals and escalations tables

Revision ID: c8a2f8c20bde
Revises: 9f5fddcb3f50
Create Date: 2026-04-04

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c8a2f8c20bde"
down_revision: Union[str, Sequence[str], None] = "9f5fddcb3f50"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


signal_type_enum = postgresql.ENUM(
    "symptom_score",
    "blood_pressure_systolic",
    "blood_pressure_diastolic",
    "weight_change",
    "missed_check_in",
    name="signaltype",
    create_type=False,
)

escalation_status_enum = postgresql.ENUM(
    "open",
    "acknowledged",
    "resolved",
    name="escalationstatus",
    create_type=False,
)

escalation_severity_enum = postgresql.ENUM(
    "low",
    "medium",
    "high",
    name="escalationseverity",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    signal_type_enum.create(bind, checkfirst=True)
    escalation_status_enum.create(bind, checkfirst=True)
    escalation_severity_enum.create(bind, checkfirst=True)

    op.create_table(
        "patient_signals",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enrollment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signal_type", signal_type_enum, nullable=False),
        sa.Column("signal_source", sa.String(length=64), nullable=True),
        sa.Column("signal_value_numeric", sa.Float(), nullable=True),
        sa.Column("signal_value_text", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["enrollment_id"], ["patient_enrollments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_patient_signals_organization_id"),
        "patient_signals",
        ["organization_id"],
    )
    op.create_index(
        op.f("ix_patient_signals_patient_id"),
        "patient_signals",
        ["patient_id"],
    )
    op.create_index(
        op.f("ix_patient_signals_enrollment_id"),
        "patient_signals",
        ["enrollment_id"],
    )

    op.create_table(
        "patient_escalations",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enrollment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("escalation_type", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            escalation_status_enum,
            server_default="open",
            nullable=False,
        ),
        sa.Column("severity", escalation_severity_enum, nullable=False),
        sa.Column(
            "triggered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["enrollment_id"], ["patient_enrollments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["signal_id"], ["patient_signals.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("signal_id", name="uq_patient_escalations_signal"),
    )
    op.create_index(
        op.f("ix_patient_escalations_organization_id"),
        "patient_escalations",
        ["organization_id"],
    )
    op.create_index(
        op.f("ix_patient_escalations_patient_id"),
        "patient_escalations",
        ["patient_id"],
    )
    op.create_index(
        op.f("ix_patient_escalations_enrollment_id"),
        "patient_escalations",
        ["enrollment_id"],
    )
    op.create_index(
        op.f("ix_patient_escalations_signal_id"),
        "patient_escalations",
        ["signal_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_patient_escalations_signal_id"), table_name="patient_escalations")
    op.drop_index(op.f("ix_patient_escalations_enrollment_id"), table_name="patient_escalations")
    op.drop_index(op.f("ix_patient_escalations_patient_id"), table_name="patient_escalations")
    op.drop_index(op.f("ix_patient_escalations_organization_id"), table_name="patient_escalations")
    op.drop_table("patient_escalations")

    op.drop_index(op.f("ix_patient_signals_enrollment_id"), table_name="patient_signals")
    op.drop_index(op.f("ix_patient_signals_patient_id"), table_name="patient_signals")
    op.drop_index(op.f("ix_patient_signals_organization_id"), table_name="patient_signals")
    op.drop_table("patient_signals")

    bind = op.get_bind()
    escalation_severity_enum.drop(bind, checkfirst=True)
    escalation_status_enum.drop(bind, checkfirst=True)
    signal_type_enum.drop(bind, checkfirst=True)

