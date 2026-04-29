from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, DateTime, Enum as SAEnum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.intervention_task import enum_values
from app.models.mixins import IDTimestampMixin


class AccessReviewPacketSnapshotReviewStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class AccessReviewPacketSnapshotEventType(str, Enum):
    SNAPSHOT_CREATED = "snapshot_created"
    SNAPSHOT_ASSIGNED = "snapshot_assigned"
    SNAPSHOT_APPROVED = "snapshot_approved"
    SNAPSHOT_REJECTED = "snapshot_rejected"
    AUDIT_BUNDLE_EXPORTED = "audit_bundle_exported"


class AccessReviewPacketSnapshot(IDTimestampMixin, Base):
    __tablename__ = "access_review_packet_snapshots"
    __table_args__ = (
        Index(
            "ix_access_review_packet_snapshots_patient_generated_at",
            "patient_id",
            "generated_at",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    review_readiness_status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    review_status: Mapped[AccessReviewPacketSnapshotReviewStatus] = mapped_column(
        SAEnum(
            AccessReviewPacketSnapshotReviewStatus,
            name="accessreviewpacketsnapshotreviewstatus",
            values_callable=enum_values,
        ),
        nullable=False,
        default=AccessReviewPacketSnapshotReviewStatus.PENDING_REVIEW,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    assigned_reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    review_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    packet_json: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )

    packet_markdown: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    reviewed_by_user = relationship("User", foreign_keys=[reviewed_by_user_id])
    assigned_reviewer_user = relationship("User", foreign_keys=[assigned_reviewer_user_id])


class AccessReviewPacketSnapshotEvent(IDTimestampMixin, Base):
    __tablename__ = "access_review_packet_snapshot_events"
    __table_args__ = (
        Index(
            "ix_access_review_packet_snapshot_events_org_snapshot_created_id",
            "organization_id",
            "snapshot_id",
            "created_at",
            "id",
        ),
        Index(
            "ix_access_review_packet_snapshot_events_org_patient_created_id",
            "organization_id",
            "patient_id",
            "created_at",
            "id",
        ),
        Index(
            "ix_access_review_packet_snapshot_events_org_type_created",
            "organization_id",
            "event_type",
            "created_at",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )

    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("access_review_packet_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
    )

    event_type: Mapped[AccessReviewPacketSnapshotEventType] = mapped_column(
        SAEnum(
            AccessReviewPacketSnapshotEventType,
            name="accessreviewpacketsnapshoteventtype",
            values_callable=enum_values,
        ),
        nullable=False,
    )

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    metadata_json: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
