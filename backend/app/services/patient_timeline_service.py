from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import RequestContext
from app.models.care_update import CareUpdate
from app.models.intervention_task import InterventionTask, InterventionTaskStatus
from app.models.intervention_task_outcome import InterventionTaskOutcome
from app.models.patient import Patient
from app.models.patient_signal import (
    EscalationStatus,
    PatientEscalation,
    PatientEscalationStatusEvent,
    PatientSignal,
)
from app.services.authz import ensure_tenant_scoped_resource

TimelineItemPayload = Dict[str, Any]

SOURCE_SIGNAL = "signal"
SOURCE_ESCALATION = "escalation"
SOURCE_ESCALATION_STATUS = "escalation_status_event"
SOURCE_TASK = "intervention_task"
SOURCE_TASK_OUTCOME = "intervention_task_outcome"
SOURCE_CARE_UPDATE = "care_update"

EVENT_TYPE_SIGNAL = "signal_recorded"
EVENT_TYPE_ESCALATION = "escalation_triggered"
EVENT_TYPE_ESCALATION_STATUS = "escalation_status_changed"
EVENT_TYPE_TASK_CREATED = "intervention_task_created"
EVENT_TYPE_TASK_OUTCOME = "intervention_task_outcome_logged"
EVENT_TYPE_CARE_UPDATE = "care_update_logged"

ALL_SOURCE_KINDS = (
    SOURCE_SIGNAL,
    SOURCE_ESCALATION,
    SOURCE_TASK,
    SOURCE_ESCALATION_STATUS,
    SOURCE_TASK_OUTCOME,
    SOURCE_CARE_UPDATE,
)

ALL_EVENT_TYPES = (
    EVENT_TYPE_SIGNAL,
    EVENT_TYPE_ESCALATION,
    EVENT_TYPE_TASK_CREATED,
    EVENT_TYPE_ESCALATION_STATUS,
    EVENT_TYPE_TASK_OUTCOME,
    EVENT_TYPE_CARE_UPDATE,
)

TASK_RELATED_EVENT_TYPES = (
    EVENT_TYPE_TASK_CREATED,
    EVENT_TYPE_TASK_OUTCOME,
    EVENT_TYPE_CARE_UPDATE,
)

OPEN_TASK_STATUSES: tuple[InterventionTaskStatus, ...] = (
    InterventionTaskStatus.OPEN,
    InterventionTaskStatus.IN_PROGRESS,
)
OPEN_TASK_STATUS_VALUES: tuple[str, ...] = tuple(status.value for status in OPEN_TASK_STATUSES)

UNRESOLVED_ESCALATION_STATUSES: tuple[EscalationStatus, ...] = (
    EscalationStatus.OPEN,
    EscalationStatus.IN_PROGRESS,
)
UNRESOLVED_ESCALATION_STATUS_VALUES: tuple[str, ...] = tuple(
    status.value for status in UNRESOLVED_ESCALATION_STATUSES
)


@dataclass(frozen=True)
class PatientTimelineDataset:
    events: List[TimelineItemPayload]
    task_status_index: Dict[UUID, str]
    escalation_status_index: Dict[UUID, str]


@dataclass(frozen=True)
class PatientTimelineContext:
    escalation: PatientEscalation | None = None
    task: InterventionTask | None = None


@dataclass(frozen=True)
class PatientTimelineFilters:
    event_types: Tuple[str, ...] | None = None
    occurred_after: datetime | None = None
    occurred_before: datetime | None = None
    related_escalation_id: UUID | None = None
    related_task_id: UUID | None = None
    task_statuses: Tuple[str, ...] | None = None
    include_only_open_work: bool = False


class PatientTimelineEventNotFoundError(Exception):
    """Raised when a requested timeline event cannot be located."""


class PatientTimelineContextError(Exception):
    """Base error for invalid timeline filter context."""


class PatientTimelineContextNotFoundError(PatientTimelineContextError):
    """Raised when a related escalation or task is not scoped to the patient."""


