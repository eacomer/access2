from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_request_context
from app.core.context import RequestContext
from pydantic import ValidationError
from app.schemas.patient_timeline import (
    PatientTimelineDetailResponse,
    PatientTimelineFilterParams,
    PatientTimelineInboxSummaryResponse,
    PatientTimelineWorklistSummaryResponse,
    PatientTimelineListResponse,
    PatientTimelineFilterSnapshotResponse,
    PatientTimelineReadStateResponse,
    PatientTimelineReadStateUpdateRequest,
    PatientTimelineSinceResponse,
    PatientTimelineSummaryResponse,
    PatientTimelineTargetedMarkReadRequest,
    PatientTimelineWorkflowSummaryResponse,
)
from app.services.authz import OrganizationAccessError
from app.services.patient_service import PatientNotFoundError, get_patient_by_id
from app.services.patient_timeline_service import (
    PatientTimelineContextMismatchError,
    PatientTimelineContextNotFoundError,
    PatientTimelineEventNotFoundError,
    build_patient_escalation_evidence,
    build_patient_attention_summary,
    build_patient_task_summary,
    build_intervention_evidence_summary,
    derive_workflow_status_summary,
    get_patient_timeline_event,
    list_patient_timeline_events,
    list_patient_timeline_events_since,
    summarize_patient_timeline_events,
)
from app.services.patient_timeline_read_state_service import (
    build_blocking_issue_label,
    build_care_gap_label,
    build_closure_readiness_label,
    build_operational_status_snapshot,
    build_resolution_confidence_label,
    build_resolution_target_label,
    build_workflow_ownership_labels,
    get_patient_timeline_filter_snapshot,
    get_patient_timeline_inbox_summary,
    get_patient_timeline_filtered_read_state,
    get_patient_timeline_read_state,
    list_patient_timeline_worklist_summaries,
    mark_patient_timeline_through_event,
    mark_patient_timeline_through_filtered_event,
    mark_patient_timeline_all_read,
    PatientTimelineFilteredEventVisibilityError,
    update_patient_timeline_read_state,
)
from app.services.patient_timeline_workflow_summary_service import (
    get_patient_timeline_workflow_summary,
)

router = APIRouter(prefix="/patients", tags=["patient-timeline"])


def _parse_timeline_filters(
    event_types: list[str] | None = Query(default=None, description="Filter by event types."),
    occurred_after: datetime | None = Query(default=None, description="ISO timestamp lower bound."),
    occurred_before: datetime | None = Query(default=None, description="ISO timestamp upper bound."),
    related_escalation_id: UUID | None = Query(default=None, description="Filter by escalation id."),
    related_task_id: UUID | None = Query(default=None, description="Filter by task id."),
    task_statuses: list[str] | None = Query(
        default=None,
        description="Filter task-related events by intervention task statuses.",
    ),
    include_only_open_work: bool = Query(
        default=False,
        description="Return only events tied to unresolved escalations or open tasks.",
    ),
) -> PatientTimelineFilterParams:
    try:
        return PatientTimelineFilterParams(
            event_types=event_types,
            occurred_after=occurred_after,
            occurred_before=occurred_before,
            related_escalation_id=related_escalation_id,
            related_task_id=related_task_id,
            task_statuses=task_statuses,
            include_only_open_work=include_only_open_work,
        )
    except (ValueError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )


def _parse_workflow_summary_filters(
    related_escalation_id: UUID | None = Query(default=None, description="Scope to escalation context."),
    related_task_id: UUID | None = Query(default=None, description="Scope to task context."),
    include_only_open_work: bool = Query(
        default=False,
        description="Restrict workflow summary to open escalation/task work.",
    ),
) -> PatientTimelineFilterParams:
    try:
        return PatientTimelineFilterParams(
            related_escalation_id=related_escalation_id,
            related_task_id=related_task_id,
            include_only_open_work=include_only_open_work,
        )
    except (ValueError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )


