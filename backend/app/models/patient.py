from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IDTimestampMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.patient_enrollment import PatientEnrollment


class Patient(IDTimestampMixin, Base):
    __tablename__ = "patients"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "external_patient_id",
            name="uq_patients_org_external_id",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    first_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    last_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    date_of_birth: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    sex: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    external_patient_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    organization: Mapped["Organization"] = relationship("Organization")

    enrollments: Mapped[list["PatientEnrollment"]] = relationship(
        "PatientEnrollment",
        back_populates="patient",
        cascade="all, delete-orphan",
    )