class PatientTimelineContextMismatchError(PatientTimelineContextError):
    """Raised when related filters reference inconsistent workflow context."""


def get_sorted_patient_timeline_events(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
    filters: PatientTimelineFilters | None = None,
) -> List[TimelineItemPayload]:
    ensure_tenant_scoped_resource(context=context, resource=patient)

    validate_patient_timeline_filters(db=db, patient=patient, filters=filters)
    dataset = _collect_patient_events(db=db, patient=patient)
    filtered_events = _filter_events(dataset, filters)
    filtered_events.sort(key=_timeline_sort_key, reverse=True)
    return filtered_events


def list_patient_timeline_events(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
    limit: int = 50,
    cursor_occurred_at: datetime | None = None,
    cursor_event_id: str | None = None,
    filters: PatientTimelineFilters | None = None,
) -> dict:
    filtered_events = get_sorted_patient_timeline_events(
        db=db,
        context=context,
        patient=patient,
        filters=filters,
    )

    total = len(filtered_events)
    cursor_filtered_events = _filter_before_cursor(
        filtered_events,
        cursor_occurred_at=cursor_occurred_at,
        cursor_event_id=cursor_event_id,
    )
    bounded_limit = max(1, limit)
    page_items = cursor_filtered_events[:bounded_limit]
    has_more = len(cursor_filtered_events) > bounded_limit
    next_cursor_occurred_at = page_items[-1]["occurred_at"] if has_more else None
    next_cursor_event_id = page_items[-1]["event_id"] if has_more else None

    return {
        "items": page_items,
        "total": total,
        "limit": bounded_limit,
        "next_cursor_occurred_at": next_cursor_occurred_at,
        "next_cursor_event_id": next_cursor_event_id,
        "has_more": has_more,
    }


def list_patient_timeline_events_since(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
    since: datetime,
    limit: int = 50,
    filters: PatientTimelineFilters | None = None,
) -> dict:
    filtered_events = get_sorted_patient_timeline_events(
        db=db,
        context=context,
        patient=patient,
        filters=filters,
    )

    normalized_since = _normalize_datetime(since)
    bounded_limit = max(1, limit)
    newer_events = [
        item
        for item in filtered_events
        if _normalize_datetime(item["occurred_at"]) > normalized_since
    ]
    page_items = newer_events[:bounded_limit]
    has_more = len(newer_events) > bounded_limit
    newest_occurred_at = page_items[0]["occurred_at"] if page_items else None

    return {
        "items": page_items,
        "limit": bounded_limit,
        "returned_count": len(page_items),
        "has_more": has_more,
        "newest_occurred_at": newest_occurred_at,
    }


def summarize_patient_timeline_events(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
    filters: PatientTimelineFilters | None = None,
) -> dict:
    ensure_tenant_scoped_resource(context=context, resource=patient)

    validate_patient_timeline_filters(db=db, patient=patient, filters=filters)
    dataset = _collect_patient_events(db=db, patient=patient)
    filtered_events = _filter_events(dataset, filters)

    counts: Dict[str, int] = {event_type: 0 for event_type in ALL_EVENT_TYPES}
    for item in filtered_events:
        event_type = item["event_type"]
        if event_type not in counts:
            counts[event_type] = 0
        counts[event_type] += 1

    return {
        "total": len(filtered_events),
        "counts": counts,
    }


def validate_patient_timeline_filters(
    db: Session,
    *,
    patient: Patient,
    filters: PatientTimelineFilters | None = None,
) -> PatientTimelineContext:
    if filters is None:
        return PatientTimelineContext()

    escalation: PatientEscalation | None = None
    task: InterventionTask | None = None

    if filters.related_escalation_id:
        escalation = db.get(PatientEscalation, filters.related_escalation_id)
        if escalation is None or escalation.patient_id != patient.id:
            raise PatientTimelineContextNotFoundError("Escalation not found for this patient.")

    if filters.related_task_id:
        task = db.get(InterventionTask, filters.related_task_id)
        if task is None or task.patient_id != patient.id:
            raise PatientTimelineContextNotFoundError("Intervention task not found for this patient.")

    if escalation and task and task.escalation_id != escalation.id:
        raise PatientTimelineContextMismatchError(
            "Intervention task does not belong to the specified escalation."
        )

    return PatientTimelineContext(escalation=escalation, task=task)


