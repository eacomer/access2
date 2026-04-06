"""add escalation workflow actions

Revision ID: f4fa50a6c98b
Revises: e1f3be20d3c1
Create Date: 2026-04-06
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "f4fa50a6c98b"
down_revision: Union[str, Sequence[str], None] = "e1f3be20d3c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


new_escalation_status_enum = postgresql.ENUM(
    "open",
    "in_progress",
    "resolved",
    "canceled",
    name="escalationstatus",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    op.execute("ALTER TYPE escalationstatus RENAME TO escalationstatus_old")
    new_escalation_status_enum.create(bind, checkfirst=False)
    op.execute("ALTER TABLE patient_escalations ALTER COLUMN status DROP DEFAULT")
    op.execute(
        """
        ALTER TABLE patient_escalations
        ALTER COLUMN status TYPE escalationstatus
        USING (
            CASE
                WHEN status::text = 'acknowledged' THEN 'in_progress'
                ELSE status::text
            END
        )::escalationstatus
        """
    )
    op.execute("ALTER TABLE patient_escalations ALTER COLUMN status SET DEFAULT 'open'")
    op.execute("DROP TYPE escalationstatus_old")

    op.alter_column(
        "patient_escalations",
        "acknowledged_at",
        new_column_name="in_progress_at",
    )
    op.add_column(
        "patient_escalations",
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "patient_escalations",
        sa.Column("cancellation_notes", sa.Text(), nullable=True),
    )

    op.create_table(
        "patient_escalation_status_events",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("escalation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", new_escalation_status_enum, nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["escalation_id"], ["patient_escalations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_patient_escalation_status_events_organization_id"),
        "patient_escalation_status_events",
        ["organization_id"],
    )
    op.create_index(
        op.f("ix_patient_escalation_status_events_patient_id"),
        "patient_escalation_status_events",
        ["patient_id"],
    )
    op.create_index(
        op.f("ix_patient_escalation_status_events_escalation_id"),
        "patient_escalation_status_events",
        ["escalation_id"],
    )
    op.create_index(
        op.f("ix_patient_escalation_status_events_actor_user_id"),
        "patient_escalation_status_events",
        ["actor_user_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index(
        op.f("ix_patient_escalation_status_events_actor_user_id"),
        table_name="patient_escalation_status_events",
    )
    op.drop_index(
        op.f("ix_patient_escalation_status_events_escalation_id"),
        table_name="patient_escalation_status_events",
    )
    op.drop_index(
        op.f("ix_patient_escalation_status_events_patient_id"),
        table_name="patient_escalation_status_events",
    )
    op.drop_index(
        op.f("ix_patient_escalation_status_events_organization_id"),
        table_name="patient_escalation_status_events",
    )
    op.drop_table("patient_escalation_status_events")

    op.drop_column("patient_escalations", "cancellation_notes")
    op.drop_column("patient_escalations", "canceled_at")
    op.alter_column(
        "patient_escalations",
        "in_progress_at",
        new_column_name="acknowledged_at",
    )

    op.execute("ALTER TYPE escalationstatus RENAME TO escalationstatus_new")
    old_escalation_status_enum = postgresql.ENUM(
        "open",
        "acknowledged",
        "resolved",
        name="escalationstatus",
    )
    old_escalation_status_enum.create(bind, checkfirst=False)
    op.execute("ALTER TABLE patient_escalations ALTER COLUMN status DROP DEFAULT")
    op.execute(
        """
        ALTER TABLE patient_escalations
        ALTER COLUMN status TYPE escalationstatus
        USING (
            CASE
                WHEN status::text = 'in_progress' THEN 'acknowledged'
                WHEN status::text = 'canceled' THEN 'resolved'
                ELSE status::text
            END
        )::escalationstatus
        """
    )
    op.execute("ALTER TABLE patient_escalations ALTER COLUMN status SET DEFAULT 'open'")
    op.execute("DROP TYPE escalationstatus_new")
