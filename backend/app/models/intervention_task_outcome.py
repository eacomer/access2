from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.sql import expression
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IDTimestampMixin

if TYPE_CHECKING:
    from app.models.intervention_task import InterventionTask
    from app.models.patient import Patient
    from app.models.patient_signal import PatientEscalation
    from app.models.user import User


class InterventionTaskOutcomeStatus(str, Enum):
    SUCCESSFUL = "successful"
    UNSUCCESSFUL = "unsuccessful"
    NO_RESPONSE = "no_response"
    DEFERRED = "deferred"


class InterventionTaskOutcome(IDTimestampMixin, Base):
    __tablename__ = "intervention_task_outcomes"
    __table_args__ = (
        UniqueConstraint("intervention_task_id", name="uq_task_outcome_task"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    intervention_task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("intervention_tasks.id", ondelete="CASCADE"),
        nullable=False,
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

    completed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    completion_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    intervention_type: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    outcome_status: Mapped[InterventionTaskOutcomeStatus] = mapped_column(
        SAEnum(InterventionTaskOutcomeStatus, name="interventiontaskoutcomestatus"),
        nullable=False,
    )

    patient_response: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    follow_up_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=expression.false(),
    )

    follow_up_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    task: Mapped["InterventionTask"] = relationship(
        "InterventionTask",
        back_populates="outcome",
    )
    patient: Mapped["Patient"] = relationship("Patient")
    escalation: Mapped["PatientEscalation | None"] = relationship("PatientEscalation")
    completed_by_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[completed_by_user_id],
    )
