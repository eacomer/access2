from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IDTimestampMixin

if TYPE_CHECKING:
    from app.models.intervention_task import InterventionTask
    from app.models.intervention_task_outcome import InterventionTaskOutcome
    from app.models.patient import Patient
    from app.models.patient_signal import PatientEscalation
    from app.models.user import User


class CareUpdateType(str, Enum):
    OUTREACH = "outreach"
    COORDINATION = "coordination"
    EDUCATION = "education"
    ADHERENCE = "adherence"
    FOLLOW_UP = "follow_up"
    OTHER = "other"


class CareUpdate(IDTimestampMixin, Base):
    __tablename__ = "care_updates"
    __table_args__ = (
        Index("ix_care_updates_patient_occurred_at", "patient_id", "occurred_at"),
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

    escalation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("patient_escalations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    intervention_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("intervention_tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    intervention_task_outcome_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("intervention_task_outcomes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    care_update_type: Mapped[CareUpdateType] = mapped_column(
        SAEnum(CareUpdateType, name="careupdatetype"),
        nullable=False,
    )

    summary: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    patient: Mapped["Patient"] = relationship("Patient")
    escalation: Mapped["PatientEscalation | None"] = relationship("PatientEscalation")
    intervention_task: Mapped["InterventionTask | None"] = relationship("InterventionTask")
    intervention_task_outcome: Mapped["InterventionTaskOutcome | None"] = relationship(
        "InterventionTaskOutcome"
    )
    created_by_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by_user_id],
    )
