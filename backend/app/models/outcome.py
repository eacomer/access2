from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum as SAEnum, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.intervention_task import enum_values
from app.models.mixins import IDTimestampMixin

if TYPE_CHECKING:
    from app.models.intervention_task import InterventionTask
    from app.models.patient import Patient
    from app.models.patient_signal import PatientSignal


class OutcomeType(str, Enum):
    BP = "bp"
    A1C = "a1c"
    WEIGHT = "weight"
    ADHERENCE = "adherence"
    CHECKIN_STATUS = "checkin_status"


class Outcome(IDTimestampMixin, Base):
    __tablename__ = "outcomes"
    __table_args__ = (
        CheckConstraint(
            "value_numeric IS NOT NULL OR value_text IS NOT NULL",
            name="ck_outcomes_value_present",
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
    intervention_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("intervention_tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    signal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("patient_signals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    type: Mapped[OutcomeType] = mapped_column(
        SAEnum(OutcomeType, name="outcometype", values_callable=enum_values),
        nullable=False,
    )
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False)
    value_numeric: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)

    patient: Mapped["Patient"] = relationship("Patient")
    intervention_task: Mapped["InterventionTask | None"] = relationship("InterventionTask")
    signal: Mapped["PatientSignal | None"] = relationship("PatientSignal")
