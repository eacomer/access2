"""add access review snapshot events

Revision ID: d4a1b7c3e9f2
Revises: b2c4d6e8f901
Create Date: 2026-04-25 09:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "d4a1b7c3e9f2"
down_revision = "b2c4d6e8f901"
branch_labels = None
depends_on = None


event_type_enum = postgresql.ENUM(
    "snapshot_created",
    "snapshot_assigned",
    "snapshot_approved",
    "snapshot_rejected",
    name="accessreviewpacketsnapshoteventtype",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    event_type_enum.create(bind, checkfirst=True)

    op.create_table(
        "access_review_packet_snapshot_events",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", event_type_enum, nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
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
            ["actor_user_id"],
            ["users.id"],
            ondelete="SET NULL",
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
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["access_review_packet_snapshots.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_access_review_packet_snapshot_events_org_snapshot_created_id",
        "access_review_packet_snapshot_events",
        ["organization_id", "snapshot_id", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_access_review_packet_snapshot_events_org_patient_created_id",
        "access_review_packet_snapshot_events",
        ["organization_id", "patient_id", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_access_review_packet_snapshot_events_org_type_created",
        "access_review_packet_snapshot_events",
        ["organization_id", "event_type", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_access_review_packet_snapshot_events_org_type_created",
        table_name="access_review_packet_snapshot_events",
    )
    op.drop_index(
        "ix_access_review_packet_snapshot_events_org_patient_created_id",
        table_name="access_review_packet_snapshot_events",
    )
    op.drop_index(
        "ix_access_review_packet_snapshot_events_org_snapshot_created_id",
        table_name="access_review_packet_snapshot_events",
    )
    op.drop_table("access_review_packet_snapshot_events")

    bind = op.get_bind()
    event_type_enum.drop(bind, checkfirst=True)