def _collect_patient_events(*, db: Session, patient: Patient) -> PatientTimelineDataset:
    events: List[TimelineItemPayload] = []
    signals = list(_load_signals(db=db, patient=patient))
    escalations = list(_load_escalations(db=db, patient=patient))
    status_events = list(_load_escalation_status_events(db=db, patient=patient))
    tasks = list(_load_tasks(db=db, patient=patient))
    task_outcomes = list(_load_task_outcomes(db=db, patient=patient))
    care_updates = list(_load_care_updates(db=db, patient=patient))

    events.extend(_normalize_signal(signal) for signal in signals)
    events.extend(_normalize_escalation(escalation) for escalation in escalations)
    events.extend(_normalize_escalation_status_event(event) for event in status_events)
    events.extend(_normalize_task(task) for task in tasks)
    events.extend(_normalize_task_outcome(outcome) for outcome in task_outcomes)
    events.extend(_normalize_care_update(update) for update in care_updates)

    task_status_index = {task.id: task.status.value for task in tasks}
    escalation_status_index = {escalation.id: escalation.status.value for escalation in escalations}
    return PatientTimelineDataset(
        events=events,
        task_status_index=task_status_index,
        escalation_status_index=escalation_status_index,
    )


def _filter_events(
    dataset: PatientTimelineDataset,
    filters: PatientTimelineFilters | None,
) -> List[TimelineItemPayload]:
    events = dataset.events
    if filters is None:
        return list(events)

    def matches(item: TimelineItemPayload) -> bool:
        if filters.event_types and item["event_type"] not in filters.event_types:
            return False
        if filters.occurred_after and _normalize_datetime(item["occurred_at"]) < _normalize_datetime(
            filters.occurred_after
        ):
            return False
        if filters.occurred_before and _normalize_datetime(item["occurred_at"]) > _normalize_datetime(
            filters.occurred_before
        ):
            return False
        if (
            filters.related_escalation_id
            and item.get("related_escalation_id") != filters.related_escalation_id
        ):
            return False
        if filters.related_task_id and item.get("related_task_id") != filters.related_task_id:
            return False
        if filters.task_statuses and not _matches_task_status_filters(
            item,
            filters,
            dataset.task_status_index,
        ):
            return False
        if filters.include_only_open_work and not _is_open_work_item(
            item,
            dataset.task_status_index,
            dataset.escalation_status_index,
        ):
            return False
        return True

    return [item for item in events if matches(item)]


