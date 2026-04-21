from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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
    EscalationSeverity,
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
SOURCE_ESCALATION_SLA_AT_RISK = "escalation_sla_at_risk"
SOURCE_ESCALATION_SLA_OVERDUE = "escalation_sla_overdue"
SOURCE_TASK = "intervention_task"
SOURCE_TASK_OUTCOME = "intervention_task_outcome"
SOURCE_CARE_UPDATE = "care_update"
SOURCE_TASK_DUE_UPCOMING = "intervention_task_due_upcoming"
SOURCE_TASK_DUE_OVERDUE = "intervention_task_overdue"

EVENT_TYPE_SIGNAL = "signal_recorded"
EVENT_TYPE_ESCALATION = "escalation_triggered"
EVENT_TYPE_ESCALATION_STATUS = "escalation_status_changed"
EVENT_TYPE_ESCALATION_SLA_AT_RISK = "escalation_sla_at_risk"
EVENT_TYPE_ESCALATION_SLA_OVERDUE = "escalation_sla_overdue"
EVENT_TYPE_TASK_CREATED = "intervention_task_created"
EVENT_TYPE_TASK_OUTCOME = "intervention_task_outcome_logged"
EVENT_TYPE_CARE_UPDATE = "care_update_logged"
EVENT_TYPE_TASK_DUE_UPCOMING = "intervention_task_due_upcoming"
EVENT_TYPE_TASK_DUE_OVERDUE = "intervention_task_due_overdue"

ALL_SOURCE_KINDS = (
    SOURCE_SIGNAL,
    SOURCE_ESCALATION,
    SOURCE_TASK,
    SOURCE_ESCALATION_STATUS,
    SOURCE_TASK_OUTCOME,
    SOURCE_CARE_UPDATE,
    SOURCE_TASK_DUE_UPCOMING,
    SOURCE_TASK_DUE_OVERDUE,
    SOURCE_ESCALATION_SLA_AT_RISK,
    SOURCE_ESCALATION_SLA_OVERDUE,
)

ALL_EVENT_TYPES = (
    EVENT_TYPE_SIGNAL,
    EVENT_TYPE_ESCALATION,
    EVENT_TYPE_TASK_CREATED,
    EVENT_TYPE_ESCALATION_STATUS,
    EVENT_TYPE_TASK_OUTCOME,
    EVENT_TYPE_CARE_UPDATE,
    EVENT_TYPE_TASK_DUE_UPCOMING,
    EVENT_TYPE_TASK_DUE_OVERDUE,
    EVENT_TYPE_ESCALATION_SLA_AT_RISK,
    EVENT_TYPE_ESCALATION_SLA_OVERDUE,
)

ESCALATION_EVIDENCE_EVENT_TYPES = (
    EVENT_TYPE_ESCALATION,
    EVENT_TYPE_ESCALATION_STATUS,
    EVENT_TYPE_ESCALATION_SLA_AT_RISK,
    EVENT_TYPE_ESCALATION_SLA_OVERDUE,
)

TASK_RELATED_EVENT_TYPES = (
    EVENT_TYPE_TASK_CREATED,
    EVENT_TYPE_TASK_OUTCOME,
    EVENT_TYPE_CARE_UPDATE,
    EVENT_TYPE_TASK_DUE_UPCOMING,
    EVENT_TYPE_TASK_DUE_OVERDUE,
)

OPEN_TASK_STATUSES: tuple[InterventionTaskStatus, ...] = (
    InterventionTaskStatus.OPEN,
    InterventionTaskStatus.IN_PROGRESS,
)
OPEN_TASK_STATUS_VALUES: tuple[str, ...] = tuple(status.value for status in OPEN_TASK_STATUSES)
TERMINAL_TASK_STATUSES: tuple[InterventionTaskStatus, ...] = (
    InterventionTaskStatus.COMPLETED,
    InterventionTaskStatus.CANCELLED,
)
TASK_DUE_STATE_UPCOMING = "due_upcoming"
TASK_DUE_STATE_OVERDUE = "overdue"

