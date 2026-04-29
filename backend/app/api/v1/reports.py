from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_request_context
from app.core.context import RequestContext
from app.models.access_review_packet_snapshot import AccessReviewPacketSnapshotReviewStatus
from app.schemas.access_evidence import (
    AccessCaseSummaryResponse,
    AccessEvidenceResponse,
    AccessReviewPacketResponse,
    AccessReviewPacketSnapshotAuditBundleResponse,
    AccessReviewPacketAuditReadinessListResponse,
    AccessReviewPacketSnapshotAuditManifestVerifyRequest,
    AccessReviewPacketSnapshotAuditManifestVerifyResponse,
    AccessReviewPacketSnapshotAssignmentUpdateRequest,
    AccessReviewPacketSnapshotEventListResponse,
    AccessReviewPacketPatientAuditStatusResponse,
    AccessReviewPacketPatientDrillInResponse,
    AccessReviewPacketSnapshotPatientBacklogItem,
    AccessReviewPacketSnapshotQueueSummaryResponse,
    AccessReviewPacketReviewerSummaryResponse,
    AccessReviewPacketSnapshotResponse,
    AccessReviewPacketSnapshotSummaryResponse,
    AccessReviewPacketSnapshotReviewUpdateRequest,
)
from app.services.access_evidence_service import (
    AccessReviewPacketApprovalBlockedError,
    AccessReviewPacketAuditBundleConflictError,
    AccessReviewPacketApprovalOverrideAuthorizationError,
    build_access_case_summary,
    build_access_evidence_report,
    build_access_review_packet,
    build_access_review_packet_snapshot_audit_bundle_markdown_payload,
    build_access_review_packet_snapshot_export_metadata,
    create_access_review_packet_snapshot,
    enrich_access_review_packet_patient_backlog_items,
    get_access_review_packet_snapshot_audit_bundle,
    get_access_review_packet_patient_audit_status,
    get_access_review_packet_patient_drill_in,
    get_latest_access_review_packet_snapshot_for_patient_in_organization,
    get_access_review_packet_snapshot_by_id,
    list_access_review_packet_snapshot_events,
    list_access_review_packet_audit_readiness_for_organization,
    list_latest_actionable_access_review_packet_snapshots_for_organization,
    list_access_review_packet_snapshot_patient_backlog_for_organization,
    list_access_review_packet_snapshots,
    list_access_review_packet_snapshots_for_organization,
    render_access_review_packet_markdown,
    render_access_review_packet_audit_readiness_csv,
    render_access_review_packet_snapshot_audit_bundle_markdown,
    render_access_review_packet_snapshot_audit_bundle_pdf,
    record_access_review_packet_snapshot_audit_bundle_export,
    serialize_access_review_packet_snapshot,
    serialize_access_review_packet_snapshots,
    summarize_access_review_packet_snapshots,
    summarize_access_review_packet_snapshot_queue_for_organization,
    summarize_access_review_packet_snapshots_for_reviewer,
    summarize_access_review_packet_snapshots_for_organization,
    update_access_review_packet_snapshot_assignment,
    update_access_review_packet_snapshot_review,
    verify_access_review_packet_snapshot_audit_manifest,
)
from app.services.authz import OrganizationAccessError
from app.services.patient_service import PatientNotFoundError, get_patient_by_id

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/access-evidence/{patient_id}", response_model=AccessEvidenceResponse)
def get_access_evidence_endpoint(
    patient_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> AccessEvidenceResponse:
    try:
        patient = get_patient_by_id(db=db, context=context, patient_id=patient_id)
    except PatientNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    except OrganizationAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    return AccessEvidenceResponse(
        **build_access_evidence_report(db=db, context=context, patient=patient)
    )


@router.get("/access-case-summary/{patient_id}", response_model=AccessCaseSummaryResponse)
def get_access_case_summary_endpoint(
    patient_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> AccessCaseSummaryResponse:
    try:
        patient = get_patient_by_id(db=db, context=context, patient_id=patient_id)
    except PatientNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    except OrganizationAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    return AccessCaseSummaryResponse(
        **build_access_case_summary(db=db, context=context, patient=patient)
    )


@router.get(
    "/access-review-packet/snapshots/summary",
    response_model=AccessReviewPacketSnapshotSummaryResponse,
)
def get_access_review_packet_snapshot_organization_summary_endpoint(
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> AccessReviewPacketSnapshotSummaryResponse:
    return AccessReviewPacketSnapshotSummaryResponse(
        **summarize_access_review_packet_snapshots_for_organization(
            db=db,
            context=context,
        )
    )


@router.get(
    "/access-review-packet/snapshots/queue-summary",
    response_model=AccessReviewPacketSnapshotQueueSummaryResponse,
)
def get_access_review_packet_snapshot_queue_summary_endpoint(
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> AccessReviewPacketSnapshotQueueSummaryResponse:
    return AccessReviewPacketSnapshotQueueSummaryResponse(
        **summarize_access_review_packet_snapshot_queue_for_organization(
            db=db,
            context=context,
        )
    )


@router.get(
    "/access-review-packet/audit-readiness",
    response_model=AccessReviewPacketAuditReadinessListResponse,
)
def list_access_review_packet_audit_readiness_endpoint(
    completion_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> AccessReviewPacketAuditReadinessListResponse:
    if completion_status is not None and completion_status not in {
        "incomplete",
        "review_ready",
        "approved_not_exported",
        "audit_ready",
        "rejected",
    }:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid audit readiness status filter.",
        )
    return AccessReviewPacketAuditReadinessListResponse(
        **list_access_review_packet_audit_readiness_for_organization(
            db=db,
            context=context,
            completion_status=completion_status,
            limit=limit,
            offset=offset,
        )
    )


@router.get("/access-review-packet/audit-readiness/export.csv")
def export_access_review_packet_audit_readiness_csv_endpoint(
    completion_status: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> Response:
    if completion_status is not None and completion_status not in {
        "incomplete",
        "review_ready",
        "approved_not_exported",
        "audit_ready",
        "rejected",
    }:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid audit readiness status filter.",
        )
    payload = list_access_review_packet_audit_readiness_for_organization(
        db=db,
        context=context,
        completion_status=completion_status,
        limit=10_000,
        offset=0,
    )
    filename = "access-review-packet-audit-readiness.csv"
    if completion_status is not None:
        filename = f"access-review-packet-audit-readiness-{completion_status}.csv"
    return Response(
        content=render_access_review_packet_audit_readiness_csv(payload),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/access-review-packet/snapshots",
    response_model=list[AccessReviewPacketSnapshotResponse],
)
def list_access_review_packet_snapshots_for_organization_endpoint(
    review_status: AccessReviewPacketSnapshotReviewStatus | None = Query(default=None),
    review_readiness_status: str | None = Query(default=None),
    assigned_reviewer_user_id: UUID | None = Query(default=None),
    unassigned: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> list[AccessReviewPacketSnapshotResponse]:
    snapshots = list_access_review_packet_snapshots_for_organization(
        db=db,
        context=context,
        review_status=review_status,
        review_readiness_status=review_readiness_status,
        assigned_reviewer_user_id=assigned_reviewer_user_id,
        unassigned=unassigned,
        limit=limit,
        offset=offset,
    )
    return [
        AccessReviewPacketSnapshotResponse.model_validate(snapshot)
        for snapshot in serialize_access_review_packet_snapshots(
            db=db,
            context=context,
            snapshots=snapshots,
        )
    ]


@router.get(
    "/access-review-packet/snapshots/latest-actionable",
    response_model=list[AccessReviewPacketSnapshotResponse],
)
def list_latest_actionable_access_review_packet_snapshots_for_organization_endpoint(
    review_status: AccessReviewPacketSnapshotReviewStatus | None = Query(default=None),
    review_readiness_status: str | None = Query(default=None),
    assigned_reviewer_user_id: UUID | None = Query(default=None),
    unassigned: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> list[AccessReviewPacketSnapshotResponse]:
    snapshots = list_latest_actionable_access_review_packet_snapshots_for_organization(
        db=db,
        context=context,
        review_status=review_status,
        review_readiness_status=review_readiness_status,
        assigned_reviewer_user_id=assigned_reviewer_user_id,
        unassigned=unassigned,
        limit=limit,
        offset=offset,
    )
    return [
        AccessReviewPacketSnapshotResponse.model_validate(snapshot)
        for snapshot in serialize_access_review_packet_snapshots(
            db=db,
            context=context,
            snapshots=snapshots,
        )
    ]


@router.get(
    "/access-review-packet/snapshots/my-pending",
    response_model=list[AccessReviewPacketSnapshotResponse],
)
def list_my_pending_access_review_packet_snapshots_endpoint(
    review_readiness_status: str | None = Query(default=None),
    review_status: AccessReviewPacketSnapshotReviewStatus | None = Query(default=None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> list[AccessReviewPacketSnapshotResponse]:
    snapshots = list_access_review_packet_snapshots_for_organization(
        db=db,
        context=context,
        assigned_reviewer_user_id=context.user.id,
        review_status=review_status or AccessReviewPacketSnapshotReviewStatus.PENDING_REVIEW,
        review_readiness_status=review_readiness_status,
        limit=limit,
        offset=offset,
    )
    return [
        AccessReviewPacketSnapshotResponse.model_validate(snapshot)
        for snapshot in serialize_access_review_packet_snapshots(
            db=db,
            context=context,
            snapshots=snapshots,
        )
    ]


@router.get(
    "/access-review-packet/reviewer/my-summary",
    response_model=AccessReviewPacketReviewerSummaryResponse,
)
def get_access_review_packet_reviewer_summary_endpoint(
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> AccessReviewPacketReviewerSummaryResponse:
    return AccessReviewPacketReviewerSummaryResponse(
        **summarize_access_review_packet_snapshots_for_reviewer(
            db=db,
            context=context,
        )
    )


@router.get(
    "/access-review-packet/snapshots/patient-backlog",
    response_model=list[AccessReviewPacketSnapshotPatientBacklogItem],
)
def list_access_review_packet_snapshot_patient_backlog_endpoint(
    review_status: AccessReviewPacketSnapshotReviewStatus | None = Query(default=None),
    review_readiness_status: str | None = Query(default=None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> list[AccessReviewPacketSnapshotPatientBacklogItem]:
    backlog = list_access_review_packet_snapshot_patient_backlog_for_organization(
        db=db,
        context=context,
        review_status=review_status,
        review_readiness_status=review_readiness_status,
        limit=limit,
        offset=offset,
    )
    backlog = enrich_access_review_packet_patient_backlog_items(
        db=db,
        context=context,
        backlog_items=backlog,
    )
    return [
        AccessReviewPacketSnapshotPatientBacklogItem.model_validate(item)
        for item in backlog
    ]


@router.get(
    "/access-review-packet/snapshots/patient-backlog/{patient_id}",
    response_model=AccessReviewPacketPatientDrillInResponse,
)
def list_access_review_packet_snapshot_patient_backlog_detail_endpoint(
    patient_id: UUID,
    review_status: AccessReviewPacketSnapshotReviewStatus | None = Query(default=None),
    review_readiness_status: str | None = Query(default=None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> AccessReviewPacketPatientDrillInResponse:
    try:
        patient = get_patient_by_id(db=db, context=context, patient_id=patient_id)
    except PatientNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    except OrganizationAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    return AccessReviewPacketPatientDrillInResponse(
        **get_access_review_packet_patient_drill_in(
            db=db,
            context=context,
            patient=patient,
            review_status=review_status,
            review_readiness_status=review_readiness_status,
            limit=limit,
            offset=offset,
        )
    )


@router.get(
    "/access-review-packet/snapshots/patient-backlog/{patient_id}/latest",
    response_model=AccessReviewPacketSnapshotResponse,
)
def get_access_review_packet_snapshot_patient_backlog_latest_endpoint(
    patient_id: UUID,
    review_status: AccessReviewPacketSnapshotReviewStatus | None = Query(default=None),
    review_readiness_status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> AccessReviewPacketSnapshotResponse:
    try:
        patient = get_patient_by_id(db=db, context=context, patient_id=patient_id)
    except PatientNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    except OrganizationAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    snapshot = get_latest_access_review_packet_snapshot_for_patient_in_organization(
        db=db,
        context=context,
        patient_id=patient.id,
        review_status=review_status,
        review_readiness_status=review_readiness_status,
    )
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found.")

    return AccessReviewPacketSnapshotResponse.model_validate(
        serialize_access_review_packet_snapshot(
            db=db,
            context=context,
            snapshot=snapshot,
            include_audit_timeline=True,
        )
    )


@router.get("/access-review-packet/{patient_id}", response_model=AccessReviewPacketResponse)
def get_access_review_packet_endpoint(
    patient_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> AccessReviewPacketResponse:
    try:
        patient = get_patient_by_id(db=db, context=context, patient_id=patient_id)
    except PatientNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    except OrganizationAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    return AccessReviewPacketResponse(
        **build_access_review_packet(db=db, context=context, patient=patient)
    )


@router.get(
    "/access-review-packet/{patient_id}/markdown",
    response_class=PlainTextResponse,
)
def get_access_review_packet_markdown_endpoint(
    patient_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PlainTextResponse:
    try:
        patient = get_patient_by_id(db=db, context=context, patient_id=patient_id)
    except PatientNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    except OrganizationAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    packet = build_access_review_packet(db=db, context=context, patient=patient)
    return PlainTextResponse(
        render_access_review_packet_markdown(packet),
        media_type="text/markdown",
    )


@router.post(
    "/access-review-packet/{patient_id}/snapshots",
    response_model=AccessReviewPacketSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_access_review_packet_snapshot_endpoint(
    patient_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> AccessReviewPacketSnapshotResponse:
    try:
        patient = get_patient_by_id(db=db, context=context, patient_id=patient_id)
    except PatientNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    except OrganizationAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    snapshot = create_access_review_packet_snapshot(db=db, context=context, patient=patient)
    return AccessReviewPacketSnapshotResponse.model_validate(
        serialize_access_review_packet_snapshot(
            db=db,
            context=context,
            snapshot=snapshot,
            include_audit_timeline=True,
        )
    )


@router.get(
    "/access-review-packet/{patient_id}/snapshots",
    response_model=list[AccessReviewPacketSnapshotResponse],
)
def list_access_review_packet_snapshots_endpoint(
    patient_id: UUID,
    review_status: AccessReviewPacketSnapshotReviewStatus | None = Query(default=None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> list[AccessReviewPacketSnapshotResponse]:
    try:
        patient = get_patient_by_id(db=db, context=context, patient_id=patient_id)
    except PatientNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    except OrganizationAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    snapshots = list_access_review_packet_snapshots(
        db=db,
        context=context,
        patient=patient,
        review_status=review_status,
        limit=limit,
        offset=offset,
    )
    return [
        AccessReviewPacketSnapshotResponse.model_validate(snapshot)
        for snapshot in serialize_access_review_packet_snapshots(
            db=db,
            context=context,
            snapshots=snapshots,
        )
    ]


@router.get(
    "/access-review-packet/{patient_id}/snapshots/summary",
    response_model=AccessReviewPacketSnapshotSummaryResponse,
)
def get_access_review_packet_snapshot_summary_endpoint(
    patient_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> AccessReviewPacketSnapshotSummaryResponse:
    try:
        patient = get_patient_by_id(db=db, context=context, patient_id=patient_id)
    except PatientNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    except OrganizationAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    return AccessReviewPacketSnapshotSummaryResponse(
        **summarize_access_review_packet_snapshots(
            db=db,
            context=context,
            patient=patient,
        )
    )


@router.get(
    "/access-review-packet/patients/{patient_id}/audit-status",
    response_model=AccessReviewPacketPatientAuditStatusResponse,
)
def get_access_review_packet_patient_audit_status_endpoint(
    patient_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> AccessReviewPacketPatientAuditStatusResponse:
    try:
        patient = get_patient_by_id(db=db, context=context, patient_id=patient_id)
    except PatientNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    except OrganizationAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    return AccessReviewPacketPatientAuditStatusResponse(
        **get_access_review_packet_patient_audit_status(
            db=db,
            context=context,
            patient=patient,
        )
    )


@router.get(
    "/access-review-packet/snapshots/{snapshot_id}",
    response_model=AccessReviewPacketSnapshotResponse,
)
def get_access_review_packet_snapshot_detail_endpoint(
    snapshot_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> AccessReviewPacketSnapshotResponse:
    try:
        snapshot = get_access_review_packet_snapshot_by_id(
            db=db,
            context=context,
            snapshot_id=snapshot_id,
        )
    except OrganizationAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found.")

    return AccessReviewPacketSnapshotResponse.model_validate(
        serialize_access_review_packet_snapshot(
            db=db,
            context=context,
            snapshot=snapshot,
            include_audit_timeline=True,
        )
    )


@router.get(
    "/access-review-packet/snapshots/{snapshot_id}/markdown",
    response_class=PlainTextResponse,
)
def get_access_review_packet_snapshot_markdown_endpoint(
    snapshot_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PlainTextResponse:
    try:
        snapshot = get_access_review_packet_snapshot_by_id(
            db=db,
            context=context,
            snapshot_id=snapshot_id,
        )
    except OrganizationAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found.")

    return PlainTextResponse(snapshot.packet_markdown, media_type="text/markdown")


@router.get(
    "/access-review-packet/snapshots/{snapshot_id}/events",
    response_model=AccessReviewPacketSnapshotEventListResponse,
)
def get_access_review_packet_snapshot_events_endpoint(
    snapshot_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> AccessReviewPacketSnapshotEventListResponse:
    try:
        payload = list_access_review_packet_snapshot_events(
            db=db,
            context=context,
            snapshot_id=snapshot_id,
        )
    except OrganizationAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found.")

    return AccessReviewPacketSnapshotEventListResponse(**payload)


@router.get(
    "/access-review-packet/snapshots/{snapshot_id}/audit-bundle",
    response_model=AccessReviewPacketSnapshotAuditBundleResponse,
)
def get_access_review_packet_snapshot_audit_bundle_endpoint(
    snapshot_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> AccessReviewPacketSnapshotAuditBundleResponse:
    try:
        payload = get_access_review_packet_snapshot_audit_bundle(
            db=db,
            context=context,
            snapshot_id=snapshot_id,
        )
    except AccessReviewPacketAuditBundleConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except OrganizationAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found.")

    response_payload = AccessReviewPacketSnapshotAuditBundleResponse(**payload)
    record_access_review_packet_snapshot_audit_bundle_export(
        db=db,
        context=context,
        snapshot_id=snapshot_id,
        export_format="json",
        export_metadata=payload["export_metadata"],
    )
    return response_payload


@router.get(
    "/access-review-packet/snapshots/{snapshot_id}/audit-bundle/markdown",
    response_class=PlainTextResponse,
)
def get_access_review_packet_snapshot_audit_bundle_markdown_endpoint(
    snapshot_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PlainTextResponse:
    try:
        payload = get_access_review_packet_snapshot_audit_bundle(
            db=db,
            context=context,
            snapshot_id=snapshot_id,
        )
    except AccessReviewPacketAuditBundleConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except OrganizationAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found.")

    markdown_payload = build_access_review_packet_snapshot_audit_bundle_markdown_payload(payload)
    markdown = render_access_review_packet_snapshot_audit_bundle_markdown(markdown_payload)
    record_access_review_packet_snapshot_audit_bundle_export(
        db=db,
        context=context,
        snapshot_id=snapshot_id,
        export_format="markdown",
        export_metadata=markdown_payload["export_metadata"],
    )
    return PlainTextResponse(
        markdown,
        media_type="text/markdown",
    )


@router.get(
    "/access-review-packet/snapshots/{snapshot_id}/audit-bundle/pdf",
)
def get_access_review_packet_snapshot_audit_bundle_pdf_endpoint(
    snapshot_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> Response:
    try:
        payload = get_access_review_packet_snapshot_audit_bundle(
            db=db,
            context=context,
            snapshot_id=snapshot_id,
        )
    except AccessReviewPacketAuditBundleConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except OrganizationAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found.")

    pdf = render_access_review_packet_snapshot_audit_bundle_pdf(payload)
    export_metadata = build_access_review_packet_snapshot_export_metadata(
        snapshot_id=snapshot_id,
        export_format="pdf",
    )
    record_access_review_packet_snapshot_audit_bundle_export(
        db=db,
        context=context,
        snapshot_id=snapshot_id,
        export_format="pdf",
        export_metadata=export_metadata,
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                "attachment; "
                f'filename="access-review-packet-audit-bundle-{snapshot_id}.pdf"'
            )
        },
    )


@router.post(
    "/access-review-packet/snapshots/{snapshot_id}/audit-bundle/verify",
    response_model=AccessReviewPacketSnapshotAuditManifestVerifyResponse,
)
def verify_access_review_packet_snapshot_audit_bundle_endpoint(
    snapshot_id: UUID,
    payload: AccessReviewPacketSnapshotAuditManifestVerifyRequest,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> AccessReviewPacketSnapshotAuditManifestVerifyResponse:
    try:
        result = verify_access_review_packet_snapshot_audit_manifest(
            db=db,
            context=context,
            snapshot_id=snapshot_id,
            submitted_manifest=payload.audit_manifest.model_dump(mode="json"),
        )
    except AccessReviewPacketAuditBundleConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except OrganizationAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found.")

    return AccessReviewPacketSnapshotAuditManifestVerifyResponse(**result)


@router.patch(
    "/access-review-packet/snapshots/{snapshot_id}/review",
    response_model=AccessReviewPacketSnapshotResponse,
)
def update_access_review_packet_snapshot_review_endpoint(
    snapshot_id: UUID,
    payload: AccessReviewPacketSnapshotReviewUpdateRequest,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> AccessReviewPacketSnapshotResponse:
    try:
        snapshot = update_access_review_packet_snapshot_review(
            db=db,
            context=context,
            snapshot_id=snapshot_id,
            review_status=payload.review_status,
            review_note=payload.review_note,
            decision_note=payload.decision_note,
            override_missing_checklist=payload.override_missing_checklist,
            override_reason=payload.override_reason,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid review_status.",
        )
    except AccessReviewPacketApprovalBlockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except AccessReviewPacketApprovalOverrideAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except OrganizationAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found.")

    return AccessReviewPacketSnapshotResponse.model_validate(
        serialize_access_review_packet_snapshot(
            db=db,
            context=context,
            snapshot=snapshot,
        )
    )


@router.patch(
    "/access-review-packet/snapshots/{snapshot_id}/assignment",
    response_model=AccessReviewPacketSnapshotResponse,
)
def update_access_review_packet_snapshot_assignment_endpoint(
    snapshot_id: UUID,
    payload: AccessReviewPacketSnapshotAssignmentUpdateRequest,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> AccessReviewPacketSnapshotResponse:
    try:
        snapshot = update_access_review_packet_snapshot_assignment(
            db=db,
            context=context,
            snapshot_id=snapshot_id,
            assigned_reviewer_user_id=payload.assigned_reviewer_user_id,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid assigned_reviewer_user_id.",
        )
    except OrganizationAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found.")

    return AccessReviewPacketSnapshotResponse.model_validate(
        serialize_access_review_packet_snapshot(
            db=db,
            context=context,
            snapshot=snapshot,
        )
    )