@router.get(
    "/timeline/worklist-summary",
    response_model=PatientTimelineWorklistSummaryResponse,
)
def get_patient_timeline_worklist_summary_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    has_unread_events: bool | None = Query(default=None),
    patient_ids: list[UUID] | None = Query(default=None),
    active_only: bool = Query(default=False),
    filters: PatientTimelineFilterParams = Depends(_parse_timeline_filters),
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PatientTimelineWorklistSummaryResponse:
    try:
        summaries = list_patient_timeline_worklist_summaries(
            db=db,
            context=context,
            filters=filters.to_service_filters(),
            has_unread_events=has_unread_events,
            patient_ids=tuple(patient_ids) if patient_ids else None,
            active_only=active_only,
            skip=skip,
            limit=limit,
        )
    except PatientTimelineContextNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PatientTimelineContextMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return PatientTimelineWorklistSummaryResponse(**summaries)


@router.get(
    "/{patient_id}/timeline",
    response_model=PatientTimelineListResponse,
)
def list_patient_timeline_endpoint(
    patient_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    cursor_occurred_at: datetime | None = Query(
        default=None,
        description="Return items older than this occurred_at timestamp. Must be paired with cursor_event_id.",
    ),
    cursor_event_id: str | None = Query(
        default=None,
        description="Return items older than this event id. Must be paired with cursor_occurred_at.",
    ),
    filters: PatientTimelineFilterParams = Depends(_parse_timeline_filters),
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PatientTimelineListResponse:
    if (cursor_occurred_at is None) != (cursor_event_id is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="cursor_occurred_at and cursor_event_id must be provided together.",
        )

    patient = _get_patient_or_error(db=db, context=context, patient_id=patient_id)
    try:
        result = list_patient_timeline_events(
            db=db,
            context=context,
            patient=patient,
            limit=limit,
            cursor_occurred_at=cursor_occurred_at,
            cursor_event_id=cursor_event_id,
            filters=filters.to_service_filters(),
        )
    except PatientTimelineContextNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PatientTimelineContextMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return PatientTimelineListResponse(**result)


@router.get(
    "/{patient_id}/timeline/since",
    response_model=PatientTimelineSinceResponse,
)
def list_patient_timeline_since_endpoint(
    patient_id: UUID,
    since: datetime = Query(
        ...,
        description="Return timeline items newer than this timestamp.",
    ),
    limit: int = Query(50, ge=1, le=200),
    filters: PatientTimelineFilterParams = Depends(_parse_timeline_filters),
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PatientTimelineSinceResponse:
    patient = _get_patient_or_error(db=db, context=context, patient_id=patient_id)
    try:
        result = list_patient_timeline_events_since(
            db=db,
            context=context,
            patient=patient,
            since=since,
            limit=limit,
            filters=filters.to_service_filters(),
        )
    except PatientTimelineContextNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PatientTimelineContextMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return PatientTimelineSinceResponse(**result)


@router.get(
    "/{patient_id}/timeline/summary",
    response_model=PatientTimelineSummaryResponse,
)
def summarize_patient_timeline_endpoint(
    patient_id: UUID,
    filters: PatientTimelineFilterParams = Depends(_parse_timeline_filters),
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PatientTimelineSummaryResponse:
    patient = _get_patient_or_error(db=db, context=context, patient_id=patient_id)
    try:
        summary = summarize_patient_timeline_events(
            db=db,
            context=context,
            patient=patient,
            filters=filters.to_service_filters(),
        )
    except PatientTimelineContextNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PatientTimelineContextMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return PatientTimelineSummaryResponse(**summary)


@router.get(
    "/{patient_id}/timeline/workflow-summary",
    response_model=PatientTimelineWorkflowSummaryResponse,
)
def get_patient_timeline_workflow_summary_endpoint(
    patient_id: UUID,
    filters: PatientTimelineFilterParams = Depends(_parse_workflow_summary_filters),
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PatientTimelineWorkflowSummaryResponse:
    patient = _get_patient_or_error(db=db, context=context, patient_id=patient_id)
    try:
        summary = get_patient_timeline_workflow_summary(
            db=db,
            context=context,
            patient=patient,
            filters=filters.to_service_filters(),
        )
    except PatientTimelineContextNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PatientTimelineContextMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return PatientTimelineWorkflowSummaryResponse(**summary)


@router.get(
    "/{patient_id}/timeline/read-state",
    response_model=PatientTimelineReadStateResponse,
)
def get_patient_timeline_read_state_endpoint(
    patient_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PatientTimelineReadStateResponse:
    patient = _get_patient_or_error(db=db, context=context, patient_id=patient_id)
    result = get_patient_timeline_read_state(
        db=db,
        context=context,
        patient=patient,
    )
    return PatientTimelineReadStateResponse(**result)


@router.get(
    "/{patient_id}/timeline/read-state/filtered",
    response_model=PatientTimelineReadStateResponse,
)
def get_patient_timeline_filtered_read_state_endpoint(
    patient_id: UUID,
    filters: PatientTimelineFilterParams = Depends(_parse_timeline_filters),
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PatientTimelineReadStateResponse:
    patient = _get_patient_or_error(db=db, context=context, patient_id=patient_id)
    try:
        result = get_patient_timeline_filtered_read_state(
            db=db,
            context=context,
            patient=patient,
            filters=filters.to_service_filters(),
        )
    except PatientTimelineContextNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PatientTimelineContextMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return PatientTimelineReadStateResponse(**result)


@router.get(
    "/{patient_id}/timeline/read-state/filtered/preview",
    response_model=PatientTimelineReadStateResponse,
)
def preview_patient_timeline_filtered_read_state_endpoint(
    patient_id: UUID,
    filters: PatientTimelineFilterParams = Depends(_parse_timeline_filters),
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PatientTimelineReadStateResponse:
    patient = _get_patient_or_error(db=db, context=context, patient_id=patient_id)
    try:
        result = get_patient_timeline_filtered_read_state(
            db=db,
            context=context,
            patient=patient,
            filters=filters.to_service_filters(),
        )
    except PatientTimelineContextNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PatientTimelineContextMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return PatientTimelineReadStateResponse(**result)


@router.get(
    "/{patient_id}/timeline/filter-set/snapshot",
    response_model=PatientTimelineFilterSnapshotResponse,
)
def get_patient_timeline_filter_snapshot_endpoint(
    patient_id: UUID,
    filters: PatientTimelineFilterParams = Depends(_parse_timeline_filters),
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PatientTimelineFilterSnapshotResponse:
    patient = _get_patient_or_error(db=db, context=context, patient_id=patient_id)
    try:
        snapshot = get_patient_timeline_filter_snapshot(
            db=db,
            context=context,
        patient=patient,
        filters=filters.to_service_filters(),
    )
    except PatientTimelineContextNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PatientTimelineContextMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return PatientTimelineFilterSnapshotResponse(**snapshot)


@router.get(
    "/{patient_id}/timeline/inbox-summary",
    response_model=PatientTimelineInboxSummaryResponse,
)
def get_patient_timeline_inbox_summary_endpoint(
    patient_id: UUID,
    filters: PatientTimelineFilterParams = Depends(_parse_timeline_filters),
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PatientTimelineInboxSummaryResponse:
    patient = _get_patient_or_error(db=db, context=context, patient_id=patient_id)
    try:
        summary = get_patient_timeline_inbox_summary(
            db=db,
            context=context,
            patient=patient,
            filters=filters.to_service_filters(),
        )
    except PatientTimelineContextNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PatientTimelineContextMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return PatientTimelineInboxSummaryResponse(**summary)


@router.put(
    "/{patient_id}/timeline/read-state",
    response_model=PatientTimelineReadStateResponse,
)
def update_patient_timeline_read_state_endpoint(
    patient_id: UUID,
    payload: PatientTimelineReadStateUpdateRequest,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PatientTimelineReadStateResponse:
    patient = _get_patient_or_error(db=db, context=context, patient_id=patient_id)
    try:
        result = update_patient_timeline_read_state(
            db=db,
            context=context,
            patient=patient,
            event_id=payload.last_read_event_id,
        )
    except PatientTimelineEventNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Timeline event not found for this patient.",
        )
    return PatientTimelineReadStateResponse(**result)


@router.post(
    "/{patient_id}/timeline/read-state/mark-through",
    response_model=PatientTimelineReadStateResponse,
)
def mark_patient_timeline_through_event_endpoint(
    patient_id: UUID,
    payload: PatientTimelineTargetedMarkReadRequest,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PatientTimelineReadStateResponse:
    patient = _get_patient_or_error(db=db, context=context, patient_id=patient_id)
    try:
        result = mark_patient_timeline_through_event(
            db=db,
            context=context,
            patient=patient,
            event_id=payload.event_id,
        )
    except PatientTimelineEventNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Timeline event not found for this patient.",
        )
    return PatientTimelineReadStateResponse(**result)


@router.post(
    "/{patient_id}/timeline/read-state/filtered/mark-through",
    response_model=PatientTimelineReadStateResponse,
)
def mark_patient_timeline_through_filtered_event_endpoint(
    patient_id: UUID,
    payload: PatientTimelineTargetedMarkReadRequest,
    filters: PatientTimelineFilterParams = Depends(_parse_timeline_filters),
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PatientTimelineReadStateResponse:
    patient = _get_patient_or_error(db=db, context=context, patient_id=patient_id)
    try:
        result = mark_patient_timeline_through_filtered_event(
            db=db,
            context=context,
            patient=patient,
            event_id=payload.event_id,
            filters=filters.to_service_filters(),
        )
    except PatientTimelineEventNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Timeline event not found for this patient.",
        )
    except PatientTimelineContextNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PatientTimelineContextMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except PatientTimelineFilteredEventVisibilityError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return PatientTimelineReadStateResponse(**result)


@router.post(
    "/{patient_id}/timeline/read-state/mark-all-read",
    response_model=PatientTimelineReadStateResponse,
)
def mark_all_patient_timeline_events_read_endpoint(
    patient_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PatientTimelineReadStateResponse:
    patient = _get_patient_or_error(db=db, context=context, patient_id=patient_id)
    result = mark_patient_timeline_all_read(
        db=db,
        context=context,
        patient=patient,
    )
    return PatientTimelineReadStateResponse(**result)


@router.get(
    "/{patient_id}/timeline/{event_id}",
    response_model=PatientTimelineDetailResponse,
)
def get_patient_timeline_event_endpoint(
    patient_id: UUID,
    event_id: str,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PatientTimelineDetailResponse:
    patient = _get_patient_or_error(db=db, context=context, patient_id=patient_id)

    try:
        item = get_patient_timeline_event(
            db=db,
            context=context,
            patient=patient,
            event_id=event_id,
        )
    except PatientTimelineEventNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timeline event not found.",
        )

    evidence = build_patient_escalation_evidence(
        db=db,
        context=context,
        patient=patient,
    )
    task_summary = build_patient_task_summary(
        db=db,
        context=context,
        patient=patient,
    )
    workflow_status = derive_workflow_status_summary(
        task_summary=task_summary,
        escalation_evidence=evidence,
    )
    intervention_evidence_summary = build_intervention_evidence_summary(
        db=db,
        context=context,
        patient=patient,
    )
    attention_summary = build_patient_attention_summary(
        escalation_evidence=evidence,
        task_summary=task_summary,
        workflow_status=workflow_status,
        intervention_evidence_summary=intervention_evidence_summary,
    )
    status_snapshot = build_operational_status_snapshot(
        attention_summary=attention_summary,
        task_summary=task_summary,
    )
    care_gap_label = build_care_gap_label(attention_summary=attention_summary)
    blocking_issue_label = build_blocking_issue_label(attention_summary=attention_summary)
    resolution_target_label = build_resolution_target_label(attention_summary=attention_summary)
    closure_readiness_label = build_closure_readiness_label(attention_summary=attention_summary)
    resolution_confidence_label = build_resolution_confidence_label(attention_summary=attention_summary)
    ownership_labels = build_workflow_ownership_labels(
        task_summary=task_summary,
        open_escalation_count=evidence.open_escalation_count,
        completed_task_count=intervention_evidence_summary.completed_tasks,
    )

    return PatientTimelineDetailResponse(
        item=item,
        escalation_evidence=evidence.as_dict(),
        task_summary=task_summary.as_dict(),
        workflow_status=workflow_status.as_dict(),
        intervention_evidence_summary=intervention_evidence_summary.as_dict(),
        attention_summary=attention_summary.as_dict(),
        status_snapshot=status_snapshot,
        care_gap_label=care_gap_label,
        blocking_issue_label=blocking_issue_label,
        resolution_target_label=resolution_target_label,
        closure_readiness_label=closure_readiness_label,
        resolution_confidence_label=resolution_confidence_label,
        **ownership_labels,
    )


def _get_patient_or_error(
    *,
    db: Session,
    context: RequestContext,
    patient_id: UUID,
):
    try:
        return get_patient_by_id(db=db, context=context, patient_id=patient_id)
    except PatientNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found.",
        )
    except OrganizationAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