ESCALATION_SLA_STATE_AT_RISK = "sla_at_risk"
ESCALATION_SLA_STATE_OVERDUE = "sla_overdue"
ESCALATION_SLA_AT_RISK_THRESHOLD = timedelta(hours=24)
ESCALATION_SEVERITY_PRIORITY = {
    EscalationSeverity.LOW: 0,
    EscalationSeverity.MEDIUM: 1,
    EscalationSeverity.HIGH: 2,
}

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
class EscalationWorklistSummary:
    open_escalation_count: int = 0
    overdue_escalation_count: int = 0
    at_risk_escalation_count: int = 0
    highest_escalation_priority: str | None = None
    next_escalation_sla_due_at: datetime | None = None
    latest_open_escalation_id: UUID | None = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "open_escalation_count": self.open_escalation_count,
            "overdue_escalation_count": self.overdue_escalation_count,
            "at_risk_escalation_count": self.at_risk_escalation_count,
            "highest_escalation_priority": self.highest_escalation_priority,
            "next_escalation_sla_due_at": self.next_escalation_sla_due_at,
            "latest_open_escalation_id": self.latest_open_escalation_id,
        }


@dataclass(frozen=True)
class EscalationEvidence:
    has_open_escalation: bool = False
    open_escalation_count: int = 0
    overdue_escalation_count: int = 0
    at_risk_escalation_count: int = 0
    highest_open_escalation_priority: str | None = None
    next_open_escalation_sla_due_at: datetime | None = None
    latest_open_escalation_id: UUID | None = None
    latest_open_escalation_status: str | None = None
    latest_open_escalation_created_at: datetime | None = None
    latest_escalation_event_id: str | None = None
    latest_escalation_event_type: str | None = None
    latest_escalation_event_occurred_at: datetime | None = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "has_open_escalation": self.has_open_escalation,
            "open_escalation_count": self.open_escalation_count,
            "overdue_escalation_count": self.overdue_escalation_count,
            "at_risk_escalation_count": self.at_risk_escalation_count,
            "highest_open_escalation_priority": self.highest_open_escalation_priority,
            "next_open_escalation_sla_due_at": self.next_open_escalation_sla_due_at,
            "latest_open_escalation_id": self.latest_open_escalation_id,
            "latest_open_escalation_status": self.latest_open_escalation_status,
            "latest_open_escalation_created_at": self.latest_open_escalation_created_at,
            "latest_escalation_event_id": self.latest_escalation_event_id,
            "latest_escalation_event_type": self.latest_escalation_event_type,
            "latest_escalation_event_occurred_at": self.latest_escalation_event_occurred_at,
        }


@dataclass(frozen=True)
class InterventionTaskSummary:
    open_task_count: int = 0
    in_progress_task_count: int = 0
    overdue_task_count: int = 0
    latest_active_task_id: UUID | None = None
    latest_active_task_title: str | None = None
    latest_active_task_status: str | None = None
    latest_active_task_priority: str | None = None
    latest_active_task_due_at: datetime | None = None
    latest_active_task_created_at: datetime | None = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "open_task_count": self.open_task_count,
            "in_progress_task_count": self.in_progress_task_count,
            "overdue_task_count": self.overdue_task_count,
            "latest_active_task_id": self.latest_active_task_id,
            "latest_active_task_title": self.latest_active_task_title,
            "latest_active_task_status": self.latest_active_task_status,
            "latest_active_task_priority": self.latest_active_task_priority,
            "latest_active_task_due_at": self.latest_active_task_due_at,
            "latest_active_task_created_at": self.latest_active_task_created_at,
        }


@dataclass(frozen=True)
class WorkflowStatusSummary:
    status_key: str
    label: str
    has_active_work: bool
    primary_driver: str
    severity: str | None = None
    detail: str | None = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "status_key": self.status_key,
            "label": self.label,
            "has_active_work": self.has_active_work,
            "primary_driver": self.primary_driver,
            "severity": self.severity,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class InterventionEvidenceSummaryItem:
    title: str
    status: str | None = None
    occurred_at: datetime | None = None
    detail: str | None = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "status": self.status,
            "occurred_at": self.occurred_at,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class InterventionEvidenceSummary:
    total_escalations: int = 0
    open_escalations: int = 0
    total_tasks: int = 0
    open_tasks: int = 0
    in_progress_tasks: int = 0
    completed_tasks: int = 0
    canceled_tasks: int = 0
    recent_trigger_reasons: Tuple[InterventionEvidenceSummaryItem, ...] = ()
    recent_completed_interventions: Tuple[InterventionEvidenceSummaryItem, ...] = ()
    current_open_work: Tuple[InterventionEvidenceSummaryItem, ...] = ()
    evidence_event_count: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "total_escalations": self.total_escalations,
            "open_escalations": self.open_escalations,
            "total_tasks": self.total_tasks,
            "open_tasks": self.open_tasks,
            "in_progress_tasks": self.in_progress_tasks,
            "completed_tasks": self.completed_tasks,
            "canceled_tasks": self.canceled_tasks,
            "recent_trigger_reasons": [
                item.as_dict() for item in self.recent_trigger_reasons
            ],
            "recent_completed_interventions": [
                item.as_dict() for item in self.recent_completed_interventions
            ],
            "current_open_work": [item.as_dict() for item in self.current_open_work],
            "evidence_event_count": self.evidence_event_count,
        }


