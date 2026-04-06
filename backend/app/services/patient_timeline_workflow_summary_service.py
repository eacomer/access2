from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.context import RequestContext
from app.models.intervention_task import InterventionTask
from app.models.patient import Patient
from app.models.patient_signal import PatientEscalation
from app.services.authz import ensure_tenant_scoped_resource
from app.services.patient_timeline_read_state_service import (
    calculate_unread_count_for_events,
    get_patient_timeline_read_state,
)
from app.services.patient_timeline_service import (
    PatientTimelineFilters,
    OPEN_TASK_STATUSES,
    UNRESOLVED_ESCALATION_STATUSES,
    get_sorted_patient_timeline_events,
)


def get_patient_timeline_workflow_summary(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
    filters: PatientTimelineFilters | None = None,
) -> dict:
    ensure_tenant_scoped_resource(context=context, resource=patient)

    related_escalation_id = filters.related_escalation_id if filters else None
    related_task_id = filters.related_task_id if filters else None

    events = get_sorted_patient_timeline_events(
        db=db,
        context=context,
        patient=patient,
        filters=filters,
    )
    latest_event = events[0] if events else None

    read_state = get_patient_timeline_read_state(
        db=db,
        context=context,
        patient=patient,
    )
    filtered_unread_count = calculate_unread_count_for_events(
        events=events,
        last_read_event_id=read_state["last_read_event_id"],
        last_read_occurred_at=read_state["last_read_occurred_at"],
    )

    open_task_count, newest_task = _get_open_task_snapshot(
        db=db,
        patient=patient,
        related_escalation_id=related_escalation_id,
        related_task_id=related_task_id,
    )
    open_escalation = _get_latest_unresolved_escalation(
        db=db,
        patient=patient,
        target_escalation_id=related_escalation_id,
    )

    return {
        "patient_id": patient.id,
        "has_open_escalation": open_escalation is not None,
        "open_escalation_id": open_escalation.id if open_escalation else None,
        "open_escalation_severity": (
            open_escalation.severity.value if open_escalation else None
        ),
        "open_escalation_triggered_at": (
            open_escalation.triggered_at if open_escalation else None
        ),
        "open_task_count": open_task_count,
        "newest_open_task_id": newest_task.id if newest_task else None,
        "newest_open_task_title": newest_task.title if newest_task else None,
        "newest_open_task_status": newest_task.status.value if newest_task else None,
        "newest_open_task_priority": newest_task.priority.value if newest_task else None,
        "newest_open_task_created_at": newest_task.created_at if newest_task else None,
        "latest_workflow_event_id": latest_event["event_id"] if latest_event else None,
        "latest_workflow_event_type": latest_event["event_type"] if latest_event else None,
        "latest_workflow_event_occurred_at": (
            latest_event["occurred_at"] if latest_event else None
        ),
        "unread_count": filtered_unread_count,
        "last_read_event_id": read_state["last_read_event_id"],
        "last_read_occurred_at": read_state["last_read_occurred_at"],
    }


def _get_open_task_snapshot(
    *,
    db: Session,
    patient: Patient,
    related_escalation_id: UUID | None = None,
    related_task_id: UUID | None = None,
) -> tuple[int, InterventionTask | None]:
    open_filter = [InterventionTask.status.in_(OPEN_TASK_STATUSES)]
    if related_escalation_id:
        open_filter.append(InterventionTask.escalation_id == related_escalation_id)
    if related_task_id:
        open_filter.append(InterventionTask.id == related_task_id)

    count_stmt = (
        select(func.count())
        .select_from(InterventionTask)
        .where(
            InterventionTask.patient_id == patient.id,
            *open_filter,
        )
    )
    open_count = db.execute(count_stmt).scalar_one()

    newest_stmt = (
        select(InterventionTask)
        .where(
            InterventionTask.patient_id == patient.id,
            *open_filter,
        )
        .order_by(InterventionTask.created_at.desc(), InterventionTask.id.desc())
        .limit(1)
    )
    newest_task = db.execute(newest_stmt).scalar_one_or_none()
    return int(open_count), newest_task


def _get_latest_unresolved_escalation(
    *,
    db: Session,
    patient: Patient,
    target_escalation_id: UUID | None = None,
) -> PatientEscalation | None:
    stmt = (
        select(PatientEscalation)
        .where(
            PatientEscalation.patient_id == patient.id,
            PatientEscalation.status.in_(UNRESOLVED_ESCALATION_STATUSES),
        )
        .order_by(PatientEscalation.triggered_at.desc(), PatientEscalation.id.desc())
        .limit(1)
    )
    if target_escalation_id:
        stmt = stmt.where(PatientEscalation.id == target_escalation_id)
    return db.execute(stmt).scalar_one_or_none()

