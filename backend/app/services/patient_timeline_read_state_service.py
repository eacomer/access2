from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Iterable, Sequence

from sqlalchemy import (
    String,
    and_,
    case,
    cast,
    func,
    literal,
    or_,
    select,
    union_all,
)
from sqlalchemy.orm import Session

from app.core.context import RequestContext
from app.models.patient import Patient
from app.models.care_update import CareUpdate
from app.models.intervention_task import InterventionTask
from app.models.intervention_task_outcome import InterventionTaskOutcome
from app.models.patient_signal import PatientEscalation, PatientEscalationStatusEvent, PatientSignal
from app.models.patient_timeline_read_state import PatientTimelineReadState
from app.services.authz import ensure_tenant_scoped_resource
from app.services.patient_timeline_service import (
    EVENT_TYPE_CARE_UPDATE,
    EVENT_TYPE_ESCALATION,
    EVENT_TYPE_ESCALATION_STATUS,
    EVENT_TYPE_SIGNAL,
    EVENT_TYPE_TASK_CREATED,
    EVENT_TYPE_TASK_OUTCOME,
    OPEN_TASK_STATUS_VALUES,
    UNRESOLVED_ESCALATION_STATUS_VALUES,
    PatientTimelineContextMismatchError,
    PatientTimelineContextNotFoundError,
    PatientTimelineFilters,
    TimelineItemPayload,
    compare_timeline_positions,
    get_patient_timeline_event,
    get_sorted_patient_timeline_events,
    timeline_event_matches_filters,
    validate_patient_timeline_filters,
)


class PatientTimelineReadStateError(Exception):
    """Base error for patient timeline read-state failures."""


class PatientTimelineFilteredEventVisibilityError(PatientTimelineReadStateError):
    """Raised when a targeted mark-read event is not present in the filtered subset."""


DEFAULT_SORT_TIMESTAMP = datetime(1970, 1, 1, tzinfo=timezone.utc)


def get_patient_timeline_read_state(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
) -> dict:
    ensure_tenant_scoped_resource(context=context, resource=patient)
    events = get_sorted_patient_timeline_events(db=db, context=context, patient=patient)
    state = _load_read_state(
        db=db,
        organization_id=patient.organization_id,
        patient_id=patient.id,
        user_id=context.user.id,
    )
    return _build_response(
        patient=patient,
        user_id=context.user.id,
        events=events,
        state=state,
    )


def get_patient_timeline_filtered_read_state(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
    filters: PatientTimelineFilters | None = None,
) -> dict:
    ensure_tenant_scoped_resource(context=context, resource=patient)
    events = get_sorted_patient_timeline_events(
        db=db,
        context=context,
        patient=patient,
        filters=filters,
    )
    state = _load_read_state(
        db=db,
        organization_id=patient.organization_id,
        patient_id=patient.id,
        user_id=context.user.id,
    )
    return _build_response(
        patient=patient,
        user_id=context.user.id,
        events=events,
        state=state,
    )


def update_patient_timeline_read_state(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
    event_id: str,
) -> dict:
    ensure_tenant_scoped_resource(context=context, resource=patient)
    event_payload = _resolve_timeline_event(
        db=db,
        context=context,
        patient=patient,
        event_id=event_id,
    )
    return _persist_marker_and_build_response(
        db=db,
        context=context,
        patient=patient,
        event_payload=event_payload,
    )


def mark_patient_timeline_through_event(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
    event_id: str,
) -> dict:
    return _mark_patient_timeline_through_event(
        db=db,
        context=context,
        patient=patient,
        event_id=event_id,
        filters=None,
        require_filtered_visibility=False,
    )


def mark_patient_timeline_through_filtered_event(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
    event_id: str,
    filters: PatientTimelineFilters | None = None,
) -> dict:
    return _mark_patient_timeline_through_event(
        db=db,
        context=context,
        patient=patient,
        event_id=event_id,
        filters=filters,
        require_filtered_visibility=True,
    )


