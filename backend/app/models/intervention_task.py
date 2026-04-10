from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IDTimestampMixin

if TYPE_CHECKING:
    from app.models.patient import Patient
    from app.models.patient_enrollment import PatientEnrollment
    from app.models.patient_signal import PatientEscalation
    from app.models.user import User
    from app.models.intervention_task_outcome import InterventionTaskOutcome


def enum_values(enum_cls: type[Enum]) -> list[str]:
    """Return SAEnum values matching lowercase database enums."""
    return [item.value for item in enum_cls]


class InterventionTaskStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class InterventionTaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class InterventionTask(IDTimestampMixin, Base):
    __tablename__ = "intervention_tasks"

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

    escalation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patient_escalations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[InterventionTaskStatus] = mapped_column(
        SAEnum(
            InterventionTaskStatus,
            name="interventiontaskstatus",
            values_callable=enum_values,
        ),
        nullable=False,
        default=InterventionTaskStatus.OPEN,
        server_default=InterventionTaskStatus.OPEN.value,
    )

    priority: Mapped[InterventionTaskPriority] = mapped_column(
        SAEnum(
            InterventionTaskPriority,
            name="interventiontaskpriority",
            values_callable=enum_values,
        ),
        nullable=False,
        default=InterventionTaskPriority.MEDIUM,
        server_default=InterventionTaskPriority.MEDIUM.value,
    )

    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    completion_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    patient: Mapped["Patient"] = relationship("Patient")
    enrollment: Mapped["PatientEnrollment"] = relationship("PatientEnrollment")
    escalation: Mapped["PatientEscalation"] = relationship("PatientEscalation")
    assigned_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[assigned_user_id],
    )
    created_by_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by_user_id],
    )
    completed_by_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[completed_by_user_id],
    )
    outcome: Mapped["InterventionTaskOutcome | None"] = relationship(
        "InterventionTaskOutcome",
        back_populates="task",
        uselist=False,
    )