@dataclass(frozen=True)
class PatientAttentionSummary:
    why_now: str
    primary_driver: str | None
    recommended_next_action: str
    supporting_evidence: Tuple[str, ...] = ()
    urgency_level: str | None = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "why_now": self.why_now,
            "primary_driver": self.primary_driver,
            "recommended_next_action": self.recommended_next_action,
            "supporting_evidence": list(self.supporting_evidence),
            "urgency_level": self.urgency_level,
        }


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
    task_reference_time = get_due_state_reference_time()
    sla_reference_time = get_escalation_sla_reference_time()
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
    events.extend(_derive_task_due_events(tasks, reference_time=task_reference_time))
    events.extend(_derive_escalation_sla_events(escalations, reference_time=sla_reference_time))

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

    if source_kind in (SOURCE_TASK_DUE_UPCOMING, SOURCE_TASK_DUE_OVERDUE):
        task = _load_task_by_id(db, source_uuid)
        if task is None or task.patient_id != patient.id:
            raise PatientTimelineEventNotFoundError()
        ensure_tenant_scoped_resource(context=context, resource=task)
        reference_time = get_due_state_reference_time()
        expected_state = (
            TASK_DUE_STATE_UPCOMING
            if source_kind == SOURCE_TASK_DUE_UPCOMING
            else TASK_DUE_STATE_OVERDUE
        )
        current_state = _task_due_state(task, reference_time=reference_time)
        if current_state != expected_state:
            raise PatientTimelineEventNotFoundError()
        return _normalize_task_due_state(task, due_state=expected_state)
    if source_kind in (SOURCE_ESCALATION_SLA_AT_RISK, SOURCE_ESCALATION_SLA_OVERDUE):
        escalation = _load_escalation_by_id(db, source_uuid)
        if escalation is None or escalation.patient_id != patient.id:
            raise PatientTimelineEventNotFoundError()
        ensure_tenant_scoped_resource(context=context, resource=escalation)
        reference_time = get_escalation_sla_reference_time()
        expected_state = (
            ESCALATION_SLA_STATE_AT_RISK
            if source_kind == SOURCE_ESCALATION_SLA_AT_RISK
            else ESCALATION_SLA_STATE_OVERDUE
        )
        current_state = _escalation_sla_state(escalation, reference_time=reference_time)
        if current_state != expected_state:
            raise PatientTimelineEventNotFoundError()
        return _normalize_escalation_sla_state(escalation, sla_state=expected_state)

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
        "sla_due_at": _iso(escalation.sla_due_at),
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


def _derive_task_due_events(
    tasks: Iterable[InterventionTask],
    *,
    reference_time: datetime,
) -> List[TimelineItemPayload]:
    derived: List[TimelineItemPayload] = []
    for task in tasks:
        due_state = _task_due_state(task, reference_time=reference_time)
        if due_state is None:
            continue
        derived.append(_normalize_task_due_state(task, due_state=due_state))
    return derived


def _derive_escalation_sla_events(
    escalations: Iterable[PatientEscalation],
    *,
    reference_time: datetime,
) -> List[TimelineItemPayload]:
    derived: List[TimelineItemPayload] = []
    for escalation in escalations:
        sla_state = _escalation_sla_state(escalation, reference_time=reference_time)
        if sla_state is None:
            continue
        derived.append(_normalize_escalation_sla_state(escalation, sla_state=sla_state))
    return derived


def _task_due_state(task: InterventionTask, *, reference_time: datetime) -> str | None:
    if task.due_at is None:
        return None
    if task.status in TERMINAL_TASK_STATUSES:
        return None
    normalized_due_at = _normalize_datetime(task.due_at)
    normalized_reference = _normalize_datetime(reference_time)
    if normalized_due_at < normalized_reference:
        return TASK_DUE_STATE_OVERDUE
    return TASK_DUE_STATE_UPCOMING


