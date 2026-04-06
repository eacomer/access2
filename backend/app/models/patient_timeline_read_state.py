from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IDTimestampMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.patient import Patient
    from app.models.user import User


class PatientTimelineReadState(IDTimestampMixin, Base):
    __tablename__ = "patient_timeline_read_states"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "patient_id",
            "user_id",
            name="uq_patient_timeline_read_states_scope",
        ),
        Index(
            "ix_patient_timeline_read_states_patient_user",
            "patient_id",
            "user_id",
        ),
        Index(
            "ix_patient_timeline_read_states_org_user",
            "organization_id",
            "user_id",
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

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    last_read_event_id: Mapped[str | None] = mapped_column(
        String(length=128),
        nullable=True,
    )

    last_read_occurred_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    organization: Mapped["Organization"] = relationship("Organization")
    patient: Mapped["Patient"] = relationship("Patient")
    user: Mapped["User"] = relationship("User")
