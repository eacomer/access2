"""add patients and enrollments tables

Revision ID: 9f5fddcb3f50
Revises: 7c15c6561c7e
Create Date: 2026-04-03

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "9f5fddcb3f50"
down_revision: Union[str, Sequence[str], None] = "7c15c6561c7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


consent_status_enum = postgresql.ENUM(
    "unknown",
    "requested",
    "consented",
    "declined",
    "revoked",
    name="consentstatus",
    create_type=False,
)

enrollment_status_enum = postgresql.ENUM(
    "pending",
    "active",
    "completed",
    "disenrolled",
    "inactive",
    name="enrollmentstatus",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    consent_status_enum.create(bind, checkfirst=True)
    enrollment_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "patients",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("first_name", sa.String(length=255), nullable=False),
        sa.Column("last_name", sa.String(length=255), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("sex", sa.String(length=32), nullable=True),
        sa.Column("external_patient_id", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "external_patient_id",
            name="uq_patients_org_external_id",
        ),
    )
    op.create_index(
        op.f("ix_patients_organization_id"),
        "patients",
        ["organization_id"],
    )

    op.create_table(
        "patient_enrollments",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("track_code", sa.String(length=64), nullable=False),
        sa.Column(
            "enrollment_status",
            enrollment_status_enum,
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "consent_status",
            consent_status_enum,
            server_default="unknown",
            nullable=False,
        ),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enrollment_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enrollment_ended_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "patient_id",
            "track_code",
            name="uq_patient_enrollment_track",
        ),
    )
    op.create_index(
        op.f("ix_patient_enrollments_organization_id"),
        "patient_enrollments",
        ["organization_id"],
    )
    op.create_index(
        op.f("ix_patient_enrollments_patient_id"),
        "patient_enrollments",
        ["patient_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_patient_enrollments_patient_id"), table_name="patient_enrollments")
    op.drop_index(op.f("ix_patient_enrollments_organization_id"), table_name="patient_enrollments")
    op.drop_table("patient_enrollments")
    op.drop_index(op.f("ix_patients_organization_id"), table_name="patients")
    op.drop_table("patients")

    bind = op.get_bind()
    enrollment_status_enum.drop(bind, checkfirst=True)
    consent_status_enum.drop(bind, checkfirst=True)