def _escalation_sla_state(
    escalation: PatientEscalation,
    *,
    reference_time: datetime,
) -> str | None:
    if escalation.sla_due_at is None:
        return None
    if escalation.status not in UNRESOLVED_ESCALATION_STATUSES:
        return None

    normalized_due_at = _normalize_datetime(escalation.sla_due_at)
    normalized_reference = _normalize_datetime(reference_time)
    if normalized_due_at < normalized_reference:
        return ESCALATION_SLA_STATE_OVERDUE

    risk_cutoff = normalized_reference + ESCALATION_SLA_AT_RISK_THRESHOLD
    if normalized_reference <= normalized_due_at <= risk_cutoff:
        return ESCALATION_SLA_STATE_AT_RISK
    return None


def _normalize_task_due_state(task: InterventionTask, *, due_state: str) -> TimelineItemPayload:
    if task.due_at is None:
        raise PatientTimelineEventNotFoundError()

    if due_state == TASK_DUE_STATE_OVERDUE:
        source_kind = SOURCE_TASK_DUE_OVERDUE
        event_type = EVENT_TYPE_TASK_DUE_OVERDUE
        title_prefix = "Task overdue"
    elif due_state == TASK_DUE_STATE_UPCOMING:
        source_kind = SOURCE_TASK_DUE_UPCOMING
        event_type = EVENT_TYPE_TASK_DUE_UPCOMING
        title_prefix = "Task due soon"
    else:
        raise PatientTimelineEventNotFoundError()

    display_title = f"{title_prefix}: {task.title}"
    display_text = task.description or f"Due at {task.due_at.isoformat()}"
    metadata = {
        "due_state": due_state,
        "due_at": _iso(task.due_at),
        "assigned_user_id": str(task.assigned_user_id) if task.assigned_user_id else None,
        "escalation_id": str(task.escalation_id),
        "priority": task.priority.value,
        "status": task.status.value,
    }

    return {
        "event_id": _compose_event_id(source_kind, task.id),
        "event_type": event_type,
        "occurred_at": task.due_at,
        "patient_id": task.patient_id,
        "organization_id": task.organization_id,
        "source_id": task.id,
        "source_kind": source_kind,
        "display_title": display_title,
        "display_text": display_text,
        "status": task.status.value,
        "priority": task.priority.value,
        "authored_by_user_id": task.created_by_user_id,
        "actor_user_id": task.assigned_user_id,
        "related_escalation_id": task.escalation_id,
        "related_task_id": task.id,
        "related_outcome_id": None,
        "metadata": metadata,
    }