def _mark_patient_timeline_through_event(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
    event_id: str,
    filters: PatientTimelineFilters | None,
    require_filtered_visibility: bool,
) -> dict:
    ensure_tenant_scoped_resource(context=context, resource=patient)

    event_payload = _resolve_timeline_event(
        db=db,
        context=context,
        patient=patient,
        event_id=event_id,
    )

    if require_filtered_visibility:
        if filters is None:
            raise PatientTimelineFilteredEventVisibilityError("Filters are required for filtered visibility checks.")
        _ensure_event_visible_in_filters(
            db=db,
            patient=patient,
            event_payload=event_payload,
            filters=filters,
        )

    return _persist_marker_and_build_response(
        db=db,
        context=context,
        patient=patient,
        event_payload=event_payload,
    )


def mark_patient_timeline_all_read(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
) -> dict:
    ensure_tenant_scoped_resource(context=context, resource=patient)
    events = get_sorted_patient_timeline_events(db=db, context=context, patient=patient)

    if events:
        newest_event = events[0]
        state = _save_read_state(
            db=db,
            patient=patient,
            user_id=context.user.id,
            event=newest_event,
        )
    else:
        state = _save_read_state(
            db=db,
            patient=patient,
            user_id=context.user.id,
            event=None,
        )

    return _build_response(
        patient=patient,
        user_id=context.user.id,
        events=events,
        state=state,
    )


def get_patient_timeline_filter_snapshot(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
    filters: PatientTimelineFilters | None = None,
) -> dict:
    ensure_tenant_scoped_resource(context=context, resource=patient)
    events = get_sorted_patient_timeline_events(
        db=db,
        context=context,
        patient=patient,
        filters=filters,
    )
    state = _load_read_state(
        db=db,
        organization_id=patient.organization_id,
        patient_id=patient.id,
        user_id=context.user.id,
    )
    newest = events[0] if events else None
    oldest = events[-1] if events else None
    unread_count = _calculate_unread_count(
        events=events,
        last_read_event_id=state.last_read_event_id if state else None,
        last_read_occurred_at=state.last_read_occurred_at if state else None,
    )
    return {
        "patient_id": patient.id,
        "total": len(events),
        "unread_count": unread_count,
        "newest_event_id": newest["event_id"] if newest else None,
        "newest_event_occurred_at": newest["occurred_at"] if newest else None,
        "oldest_event_id": oldest["event_id"] if oldest else None,
        "oldest_event_occurred_at": oldest["occurred_at"] if oldest else None,
        "latest_workflow_event_id": newest["event_id"] if newest else None,
        "latest_workflow_event_type": newest["event_type"] if newest else None,
        "latest_workflow_event_occurred_at": newest["occurred_at"] if newest else None,
    }


def get_patient_timeline_inbox_summary(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
    filters: PatientTimelineFilters | None = None,
) -> dict:
    ensure_tenant_scoped_resource(context=context, resource=patient)
    events = get_sorted_patient_timeline_events(
        db=db,
        context=context,
        patient=patient,
        filters=filters,
    )
    events_list = list(events)
    state = _load_read_state(
        db=db,
        organization_id=patient.organization_id,
        patient_id=patient.id,
        user_id=context.user.id,
    )
    return _build_inbox_summary_payload(
        patient=patient,
        events=events_list,
        state=state,
    )


def list_patient_timeline_worklist_summaries(
    db: Session,
    *,
    context: RequestContext,
    filters: PatientTimelineFilters | None = None,
    has_unread_events: bool | None = None,
    patient_ids: Sequence[uuid.UUID] | None = None,
    active_only: bool = False,
    skip: int = 0,
    limit: int = 50,
) -> dict:
    scoped_filters = filters
    derived_patient_id = _resolve_patient_scope_from_filters(
        db=db,
        context=context,
        filters=scoped_filters,
    )

    requested_patient_ids = tuple(dict.fromkeys(patient_ids or [])) if patient_ids else None
    effective_patient_ids: Sequence[uuid.UUID] | None = requested_patient_ids
    if derived_patient_id is not None:
        if effective_patient_ids is None:
            effective_patient_ids = (derived_patient_id,)
        else:
            effective_patient_ids = tuple(pid for pid in effective_patient_ids if pid == derived_patient_id)
    if effective_patient_ids is not None and len(effective_patient_ids) == 0:
        return {"items": [], "total": 0}

    page_rows, total = _fetch_worklist_patient_rows(
        db=db,
        context=context,
        filters=scoped_filters,
        has_unread_events=has_unread_events,
        patient_ids=effective_patient_ids,
        active_only=active_only,
        skip=skip,
        limit=limit,
    )

    if not page_rows:
        return {"items": [], "total": total}

    patient_map = _load_patients_by_ids(db=db, patient_ids=[row["patient_id"] for row in page_rows])
    state_map = _load_read_states_for_patients(
        db=db,
        organization_id=context.organization_id,
        patient_ids=list(patient_map.keys()),
        user_id=context.user.id,
    )

    items: list[dict] = []
    for row in page_rows:
        patient = patient_map.get(row["patient_id"])
        if patient is None:
            continue
        events = get_sorted_patient_timeline_events(
            db=db,
            context=context,
            patient=patient,
            filters=scoped_filters,
        )
        payload = _build_inbox_summary_payload(
            patient=patient,
            events=list(events),
            state=state_map.get(patient.id),
        )
        items.append(
            {
                **payload,
                "patient_display_name": f"{patient.first_name} {patient.last_name}",
            }
        )

    return {"items": items, "total": total}