def timeline_event_matches_filters(
    db: Session,
    *,
    patient: Patient,
    event: TimelineItemPayload,
    filters: PatientTimelineFilters | None,
    context: PatientTimelineContext | None = None,
) -> bool:
    """Evaluate whether a single timeline event belongs to the filtered subset."""
    if filters is None:
        return True

    task_status_cache: Dict[UUID, str | None] = {}
    escalation_status_cache: Dict[UUID, str | None] = {}

    if context and context.task:
        task_status_cache[context.task.id] = context.task.status.value
    if context and context.escalation:
        escalation_status_cache[context.escalation.id] = context.escalation.status.value

    def get_task_status(task_id: UUID | None) -> str | None:
        if task_id is None:
            return None
        if task_id not in task_status_cache:
            task = db.get(InterventionTask, task_id)
            if task is None or task.patient_id != patient.id:
                task_status_cache[task_id] = None
            else:
                task_status_cache[task_id] = task.status.value
        return task_status_cache[task_id]

    def get_escalation_status(escalation_id: UUID | None) -> str | None:
        if escalation_id is None:
            return None
        if escalation_id not in escalation_status_cache:
            escalation = db.get(PatientEscalation, escalation_id)
            if escalation is None or escalation.patient_id != patient.id:
                escalation_status_cache[escalation_id] = None
            else:
                escalation_status_cache[escalation_id] = escalation.status.value
        return escalation_status_cache[escalation_id]

    if filters.event_types and event["event_type"] not in filters.event_types:
        return False
    if filters.occurred_after and _normalize_datetime(event["occurred_at"]) < _normalize_datetime(
        filters.occurred_after
    ):
        return False
    if filters.occurred_before and _normalize_datetime(event["occurred_at"]) > _normalize_datetime(
        filters.occurred_before
    ):
        return False
    if filters.related_escalation_id and event.get("related_escalation_id") != filters.related_escalation_id:
        return False
    if filters.related_task_id and event.get("related_task_id") != filters.related_task_id:
        return False
    if filters.task_statuses:
        if event["event_type"] not in TASK_RELATED_EVENT_TYPES:
            return False
        related_task_id = event.get("related_task_id")
        task_status = get_task_status(related_task_id)
        if task_status is None or task_status not in filters.task_statuses:
            return False
    if filters.include_only_open_work:
        related_task_id = event.get("related_task_id")
        related_escalation_id = event.get("related_escalation_id")
        task_status = get_task_status(related_task_id)
        escalation_status = get_escalation_status(related_escalation_id)
        task_open = task_status in OPEN_TASK_STATUS_VALUES if task_status else False
        escalation_open = (
            escalation_status in UNRESOLVED_ESCALATION_STATUS_VALUES if escalation_status else False
        )
        if not (task_open or escalation_open):
            return False

    return True


def _matches_task_status_filters(
    item: TimelineItemPayload,
    filters: PatientTimelineFilters,
    task_status_index: Dict[UUID, str],
) -> bool:
    if item["event_type"] not in TASK_RELATED_EVENT_TYPES:
        return True
    related_task_id = item.get("related_task_id")
    if related_task_id is None:
        return False
    task_status = task_status_index.get(related_task_id)
    if task_status is None:
        return False
    return task_status in filters.task_statuses


def _is_open_work_item(
    item: TimelineItemPayload,
    task_status_index: Dict[UUID, str],
    escalation_status_index: Dict[UUID, str],
) -> bool:
    related_task_id = item.get("related_task_id")
    if related_task_id is not None:
        status = task_status_index.get(related_task_id)
        if status in OPEN_TASK_STATUS_VALUES:
            return True
    related_escalation_id = item.get("related_escalation_id")
    if related_escalation_id is not None:
        status = escalation_status_index.get(related_escalation_id)
        if status in UNRESOLVED_ESCALATION_STATUS_VALUES:
            return True
    return False


def _filter_before_cursor(
    events: Iterable[TimelineItemPayload],
    *,
    cursor_occurred_at: datetime | None,
    cursor_event_id: str | None,
) -> List[TimelineItemPayload]:
    if cursor_occurred_at is None and cursor_event_id is None:
        return list(events)
    if cursor_occurred_at is None or cursor_event_id is None:
        raise ValueError("cursor_occurred_at and cursor_event_id must be provided together.")

    return [
        item
        for item in events
        if compare_timeline_positions(
            item_occurred_at=item["occurred_at"],
            item_event_id=item["event_id"],
            reference_occurred_at=cursor_occurred_at,
            reference_event_id=cursor_event_id,
        )
        == -1
    ]


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def get_patient_timeline_event(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
    event_id: str,
) -> TimelineItemPayload:
    ensure_tenant_scoped_resource(context=context, resource=patient)

    source_kind, source_uuid = _parse_event_id(event_id)

    loader: Callable[[Session, UUID], Any]
    normalizer: Callable[[Any], TimelineItemPayload]

    if source_kind == SOURCE_SIGNAL:
        loader = _load_signal_by_id
        normalizer = _normalize_signal
    elif source_kind == SOURCE_ESCALATION:
        loader = _load_escalation_by_id
        normalizer = _normalize_escalation
    elif source_kind == SOURCE_TASK:
        loader = _load_task_by_id
        normalizer = _normalize_task
    elif source_kind == SOURCE_TASK_OUTCOME:
        loader = _load_task_outcome_by_id
        normalizer = _normalize_task_outcome
    elif source_kind == SOURCE_CARE_UPDATE:
        loader = _load_care_update_by_id
        normalizer = _normalize_care_update
    elif source_kind == SOURCE_ESCALATION_STATUS:
        loader = _load_escalation_status_event_by_id
        normalizer = _normalize_escalation_status_event
    else:
        raise PatientTimelineEventNotFoundError()

    record = loader(db, source_uuid)
    if record is None or getattr(record, "patient_id", None) != patient.id:
        raise PatientTimelineEventNotFoundError()

    ensure_tenant_scoped_resource(context=context, resource=record)
    return normalizer(record)


