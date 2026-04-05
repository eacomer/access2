from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IDTimestampMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.patient import Patient


class EnrollmentStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    DISENROLLED = "disenrolled"
    INACTIVE = "inactive"


class ConsentStatus(str, Enum):
    UNKNOWN = "unknown"
    REQUESTED = "requested"
    CONSENTED = "consented"
    DECLINED = "declined"
    REVOKED = "revoked"


class PatientEnrollment(IDTimestampMixin, Base):
    __tablename__ = "patient_enrollments"
    __table_args__ = (
        UniqueConstraint(
            "patient_id",
            "track_code",
            name="uq_patient_enrollment_track",
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

    track_code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    enrollment_status: Mapped[EnrollmentStatus] = mapped_column(
        SAEnum(EnrollmentStatus, name="enrollmentstatus"),
        nullable=False,
        default=EnrollmentStatus.PENDING,
        server_default=EnrollmentStatus.PENDING.value,
    )

    consent_status: Mapped[ConsentStatus] = mapped_column(
        SAEnum(ConsentStatus, name="consentstatus"),
        nullable=False,
        default=ConsentStatus.UNKNOWN,
        server_default=ConsentStatus.UNKNOWN.value,
    )

    consented_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    enrollment_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    enrollment_ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="enrollments",
    )

    organization: Mapped["Organization"] = relationship("Organization")