def _load_read_state(
    db: Session,
    *,
    organization_id: uuid.UUID,
    patient_id: uuid.UUID,
    user_id: uuid.UUID,
) -> PatientTimelineReadState | None:
    stmt = (
        select(PatientTimelineReadState)
        .where(
            PatientTimelineReadState.organization_id == organization_id,
            PatientTimelineReadState.patient_id == patient_id,
            PatientTimelineReadState.user_id == user_id,
        )
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def _resolve_timeline_event(
    *,
    db: Session,
    context: RequestContext,
    patient: Patient,
    event_id: str,
) -> TimelineItemPayload:
    return get_patient_timeline_event(
        db=db,
        context=context,
        patient=patient,
        event_id=event_id,
    )


def _save_read_state(
    db: Session,
    *,
    patient: Patient,
    user_id: uuid.UUID,
    event: TimelineItemPayload | None,
) -> PatientTimelineReadState:
    state = _load_read_state(
        db=db,
        organization_id=patient.organization_id,
        patient_id=patient.id,
        user_id=user_id,
    )
    if state is None:
        state = PatientTimelineReadState(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            user_id=user_id,
        )

    if event is None:
        state.last_read_event_id = None
        state.last_read_occurred_at = None
    else:
        state.last_read_event_id = event["event_id"]
        state.last_read_occurred_at = event["occurred_at"]

    db.add(state)
    db.commit()
    db.refresh(state)
    return state


def _load_read_states_for_patients(
    db: Session,
    *,
    organization_id: uuid.UUID,
    patient_ids: Sequence[uuid.UUID],
    user_id: uuid.UUID,
) -> dict[uuid.UUID, PatientTimelineReadState]:
    unique_ids = list({patient_id for patient_id in patient_ids})
    if not unique_ids:
        return {}
    stmt = (
        select(PatientTimelineReadState)
        .where(
            PatientTimelineReadState.organization_id == organization_id,
            PatientTimelineReadState.user_id == user_id,
            PatientTimelineReadState.patient_id.in_(unique_ids),
        )
    )
    rows = db.execute(stmt).scalars().all()
    return {row.patient_id: row for row in rows}


def _persist_marker_and_build_response(
    *,
    db: Session,
    context: RequestContext,
    patient: Patient,
    event_payload: TimelineItemPayload | None,
) -> dict:
    ensure_tenant_scoped_resource(context=context, resource=patient)
    state = _save_read_state(
        db=db,
        patient=patient,
        user_id=context.user.id,
        event=event_payload,
    )
    events = get_sorted_patient_timeline_events(db=db, context=context, patient=patient)
    return _build_response(
        patient=patient,
        user_id=context.user.id,
        events=events,
        state=state,
    )


def _build_response(
    *,
    patient: Patient,
    user_id: uuid.UUID,
    events: Iterable[TimelineItemPayload],
    state: PatientTimelineReadState | None,
) -> dict:
    events_list = list(events)
    newest_event = events_list[0] if events_list else None
    last_read_event_id = state.last_read_event_id if state else None
    last_read_occurred_at = state.last_read_occurred_at if state else None
    unread_count = _calculate_unread_count(
        events=events_list,
        last_read_event_id=last_read_event_id,
        last_read_occurred_at=last_read_occurred_at,
    )

    return {
        "patient_id": patient.id,
        "user_id": user_id,
        "last_read_event_id": last_read_event_id,
        "last_read_occurred_at": last_read_occurred_at,
        "unread_count": unread_count,
        "newest_event_id": newest_event["event_id"] if newest_event else None,
        "newest_event_occurred_at": newest_event["occurred_at"] if newest_event else None,
    }


def _calculate_unread_count(
    *,
    events: list[TimelineItemPayload],
    last_read_event_id: str | None,
    last_read_occurred_at: datetime | None,
) -> int:
    if not events:
        return 0
    if not last_read_event_id or not last_read_occurred_at:
        return len(events)
    for index, event in enumerate(events):
        comparison = compare_timeline_positions(
            item_occurred_at=event["occurred_at"],
            item_event_id=event["event_id"],
            reference_occurred_at=last_read_occurred_at,
            reference_event_id=last_read_event_id,
        )
        if comparison <= 0:
            return index
    return len(events)


def calculate_unread_count_for_events(
    *,
    events: Iterable[TimelineItemPayload],
    last_read_event_id: str | None,
    last_read_occurred_at: datetime | None,
) -> int:
    return _calculate_unread_count(
        events=list(events),
        last_read_event_id=last_read_event_id,
        last_read_occurred_at=last_read_occurred_at,
    )


def _build_inbox_summary_payload(
    *,
    patient: Patient,
    events: list[TimelineItemPayload],
    state: PatientTimelineReadState | None,
) -> dict:
    last_read_event_id = state.last_read_event_id if state else None
    last_read_occurred_at = state.last_read_occurred_at if state else None
    unread_count = _calculate_unread_count(
        events=events,
        last_read_event_id=last_read_event_id,
        last_read_occurred_at=last_read_occurred_at,
    )
    latest_event = events[0] if events else None
    latest_unread_event = events[0] if unread_count else None
    oldest_unread_event = events[unread_count - 1] if unread_count else None

    return {
        "patient_id": patient.id,
        "has_unread_events": unread_count > 0,
        "unread_count": unread_count,
        "total_events": len(events),
        "latest_event_id": latest_event["event_id"] if latest_event else None,
        "latest_event_type": latest_event["event_type"] if latest_event else None,
        "latest_event_occurred_at": latest_event["occurred_at"] if latest_event else None,
        "latest_event_title": latest_event["display_title"] if latest_event else None,
        "latest_unread_event_id": latest_unread_event["event_id"] if latest_unread_event else None,
        "latest_unread_event_type": latest_unread_event["event_type"] if latest_unread_event else None,
        "latest_unread_event_occurred_at": latest_unread_event["occurred_at"]
        if latest_unread_event
        else None,
        "oldest_unread_event_id": oldest_unread_event["event_id"] if oldest_unread_event else None,
        "oldest_unread_event_occurred_at": oldest_unread_event["occurred_at"]
        if oldest_unread_event
        else None,
    }


def _ensure_event_visible_in_filters(
    *,
    db: Session,
    patient: Patient,
    event_payload: TimelineItemPayload,
    filters: PatientTimelineFilters,
) -> None:
    context = validate_patient_timeline_filters(
        db=db,
        patient=patient,
        filters=filters,
    )
    if not timeline_event_matches_filters(
        db=db,
        patient=patient,
        event=event_payload,
        filters=filters,
        context=context,
    ):
        raise PatientTimelineFilteredEventVisibilityError(
            "Selected event is not included in the filtered subset."
        )


def _worklist_sort_payload_key(row: dict) -> tuple:
    key = row.get("_worklist_sort_key")
    if key is None:
        latest_sort_ts = _normalize_sort_timestamp(row.get("latest_event_occurred_at"))
        created_sort_ts = _normalize_sort_timestamp(row.get("_patient_created_at"))
        has_unread_value = 0 if row.get("has_unread_events") else 1
        return (
            has_unread_value,
            -latest_sort_ts.timestamp(),
            created_sort_ts.timestamp(),
            str(row.get("patient_id")),
        )
    return (
        0 if key[0] else 1,
        -_normalize_sort_timestamp(key[1]).timestamp(),
        _normalize_sort_timestamp(key[2]).timestamp(),
        key[3],
    )


def _normalize_sort_timestamp(value: datetime | None) -> datetime:
    if value is None:
        return DEFAULT_SORT_TIMESTAMP
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
def _resolve_patient_scope_from_filters(
    db: Session,
    *,
    context: RequestContext,
    filters: PatientTimelineFilters | None,
) -> uuid.UUID | None:
    if filters is None or (
        filters.related_escalation_id is None and filters.related_task_id is None
    ):
        return None

    escalation: PatientEscalation | None = None
    task: InterventionTask | None = None

    if filters.related_escalation_id is not None:
        escalation = db.get(PatientEscalation, filters.related_escalation_id)
        if escalation is None or escalation.organization_id != context.organization_id:
            raise PatientTimelineContextNotFoundError(
                "Escalation not found for this patient."
            )

    if filters.related_task_id is not None:
        task = db.get(InterventionTask, filters.related_task_id)
        if task is None or task.organization_id != context.organization_id:
            raise PatientTimelineContextNotFoundError(
                "Intervention task not found for this patient."
            )

    if escalation and task and task.escalation_id != escalation.id:
        raise PatientTimelineContextMismatchError(
            "Intervention task does not belong to the specified escalation."
        )

    if task is not None:
        return task.patient_id
    if escalation is not None:
        return escalation.patient_id
    return None


def _fetch_worklist_patient_rows(
    *,
    db: Session,
    context: RequestContext,
    filters: PatientTimelineFilters | None,
    has_unread_events: bool | None,
    patient_ids: Sequence[uuid.UUID] | None,
    active_only: bool,
    skip: int,
    limit: int,
) -> tuple[list[dict], int]:
    normalized_skip = max(skip, 0)
    normalized_limit = max(1, limit)

    base_stmt = (
        select(
            Patient.id.label("patient_id"),
            Patient.created_at.label("patient_created_at"),
        )
        .where(Patient.organization_id == context.organization_id)
    )
    if patient_ids:
        base_stmt = base_stmt.where(Patient.id.in_(tuple(patient_ids)))
    if active_only:
        base_stmt = base_stmt.where(Patient.is_active.is_(True))

    patient_cte = base_stmt.cte("worklist_patients")

    events_stmt = _build_filtered_events_statement(
        context=context,
        filters=filters,
        allowed_patient_select=select(patient_cte.c.patient_id),
    ).cte("worklist_events")

    ranked_events = (
        select(
            events_stmt.c.patient_id,
            events_stmt.c.occurred_at,
            events_stmt.c.event_id,
            func.row_number()
            .over(
                partition_by=events_stmt.c.patient_id,
                order_by=(
                    events_stmt.c.occurred_at.desc(),
                    events_stmt.c.event_id.desc(),
                ),
            )
            .label("rank"),
        )
    ).cte("ranked_worklist_events")

    latest_events = (
        select(
            ranked_events.c.patient_id,
            ranked_events.c.occurred_at.label("latest_event_occurred_at"),
            ranked_events.c.event_id.label("latest_event_id"),
        )
        .where(ranked_events.c.rank == 1)
        .cte("latest_worklist_events")
    )

    read_state_subq = (
        select(
            PatientTimelineReadState.patient_id.label("rs_patient_id"),
            PatientTimelineReadState.last_read_event_id,
            PatientTimelineReadState.last_read_occurred_at,
        )
        .where(
            PatientTimelineReadState.organization_id == context.organization_id,
            PatientTimelineReadState.user_id == context.user.id,
        )
        .cte("worklist_read_states")
    )

    join_stmt = (
        select(
            patient_cte.c.patient_id,
            patient_cte.c.patient_created_at,
            latest_events.c.latest_event_id,
            latest_events.c.latest_event_occurred_at,
            read_state_subq.c.last_read_event_id,
            read_state_subq.c.last_read_occurred_at,
        )
        .select_from(patient_cte)
        .outerjoin(
            latest_events,
            patient_cte.c.patient_id == latest_events.c.patient_id,
        )
        .outerjoin(
            read_state_subq,
            patient_cte.c.patient_id == read_state_subq.c.rs_patient_id,
        )
    )

    join_subq = join_stmt.subquery()
    latest_ts = join_subq.c.latest_event_occurred_at
    latest_id = join_subq.c.latest_event_id
    last_read_ts = join_subq.c.last_read_occurred_at
    last_read_id = join_subq.c.last_read_event_id
    normalized_last_read_id = func.replace(last_read_id, literal("-"), literal(""))

    has_unread_expr = case(
        (latest_ts.is_(None), literal(False)),
        (
            or_(last_read_id.is_(None), last_read_ts.is_(None)),
            literal(True),
        ),
        (latest_ts > last_read_ts, literal(True)),
        (latest_ts < last_read_ts, literal(False)),
        (latest_id > normalized_last_read_id, literal(True)),
        else_=literal(False),
    ).label("has_unread_events")

    worklist_base = select(
        join_subq.c.patient_id,
        join_subq.c.patient_created_at,
        join_subq.c.latest_event_id,
        join_subq.c.latest_event_occurred_at,
        has_unread_expr,
    ).subquery()

    filtered_subq = worklist_base
    if has_unread_events is not None:
        filtered_subq = (
            select(worklist_base)
            .where(worklist_base.c.has_unread_events.is_(has_unread_events))
            .subquery()
        )

    sort_latest_ts = func.coalesce(
        filtered_subq.c.latest_event_occurred_at,
        literal(DEFAULT_SORT_TIMESTAMP),
    )
    sort_unread = case(
        (filtered_subq.c.has_unread_events.is_(True), literal(0)),
        else_=literal(1),
    )

    ordered_stmt = (
        select(filtered_subq)
        .order_by(
            sort_unread,
            sort_latest_ts.desc(),
            filtered_subq.c.patient_created_at.asc(),
            filtered_subq.c.patient_id.asc(),
        )
        .offset(normalized_skip)
        .limit(normalized_limit)
    )

    count_stmt = select(func.count()).select_from(filtered_subq)

    rows = db.execute(ordered_stmt).mappings().all()
    total = int(db.execute(count_stmt).scalar() or 0)
    return rows, total


def _build_filtered_events_statement(
    *,
    context: RequestContext,
    filters: PatientTimelineFilters | None,
    allowed_patient_select,
):
    signal_stmt = (
        select(
            PatientSignal.patient_id.label("patient_id"),
            PatientSignal.organization_id.label("organization_id"),
            PatientSignal.recorded_at.label("occurred_at"),
            func.concat(literal("signal:"), cast(PatientSignal.id, String)).label("event_id"),
            literal(EVENT_TYPE_SIGNAL).label("event_type"),
            PatientEscalation.id.label("related_escalation_id"),
            literal(None).label("related_task_id"),
            cast(PatientEscalation.status, String).label("related_escalation_status"),
            literal(None).label("related_task_status"),
        )
        .select_from(
            PatientSignal.__table__.outerjoin(
                PatientEscalation.__table__,
                PatientEscalation.signal_id == PatientSignal.id,
            )
        )
    )

    escalation_stmt = select(
        PatientEscalation.patient_id.label("patient_id"),
        PatientEscalation.organization_id.label("organization_id"),
        PatientEscalation.triggered_at.label("occurred_at"),
        func.concat(literal("escalation:"), cast(PatientEscalation.id, String)).label("event_id"),
        literal(EVENT_TYPE_ESCALATION).label("event_type"),
        PatientEscalation.id.label("related_escalation_id"),
        literal(None).label("related_task_id"),
        cast(PatientEscalation.status, String).label("related_escalation_status"),
        literal(None).label("related_task_status"),
    )

    escalation_status_stmt = (
        select(
            PatientEscalationStatusEvent.patient_id.label("patient_id"),
            PatientEscalationStatusEvent.organization_id.label("organization_id"),
            PatientEscalationStatusEvent.occurred_at.label("occurred_at"),
            func.concat(literal("escalation_status_event:"), cast(PatientEscalationStatusEvent.id, String)).label(
                "event_id"
            ),
            literal(EVENT_TYPE_ESCALATION_STATUS).label("event_type"),
            PatientEscalationStatusEvent.escalation_id.label("related_escalation_id"),
            literal(None).label("related_task_id"),
            cast(PatientEscalationStatusEvent.status, String).label("related_escalation_status"),
            literal(None).label("related_task_status"),
        )
    )

    task_stmt = (
        select(
            InterventionTask.patient_id.label("patient_id"),
            InterventionTask.organization_id.label("organization_id"),
            InterventionTask.created_at.label("occurred_at"),
            func.concat(literal("intervention_task:"), cast(InterventionTask.id, String)).label("event_id"),
            literal(EVENT_TYPE_TASK_CREATED).label("event_type"),
            InterventionTask.escalation_id.label("related_escalation_id"),
            InterventionTask.id.label("related_task_id"),
            cast(PatientEscalation.status, String).label("related_escalation_status"),
            cast(InterventionTask.status, String).label("related_task_status"),
        )
        .outerjoin(
            PatientEscalation,
            InterventionTask.escalation_id == PatientEscalation.id,
        )
    )

    outcome_stmt = (
        select(
            InterventionTaskOutcome.patient_id.label("patient_id"),
            InterventionTaskOutcome.organization_id.label("organization_id"),
            InterventionTaskOutcome.completed_at.label("occurred_at"),
            func.concat(literal("intervention_task_outcome:"), cast(InterventionTaskOutcome.id, String)).label(
                "event_id"
            ),
            literal(EVENT_TYPE_TASK_OUTCOME).label("event_type"),
            InterventionTaskOutcome.escalation_id.label("related_escalation_id"),
            InterventionTaskOutcome.intervention_task_id.label("related_task_id"),
            cast(PatientEscalation.status, String).label("related_escalation_status"),
            cast(InterventionTask.status, String).label("related_task_status"),
        )
        .outerjoin(
            InterventionTask,
            InterventionTaskOutcome.intervention_task_id == InterventionTask.id,
        )
        .outerjoin(
            PatientEscalation,
            InterventionTaskOutcome.escalation_id == PatientEscalation.id,
        )
    )

    care_update_stmt = (
        select(
            CareUpdate.patient_id.label("patient_id"),
            CareUpdate.organization_id.label("organization_id"),
            CareUpdate.occurred_at.label("occurred_at"),
            func.concat(literal("care_update:"), cast(CareUpdate.id, String)).label("event_id"),
            literal(EVENT_TYPE_CARE_UPDATE).label("event_type"),
            CareUpdate.escalation_id.label("related_escalation_id"),
            CareUpdate.intervention_task_id.label("related_task_id"),
            cast(PatientEscalation.status, String).label("related_escalation_status"),
            cast(InterventionTask.status, String).label("related_task_status"),
        )
        .outerjoin(
            InterventionTask,
            CareUpdate.intervention_task_id == InterventionTask.id,
        )
        .outerjoin(
            PatientEscalation,
            CareUpdate.escalation_id == PatientEscalation.id,
        )
    )

    timeline_union = union_all(
        signal_stmt,
        escalation_stmt,
        escalation_status_stmt,
        task_stmt,
        outcome_stmt,
        care_update_stmt,
    ).alias("unioned_timeline_events")

    stmt = select(timeline_union).where(
        timeline_union.c.organization_id == context.organization_id,
        timeline_union.c.patient_id.in_(allowed_patient_select),
    )

    if filters is not None:
        if filters.event_types:
            stmt = stmt.where(timeline_union.c.event_type.in_(tuple(filters.event_types)))
        if filters.occurred_after:
            stmt = stmt.where(timeline_union.c.occurred_at >= filters.occurred_after)
        if filters.occurred_before:
            stmt = stmt.where(timeline_union.c.occurred_at <= filters.occurred_before)
        if filters.related_escalation_id:
            stmt = stmt.where(
                timeline_union.c.related_escalation_id == filters.related_escalation_id
            )
        if filters.related_task_id:
            stmt = stmt.where(
                timeline_union.c.related_task_id == filters.related_task_id
            )
        if filters.task_statuses:
            stmt = stmt.where(
                and_(
                    timeline_union.c.related_task_id.is_not(None),
                    timeline_union.c.related_task_status.in_(tuple(filters.task_statuses)),
                )
            )
        if filters.include_only_open_work:
            stmt = stmt.where(
                or_(
                    and_(
                        timeline_union.c.related_task_id.is_not(None),
                        timeline_union.c.related_task_status.in_(OPEN_TASK_STATUS_VALUES),
                    ),
                    and_(
                        timeline_union.c.related_escalation_id.is_not(None),
                        timeline_union.c.related_escalation_status.in_(
                            UNRESOLVED_ESCALATION_STATUS_VALUES
                        ),
                    ),
                )
            )

    return stmt


def _load_patients_by_ids(
    *,
    db: Session,
    patient_ids: Sequence[uuid.UUID],
) -> dict[uuid.UUID, Patient]:
    unique_ids = list(dict.fromkeys(patient_ids))
    if not unique_ids:
        return {}
    stmt = select(Patient).where(Patient.id.in_(tuple(unique_ids)))
    rows = db.execute(stmt).scalars().all()
    return {row.id: row for row in rows}