def _load_signals(*, db: Session, patient: Patient) -> Iterable[PatientSignal]:
    stmt = select(PatientSignal).where(PatientSignal.patient_id == patient.id)
    return db.execute(stmt).scalars().all()


def _load_escalations(*, db: Session, patient: Patient) -> Iterable[PatientEscalation]:
    stmt = select(PatientEscalation).where(PatientEscalation.patient_id == patient.id)
    return db.execute(stmt).scalars().all()


def _load_escalation_status_events(
    *,
    db: Session,
    patient: Patient,
) -> Iterable[PatientEscalationStatusEvent]:
    stmt = select(PatientEscalationStatusEvent).where(PatientEscalationStatusEvent.patient_id == patient.id)
    return db.execute(stmt).scalars().all()


def _load_tasks(*, db: Session, patient: Patient) -> Iterable[InterventionTask]:
    stmt = select(InterventionTask).where(InterventionTask.patient_id == patient.id)
    return db.execute(stmt).scalars().all()


def _load_task_outcomes(*, db: Session, patient: Patient) -> Iterable[InterventionTaskOutcome]:
    stmt = select(InterventionTaskOutcome).where(InterventionTaskOutcome.patient_id == patient.id)
    return db.execute(stmt).scalars().all()


def _load_care_updates(*, db: Session, patient: Patient) -> Iterable[CareUpdate]:
    stmt = select(CareUpdate).where(CareUpdate.patient_id == patient.id)
    return db.execute(stmt).scalars().all()


def _load_signal_by_id(db: Session, source_id: UUID) -> PatientSignal | None:
    return db.get(PatientSignal, source_id)


def _load_escalation_by_id(db: Session, source_id: UUID) -> PatientEscalation | None:
    return db.get(PatientEscalation, source_id)


def _load_task_by_id(db: Session, source_id: UUID) -> InterventionTask | None:
    return db.get(InterventionTask, source_id)


def _load_task_outcome_by_id(db: Session, source_id: UUID) -> InterventionTaskOutcome | None:
    return db.get(InterventionTaskOutcome, source_id)


def _load_care_update_by_id(db: Session, source_id: UUID) -> CareUpdate | None:
    return db.get(CareUpdate, source_id)


def _load_escalation_status_event_by_id(
    db: Session,
    source_id: UUID,
) -> PatientEscalationStatusEvent | None:
    return db.get(PatientEscalationStatusEvent, source_id)


def _normalize_signal(signal: PatientSignal) -> TimelineItemPayload:
    display_pieces: List[str] = []
    if signal.signal_value_numeric is not None:
        value_text = f"{signal.signal_value_numeric:g}"
        if signal.unit:
            value_text = f"{value_text} {signal.unit}"
        display_pieces.append(value_text)
    if signal.signal_value_text:
        display_pieces.append(signal.signal_value_text)
    if signal.notes:
        display_pieces.append(signal.notes)

    metadata = {
        "signal_type": signal.signal_type.value,
        "signal_source": signal.signal_source,
        "signal_value_numeric": signal.signal_value_numeric,
        "signal_value_text": signal.signal_value_text,
        "unit": signal.unit,
        "notes": signal.notes,
        "enrollment_id": str(signal.enrollment_id) if signal.enrollment_id else None,
    }

    return {
        "event_id": _compose_event_id(SOURCE_SIGNAL, signal.id),
        "event_type": EVENT_TYPE_SIGNAL,
        "occurred_at": signal.recorded_at,
        "patient_id": signal.patient_id,
        "organization_id": signal.organization_id,
        "source_id": signal.id,
        "source_kind": SOURCE_SIGNAL,
        "display_title": f"Signal: {signal.signal_type.value.replace('_', ' ').title()}",
        "display_text": " | ".join(display_pieces) if display_pieces else None,
        "status": None,
        "priority": None,
        "authored_by_user_id": None,
        "actor_user_id": None,
        "related_escalation_id": signal.escalation.id if signal.escalation else None,
        "related_task_id": None,
        "related_outcome_id": None,
        "metadata": metadata,
    }