def _normalize_escalation_sla_state(
    escalation: PatientEscalation,
    *,
    sla_state: str,
) -> TimelineItemPayload:
    if escalation.sla_due_at is None:
        raise PatientTimelineEventNotFoundError()

    if sla_state == ESCALATION_SLA_STATE_OVERDUE:
        source_kind = SOURCE_ESCALATION_SLA_OVERDUE
        event_type = EVENT_TYPE_ESCALATION_SLA_OVERDUE
        title = "Escalation SLA overdue"
    elif sla_state == ESCALATION_SLA_STATE_AT_RISK:
        source_kind = SOURCE_ESCALATION_SLA_AT_RISK
        event_type = EVENT_TYPE_ESCALATION_SLA_AT_RISK
        title = "Escalation SLA at risk"
    else:
        raise PatientTimelineEventNotFoundError()

    metadata = {
        "sla_state": sla_state,
        "sla_due_at": _iso(escalation.sla_due_at),
        "escalation_status": escalation.status.value,
        "severity": escalation.severity.value,
    }

    display_text = f"SLA target at {escalation.sla_due_at.isoformat()}"

    return {
        "event_id": _compose_event_id(source_kind, escalation.id),
        "event_type": event_type,
        "occurred_at": escalation.sla_due_at,
        "patient_id": escalation.patient_id,
        "organization_id": escalation.organization_id,
        "source_id": escalation.id,
        "source_kind": source_kind,
        "display_title": title,
        "display_text": display_text,
        "status": escalation.status.value,
        "priority": escalation.severity.value,
        "authored_by_user_id": None,
        "actor_user_id": None,
        "related_escalation_id": escalation.id,
        "related_task_id": None,
        "related_outcome_id": None,
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


def build_escalation_worklist_summary(
    escalations: Iterable[PatientEscalation],
    *,
    reference_time: datetime | None = None,
) -> EscalationWorklistSummary:
    reference = reference_time or get_escalation_sla_reference_time()
    open_escalations: list[PatientEscalation] = [
        escalation
        for escalation in escalations
        if escalation.status in UNRESOLVED_ESCALATION_STATUSES
    ]
    if not open_escalations:
        return EscalationWorklistSummary()

    overdue_count = 0
    at_risk_count = 0
    next_sla_due_at: datetime | None = None
    next_sla_due_at_normalized: datetime | None = None

    for escalation in open_escalations:
        sla_state = _escalation_sla_state(escalation, reference_time=reference)
        if sla_state == ESCALATION_SLA_STATE_OVERDUE:
            overdue_count += 1
        elif sla_state == ESCALATION_SLA_STATE_AT_RISK:
            at_risk_count += 1

        if escalation.sla_due_at is None:
            continue
        normalized_due = _normalize_datetime(escalation.sla_due_at)
        if next_sla_due_at_normalized is None or normalized_due < next_sla_due_at_normalized:
            next_sla_due_at_normalized = normalized_due
            next_sla_due_at = escalation.sla_due_at

    highest_priority_escalation = max(
        open_escalations,
        key=lambda escalation: ESCALATION_SEVERITY_PRIORITY.get(escalation.severity, -1),
    )
    latest_open_escalation = max(
        open_escalations,
        key=lambda escalation: (_normalize_datetime(escalation.triggered_at), str(escalation.id)),
    )

    return EscalationWorklistSummary(
        open_escalation_count=len(open_escalations),
        overdue_escalation_count=overdue_count,
        at_risk_escalation_count=at_risk_count,
        highest_escalation_priority=highest_priority_escalation.severity.value
        if highest_priority_escalation.severity
        else None,
        next_escalation_sla_due_at=next_sla_due_at,
        latest_open_escalation_id=latest_open_escalation.id,
    )


def build_patient_escalation_evidence(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
    reference_time: datetime | None = None,
) -> EscalationEvidence:
    ensure_tenant_scoped_resource(context=context, resource=patient)
    escalations = list(_load_escalations(db=db, patient=patient))
    summary = build_escalation_worklist_summary(
        escalations,
        reference_time=reference_time,
    )

    open_escalations = [
        escalation
        for escalation in escalations
        if escalation.status in UNRESOLVED_ESCALATION_STATUSES
    ]
    latest_open_escalation = (
        max(
            open_escalations,
            key=lambda escalation: (_normalize_datetime(escalation.triggered_at), str(escalation.id)),
        )
        if open_escalations
        else None
    )

    latest_event: TimelineItemPayload | None = None
    if open_escalations:
        open_ids = {escalation.id for escalation in open_escalations}
        dataset = _collect_patient_events(db=db, patient=patient)
        relevant_events = [
            event
            for event in dataset.events
            if event.get("related_escalation_id") in open_ids
            and event["event_type"] in ESCALATION_EVIDENCE_EVENT_TYPES
        ]
        if relevant_events:
            latest_event = max(relevant_events, key=_timeline_sort_key)

    return EscalationEvidence(
        has_open_escalation=summary.open_escalation_count > 0,
        open_escalation_count=summary.open_escalation_count,
        overdue_escalation_count=summary.overdue_escalation_count,
        at_risk_escalation_count=summary.at_risk_escalation_count,
        highest_open_escalation_priority=summary.highest_escalation_priority,
        next_open_escalation_sla_due_at=summary.next_escalation_sla_due_at,
        latest_open_escalation_id=summary.latest_open_escalation_id,
        latest_open_escalation_status=latest_open_escalation.status.value
        if latest_open_escalation
        else None,
        latest_open_escalation_created_at=latest_open_escalation.triggered_at
        if latest_open_escalation
        else None,
        latest_escalation_event_id=latest_event["event_id"] if latest_event else None,
        latest_escalation_event_type=latest_event["event_type"] if latest_event else None,
        latest_escalation_event_occurred_at=latest_event["occurred_at"] if latest_event else None,
    )


def build_patient_task_summary(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
    reference_time: datetime | None = None,
) -> InterventionTaskSummary:
    ensure_tenant_scoped_resource(context=context, resource=patient)
    tasks = list(_load_tasks(db=db, patient=patient))
    return summarize_intervention_tasks(tasks, reference_time=reference_time)


def build_intervention_evidence_summary(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
) -> InterventionEvidenceSummary:
    ensure_tenant_scoped_resource(context=context, resource=patient)

    dataset = _collect_patient_events(db=db, patient=patient)
    escalations = list(_load_escalations(db=db, patient=patient))
    tasks = list(_load_tasks(db=db, patient=patient))

    sorted_events = sorted(dataset.events, key=_timeline_sort_key, reverse=True)
    trigger_events = [
        event for event in sorted_events if event["event_type"] == EVENT_TYPE_ESCALATION
    ][:3]
    completed_events = [
        event
        for event in sorted_events
        if event["event_type"] in (EVENT_TYPE_TASK_OUTCOME, EVENT_TYPE_CARE_UPDATE)
    ][:3]
    open_work_events = [
        event
        for event in sorted_events
        if _is_intervention_summary_open_work_item(
            event,
            dataset.task_status_index,
            dataset.escalation_status_index,
        )
        and event["event_type"]
        in (
            EVENT_TYPE_ESCALATION,
            EVENT_TYPE_TASK_CREATED,
            EVENT_TYPE_TASK_DUE_UPCOMING,
            EVENT_TYPE_TASK_DUE_OVERDUE,
            EVENT_TYPE_ESCALATION_SLA_AT_RISK,
            EVENT_TYPE_ESCALATION_SLA_OVERDUE,
        )
    ][:3]
    evidence_events = [
        event
        for event in dataset.events
        if event["event_type"]
        in (
            EVENT_TYPE_ESCALATION,
            EVENT_TYPE_ESCALATION_STATUS,
            EVENT_TYPE_TASK_CREATED,
            EVENT_TYPE_TASK_OUTCOME,
            EVENT_TYPE_CARE_UPDATE,
            EVENT_TYPE_TASK_DUE_UPCOMING,
            EVENT_TYPE_TASK_DUE_OVERDUE,
            EVENT_TYPE_ESCALATION_SLA_AT_RISK,
            EVENT_TYPE_ESCALATION_SLA_OVERDUE,
        )
    ]

    return InterventionEvidenceSummary(
        total_escalations=len(escalations),
        open_escalations=sum(
            1 for escalation in escalations if escalation.status in UNRESOLVED_ESCALATION_STATUSES
        ),
        total_tasks=len(tasks),
        open_tasks=sum(1 for task in tasks if task.status == InterventionTaskStatus.OPEN),
        in_progress_tasks=sum(
            1 for task in tasks if task.status == InterventionTaskStatus.IN_PROGRESS
        ),
        completed_tasks=sum(
            1 for task in tasks if task.status == InterventionTaskStatus.COMPLETED
        ),
        canceled_tasks=sum(
            1 for task in tasks if task.status == InterventionTaskStatus.CANCELLED
        ),
        recent_trigger_reasons=tuple(_summary_item_from_event(event) for event in trigger_events),
        recent_completed_interventions=tuple(
            _summary_item_from_event(event) for event in completed_events
        ),
        current_open_work=tuple(_summary_item_from_event(event) for event in open_work_events),
        evidence_event_count=len(evidence_events),
    )


def build_patient_attention_summary(
    *,
    escalation_evidence: EscalationEvidence | None = None,
    task_summary: InterventionTaskSummary | None = None,
    workflow_status: WorkflowStatusSummary | None = None,
    intervention_evidence_summary: InterventionEvidenceSummary | None = None,
) -> PatientAttentionSummary:
    open_escalations = escalation_evidence.open_escalation_count if escalation_evidence else 0
    overdue_escalations = escalation_evidence.overdue_escalation_count if escalation_evidence else 0
    at_risk_escalations = escalation_evidence.at_risk_escalation_count if escalation_evidence else 0
    highest_escalation_priority = (
        escalation_evidence.highest_open_escalation_priority if escalation_evidence else None
    )
    open_tasks = task_summary.open_task_count if task_summary else 0
    in_progress_tasks = task_summary.in_progress_task_count if task_summary else 0
    overdue_tasks = task_summary.overdue_task_count if task_summary else 0
    completed_tasks = (
        intervention_evidence_summary.completed_tasks if intervention_evidence_summary else 0
    )
    total_evidence_events = (
        intervention_evidence_summary.evidence_event_count if intervention_evidence_summary else 0
    )
    current_open_work = (
        intervention_evidence_summary.current_open_work if intervention_evidence_summary else ()
    )
    recent_triggers = (
        intervention_evidence_summary.recent_trigger_reasons
        if intervention_evidence_summary
        else ()
    )

    evidence: list[str] = []
    if open_escalations:
        evidence.append(_pluralize(open_escalations, "open escalation"))
    if highest_escalation_priority:
        evidence.append(f"Highest open escalation severity: {highest_escalation_priority}")
    if overdue_escalations:
        evidence.append(_pluralize(overdue_escalations, "escalation SLA overdue", "escalation SLAs overdue"))
    elif at_risk_escalations:
        evidence.append(_pluralize(at_risk_escalations, "escalation SLA at risk", "escalation SLAs at risk"))
    if overdue_tasks:
        evidence.append(_pluralize(overdue_tasks, "task overdue"))
    if in_progress_tasks:
        evidence.append(_pluralize(in_progress_tasks, "task in progress", "tasks in progress"))
    elif open_tasks:
        evidence.append(_pluralize(open_tasks, "open task"))
    if recent_triggers:
        latest_trigger = recent_triggers[0]
        trigger_detail = latest_trigger.detail or latest_trigger.title
        evidence.append(f"Recent trigger: {trigger_detail}")
    for item in current_open_work:
        if len(evidence) >= 4:
            break
        evidence.append(item.title)
    if completed_tasks and not open_escalations and not open_tasks:
        evidence.append(_pluralize(completed_tasks, "completed intervention"))
    if not evidence and total_evidence_events:
        evidence.append(_pluralize(total_evidence_events, "timeline evidence event"))

    primary_driver = workflow_status.primary_driver if workflow_status else None

    if overdue_tasks:
        return PatientAttentionSummary(
            why_now="One or more active intervention tasks are overdue.",
            primary_driver="task",
            recommended_next_action="Complete immediate follow-up or update the task disposition.",
            supporting_evidence=tuple(evidence),
            urgency_level="overdue",
        )
    if in_progress_tasks:
        return PatientAttentionSummary(
            why_now="Active intervention work is already in progress.",
            primary_driver="task",
            recommended_next_action="Follow through on the current task and document the outcome.",
            supporting_evidence=tuple(evidence),
            urgency_level="active",
        )
    if open_escalations and open_tasks == 0:
        return PatientAttentionSummary(
            why_now="There is an open escalation with no active intervention task.",
            primary_driver="escalation",
            recommended_next_action="Assign and start an outreach task.",
            supporting_evidence=tuple(evidence),
            urgency_level="urgent" if overdue_escalations or at_risk_escalations else "active",
        )
    if open_escalations:
        return PatientAttentionSummary(
            why_now="There is unresolved escalation work with an open task.",
            primary_driver="escalation",
            recommended_next_action="Start or complete the assigned intervention task.",
            supporting_evidence=tuple(evidence),
            urgency_level="urgent" if overdue_escalations or at_risk_escalations else "active",
        )
    if completed_tasks:
        return PatientAttentionSummary(
            why_now="Recent intervention work is completed and no escalation is currently open.",
            primary_driver="monitoring",
            recommended_next_action="Continue monitoring and review new timeline evidence as it arrives.",
            supporting_evidence=tuple(evidence),
            urgency_level="stable",
        )
    return PatientAttentionSummary(
        why_now="No active escalation or intervention task is currently recorded.",
        primary_driver=primary_driver or "monitoring",
        recommended_next_action="Continue routine monitoring.",
        supporting_evidence=tuple(evidence) if evidence else ("No active workflow evidence recorded.",),
        urgency_level="stable",
    )


def summarize_intervention_tasks(
    tasks: Iterable[InterventionTask],
    *,
    reference_time: datetime | None = None,
) -> InterventionTaskSummary:
    normalized_reference = _normalize_datetime(reference_time or get_due_state_reference_time())
    open_task_count = 0
    in_progress_task_count = 0
    overdue_task_count = 0
    latest_active_task: InterventionTask | None = None
    latest_sort_key: tuple[datetime, str] | None = None

    for task in tasks:
        if task.status in OPEN_TASK_STATUSES:
            open_task_count += 1
            if task.status == InterventionTaskStatus.IN_PROGRESS:
                in_progress_task_count += 1
            if task.due_at is not None and _normalize_datetime(task.due_at) < normalized_reference:
                overdue_task_count += 1
            candidate_key = (_normalize_datetime(task.created_at), str(task.id))
            if latest_sort_key is None or candidate_key > latest_sort_key:
                latest_sort_key = candidate_key
                latest_active_task = task

    return InterventionTaskSummary(
        open_task_count=open_task_count,
        in_progress_task_count=in_progress_task_count,
        overdue_task_count=overdue_task_count,
        latest_active_task_id=latest_active_task.id if latest_active_task else None,
        latest_active_task_title=latest_active_task.title if latest_active_task else None,
        latest_active_task_status=latest_active_task.status.value if latest_active_task else None,
        latest_active_task_priority=latest_active_task.priority.value if latest_active_task else None,
        latest_active_task_due_at=latest_active_task.due_at if latest_active_task else None,
        latest_active_task_created_at=latest_active_task.created_at if latest_active_task else None,
    )


def _pluralize(count: int, singular: str, plural: str | None = None) -> str:
    if count == 1:
        return f"1 {singular}"
    resolved = plural or f"{singular}s"
    return f"{count} {resolved}"


def derive_workflow_status_summary(
    *,
    task_summary: InterventionTaskSummary | None = None,
    escalation_summary: EscalationWorklistSummary | None = None,
    escalation_evidence: EscalationEvidence | None = None,
) -> WorkflowStatusSummary:
    def _status(
        key: str,
        label: str,
        *,
        driver: str,
        severity: str | None,
        active: bool,
        detail: str | None = None,
    ) -> WorkflowStatusSummary:
        return WorkflowStatusSummary(
            status_key=key,
            label=label,
            has_active_work=active,
            primary_driver=driver,
            severity=severity,
            detail=detail,
        )

    task_overdue = task_summary.overdue_task_count if task_summary else 0
    task_in_progress = task_summary.in_progress_task_count if task_summary else 0
    task_open = task_summary.open_task_count if task_summary else 0

    escalation_overdue = (
        escalation_evidence.overdue_escalation_count
        if escalation_evidence
        else (escalation_summary.overdue_escalation_count if escalation_summary else 0)
    )
    escalation_at_risk = (
        escalation_evidence.at_risk_escalation_count
        if escalation_evidence
        else (escalation_summary.at_risk_escalation_count if escalation_summary else 0)
    )
    escalation_open = (
        escalation_evidence.open_escalation_count
        if escalation_evidence
        else (escalation_summary.open_escalation_count if escalation_summary else 0)
    )

    if task_overdue > 0:
        return _status(
            "task_overdue",
            f"{_pluralize(task_overdue, 'task')} overdue",
            driver="task",
            severity="overdue",
            active=True,
        )
    if escalation_overdue > 0:
        return _status(
            "escalation_overdue",
            f"{_pluralize(escalation_overdue, 'escalation')} overdue",
            driver="escalation",
            severity="overdue",
            active=True,
        )
    if task_in_progress > 0:
        return _status(
            "task_in_progress",
            f"{_pluralize(task_in_progress, 'task')} in progress",
            driver="task",
            severity="active",
            active=True,
        )
    if escalation_at_risk > 0:
        return _status(
            "escalation_at_risk",
            f"{_pluralize(escalation_at_risk, 'escalation')} at risk",
            driver="escalation",
            severity="urgent",
            active=True,
        )
    if task_open > 0:
        return _status(
            "task_open",
            f"{_pluralize(task_open, 'open task')}",
            driver="task",
            severity="active",
            active=True,
        )
    if escalation_open > 0:
        return _status(
            "escalation_open",
            f"{_pluralize(escalation_open, 'escalation')} active",
            driver="escalation",
            severity="active",
            active=True,
        )
    return _status(
        "monitoring_stable",
        "Monitoring",
        driver="monitoring",
        severity="stable",
        active=False,
    )


def _timeline_sort_key(item: TimelineItemPayload) -> Tuple[datetime, str]:
    return (
        _normalize_datetime(item["occurred_at"]),
        item["event_id"],
    )


def _summary_item_from_event(event: TimelineItemPayload) -> InterventionEvidenceSummaryItem:
    return InterventionEvidenceSummaryItem(
        title=event["display_title"],
        status=event.get("status"),
        occurred_at=event["occurred_at"],
        detail=event.get("display_text"),
    )


def _is_intervention_summary_open_work_item(
    item: TimelineItemPayload,
    task_status_index: Dict[UUID, str],
    escalation_status_index: Dict[UUID, str],
) -> bool:
    related_task_id = item.get("related_task_id")
    if related_task_id is not None:
        return task_status_index.get(related_task_id) in OPEN_TASK_STATUS_VALUES

    related_escalation_id = item.get("related_escalation_id")
    if related_escalation_id is not None:
        return escalation_status_index.get(related_escalation_id) in UNRESOLVED_ESCALATION_STATUS_VALUES

    return False


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


def get_due_state_reference_time() -> datetime:
    """Central hook for computing the reference time used in due-state calculations."""
    return datetime.now(timezone.utc)


def get_escalation_sla_reference_time() -> datetime:
    """Central hook for computing the reference time used in escalation SLA calculations."""
    return datetime.now(timezone.utc)
