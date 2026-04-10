from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IDTimestampMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.patient import Patient
    from app.models.patient_enrollment import PatientEnrollment
    from app.models.user import User


def enum_values(enum_cls: type[Enum]) -> list[str]:
    """Return SAEnum values matching the database's lowercase labels."""
    return [item.value for item in enum_cls]


class SignalType(str, Enum):
    SYMPTOM_SCORE = "symptom_score"
    BLOOD_PRESSURE_SYSTOLIC = "blood_pressure_systolic"
    BLOOD_PRESSURE_DIASTOLIC = "blood_pressure_diastolic"
    WEIGHT_CHANGE = "weight_change"
    MISSED_CHECK_IN = "missed_check_in"


class EscalationStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CANCELED = "canceled"


class EscalationSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PatientSignal(IDTimestampMixin, Base):
    __tablename__ = "patient_signals"

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

    enrollment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("patient_enrollments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    signal_type: Mapped[SignalType] = mapped_column(
        SAEnum(SignalType, name="signaltype", values_callable=enum_values),
        nullable=False,
    )

    signal_source: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    signal_value_numeric: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    signal_value_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    unit: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    patient: Mapped["Patient"] = relationship("Patient")
    organization: Mapped["Organization"] = relationship("Organization")
    enrollment: Mapped["PatientEnrollment"] = relationship("PatientEnrollment")
    escalation: Mapped["PatientEscalation | None"] = relationship(
        "PatientEscalation",
        back_populates="signal",
        uselist=False,
    )


class PatientEscalation(IDTimestampMixin, Base):
    __tablename__ = "patient_escalations"
    __table_args__ = (
        UniqueConstraint(
            "signal_id",
            name="uq_patient_escalations_signal",
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

    enrollment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("patient_enrollments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    signal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("patient_signals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    escalation_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    status: Mapped[EscalationStatus] = mapped_column(
        SAEnum(EscalationStatus, name="escalationstatus", values_callable=enum_values),
        nullable=False,
        default=EscalationStatus.OPEN,
        server_default=EscalationStatus.OPEN.value,
    )

    severity: Mapped[EscalationSeverity] = mapped_column(
        SAEnum(EscalationSeverity, name="escalationseverity", values_callable=enum_values),
        nullable=False,
    )

    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    in_progress_at: Mapped[datetime | None] = mapped_column(
        "in_progress_at",
        DateTime(timezone=True),
        nullable=True,
    )

    sla_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    resolution_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    canceled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    cancellation_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    patient: Mapped["Patient"] = relationship("Patient")
    organization: Mapped["Organization"] = relationship("Organization")
    enrollment: Mapped["PatientEnrollment"] = relationship("PatientEnrollment")
    signal: Mapped["PatientSignal | None"] = relationship(
        "PatientSignal",
        back_populates="escalation",
        uselist=False,
    )
    status_events: Mapped[list["PatientEscalationStatusEvent"]] = relationship(
        "PatientEscalationStatusEvent",
        back_populates="escalation",
        order_by="PatientEscalationStatusEvent.occurred_at.desc()",
    )


class PatientEscalationStatusEvent(IDTimestampMixin, Base):
    __tablename__ = "patient_escalation_status_events"

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

    escalation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patient_escalations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[EscalationStatus] = mapped_column(
        SAEnum(EscalationStatus, name="escalationstatus", values_callable=enum_values),
        nullable=False,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    patient: Mapped["Patient"] = relationship("Patient")
    escalation: Mapped["PatientEscalation"] = relationship(
        "PatientEscalation",
        back_populates="status_events",
    )
    actor: Mapped["User"] = relationship("User")