def _normalize_escalation(escalation: PatientEscalation) -> TimelineItemPayload:
    metadata = {
        "escalation_type": escalation.escalation_type,
        "status": escalation.status.value,
        "severity": escalation.severity.value,
        "triggered_at": _iso(escalation.triggered_at),
        "in_progress_at": _iso(escalation.in_progress_at),
        "resolved_at": _iso(escalation.resolved_at),
        "resolution_notes": escalation.resolution_notes,
        "canceled_at": _iso(escalation.canceled_at),
        "cancellation_notes": escalation.cancellation_notes,
        "signal_id": str(escalation.signal_id) if escalation.signal_id else None,
    }

    return {
        "event_id": _compose_event_id(SOURCE_ESCALATION, escalation.id),
        "event_type": EVENT_TYPE_ESCALATION,
        "occurred_at": escalation.triggered_at,
        "patient_id": escalation.patient_id,
        "organization_id": escalation.organization_id,
        "source_id": escalation.id,
        "source_kind": SOURCE_ESCALATION,
        "display_title": f"Escalation: {escalation.escalation_type}",
        "display_text": f"Severity: {escalation.severity.value}",
        "status": escalation.status.value,
        "priority": escalation.severity.value,
        "authored_by_user_id": None,
        "actor_user_id": None,
        "related_escalation_id": escalation.id,
        "related_task_id": None,
        "related_outcome_id": None,
        "metadata": metadata,
    }


def _normalize_escalation_status_event(
    status_event: PatientEscalationStatusEvent,
) -> TimelineItemPayload:
    display_title = f"Escalation marked {status_event.status.value.replace('_', ' ')}"
    metadata = {
        "status": status_event.status.value,
        "note": status_event.note,
    }

    return {
        "event_id": _compose_event_id(SOURCE_ESCALATION_STATUS, status_event.id),
        "event_type": EVENT_TYPE_ESCALATION_STATUS,
        "occurred_at": status_event.occurred_at,
        "patient_id": status_event.patient_id,
        "organization_id": status_event.organization_id,
        "source_id": status_event.id,
        "source_kind": SOURCE_ESCALATION_STATUS,
        "display_title": display_title,
        "display_text": status_event.note,
        "status": status_event.status.value,
        "priority": None,
        "authored_by_user_id": None,
        "actor_user_id": status_event.actor_user_id,
        "related_escalation_id": status_event.escalation_id,
        "related_task_id": None,
        "related_outcome_id": None,
        "metadata": metadata,
    }


def _normalize_task(task: InterventionTask) -> TimelineItemPayload:
    metadata = {
        "assigned_user_id": str(task.assigned_user_id) if task.assigned_user_id else None,
        "due_at": _iso(task.due_at),
        "completed_at": _iso(task.completed_at),
        "completion_note": task.completion_note,
        "escalation_id": str(task.escalation_id),
        "description": task.description,
    }

    return {
        "event_id": _compose_event_id(SOURCE_TASK, task.id),
        "event_type": EVENT_TYPE_TASK_CREATED,
        "occurred_at": task.created_at,
        "patient_id": task.patient_id,
        "organization_id": task.organization_id,
        "source_id": task.id,
        "source_kind": SOURCE_TASK,
        "display_title": task.title,
        "display_text": task.description,
        "status": task.status.value,
        "priority": task.priority.value,
        "authored_by_user_id": task.created_by_user_id,
        "actor_user_id": task.completed_by_user_id,
        "related_escalation_id": task.escalation_id,
        "related_task_id": task.id,
        "related_outcome_id": task.outcome.id if task.outcome else None,
        "metadata": metadata,
    }


def _normalize_task_outcome(outcome: InterventionTaskOutcome) -> TimelineItemPayload:
    metadata = {
        "completion_summary": outcome.completion_summary,
        "intervention_type": outcome.intervention_type,
        "patient_response": outcome.patient_response,
        "follow_up_required": outcome.follow_up_required,
        "follow_up_notes": outcome.follow_up_notes,
    }

    return {
        "event_id": _compose_event_id(SOURCE_TASK_OUTCOME, outcome.id),
        "event_type": EVENT_TYPE_TASK_OUTCOME,
        "occurred_at": outcome.completed_at,
        "patient_id": outcome.patient_id,
        "organization_id": outcome.organization_id,
        "source_id": outcome.id,
        "source_kind": SOURCE_TASK_OUTCOME,
        "display_title": f"Outcome: {outcome.intervention_type}",
        "display_text": outcome.completion_summary,
        "status": outcome.outcome_status.value,
        "priority": None,
        "authored_by_user_id": None,
        "actor_user_id": outcome.completed_by_user_id,
        "related_escalation_id": outcome.escalation_id,
        "related_task_id": outcome.intervention_task_id,
        "related_outcome_id": outcome.id,
        "metadata": metadata,
    }


def _normalize_care_update(update: CareUpdate) -> TimelineItemPayload:
    metadata = {
        "care_update_type": update.care_update_type.value,
        "details": update.details,
    }

    return {
        "event_id": _compose_event_id(SOURCE_CARE_UPDATE, update.id),
        "event_type": EVENT_TYPE_CARE_UPDATE,
        "occurred_at": update.occurred_at,
        "patient_id": update.patient_id,
        "organization_id": update.organization_id,
        "source_id": update.id,
        "source_kind": SOURCE_CARE_UPDATE,
        "display_title": update.summary,
        "display_text": update.details,
        "status": update.care_update_type.value,
        "priority": None,
        "authored_by_user_id": update.created_by_user_id,
        "actor_user_id": update.created_by_user_id,
        "related_escalation_id": update.escalation_id,
        "related_task_id": update.intervention_task_id,
        "related_outcome_id": update.intervention_task_outcome_id,
        "metadata": metadata,
    }


def _timeline_sort_key(item: TimelineItemPayload) -> Tuple[datetime, str]:
    return (
        _normalize_datetime(item["occurred_at"]),
        item["event_id"],
    )


def compare_timeline_positions(
    *,
    item_occurred_at: datetime,
    item_event_id: str,
    reference_occurred_at: datetime,
    reference_event_id: str,
) -> int:
    """Compare two timeline positions using the descending order contract."""

    normalized_item = _normalize_datetime(item_occurred_at)
    normalized_reference = _normalize_datetime(reference_occurred_at)

    if normalized_item > normalized_reference:
        return 1
    if normalized_item < normalized_reference:
        return -1
    if item_event_id > reference_event_id:
        return 1
    if item_event_id < reference_event_id:
        return -1
    return 0


def _compose_event_id(source_kind: str, source_id: UUID) -> str:
    return f"{source_kind}:{source_id}"


def _parse_event_id(event_id: str) -> Tuple[str, UUID]:
    if ":" not in event_id:
        raise PatientTimelineEventNotFoundError()
    source_kind, raw_id = event_id.split(":", 1)
    if source_kind not in ALL_SOURCE_KINDS:
        raise PatientTimelineEventNotFoundError()
    try:
        source_uuid = UUID(raw_id)
    except ValueError as exc:
        raise PatientTimelineEventNotFoundError() from exc
    return source_kind, source_uuid


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
