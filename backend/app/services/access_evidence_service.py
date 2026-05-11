from __future__ import annotations

from collections import defaultdict
import csv
from datetime import datetime, timezone
import hashlib
from io import StringIO
import json
from typing import Any
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.context import RequestContext
from app.models.access_review_packet_snapshot import (
    AccessReviewPacketSnapshotEvent,
    AccessReviewPacketSnapshotEventType,
    AccessReviewPacketSnapshot,
    AccessReviewPacketSnapshotReviewStatus,
)
from app.models.care_update import CareUpdate
from app.models.intervention_task import InterventionTask
from app.models.outcome import Outcome
from app.models.patient import Patient
from app.models.patient_signal import EscalationStatus, PatientEscalation, PatientSignal
from app.models.user import User
from app.schemas.access_evidence import AccessReviewPacketResponse
from app.services.authz import ensure_organization_access, ensure_tenant_scoped_resource

LOWER_IS_BETTER = {"systolic_bp", "diastolic_bp", "a1c", "missed_days"}
HIGHER_IS_BETTER = {"completed_checkins", "completed_checkin", "adherence_rate"}


class AccessReviewPacketApprovalBlockedError(Exception):
    """Raised when a persisted snapshot checklist blocks approval."""


class AccessReviewPacketApprovalOverrideAuthorizationError(Exception):
    """Raised when a user is not allowed to override missing checklist items."""


class AccessReviewPacketReviewValidationError(Exception):
    """Raised when a review decision payload is invalid."""


class AccessReviewPacketReviewStateConflictError(Exception):
    """Raised when a review decision would rewrite a terminal snapshot state."""


class AccessReviewPacketAuditBundleConflictError(Exception):
    """Raised when a snapshot is not in an approved state for audit bundle reads."""


def build_access_evidence_report(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
) -> dict[str, Any]:
    ensure_tenant_scoped_resource(context=context, resource=patient)
    outcomes = _load_outcomes(db=db, patient=patient)
    tasks = _load_tasks(db=db, patient=patient)
    escalations = _load_escalations(db=db, patient=patient)
    care_updates = _load_care_updates(db=db, patient=patient)
    resolution_summaries = _summarize_escalation_resolutions(escalations)
    return {
        "patient_id": patient.id,
        "outcome_summaries": _summarize_outcomes(outcomes),
        "intervention_outcome_links": _derive_intervention_outcome_links(
            tasks=tasks,
            outcomes=outcomes,
        ),
        "escalation_resolution_summaries": resolution_summaries,
        "review_readiness": _build_review_readiness_summary(
            outcomes=outcomes,
            care_updates=care_updates,
            tasks=tasks,
            escalations=escalations,
            escalation_resolution_summaries=resolution_summaries,
        ),
    }


def build_access_case_summary(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
) -> dict[str, Any]:
    ensure_tenant_scoped_resource(context=context, resource=patient)
    signals = _load_signals(db=db, patient=patient)
    outcomes = _load_outcomes(db=db, patient=patient)
    tasks = _load_tasks(db=db, patient=patient)
    escalations = _load_escalations(db=db, patient=patient)
    care_updates = _load_care_updates(db=db, patient=patient)
    resolution_summaries = _summarize_escalation_resolutions(escalations)
    outcome_summaries = _summarize_outcomes(outcomes)
    review_readiness = _build_review_readiness_summary(
        outcomes=outcomes,
        care_updates=care_updates,
        tasks=tasks,
        escalations=escalations,
        escalation_resolution_summaries=resolution_summaries,
    )

    return {
        "patient_id": patient.id,
        "escalation_summary": _build_escalation_case_summary(
            escalations=escalations,
            resolution_summaries=resolution_summaries,
        ),
        "interventions": _summarize_interventions(tasks=tasks, outcomes=outcomes),
        "outcome_summaries": outcome_summaries,
        "latest_care_update": _summarize_latest_care_update(care_updates),
        "evidence_completeness": _build_evidence_completeness(
            outcomes=outcomes,
            care_updates=care_updates,
            escalation_resolution_summaries=resolution_summaries,
        ),
        "review_readiness": review_readiness,
        "review_checklist": _build_review_checklist(
            signals=signals,
            escalations=escalations,
            tasks=tasks,
            outcomes=outcomes,
            care_updates=care_updates,
            escalation_resolution_summaries=resolution_summaries,
            review_readiness=review_readiness,
        ),
    }


def build_access_review_readiness_summary(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
) -> dict[str, Any]:
    ensure_tenant_scoped_resource(context=context, resource=patient)
    outcomes = _load_outcomes(db=db, patient=patient)
    tasks = _load_tasks(db=db, patient=patient)
    escalations = _load_escalations(db=db, patient=patient)
    care_updates = _load_care_updates(db=db, patient=patient)
    resolution_summaries = _summarize_escalation_resolutions(escalations)
    return _build_review_readiness_summary(
        outcomes=outcomes,
        care_updates=care_updates,
        tasks=tasks,
        escalations=escalations,
        escalation_resolution_summaries=resolution_summaries,
    )


def build_access_review_packet(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
) -> dict[str, Any]:
    ensure_tenant_scoped_resource(context=context, resource=patient)
    case_summary = build_access_case_summary(db=db, context=context, patient=patient)
    evidence_report = build_access_evidence_report(db=db, context=context, patient=patient)
    return {
        "patient_id": patient.id,
        "generated_at": datetime.now(timezone.utc),
        "review_readiness": case_summary["review_readiness"],
        "review_checklist": case_summary["review_checklist"],
        "case_summary": case_summary,
        "evidence_report": evidence_report,
    }


def render_access_review_packet_markdown(packet: dict[str, Any]) -> str:
    case_summary = packet["case_summary"]
    evidence_report = packet["evidence_report"]
    review_readiness = packet["review_readiness"]
    review_checklist = packet["review_checklist"]
    escalation_summary = case_summary["escalation_summary"]
    evidence_completeness = case_summary["evidence_completeness"]
    latest_outcome = case_summary["outcome_summaries"][-1] if case_summary["outcome_summaries"] else None
    latest_care_update = case_summary["latest_care_update"]
    latest_resolution = escalation_summary["latest_resolution"]
    interventions = case_summary["interventions"]

    lines = [
        "# ACCESS Review Packet",
        "",
        "## Overview",
        f"- Patient ID: {packet['patient_id']}",
        f"- Generated At: {_render_datetime(packet['generated_at'])}",
        f"- Review Readiness: {review_readiness['readiness_status']}",
        "",
        "## Case Summary Highlights",
        f"- Open Escalations: {escalation_summary['open_count']}",
        f"- Resolved Escalations: {escalation_summary['resolved_count']}",
        f"- Latest Escalation Status: {escalation_summary['latest_status'] or 'none'}",
        "",
        "## Evidence Completeness",
        f"- Outcome Present: {_bool_label(evidence_completeness['has_outcome'])}",
        f"- Care Update Present: {_bool_label(evidence_completeness['has_care_update'])}",
        (
            "- Resolution Evidence Present: "
            f"{_bool_label(evidence_completeness['has_resolution_evidence'])}"
        ),
        (
            "- Missing Components: "
            f"{', '.join(evidence_completeness['missing_components'])}"
            if evidence_completeness["missing_components"]
            else "- Missing Components: none"
        ),
        "",
        "## Review Checklist",
        "| Item | Status | Reason |",
        "| --- | --- | --- |",
    ]

    for item in review_checklist["items"]:
        lines.append(
            f"| {item['label']} | {_title_case(item['status'])} | {item['reason']} |"
        )

    lines.extend(
        [
            "",
            "## Latest Outcome",
            _render_latest_outcome_line(latest_outcome),
            "",
            "## Latest Care Update",
            _render_latest_care_update_line(latest_care_update),
            "",
            "## Latest Resolution",
            _render_latest_resolution_line(latest_resolution),
            "",
            "## Intervention Summary",
        ]
    )

    if interventions:
        for intervention in interventions:
            lines.append(
                "- "
                f"{intervention['title']} "
                f"({intervention['status']}, priority={intervention['priority']}, "
                f"linked_outcomes={len(intervention['linked_outcome_ids'])})"
            )
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Audit Evidence",
            (
                f"- Outcome Summaries: {len(case_summary['outcome_summaries'])} metric group(s)"
            ),
            (
                "- Intervention-Outcome Links: "
                f"{len(evidence_report['intervention_outcome_links'])}"
            ),
            (
                "- Escalation Resolution Summaries: "
                f"{len(evidence_report['escalation_resolution_summaries'])}"
            ),
        ]
    )
    return "\n".join(lines)


def create_access_review_packet_snapshot(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
) -> AccessReviewPacketSnapshot:
    ensure_tenant_scoped_resource(context=context, resource=patient)
    packet = build_access_review_packet(db=db, context=context, patient=patient)
    packet_payload = AccessReviewPacketResponse(**packet).model_dump(mode="json")
    snapshot = AccessReviewPacketSnapshot(
        organization_id=patient.organization_id,
        patient_id=patient.id,
        generated_at=packet["generated_at"],
        review_readiness_status=packet["review_readiness"]["readiness_status"],
        review_status=AccessReviewPacketSnapshotReviewStatus.PENDING_REVIEW,
        packet_json=packet_payload,
        packet_markdown=render_access_review_packet_markdown(packet),
    )
    db.add(snapshot)
    db.flush()
    readiness_reasons = _build_access_review_packet_snapshot_event_readiness_reasons(
        snapshot=snapshot,
        state=_build_access_review_state(snapshot=snapshot, decision_event=None)["state"],
        audit_bundle_available=False,
        audit_bundle_exported=False,
    )
    _record_access_review_packet_snapshot_event(
        db=db,
        snapshot=snapshot,
        event_type=AccessReviewPacketSnapshotEventType.SNAPSHOT_CREATED,
        actor_user_id=context.user.id,
        metadata_json={
            "review_readiness_status": snapshot.review_readiness_status,
            "review_status": snapshot.review_status.value,
            "readiness_reasons": readiness_reasons,
        },
    )
    db.commit()
    db.refresh(snapshot)
    return snapshot


def list_access_review_packet_snapshots(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
    review_status: AccessReviewPacketSnapshotReviewStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AccessReviewPacketSnapshot]:
    ensure_tenant_scoped_resource(context=context, resource=patient)
    stmt = (
        select(AccessReviewPacketSnapshot)
        .where(AccessReviewPacketSnapshot.patient_id == patient.id)
        .where(AccessReviewPacketSnapshot.organization_id == patient.organization_id)
    )
    if review_status is not None:
        stmt = stmt.where(AccessReviewPacketSnapshot.review_status == review_status)
    stmt = stmt.order_by(
        AccessReviewPacketSnapshot.created_at.desc(),
        AccessReviewPacketSnapshot.generated_at.desc(),
        AccessReviewPacketSnapshot.id.desc(),
    ).offset(offset).limit(limit)
    return list(db.execute(stmt).scalars().all())


def list_access_review_packet_snapshots_for_organization(
    db: Session,
    *,
    context: RequestContext,
    patient_id: Any | None = None,
    review_status: AccessReviewPacketSnapshotReviewStatus | None = None,
    review_readiness_status: str | None = None,
    assigned_reviewer_user_id: Any | None = None,
    unassigned: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[AccessReviewPacketSnapshot]:
    ensure_organization_access(context=context, organization_id=context.organization_id)
    stmt = select(AccessReviewPacketSnapshot).where(
        AccessReviewPacketSnapshot.organization_id == context.organization_id
    )
    if patient_id is not None:
        stmt = stmt.where(AccessReviewPacketSnapshot.patient_id == patient_id)
    if review_status is not None:
        stmt = stmt.where(AccessReviewPacketSnapshot.review_status == review_status)
    if review_readiness_status is not None:
        stmt = stmt.where(
            AccessReviewPacketSnapshot.review_readiness_status == review_readiness_status
        )
    if assigned_reviewer_user_id is not None:
        stmt = stmt.where(
            AccessReviewPacketSnapshot.assigned_reviewer_user_id == assigned_reviewer_user_id
        )
    if unassigned:
        stmt = stmt.where(AccessReviewPacketSnapshot.assigned_reviewer_user_id.is_(None))
    stmt = stmt.order_by(
        AccessReviewPacketSnapshot.created_at.desc(),
        AccessReviewPacketSnapshot.generated_at.desc(),
        AccessReviewPacketSnapshot.id.desc(),
    ).offset(offset).limit(limit)
    return list(db.execute(stmt).scalars().all())


def list_access_review_packet_snapshot_patient_backlog_for_organization(
    db: Session,
    *,
    context: RequestContext,
    review_status: AccessReviewPacketSnapshotReviewStatus | None = None,
    review_readiness_status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    ensure_organization_access(context=context, organization_id=context.organization_id)

    filtered_snapshots = (
        select(
            AccessReviewPacketSnapshot.patient_id.label("patient_id"),
            AccessReviewPacketSnapshot.id.label("snapshot_id"),
            AccessReviewPacketSnapshot.created_at.label("created_at"),
            AccessReviewPacketSnapshot.generated_at.label("generated_at"),
            AccessReviewPacketSnapshot.review_status.label("review_status"),
            AccessReviewPacketSnapshot.review_readiness_status.label("review_readiness_status"),
            func.row_number()
            .over(
                partition_by=AccessReviewPacketSnapshot.patient_id,
                order_by=(
                    AccessReviewPacketSnapshot.created_at.desc(),
                    AccessReviewPacketSnapshot.generated_at.desc(),
                    AccessReviewPacketSnapshot.id.desc(),
                ),
            )
            .label("row_number"),
        )
        .where(AccessReviewPacketSnapshot.organization_id == context.organization_id)
        .subquery()
    )

    counts = (
        select(
            AccessReviewPacketSnapshot.patient_id.label("patient_id"),
            func.count(AccessReviewPacketSnapshot.id).label("total_snapshot_count"),
            func.sum(
                case(
                    (
                        AccessReviewPacketSnapshot.review_status
                        == AccessReviewPacketSnapshotReviewStatus.PENDING_REVIEW,
                        1,
                    ),
                    else_=0,
                )
            ).label("pending_review_count"),
            func.sum(
                case(
                    (
                        AccessReviewPacketSnapshot.review_status
                        == AccessReviewPacketSnapshotReviewStatus.APPROVED,
                        1,
                    ),
                    else_=0,
                )
            ).label("approved_count"),
            func.sum(
                case(
                    (
                        AccessReviewPacketSnapshot.review_status
                        == AccessReviewPacketSnapshotReviewStatus.REJECTED,
                        1,
                    ),
                    else_=0,
                )
            ).label("rejected_count"),
        )
        .where(AccessReviewPacketSnapshot.organization_id == context.organization_id)
        .group_by(AccessReviewPacketSnapshot.patient_id)
        .subquery()
    )

    stmt = (
        select(
            filtered_snapshots.c.patient_id,
            filtered_snapshots.c.snapshot_id.label("latest_snapshot_id"),
            filtered_snapshots.c.created_at.label("latest_snapshot_created_at"),
            filtered_snapshots.c.review_status.label("latest_review_status"),
            filtered_snapshots.c.review_readiness_status.label("latest_review_readiness_status"),
            counts.c.pending_review_count,
            counts.c.approved_count,
            counts.c.rejected_count,
            counts.c.total_snapshot_count,
        )
        .join(counts, counts.c.patient_id == filtered_snapshots.c.patient_id)
        .where(filtered_snapshots.c.row_number == 1)
    )
    if review_status is not None:
        stmt = stmt.where(filtered_snapshots.c.review_status == review_status)
    if review_readiness_status is not None:
        stmt = stmt.where(
            filtered_snapshots.c.review_readiness_status == review_readiness_status
        )

    stmt = stmt.order_by(
        filtered_snapshots.c.created_at.desc(),
        filtered_snapshots.c.patient_id.desc(),
    ).offset(offset).limit(limit)

    return [
        {
            "patient_id": row.patient_id,
            "latest_snapshot_id": row.latest_snapshot_id,
            "latest_snapshot_created_at": row.latest_snapshot_created_at,
            "latest_review_status": row.latest_review_status.value
            if hasattr(row.latest_review_status, "value")
            else str(row.latest_review_status),
            "latest_review_readiness_status": str(row.latest_review_readiness_status),
            "pending_review_count": row.pending_review_count or 0,
            "approved_count": row.approved_count or 0,
            "rejected_count": row.rejected_count or 0,
            "total_snapshot_count": row.total_snapshot_count or 0,
        }
        for row in db.execute(stmt).all()
    ]


def list_latest_actionable_access_review_packet_snapshots_for_organization(
    db: Session,
    *,
    context: RequestContext,
    review_status: AccessReviewPacketSnapshotReviewStatus | None = None,
    review_readiness_status: str | None = None,
    assigned_reviewer_user_id: Any | None = None,
    unassigned: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[AccessReviewPacketSnapshot]:
    ensure_organization_access(context=context, organization_id=context.organization_id)

    effective_review_status = (
        review_status or AccessReviewPacketSnapshotReviewStatus.PENDING_REVIEW
    )
    latest_snapshots = (
        select(
            AccessReviewPacketSnapshot.id.label("snapshot_id"),
            AccessReviewPacketSnapshot.patient_id.label("patient_id"),
            AccessReviewPacketSnapshot.created_at.label("created_at"),
            AccessReviewPacketSnapshot.generated_at.label("generated_at"),
            AccessReviewPacketSnapshot.review_status.label("review_status"),
            AccessReviewPacketSnapshot.review_readiness_status.label("review_readiness_status"),
            AccessReviewPacketSnapshot.assigned_reviewer_user_id.label("assigned_reviewer_user_id"),
            func.row_number()
            .over(
                partition_by=AccessReviewPacketSnapshot.patient_id,
                order_by=(
                    AccessReviewPacketSnapshot.created_at.desc(),
                    AccessReviewPacketSnapshot.generated_at.desc(),
                    AccessReviewPacketSnapshot.id.desc(),
                ),
            )
            .label("row_number"),
        )
        .where(AccessReviewPacketSnapshot.organization_id == context.organization_id)
        .subquery()
    )

    snapshot_ids = (
        select(latest_snapshots.c.snapshot_id)
        .where(latest_snapshots.c.row_number == 1)
        .where(latest_snapshots.c.review_status == effective_review_status)
    )
    if review_readiness_status is not None:
        snapshot_ids = snapshot_ids.where(
            latest_snapshots.c.review_readiness_status == review_readiness_status
        )
    if assigned_reviewer_user_id is not None:
        snapshot_ids = snapshot_ids.where(
            latest_snapshots.c.assigned_reviewer_user_id == assigned_reviewer_user_id
        )
    if unassigned:
        snapshot_ids = snapshot_ids.where(latest_snapshots.c.assigned_reviewer_user_id.is_(None))

    snapshot_ids = snapshot_ids.order_by(
        latest_snapshots.c.created_at.desc(),
        latest_snapshots.c.patient_id.desc(),
    ).offset(offset).limit(limit)

    stmt = (
        select(AccessReviewPacketSnapshot)
        .where(AccessReviewPacketSnapshot.id.in_(snapshot_ids))
        .order_by(
            AccessReviewPacketSnapshot.created_at.desc(),
            AccessReviewPacketSnapshot.patient_id.desc(),
            AccessReviewPacketSnapshot.generated_at.desc(),
            AccessReviewPacketSnapshot.id.desc(),
        )
    )
    return list(db.execute(stmt).scalars().all())


def get_latest_access_review_packet_snapshot_for_patient_in_organization(
    db: Session,
    *,
    context: RequestContext,
    patient_id: Any,
    review_status: AccessReviewPacketSnapshotReviewStatus | None = None,
    review_readiness_status: str | None = None,
) -> AccessReviewPacketSnapshot | None:
    snapshots = list_access_review_packet_snapshots_for_organization(
        db=db,
        context=context,
        patient_id=patient_id,
        review_status=review_status,
        review_readiness_status=review_readiness_status,
        limit=1,
        offset=0,
    )
    return snapshots[0] if snapshots else None


def summarize_access_review_packet_snapshots(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
) -> dict[str, int]:
    ensure_tenant_scoped_resource(context=context, resource=patient)
    stmt = (
        select(
            AccessReviewPacketSnapshot.review_status,
            func.count(AccessReviewPacketSnapshot.id),
        )
        .where(AccessReviewPacketSnapshot.patient_id == patient.id)
        .where(AccessReviewPacketSnapshot.organization_id == patient.organization_id)
        .group_by(AccessReviewPacketSnapshot.review_status)
    )
    counts_by_status = {
        status.value if hasattr(status, "value") else str(status): count
        for status, count in db.execute(stmt).all()
    }
    return {
        "total": sum(counts_by_status.values()),
        "pending_review": counts_by_status.get("pending_review", 0),
        "approved": counts_by_status.get("approved", 0),
        "rejected": counts_by_status.get("rejected", 0),
        "ready_for_review": 0,
        "active_open_work": 0,
        "incomplete": 0,
    }


def summarize_access_review_packet_snapshots_for_organization(
    db: Session,
    *,
    context: RequestContext,
) -> dict[str, int]:
    ensure_organization_access(context=context, organization_id=context.organization_id)
    review_stmt = (
        select(
            AccessReviewPacketSnapshot.review_status,
            func.count(AccessReviewPacketSnapshot.id),
        )
        .where(AccessReviewPacketSnapshot.organization_id == context.organization_id)
        .group_by(AccessReviewPacketSnapshot.review_status)
    )
    readiness_stmt = (
        select(
            AccessReviewPacketSnapshot.review_readiness_status,
            func.count(AccessReviewPacketSnapshot.id),
        )
        .where(AccessReviewPacketSnapshot.organization_id == context.organization_id)
        .group_by(AccessReviewPacketSnapshot.review_readiness_status)
    )

    review_counts = {
        status.value if hasattr(status, "value") else str(status): count
        for status, count in db.execute(review_stmt).all()
    }
    readiness_counts = {
        str(status): count
        for status, count in db.execute(readiness_stmt).all()
    }
    return {
        "total": sum(review_counts.values()),
        "pending_review": review_counts.get("pending_review", 0),
        "approved": review_counts.get("approved", 0),
        "rejected": review_counts.get("rejected", 0),
        "ready_for_review": readiness_counts.get("ready_for_review", 0),
        "active_open_work": readiness_counts.get("active_open_work", 0),
        "incomplete": readiness_counts.get("incomplete", 0),
    }


def summarize_access_review_packet_snapshot_queue_for_organization(
    db: Session,
    *,
    context: RequestContext,
) -> dict[str, Any]:
    ensure_organization_access(context=context, organization_id=context.organization_id)
    review_stmt = (
        select(
            AccessReviewPacketSnapshot.review_status,
            func.count(AccessReviewPacketSnapshot.id),
        )
        .where(AccessReviewPacketSnapshot.organization_id == context.organization_id)
        .group_by(AccessReviewPacketSnapshot.review_status)
    )
    readiness_stmt = (
        select(
            AccessReviewPacketSnapshot.review_readiness_status,
            func.count(AccessReviewPacketSnapshot.id),
        )
        .where(AccessReviewPacketSnapshot.organization_id == context.organization_id)
        .group_by(AccessReviewPacketSnapshot.review_readiness_status)
    )
    combined_stmt = (
        select(
            AccessReviewPacketSnapshot.review_status,
            AccessReviewPacketSnapshot.review_readiness_status,
            func.count(AccessReviewPacketSnapshot.id),
        )
        .where(AccessReviewPacketSnapshot.organization_id == context.organization_id)
        .group_by(
            AccessReviewPacketSnapshot.review_status,
            AccessReviewPacketSnapshot.review_readiness_status,
        )
    )
    assignment_stmt = (
        select(
            case(
                (
                    AccessReviewPacketSnapshot.assigned_reviewer_user_id.is_(None),
                    "unassigned",
                ),
                else_="assigned",
            ).label("assignment_status"),
            func.count(AccessReviewPacketSnapshot.id),
        )
        .where(AccessReviewPacketSnapshot.organization_id == context.organization_id)
        .group_by("assignment_status")
    )
    pending_assignment_stmt = (
        select(
            case(
                (
                    AccessReviewPacketSnapshot.assigned_reviewer_user_id.is_(None),
                    "unassigned",
                ),
                else_="assigned",
            ).label("assignment_status"),
            func.count(AccessReviewPacketSnapshot.id),
        )
        .where(AccessReviewPacketSnapshot.organization_id == context.organization_id)
        .where(
            AccessReviewPacketSnapshot.review_status
            == AccessReviewPacketSnapshotReviewStatus.PENDING_REVIEW
        )
        .group_by("assignment_status")
    )

    review_counts = {
        status.value if hasattr(status, "value") else str(status): count
        for status, count in db.execute(review_stmt).all()
    }
    readiness_counts = {
        str(status): count
        for status, count in db.execute(readiness_stmt).all()
    }
    combined_counts = {
        (
            review_status.value if hasattr(review_status, "value") else str(review_status),
            str(review_readiness_status),
        ): count
        for review_status, review_readiness_status, count in db.execute(combined_stmt).all()
    }
    assignment_counts = {
        str(status): count for status, count in db.execute(assignment_stmt).all()
    }
    pending_assignment_counts = {
        str(status): count for status, count in db.execute(pending_assignment_stmt).all()
    }
    snapshots = db.execute(
        select(AccessReviewPacketSnapshot).where(
            AccessReviewPacketSnapshot.organization_id == context.organization_id
        )
    ).scalars().all()
    decision_events_by_snapshot_id = _load_latest_decision_events_for_snapshots(
        db=db,
        organization_id=context.organization_id,
        snapshot_ids=[snapshot.id for snapshot in snapshots],
    )
    exported_snapshot_ids = _load_exported_snapshot_ids_for_organization(
        db=db,
        organization_id=context.organization_id,
    )
    latest_backlog_items = list_access_review_packet_snapshot_patient_backlog_for_organization(
        db=db,
        context=context,
        limit=10_000,
        offset=0,
    )
    latest_snapshot_ids = [item["latest_snapshot_id"] for item in latest_backlog_items]
    latest_snapshots_by_id = {
        snapshot.id: snapshot
        for snapshot in db.execute(
            select(AccessReviewPacketSnapshot).where(
                AccessReviewPacketSnapshot.organization_id == context.organization_id,
                AccessReviewPacketSnapshot.id.in_(latest_snapshot_ids),
            )
        ).scalars()
    }
    lifecycle_counts = {
        "pending_unassigned_count": 0,
        "pending_assigned_ready_count": 0,
        "blocked_missing_evidence_count": 0,
        "approved_count": 0,
        "approved_with_override_count": 0,
        "rejected_count": 0,
        "approved_not_exported_count": 0,
        "exported_count": 0,
        "pending_review_age": {
            "new_today_count": 0,
            "one_to_three_days_count": 0,
            "four_to_seven_days_count": 0,
            "over_seven_days_count": 0,
        },
    }
    today_utc = datetime.now(timezone.utc).date()
    for snapshot in snapshots:
        review_state = _build_access_review_state(
            snapshot=snapshot,
            decision_event=decision_events_by_snapshot_id.get(snapshot.id),
        )
        state = review_state["state"]
        lifecycle_key = f"{state}_count"
        if lifecycle_key in lifecycle_counts:
            lifecycle_counts[lifecycle_key] += 1
        if state in {"approved", "approved_with_override"}:
            if snapshot.id in exported_snapshot_ids:
                lifecycle_counts["exported_count"] += 1
            else:
                lifecycle_counts["approved_not_exported_count"] += 1
        if state in {
            "pending_unassigned",
            "pending_assigned_ready",
            "blocked_missing_evidence",
        }:
            snapshot_age_days = (
                today_utc - _normalize_datetime(snapshot.created_at).date()
            ).days
            if snapshot_age_days <= 0:
                lifecycle_counts["pending_review_age"]["new_today_count"] += 1
            elif snapshot_age_days <= 3:
                lifecycle_counts["pending_review_age"]["one_to_three_days_count"] += 1
            elif snapshot_age_days <= 7:
                lifecycle_counts["pending_review_age"]["four_to_seven_days_count"] += 1
            else:
                lifecycle_counts["pending_review_age"]["over_seven_days_count"] += 1
    audit_readiness_rollup = {
        "incomplete_count": 0,
        "review_ready_count": 0,
        "approved_not_exported_count": 0,
        "audit_ready_count": 0,
        "rejected_count": 0,
    }
    for item in latest_backlog_items:
        snapshot = latest_snapshots_by_id.get(item["latest_snapshot_id"])
        if snapshot is None:
            continue
        review_state = _build_access_review_state(
            snapshot=snapshot,
            decision_event=decision_events_by_snapshot_id.get(snapshot.id),
        )
        state = review_state["state"]
        if state == "blocked_missing_evidence":
            audit_readiness_rollup["incomplete_count"] += 1
        elif state in {"pending_unassigned", "pending_assigned_ready"}:
            audit_readiness_rollup["review_ready_count"] += 1
        elif state in {"approved", "approved_with_override"}:
            if snapshot.id in exported_snapshot_ids:
                audit_readiness_rollup["audit_ready_count"] += 1
            else:
                audit_readiness_rollup["approved_not_exported_count"] += 1
        elif state == "rejected":
            audit_readiness_rollup["rejected_count"] += 1
    return {
        "total": sum(review_counts.values()),
        "review_status": {
            "pending_review": review_counts.get("pending_review", 0),
            "approved": review_counts.get("approved", 0),
            "rejected": review_counts.get("rejected", 0),
        },
        "review_readiness_status": {
            "ready_for_review": readiness_counts.get("ready_for_review", 0),
            "active_open_work": readiness_counts.get("active_open_work", 0),
            "incomplete": readiness_counts.get("incomplete", 0),
        },
        "assigned": assignment_counts.get("assigned", 0),
        "unassigned": assignment_counts.get("unassigned", 0),
        "pending_review_assigned": pending_assignment_counts.get("assigned", 0),
        "pending_review_unassigned": pending_assignment_counts.get("unassigned", 0),
        "pending_review_ready_for_review": combined_counts.get(
            ("pending_review", "ready_for_review"),
            0,
        ),
        "pending_review_active_open_work": combined_counts.get(
            ("pending_review", "active_open_work"),
            0,
        ),
        "pending_review_incomplete": combined_counts.get(
            ("pending_review", "incomplete"),
            0,
        ),
        "snapshot_audit_lifecycle": lifecycle_counts,
        "audit_readiness_rollup": audit_readiness_rollup,
    }


def summarize_access_review_packet_snapshots_for_reviewer(
    db: Session,
    *,
    context: RequestContext,
) -> dict[str, Any]:
    ensure_organization_access(context=context, organization_id=context.organization_id)
    snapshots = list_access_review_packet_snapshots_for_organization(
        db=db,
        context=context,
        assigned_reviewer_user_id=context.user.id,
        review_status=AccessReviewPacketSnapshotReviewStatus.PENDING_REVIEW,
        limit=10_000,
        offset=0,
    )
    decision_events_by_snapshot_id = _load_latest_decision_events_for_snapshots(
        db=db,
        organization_id=context.organization_id,
        snapshot_ids=[snapshot.id for snapshot in snapshots],
    )
    today_utc = datetime.now(timezone.utc).date()
    summary: dict[str, Any] = {
        "assigned_to_me_count": 0,
        "pending_assigned_ready_count": 0,
        "blocked_missing_evidence_count": 0,
        "oldest_pending_snapshot_created_at": None,
        "pending_review_age": {
            "new_today_count": 0,
            "one_to_three_days_count": 0,
            "four_to_seven_days_count": 0,
            "over_seven_days_count": 0,
        },
    }
    oldest_pending_snapshot_created_at: datetime | None = None
    for snapshot in snapshots:
        review_state = _build_access_review_state(
            snapshot=snapshot,
            decision_event=decision_events_by_snapshot_id.get(snapshot.id),
        )
        state = review_state["state"]
        if state not in {"pending_assigned_ready", "blocked_missing_evidence"}:
            continue
        summary["assigned_to_me_count"] += 1
        if state == "pending_assigned_ready":
            summary["pending_assigned_ready_count"] += 1
        else:
            summary["blocked_missing_evidence_count"] += 1
        created_at = _normalize_datetime(snapshot.created_at)
        if oldest_pending_snapshot_created_at is None or created_at < oldest_pending_snapshot_created_at:
            oldest_pending_snapshot_created_at = created_at
        snapshot_age_days = (today_utc - created_at.date()).days
        if snapshot_age_days <= 0:
            summary["pending_review_age"]["new_today_count"] += 1
        elif snapshot_age_days <= 3:
            summary["pending_review_age"]["one_to_three_days_count"] += 1
        elif snapshot_age_days <= 7:
            summary["pending_review_age"]["four_to_seven_days_count"] += 1
        else:
            summary["pending_review_age"]["over_seven_days_count"] += 1
    summary["oldest_pending_snapshot_created_at"] = oldest_pending_snapshot_created_at
    return summary


def get_access_review_packet_patient_audit_status(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
) -> dict[str, Any]:
    ensure_tenant_scoped_resource(context=context, resource=patient)
    snapshot = get_latest_access_review_packet_snapshot_for_patient_in_organization(
        db=db,
        context=context,
        patient_id=patient.id,
    )
    if snapshot is None:
        return _build_access_review_packet_patient_audit_status_without_snapshot(patient_id=patient.id)
    return _build_access_review_packet_patient_audit_status_for_snapshot(
        db=db,
        context=context,
        snapshot=snapshot,
    )


def list_access_review_packet_audit_readiness_for_organization(
    db: Session,
    *,
    context: RequestContext,
    completion_status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    ensure_organization_access(context=context, organization_id=context.organization_id)
    latest_snapshots = _list_latest_access_review_packet_snapshots_for_organization(
        db=db,
        context=context,
    )
    items = [
        _build_access_review_packet_audit_readiness_item(
            audit_status=_build_access_review_packet_patient_audit_status_for_snapshot(
                db=db,
                context=context,
                snapshot=snapshot,
            )
        )
        for snapshot in latest_snapshots
    ]
    status_counts = _build_access_review_packet_audit_readiness_status_counts(items)
    if completion_status is not None:
        items = [item for item in items if item["completion_status"] == completion_status]
    items = sorted(
        items,
        key=lambda item: (
            -_normalize_datetime(item["latest_snapshot_created_at"]).timestamp(),
            str(item["latest_snapshot_id"]),
        ),
    )
    return {
        "items": items[offset : offset + limit],
        "total_count": len(items),
        "limit": limit,
        "offset": offset,
        "status_counts": status_counts,
    }


def render_access_review_packet_audit_readiness_csv(payload: dict[str, Any]) -> str:
    def csv_datetime(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    fieldnames = [
        "patient_id",
        "latest_snapshot_id",
        "latest_snapshot_created_at",
        "review_status",
        "review_state",
        "completion_status",
        "assigned_reviewer_user_id",
        "next_step_action",
        "next_step_priority",
        "next_step_reason",
        "audit_bundle_available",
        "audit_bundle_exported",
        "audit_bundle_last_exported_at",
        "audit_bundle_export_formats",
    ]
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for item in payload["items"]:
        next_step = item["next_step"]
        audit_bundle = item["audit_bundle"]
        writer.writerow(
            {
                "patient_id": item["patient_id"],
                "latest_snapshot_id": item["latest_snapshot_id"],
                "latest_snapshot_created_at": csv_datetime(item["latest_snapshot_created_at"]),
                "review_status": item["review_status"],
                "review_state": item["review_state"],
                "completion_status": item["completion_status"],
                "assigned_reviewer_user_id": item["assigned_reviewer_user_id"] or "",
                "next_step_action": next_step["action"],
                "next_step_priority": next_step["priority"],
                "next_step_reason": next_step["reason"],
                "audit_bundle_available": audit_bundle["available"],
                "audit_bundle_exported": audit_bundle["exported"],
                "audit_bundle_last_exported_at": csv_datetime(audit_bundle["last_exported_at"]),
                "audit_bundle_export_formats": "|".join(audit_bundle["export_formats"]),
            }
        )
    return output.getvalue()


def get_access_review_packet_patient_drill_in(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
    review_status: AccessReviewPacketSnapshotReviewStatus | None = None,
    review_readiness_status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    ensure_tenant_scoped_resource(context=context, resource=patient)
    snapshots = list_access_review_packet_snapshots_for_organization(
        db=db,
        context=context,
        patient_id=patient.id,
        review_status=review_status,
        review_readiness_status=review_readiness_status,
        limit=limit,
        offset=offset,
    )
    return {
        "patient_id": patient.id,
        "audit_status": get_access_review_packet_patient_audit_status(
            db=db,
            context=context,
            patient=patient,
        ),
        "snapshots": serialize_access_review_packet_snapshots(
            db=db,
            context=context,
            snapshots=snapshots,
        ),
    }


def get_access_review_packet_snapshot_by_id(
    db: Session,
    *,
    context: RequestContext,
    snapshot_id: Any,
) -> AccessReviewPacketSnapshot | None:
    stmt = select(AccessReviewPacketSnapshot).where(AccessReviewPacketSnapshot.id == snapshot_id)
    snapshot = db.execute(stmt).scalar_one_or_none()
    if snapshot is None:
        return None
    ensure_tenant_scoped_resource(context=context, resource=snapshot)
    return snapshot


def serialize_access_review_packet_snapshot(
    db: Session,
    *,
    context: RequestContext,
    snapshot: AccessReviewPacketSnapshot,
    include_audit_timeline: bool = False,
) -> dict[str, Any]:
    return serialize_access_review_packet_snapshots(
        db=db,
        context=context,
        snapshots=[snapshot],
        include_audit_timeline=include_audit_timeline,
    )[0]


def serialize_access_review_packet_snapshots(
    db: Session,
    *,
    context: RequestContext,
    snapshots: list[AccessReviewPacketSnapshot],
    include_audit_timeline: bool = False,
) -> list[dict[str, Any]]:
    if not snapshots:
        return []
    decision_events_by_snapshot_id = _load_latest_decision_events_for_snapshots(
        db=db,
        organization_id=context.organization_id,
        snapshot_ids=[snapshot.id for snapshot in snapshots],
    )
    audit_timeline_by_snapshot_id: dict[Any, list[dict[str, Any]]] = {}
    if include_audit_timeline:
        audit_timeline_by_snapshot_id = _load_audit_timeline_for_snapshots(
            db=db,
            organization_id=context.organization_id,
            snapshot_ids=[snapshot.id for snapshot in snapshots],
        )
    return [
        _serialize_access_review_packet_snapshot(
            snapshot=snapshot,
            decision_event=decision_events_by_snapshot_id.get(snapshot.id),
            audit_timeline=audit_timeline_by_snapshot_id.get(snapshot.id),
        )
        for snapshot in snapshots
    ]


def list_access_review_packet_snapshot_events(
    db: Session,
    *,
    context: RequestContext,
    snapshot_id: Any,
) -> dict[str, Any] | None:
    snapshot = get_access_review_packet_snapshot_by_id(
        db=db,
        context=context,
        snapshot_id=snapshot_id,
    )
    if snapshot is None:
        return None

    stmt = (
        select(AccessReviewPacketSnapshotEvent)
        .where(AccessReviewPacketSnapshotEvent.organization_id == context.organization_id)
        .where(AccessReviewPacketSnapshotEvent.snapshot_id == snapshot.id)
        .order_by(
            AccessReviewPacketSnapshotEvent.created_at.asc(),
            AccessReviewPacketSnapshotEvent.id.asc(),
        )
    )
    events = db.execute(stmt).scalars().all()
    return {
        "snapshot_id": snapshot.id,
        "patient_id": snapshot.patient_id,
        "events": [
            {
                "id": event.id,
                "event_type": event.event_type.value,
                "actor_user_id": event.actor_user_id,
                "created_at": event.created_at,
                "metadata": event.metadata_json or {},
            }
            for event in events
        ],
    }


def get_access_review_packet_snapshot_audit_bundle(
    db: Session,
    *,
    context: RequestContext,
    snapshot_id: Any,
) -> dict[str, Any] | None:
    snapshot = get_access_review_packet_snapshot_by_id(
        db=db,
        context=context,
        snapshot_id=snapshot_id,
    )
    if snapshot is None:
        return None
    if snapshot.review_status != AccessReviewPacketSnapshotReviewStatus.APPROVED:
        raise AccessReviewPacketAuditBundleConflictError(
            "Audit bundle is only available for approved review packet snapshots."
        )

    serialized_snapshot = serialize_access_review_packet_snapshot(
        db=db,
        context=context,
        snapshot=snapshot,
    )
    event_payload = list_access_review_packet_snapshot_events(
        db=db,
        context=context,
        snapshot_id=snapshot.id,
    )
    events = event_payload["events"] if event_payload is not None else []
    decision_events = [
        event
        for event in events
        if event["event_type"] in {"snapshot_approved", "snapshot_rejected"}
    ]
    readiness_reasons = _readiness_reasons_from_event_metadata(events)
    approval_event = next(
        (event for event in reversed(decision_events) if event["event_type"] == "snapshot_approved"),
        None,
    )
    if approval_event is None:
        raise AccessReviewPacketAuditBundleConflictError(
            "Approved snapshot is missing its persisted approval event."
        )

    return {
        "snapshot_id": snapshot.id,
        "patient_id": snapshot.patient_id,
        "organization_id": snapshot.organization_id,
        "review_status": serialized_snapshot["review_status"],
        "review_state": serialized_snapshot["review_state"],
        "approved_at": approval_event["created_at"],
        "approved_by_user_id": approval_event["actor_user_id"],
        "approval_event": approval_event,
        "snapshot_created_at": snapshot.created_at,
        "assigned_reviewer_user_id": snapshot.assigned_reviewer_user_id,
        "packet_json": snapshot.packet_json,
        "packet_markdown": snapshot.packet_markdown,
        "review_checklist": snapshot.packet_json["review_checklist"],
        "readiness_reasons": readiness_reasons,
        "audit_manifest": _build_access_review_packet_snapshot_audit_manifest(
            snapshot=snapshot,
            approval_event=approval_event,
            decision_events=decision_events,
        ),
        "export_metadata": build_access_review_packet_snapshot_export_metadata(
            snapshot_id=snapshot.id,
            export_format="json",
        ),
        "decision_events": decision_events,
    }


def render_access_review_packet_snapshot_audit_bundle_markdown(bundle: dict[str, Any]) -> str:
    approval_event = bundle["approval_event"]
    approval_metadata = approval_event.get("metadata") or {}
    review_state = bundle["review_state"]
    missing_items = approval_metadata.get("missing_checklist_items") or []
    decision_events = bundle.get("decision_events") or []

    lines = [
        "# ACCESS Review Packet Audit Bundle",
        "",
        f"- Snapshot ID: {bundle['snapshot_id']}",
        f"- Patient ID: {bundle['patient_id']}",
        f"- Organization ID: {bundle['organization_id']}",
        f"- Review Status: {_enum_value_or_string(bundle['review_status'])}",
        f"- Review State: {review_state['state']}",
        f"- Approved At: {_render_datetime(bundle['approved_at'])}",
        f"- Approved By User ID: {bundle['approved_by_user_id'] or 'none'}",
        f"- Approval Override Used: {_bool_label(bool(approval_metadata.get('approval_override')))}",
    ]
    override_reason = approval_metadata.get("override_reason")
    if override_reason:
        lines.append(f"- Override Reason: {override_reason}")
    if missing_items:
        lines.append(f"- Missing Checklist Items: {', '.join(str(item) for item in missing_items)}")
    lines.extend(
        [
            "",
            "## Export Metadata",
            f"- Document Title: {bundle['export_metadata']['document_title']}",
            f"- Export Kind: {bundle['export_metadata']['export_kind']}",
            f"- Recommended Filename: {bundle['export_metadata']['recommended_filename']}",
            f"- Content Type: {bundle['export_metadata']['content_type']}",
            f"- Source: {bundle['export_metadata']['source']}",
            f"- Generated At: {_render_datetime(bundle['export_metadata']['generated_at'])}",
            f"- Verification Endpoint: {bundle['export_metadata']['verification_endpoint']}",
            f"- Verification Method: {bundle['export_metadata']['verification_method']}",
            "",
            "## Audit Manifest",
            f"- Snapshot ID: {bundle['audit_manifest']['snapshot_id']}",
            f"- Patient ID: {bundle['audit_manifest']['patient_id']}",
            f"- Review Status: {bundle['audit_manifest']['review_status']}",
            f"- Generated From: {bundle['audit_manifest']['generated_from']}",
            f"- Packet JSON SHA-256: {bundle['audit_manifest']['packet_json_sha256']}",
            f"- Packet Markdown SHA-256: {bundle['audit_manifest']['packet_markdown_sha256']}",
            f"- Decision Event Count: {bundle['audit_manifest']['decision_event_count']}",
            f"- Approval Event ID: {bundle['audit_manifest']['approval_event_id']}",
            f"- Approval Override Used: {_bool_label(bundle['audit_manifest']['approval_override_used'])}",
            "",
            "## Audit Readiness Reasons",
            "| Code | Severity | Label | Detail |",
            "| --- | --- | --- | --- |",
        ]
    )
    for reason in bundle.get("readiness_reasons") or []:
        lines.append(
            "| "
            f"{reason['code']} | "
            f"{_title_case(reason['severity'])} | "
            f"{reason['label']} | "
            f"{reason['detail']} |"
        )
    lines.extend(
        [
            "",
            "## Approval Event",
            f"- Event ID: {approval_event['id']}",
            f"- Event Type: {approval_event['event_type']}",
            f"- Actor User ID: {approval_event['actor_user_id'] or 'none'}",
            f"- Created At: {_render_datetime(approval_event['created_at'])}",
            "",
            "## Review Checklist",
            "| Item | Status | Reason |",
            "| --- | --- | --- |",
        ]
    )
    for item in bundle["review_checklist"]["items"]:
        lines.append(
            f"| {item['label']} | {_title_case(item['status'])} | {item['reason']} |"
        )
    lines.extend(
        [
            "",
            "## Decision Event Trail",
        ]
    )
    if decision_events:
        for event in decision_events:
            metadata = event.get("metadata") or {}
            lines.append(
                "- "
                f"{event['event_type']} "
                f"(id={event['id']}, actor={event['actor_user_id'] or 'none'}, "
                f"created_at={_render_datetime(event['created_at'])}, "
                f"approval_override={str(bool(metadata.get('approval_override'))).lower()})"
            )
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Immutable Review Packet",
            "",
            bundle["packet_markdown"],
        ]
    )
    return "\n".join(lines)


def render_access_review_packet_snapshot_audit_bundle_pdf(bundle: dict[str, Any]) -> bytes:
    markdown_payload = build_access_review_packet_snapshot_audit_bundle_markdown_payload(bundle)
    markdown = render_access_review_packet_snapshot_audit_bundle_markdown(markdown_payload)
    return _render_plain_text_pdf(markdown)


def build_access_review_packet_snapshot_export_metadata(
    *,
    snapshot_id: Any,
    export_format: str,
) -> dict[str, Any]:
    if export_format == "json":
        return _build_access_review_packet_snapshot_export_metadata(
            snapshot_id=snapshot_id,
            content_type="application/json",
            filename_extension="json",
        )
    if export_format == "markdown":
        return _build_access_review_packet_snapshot_export_metadata(
            snapshot_id=snapshot_id,
            content_type="text/markdown",
            filename_extension="md",
        )
    if export_format == "pdf":
        return _build_access_review_packet_snapshot_export_metadata(
            snapshot_id=snapshot_id,
            content_type="application/pdf",
            filename_extension="pdf",
        )
    raise ValueError(f"Unsupported export format: {export_format}")


def record_access_review_packet_snapshot_audit_bundle_export(
    db: Session,
    *,
    context: RequestContext,
    snapshot_id: Any,
    export_format: str,
    export_metadata: dict[str, Any],
) -> None:
    snapshot = get_access_review_packet_snapshot_by_id(
        db=db,
        context=context,
        snapshot_id=snapshot_id,
    )
    if snapshot is None:
        return
    _record_access_review_packet_snapshot_event(
        db=db,
        snapshot=snapshot,
        event_type=AccessReviewPacketSnapshotEventType.AUDIT_BUNDLE_EXPORTED,
        actor_user_id=context.user.id,
        metadata_json={
            "export_format": export_format,
            "snapshot_id": snapshot.id,
            "recommended_filename": export_metadata["recommended_filename"],
            "content_type": export_metadata["content_type"],
            "readiness_reasons": [
                _readiness_reason(
                    code="audit_bundle_exported",
                    severity="satisfied",
                    label="Audit bundle exported",
                    detail="Successful audit bundle export is recorded for this patient.",
                )
            ],
        },
    )
    db.commit()


def _enum_value_or_string(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def verify_access_review_packet_snapshot_audit_manifest(
    db: Session,
    *,
    context: RequestContext,
    snapshot_id: Any,
    submitted_manifest: dict[str, Any],
) -> dict[str, Any] | None:
    bundle = get_access_review_packet_snapshot_audit_bundle(
        db=db,
        context=context,
        snapshot_id=snapshot_id,
    )
    if bundle is None:
        return None
    expected_manifest = bundle["audit_manifest"]
    mismatches = _compare_audit_manifests(
        expected_manifest=expected_manifest,
        submitted_manifest=submitted_manifest,
    )
    return {
        "snapshot_id": bundle["snapshot_id"],
        "verified": len(mismatches) == 0,
        "mismatches": mismatches,
        "expected_manifest": expected_manifest,
    }


def build_access_review_packet_snapshot_audit_bundle_markdown_payload(
    bundle: dict[str, Any]
) -> dict[str, Any]:
    return {
        **bundle,
        "export_metadata": build_access_review_packet_snapshot_export_metadata(
            snapshot_id=bundle["snapshot_id"],
            export_format="markdown",
        ),
    }


def _build_access_review_packet_snapshot_audit_manifest(
    *,
    snapshot: AccessReviewPacketSnapshot,
    approval_event: dict[str, Any],
    decision_events: list[dict[str, Any]],
) -> dict[str, Any]:
    approval_override_used = bool((approval_event.get("metadata") or {}).get("approval_override"))
    return {
        "snapshot_id": snapshot.id,
        "patient_id": snapshot.patient_id,
        "review_status": _enum_value_or_string(snapshot.review_status),
        "generated_from": "persisted_snapshot",
        "packet_json_sha256": _sha256_hexdigest(
            _canonical_json_bytes(snapshot.packet_json)
        ),
        "packet_markdown_sha256": _sha256_hexdigest(
            snapshot.packet_markdown.encode("utf-8")
        ),
        "decision_event_count": len(decision_events),
        "approval_event_id": approval_event["id"],
        "approval_override_used": approval_override_used,
    }


def _build_access_review_packet_snapshot_export_metadata(
    *,
    snapshot_id: Any,
    content_type: str,
    filename_extension: str,
) -> dict[str, Any]:
    return {
        "document_title": "ACCESS Review Packet Audit Bundle",
        "export_kind": "approved_snapshot_audit_bundle",
        "recommended_filename": (
            f"access-review-packet-audit-bundle-{snapshot_id}.{filename_extension}"
        ),
        "content_type": content_type,
        "source": "persisted_snapshot",
        "generated_at": datetime.now(timezone.utc),
        "verification_endpoint": (
            f"/reports/access-review-packet/snapshots/{snapshot_id}/audit-bundle/verify"
        ),
        "verification_method": (
            "Submit audit_manifest from this bundle to the verification endpoint."
        ),
    }


def _render_plain_text_pdf(markdown: str) -> bytes:
    lines = markdown.splitlines() or [""]
    page_width = 612
    page_height = 792
    margin_left = 48
    margin_top = 48
    font_size = 10
    line_height = 14
    usable_height = page_height - (margin_top * 2)
    lines_per_page = max(1, int(usable_height // line_height))
    pages = [
        lines[index : index + lines_per_page]
        for index in range(0, len(lines), lines_per_page)
    ] or [[""]]

    objects: list[bytes] = []
    page_object_numbers: list[int] = []
    content_object_numbers: list[int] = []

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Count 0 /Kids [] >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    for page_lines in pages:
        page_object_numbers.append(len(objects) + 1)
        objects.append(b"")
        content_stream = _build_pdf_page_stream(
            lines=page_lines,
            start_x=margin_left,
            start_y=page_height - margin_top,
            font_size=font_size,
            line_height=line_height,
        )
        content_object_numbers.append(len(objects) + 1)
        objects.append(
            b"<< /Length "
            + str(len(content_stream)).encode("ascii")
            + b" >>\nstream\n"
            + content_stream
            + b"\nendstream"
        )

    kids = " ".join(f"{object_number} 0 R" for object_number in page_object_numbers).encode("ascii")
    objects[1] = (
        b"<< /Type /Pages /Count "
        + str(len(page_object_numbers)).encode("ascii")
        + b" /Kids [ "
        + kids
        + b" ] >>"
    )

    for index, page_object_number in enumerate(page_object_numbers):
        content_object_number = content_object_numbers[index]
        objects[page_object_number - 1] = (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 "
            + str(page_width).encode("ascii")
            + b" "
            + str(page_height).encode("ascii")
            + b"] /Resources << /Font << /F1 3 0 R >> >> /Contents "
            + str(content_object_number).encode("ascii")
            + b" 0 R >>"
        )

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF"
        ).encode("ascii")
    )
    return bytes(pdf)


def _build_pdf_page_stream(
    *,
    lines: list[str],
    start_x: int,
    start_y: int,
    font_size: int,
    line_height: int,
) -> bytes:
    content = bytearray()
    content.extend(b"BT\n")
    content.extend(b"/F1 " + str(font_size).encode("ascii") + b" Tf\n")
    content.extend(
        str(start_x).encode("ascii")
        + b" "
        + str(start_y).encode("ascii")
        + b" Td\n"
    )
    content.extend(str(line_height).encode("ascii") + b" TL\n")
    for line in lines:
        content.extend(b"(" + _escape_pdf_literal_string(line) + b") Tj\n")
        content.extend(b"T*\n")
    content.extend(b"ET")
    return bytes(content)


def _escape_pdf_literal_string(value: str) -> bytes:
    encoded = value.encode("cp1252", errors="replace")
    encoded = encoded.replace(b"\\", b"\\\\")
    encoded = encoded.replace(b"(", b"\\(")
    encoded = encoded.replace(b")", b"\\)")
    return encoded


def _compare_audit_manifests(
    *,
    expected_manifest: dict[str, Any],
    submitted_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []
    for field in (
        "snapshot_id",
        "patient_id",
        "review_status",
        "generated_from",
        "packet_json_sha256",
        "packet_markdown_sha256",
        "decision_event_count",
        "approval_event_id",
        "approval_override_used",
    ):
        expected = _normalize_manifest_value(expected_manifest.get(field))
        actual = _normalize_manifest_value(submitted_manifest.get(field))
        if expected != actual:
            mismatches.append(
                {
                    "field": field,
                    "expected": expected,
                    "actual": actual,
                }
            )
    return mismatches


def _normalize_manifest_value(value: Any) -> str | int | bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if value is None:
        return None
    return str(value)


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def _sha256_hexdigest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def enrich_access_review_packet_patient_backlog_items(
    db: Session,
    *,
    context: RequestContext,
    backlog_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not backlog_items:
        return []
    snapshot_ids = [item["latest_snapshot_id"] for item in backlog_items]
    snapshots = db.execute(
        select(AccessReviewPacketSnapshot).where(
            AccessReviewPacketSnapshot.organization_id == context.organization_id,
            AccessReviewPacketSnapshot.id.in_(snapshot_ids),
        )
    ).scalars().all()
    snapshots_by_id = {snapshot.id: snapshot for snapshot in snapshots}
    decision_events_by_snapshot_id = _load_latest_decision_events_for_snapshots(
        db=db,
        organization_id=context.organization_id,
        snapshot_ids=snapshot_ids,
    )
    enriched: list[dict[str, Any]] = []
    for item in backlog_items:
        snapshot = snapshots_by_id.get(item["latest_snapshot_id"])
        if snapshot is None:
            continue
        enriched.append(
            {
                **item,
                "review_state": _build_access_review_state(
                    snapshot=snapshot,
                    decision_event=decision_events_by_snapshot_id.get(snapshot.id),
                ),
            }
        )
    return enriched


def update_access_review_packet_snapshot_review(
    db: Session,
    *,
    context: RequestContext,
    snapshot_id: Any,
    review_status: str,
    review_note: str | None,
    decision_note: str | None = None,
    override_missing_checklist: bool = False,
    override_reason: str | None = None,
) -> AccessReviewPacketSnapshot | None:
    snapshot = get_access_review_packet_snapshot_by_id(
        db=db,
        context=context,
        snapshot_id=snapshot_id,
    )
    if snapshot is None:
        return None

    normalized_status = AccessReviewPacketSnapshotReviewStatus(review_status)
    normalized_decision_note = (decision_note or "").strip() or None
    normalized_review_note = (review_note or "").strip() or None
    effective_decision_note = normalized_decision_note or normalized_review_note
    previous_status = snapshot.review_status.value
    if snapshot.review_status in {
        AccessReviewPacketSnapshotReviewStatus.APPROVED,
        AccessReviewPacketSnapshotReviewStatus.REJECTED,
    }:
        raise AccessReviewPacketReviewStateConflictError(
            "Terminal review packet snapshots cannot be changed."
        )
    if (
        normalized_status == AccessReviewPacketSnapshotReviewStatus.REJECTED
        and effective_decision_note is None
    ):
        raise AccessReviewPacketReviewValidationError(
            "decision_note or review_note is required when rejecting a snapshot."
        )
    missing_count = _snapshot_review_checklist_missing_count(snapshot)
    missing_items = _snapshot_review_checklist_missing_items(snapshot)
    if (
        normalized_status == AccessReviewPacketSnapshotReviewStatus.APPROVED
        and missing_count > 0
    ):
        if not override_missing_checklist:
            raise AccessReviewPacketApprovalBlockedError(
                "Snapshot cannot be approved while persisted review_checklist has missing items."
            )
        normalized_override_reason = (override_reason or "").strip()
        if not normalized_override_reason:
            raise AccessReviewPacketApprovalBlockedError(
                "override_reason is required when overriding missing review_checklist items."
            )
        if not context.user.is_superuser:
            raise AccessReviewPacketApprovalOverrideAuthorizationError(
                "Superuser privileges required to override missing review_checklist items."
            )
    else:
        normalized_override_reason = (override_reason or "").strip() or None
    snapshot.review_status = normalized_status
    snapshot.review_note = effective_decision_note
    if normalized_status in {
        AccessReviewPacketSnapshotReviewStatus.APPROVED,
        AccessReviewPacketSnapshotReviewStatus.REJECTED,
    }:
        snapshot.reviewed_at = datetime.now(timezone.utc)
        snapshot.reviewed_by_user_id = context.user.id
    else:
        snapshot.reviewed_at = None
        snapshot.reviewed_by_user_id = None

    db.add(snapshot)
    if normalized_status in {
        AccessReviewPacketSnapshotReviewStatus.APPROVED,
        AccessReviewPacketSnapshotReviewStatus.REJECTED,
    }:
        event_type = (
            AccessReviewPacketSnapshotEventType.SNAPSHOT_APPROVED
            if normalized_status == AccessReviewPacketSnapshotReviewStatus.APPROVED
            else AccessReviewPacketSnapshotEventType.SNAPSHOT_REJECTED
        )
        approval_override_used = bool(
            normalized_status == AccessReviewPacketSnapshotReviewStatus.APPROVED
            and missing_count > 0
            and override_missing_checklist
        )
        if normalized_status == AccessReviewPacketSnapshotReviewStatus.REJECTED:
            readiness_state = "rejected"
            audit_bundle_available = False
        elif approval_override_used:
            readiness_state = "approved_with_override"
            audit_bundle_available = True
        else:
            readiness_state = "approved"
            audit_bundle_available = True
        _record_access_review_packet_snapshot_event(
            db=db,
            snapshot=snapshot,
            event_type=event_type,
            actor_user_id=context.user.id,
            metadata_json={
                "previous_review_status": previous_status,
                "new_review_status": normalized_status.value,
                "decision_note": effective_decision_note,
                "review_note": effective_decision_note,
                "approval_override": approval_override_used,
                "override_reason": normalized_override_reason,
                "missing_checklist_items": (
                    missing_items
                    if normalized_status == AccessReviewPacketSnapshotReviewStatus.APPROVED
                    and missing_count > 0
                    else []
                ),
                "readiness_reasons": _build_access_review_packet_snapshot_event_readiness_reasons(
                    snapshot=snapshot,
                    state=readiness_state,
                    audit_bundle_available=audit_bundle_available,
                    audit_bundle_exported=False,
                ),
            },
        )
    db.commit()
    db.refresh(snapshot)
    return snapshot


def update_access_review_packet_snapshot_assignment(
    db: Session,
    *,
    context: RequestContext,
    snapshot_id: Any,
    assigned_reviewer_user_id: Any | None,
) -> AccessReviewPacketSnapshot | None:
    snapshot = get_access_review_packet_snapshot_by_id(
        db=db,
        context=context,
        snapshot_id=snapshot_id,
    )
    if snapshot is None:
        return None

    previous_assigned_reviewer_user_id = snapshot.assigned_reviewer_user_id
    if assigned_reviewer_user_id is None:
        snapshot.assigned_reviewer_user_id = None
    else:
        reviewer = db.execute(
            select(User).where(User.id == assigned_reviewer_user_id)
        ).scalar_one_or_none()
        if reviewer is None or reviewer.organization_id != context.organization_id:
            raise ValueError("Invalid assigned_reviewer_user_id.")
        snapshot.assigned_reviewer_user_id = reviewer.id

    db.add(snapshot)
    _record_access_review_packet_snapshot_event(
        db=db,
        snapshot=snapshot,
        event_type=AccessReviewPacketSnapshotEventType.SNAPSHOT_ASSIGNED,
        actor_user_id=context.user.id,
        metadata_json={
            "previous_assigned_reviewer_user_id": previous_assigned_reviewer_user_id,
            "assigned_reviewer_user_id": snapshot.assigned_reviewer_user_id,
        },
    )
    db.commit()
    db.refresh(snapshot)
    return snapshot


def _record_access_review_packet_snapshot_event(
    db: Session,
    *,
    snapshot: AccessReviewPacketSnapshot,
    event_type: AccessReviewPacketSnapshotEventType,
    actor_user_id: Any | None,
    metadata_json: dict[str, Any] | None = None,
) -> None:
    created_at = datetime.now(timezone.utc)
    db.add(
        AccessReviewPacketSnapshotEvent(
            organization_id=snapshot.organization_id,
            snapshot_id=snapshot.id,
            patient_id=snapshot.patient_id,
            event_type=event_type,
            actor_user_id=actor_user_id,
            metadata_json=_json_safe_value(metadata_json or {}),
            created_at=created_at,
            updated_at=created_at,
        )
    )


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe_value(item) for item in value]
    return value


def _snapshot_review_checklist_missing_count(snapshot: AccessReviewPacketSnapshot) -> int:
    checklist = snapshot.packet_json.get("review_checklist")
    if not isinstance(checklist, dict):
        return 0
    missing_count = checklist.get("missing_count", 0)
    try:
        return int(missing_count)
    except (TypeError, ValueError):
        return 0


def _snapshot_review_checklist_missing_items(snapshot: AccessReviewPacketSnapshot) -> list[str]:
    review_checklist = (snapshot.packet_json or {}).get("review_checklist") or {}
    items = review_checklist.get("items") or []
    missing_items: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("status") != "missing":
            continue
        key = item.get("key")
        if isinstance(key, str) and key:
            missing_items.append(key)
    return missing_items


def _load_exported_snapshot_ids_for_organization(
    db: Session,
    *,
    organization_id: Any,
) -> set[Any]:
    exported_snapshot_ids = db.execute(
        select(AccessReviewPacketSnapshotEvent.snapshot_id)
        .where(AccessReviewPacketSnapshotEvent.organization_id == organization_id)
        .where(
            AccessReviewPacketSnapshotEvent.event_type
            == AccessReviewPacketSnapshotEventType.AUDIT_BUNDLE_EXPORTED
        )
        .distinct()
    ).scalars().all()
    return set(exported_snapshot_ids)


def _load_latest_decision_events_for_snapshots(
    db: Session,
    *,
    organization_id: Any,
    snapshot_ids: list[Any],
) -> dict[Any, AccessReviewPacketSnapshotEvent]:
    if not snapshot_ids:
        return {}
    events = db.execute(
        select(AccessReviewPacketSnapshotEvent)
        .where(AccessReviewPacketSnapshotEvent.organization_id == organization_id)
        .where(AccessReviewPacketSnapshotEvent.snapshot_id.in_(snapshot_ids))
        .where(
            AccessReviewPacketSnapshotEvent.event_type.in_(
                [
                    AccessReviewPacketSnapshotEventType.SNAPSHOT_APPROVED,
                    AccessReviewPacketSnapshotEventType.SNAPSHOT_REJECTED,
                ]
            )
        )
        .order_by(
            AccessReviewPacketSnapshotEvent.snapshot_id.asc(),
            AccessReviewPacketSnapshotEvent.created_at.desc(),
            AccessReviewPacketSnapshotEvent.id.desc(),
        )
    ).scalars().all()
    latest_by_snapshot_id: dict[Any, AccessReviewPacketSnapshotEvent] = {}
    for event in events:
        latest_by_snapshot_id.setdefault(event.snapshot_id, event)
    return latest_by_snapshot_id


def _serialize_access_review_packet_snapshot(
    *,
    snapshot: AccessReviewPacketSnapshot,
    decision_event: AccessReviewPacketSnapshotEvent | None,
    audit_timeline: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    review_state = _build_access_review_state(
        snapshot=snapshot,
        decision_event=decision_event,
    )
    return {
        "id": snapshot.id,
        "patient_id": snapshot.patient_id,
        "organization_id": snapshot.organization_id,
        "generated_at": snapshot.generated_at,
        "created_at": snapshot.created_at,
        "updated_at": snapshot.updated_at,
        "review_readiness_status": snapshot.review_readiness_status,
        "review_status": snapshot.review_status,
        "reviewed_at": snapshot.reviewed_at,
        "reviewed_by_user_id": snapshot.reviewed_by_user_id,
        "assigned_reviewer_user_id": snapshot.assigned_reviewer_user_id,
        "review_note": snapshot.review_note,
        "review_state": review_state,
        "review_action": _build_access_review_action(
            snapshot=snapshot,
            review_state=review_state,
        ),
        "audit_timeline": audit_timeline,
        "packet_json": snapshot.packet_json,
        "packet_markdown": snapshot.packet_markdown,
    }


def _load_audit_timeline_for_snapshots(
    db: Session,
    *,
    organization_id: Any,
    snapshot_ids: list[Any],
) -> dict[Any, list[dict[str, Any]]]:
    if not snapshot_ids:
        return {}
    events = db.execute(
        select(AccessReviewPacketSnapshotEvent)
        .where(AccessReviewPacketSnapshotEvent.organization_id == organization_id)
        .where(AccessReviewPacketSnapshotEvent.snapshot_id.in_(snapshot_ids))
        .order_by(
            AccessReviewPacketSnapshotEvent.snapshot_id.asc(),
            AccessReviewPacketSnapshotEvent.created_at.asc(),
            AccessReviewPacketSnapshotEvent.id.asc(),
        )
    ).scalars().all()
    timeline_by_snapshot_id: dict[Any, list[dict[str, Any]]] = {}
    for event in events:
        timeline_by_snapshot_id.setdefault(event.snapshot_id, []).append(
            {
                "event_type": event.event_type.value,
                "occurred_at": event.created_at,
                "actor_user_id": event.actor_user_id,
                "summary": _build_access_review_audit_timeline_summary(event),
            }
        )
    return timeline_by_snapshot_id


def _build_access_review_audit_timeline_summary(event: AccessReviewPacketSnapshotEvent) -> str:
    if event.event_type == AccessReviewPacketSnapshotEventType.SNAPSHOT_CREATED:
        return "Snapshot created"
    if event.event_type == AccessReviewPacketSnapshotEventType.SNAPSHOT_ASSIGNED:
        return "Snapshot assigned for review"
    if event.event_type == AccessReviewPacketSnapshotEventType.SNAPSHOT_APPROVED:
        return "Snapshot approved"
    if event.event_type == AccessReviewPacketSnapshotEventType.SNAPSHOT_REJECTED:
        return "Snapshot rejected"
    if event.event_type == AccessReviewPacketSnapshotEventType.AUDIT_BUNDLE_EXPORTED:
        export_format = (event.metadata_json or {}).get("export_format")
        if export_format == "json":
            return "Audit bundle exported as JSON"
        if export_format == "markdown":
            return "Audit bundle exported as Markdown"
        if export_format == "pdf":
            return "Audit bundle exported as PDF"
        return "Audit bundle exported"
    return _enum_value_or_string(event.event_type)


def _build_access_review_state(
    *,
    snapshot: AccessReviewPacketSnapshot,
    decision_event: AccessReviewPacketSnapshotEvent | None,
) -> dict[str, Any]:
    missing_items = _snapshot_review_checklist_missing_items(snapshot)
    missing_count = _snapshot_review_checklist_missing_count(snapshot)
    metadata = (decision_event.metadata_json or {}) if decision_event is not None else {}
    approval_override_used = bool(metadata.get("approval_override"))
    last_decision_at = decision_event.created_at if decision_event is not None else None
    last_decision_by_user_id = decision_event.actor_user_id if decision_event is not None else None

    if snapshot.review_status == AccessReviewPacketSnapshotReviewStatus.REJECTED:
        return {
            "state": "rejected",
            "label": "Rejected",
            "next_action": "Address review feedback and create a new immutable snapshot when ready.",
            "is_actionable": False,
            "is_approvable": False,
            "requires_override_for_approval": False,
            "approval_override_used": False,
            "missing_checklist_items": missing_items,
            "assigned_reviewer_user_id": snapshot.assigned_reviewer_user_id,
            "last_decision_at": last_decision_at,
            "last_decision_by_user_id": last_decision_by_user_id,
        }
    if snapshot.review_status == AccessReviewPacketSnapshotReviewStatus.APPROVED:
        if approval_override_used:
            return {
                "state": "approved_with_override",
                "label": "Approved with override",
                "next_action": "Approval exception was recorded; use persisted event metadata for audit review.",
                "is_actionable": False,
                "is_approvable": True,
                "requires_override_for_approval": False,
                "approval_override_used": True,
                "missing_checklist_items": missing_items,
                "assigned_reviewer_user_id": snapshot.assigned_reviewer_user_id,
                "last_decision_at": last_decision_at,
                "last_decision_by_user_id": last_decision_by_user_id,
            }
        return {
            "state": "approved",
            "label": "Approved",
            "next_action": "Packet is approved and ready for downstream audit or payment workflows.",
            "is_actionable": False,
            "is_approvable": True,
            "requires_override_for_approval": False,
            "approval_override_used": False,
            "missing_checklist_items": [],
            "assigned_reviewer_user_id": snapshot.assigned_reviewer_user_id,
            "last_decision_at": last_decision_at,
            "last_decision_by_user_id": last_decision_by_user_id,
        }
    if missing_count > 0:
        return {
            "state": "blocked_missing_evidence",
            "label": "Blocked: missing evidence",
            "next_action": "Reject or request missing evidence; superuser override is available with reason.",
            "is_actionable": True,
            "is_approvable": False,
            "requires_override_for_approval": True,
            "approval_override_used": False,
            "missing_checklist_items": missing_items,
            "assigned_reviewer_user_id": snapshot.assigned_reviewer_user_id,
            "last_decision_at": last_decision_at,
            "last_decision_by_user_id": last_decision_by_user_id,
        }
    if snapshot.assigned_reviewer_user_id is not None:
        return {
            "state": "pending_assigned_ready",
            "label": "Pending: assigned and ready",
            "next_action": "Reviewer can approve or reject this ready snapshot.",
            "is_actionable": True,
            "is_approvable": True,
            "requires_override_for_approval": False,
            "approval_override_used": False,
            "missing_checklist_items": [],
            "assigned_reviewer_user_id": snapshot.assigned_reviewer_user_id,
            "last_decision_at": last_decision_at,
            "last_decision_by_user_id": last_decision_by_user_id,
        }
    return {
        "state": "pending_unassigned",
        "label": "Pending: unassigned",
        "next_action": "Assign a reviewer or review directly if organization workflow allows.",
        "is_actionable": True,
        "is_approvable": True,
        "requires_override_for_approval": False,
        "approval_override_used": False,
        "missing_checklist_items": [],
        "assigned_reviewer_user_id": None,
        "last_decision_at": last_decision_at,
        "last_decision_by_user_id": last_decision_by_user_id,
    }


def _load_outcomes(*, db: Session, patient: Patient) -> list[Outcome]:
    stmt = (
        select(Outcome)
        .where(Outcome.patient_id == patient.id)
        .order_by(Outcome.observed_at, Outcome.id)
    )
    return list(db.execute(stmt).scalars().all())


def _load_signals(*, db: Session, patient: Patient) -> list[PatientSignal]:
    stmt = (
        select(PatientSignal)
        .where(PatientSignal.patient_id == patient.id)
        .order_by(PatientSignal.recorded_at, PatientSignal.id)
    )
    return list(db.execute(stmt).scalars().all())


def _load_tasks(*, db: Session, patient: Patient) -> list[InterventionTask]:
    stmt = select(InterventionTask).where(InterventionTask.patient_id == patient.id)
    return list(db.execute(stmt).scalars().all())


def _load_escalations(*, db: Session, patient: Patient) -> list[PatientEscalation]:
    stmt = select(PatientEscalation).where(PatientEscalation.patient_id == patient.id)
    return list(db.execute(stmt).scalars().all())


def _load_care_updates(*, db: Session, patient: Patient) -> list[CareUpdate]:
    stmt = (
        select(CareUpdate)
        .where(CareUpdate.patient_id == patient.id)
        .order_by(CareUpdate.occurred_at.desc(), CareUpdate.id.desc())
    )
    return list(db.execute(stmt).scalars().all())


def _summarize_outcomes(outcomes: list[Outcome]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Outcome]] = defaultdict(list)
    for outcome in outcomes:
        grouped[outcome.metric_name].append(outcome)

    summaries: list[dict[str, Any]] = []
    for metric_name in sorted(grouped):
        metric_outcomes = sorted(
            grouped[metric_name],
            key=lambda outcome: (_normalize_datetime(outcome.observed_at), str(outcome.id)),
        )
        baseline = metric_outcomes[0]
        latest = metric_outcomes[-1]
        numeric = baseline.value_numeric is not None and latest.value_numeric is not None
        delta = latest.value_numeric - baseline.value_numeric if numeric else None
        summaries.append(
            {
                "metric_name": metric_name,
                "baseline": baseline.value_numeric
                if baseline.value_numeric is not None
                else baseline.value_text,
                "latest": latest.value_numeric if latest.value_numeric is not None else latest.value_text,
                "delta": delta,
                "status": _trend_status(
                    metric_name=metric_name,
                    outcome_count=len(metric_outcomes),
                    delta=delta,
                    numeric=numeric,
                ),
                "direction": _metric_direction(metric_name),
                "baseline_outcome_id": baseline.id,
                "latest_outcome_id": latest.id,
            }
        )
    return summaries


def _trend_status(
    *,
    metric_name: str,
    outcome_count: int,
    delta: float | None,
    numeric: bool,
) -> str:
    if outcome_count < 2:
        return "insufficient_data"
    if not numeric or delta is None:
        return "insufficient_data"
    if delta == 0:
        return "stable"

    direction = _metric_direction(metric_name)
    if direction == "lower_is_better":
        return "improved" if delta < 0 else "worsened"
    if direction == "higher_is_better":
        return "improved" if delta > 0 else "worsened"
    return "stable"


def _metric_direction(metric_name: str) -> str:
    normalized = metric_name.strip().lower()
    if normalized in LOWER_IS_BETTER:
        return "lower_is_better"
    if normalized in HIGHER_IS_BETTER:
        return "higher_is_better"
    return "unknown_direction"


def _derive_intervention_outcome_links(
    *,
    tasks: list[InterventionTask],
    outcomes: list[Outcome],
) -> list[dict[str, Any]]:
    outcomes_by_task: dict[Any, list[Outcome]] = defaultdict(list)
    for outcome in outcomes:
        if outcome.intervention_task_id is not None:
            outcomes_by_task[outcome.intervention_task_id].append(outcome)

    links: list[dict[str, Any]] = []
    for task in sorted(tasks, key=lambda item: (_task_timestamp(item), str(item.id))):
        linked = sorted(
            outcomes_by_task.get(task.id, []),
            key=lambda outcome: (_normalize_datetime(outcome.observed_at), str(outcome.id)),
        )
        if not linked:
            continue

        intervention_timestamp = task.completed_at or task.created_at
        after_flags = [
            _normalize_datetime(outcome.observed_at) >= _normalize_datetime(intervention_timestamp)
            for outcome in linked
            if intervention_timestamp is not None
        ]
        first_lag_hours = None
        if intervention_timestamp is not None:
            first_lag = _normalize_datetime(linked[0].observed_at) - _normalize_datetime(
                intervention_timestamp
            )
            first_lag_hours = first_lag.total_seconds() / 3600

        links.append(
            {
                "intervention_task_id": task.id,
                "intervention_timestamp": intervention_timestamp,
                "linked_outcome_ids": [outcome.id for outcome in linked],
                "linked_outcome_metric_names": sorted({outcome.metric_name for outcome in linked}),
                "outcomes_after_intervention": bool(after_flags) and all(after_flags),
                "first_outcome_lag_hours": first_lag_hours,
                "first_outcome_lag_days": first_lag_hours / 24 if first_lag_hours is not None else None,
            }
        )
    return links


def _summarize_escalation_resolutions(
    escalations: list[PatientEscalation],
) -> list[dict[str, Any]]:
    resolved = [
        escalation
        for escalation in escalations
        if escalation.status == EscalationStatus.RESOLVED and escalation.resolved_at is not None
    ]
    resolved.sort(key=lambda item: (_normalize_datetime(item.resolved_at), str(item.id)), reverse=True)
    return [
        {
            "escalation_id": escalation.id,
            "resolved_at": escalation.resolved_at,
            "resolution_reason": escalation.resolution_reason.value
            if escalation.resolution_reason is not None
            else None,
            "resolution_notes": escalation.resolution_notes,
            "outcome_id": escalation.resolution_outcome_id,
            "care_update_id": escalation.resolution_care_update_id,
        }
        for escalation in resolved
    ]


def _build_escalation_case_summary(
    *,
    escalations: list[PatientEscalation],
    resolution_summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    latest = (
        max(escalations, key=lambda item: (_normalize_datetime(item.triggered_at), str(item.id)))
        if escalations
        else None
    )
    latest_resolution = resolution_summaries[0] if resolution_summaries else None
    return {
        "open_count": sum(1 for escalation in escalations if escalation.status == EscalationStatus.OPEN),
        "resolved_count": sum(
            1 for escalation in escalations if escalation.status == EscalationStatus.RESOLVED
        ),
        "latest_escalation_id": latest.id if latest is not None else None,
        "latest_status": latest.status.value if latest is not None else None,
        "latest_triggered_at": latest.triggered_at if latest is not None else None,
        "latest_resolution": latest_resolution,
    }


def _summarize_interventions(
    *,
    tasks: list[InterventionTask],
    outcomes: list[Outcome],
) -> list[dict[str, Any]]:
    outcome_ids_by_task: dict[Any, list[Any]] = defaultdict(list)
    for outcome in outcomes:
        if outcome.intervention_task_id is not None:
            outcome_ids_by_task[outcome.intervention_task_id].append(outcome.id)

    ordered_tasks = sorted(
        tasks,
        key=lambda task: (_normalize_datetime(task.created_at), str(task.id)),
        reverse=True,
    )
    return [
        {
            "intervention_task_id": task.id,
            "escalation_id": task.escalation_id,
            "status": task.status.value,
            "priority": task.priority.value,
            "title": task.title,
            "created_at": task.created_at,
            "completed_at": task.completed_at,
            "linked_outcome_ids": sorted(
                outcome_ids_by_task.get(task.id, []),
                key=str,
            ),
        }
        for task in ordered_tasks
    ]


def _summarize_latest_care_update(care_updates: list[CareUpdate]) -> dict[str, Any] | None:
    if not care_updates:
        return None
    latest = max(
        care_updates,
        key=lambda item: (_normalize_datetime(item.occurred_at), str(item.id)),
    )
    return {
        "care_update_id": latest.id,
        "occurred_at": latest.occurred_at,
        "care_update_type": latest.care_update_type.value,
        "summary": latest.summary,
        "escalation_id": latest.escalation_id,
        "intervention_task_id": latest.intervention_task_id,
        "outcome_id": latest.outcome_id,
    }


def _build_evidence_completeness(
    *,
    outcomes: list[Outcome],
    care_updates: list[CareUpdate],
    escalation_resolution_summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    has_outcome = bool(outcomes)
    has_care_update = bool(care_updates)
    has_resolution_evidence = any(
        summary["outcome_id"] is not None or summary["care_update_id"] is not None
        for summary in escalation_resolution_summaries
    )
    missing_components: list[str] = []
    if not has_outcome:
        missing_components.append("outcome")
    if not has_care_update:
        missing_components.append("care_update")
    if not has_resolution_evidence:
        missing_components.append("resolution_evidence")
    return {
        "has_outcome": has_outcome,
        "has_care_update": has_care_update,
        "has_resolution_evidence": has_resolution_evidence,
        "missing_components": missing_components,
    }


def _build_review_readiness_summary(
    *,
    outcomes: list[Outcome],
    care_updates: list[CareUpdate],
    tasks: list[InterventionTask],
    escalations: list[PatientEscalation],
    escalation_resolution_summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    has_measured_outcome = bool(outcomes)
    has_care_update = bool(care_updates)
    has_resolution_evidence = any(
        summary["outcome_id"] is not None or summary["care_update_id"] is not None
        for summary in escalation_resolution_summaries
    )
    has_open_work = any(
        escalation.status in {EscalationStatus.OPEN, EscalationStatus.IN_PROGRESS}
        for escalation in escalations
    ) or any(task.status.value in {"open", "in_progress"} for task in tasks)
    latest_outcome_at = outcomes[-1].observed_at if outcomes else None
    latest_care_update_at = care_updates[0].occurred_at if care_updates else None
    latest_resolution_at = (
        escalation_resolution_summaries[0]["resolved_at"]
        if escalation_resolution_summaries
        else None
    )

    if has_open_work:
        readiness_status = "active_open_work"
    elif has_measured_outcome and has_care_update and has_resolution_evidence:
        readiness_status = "ready_for_review"
    else:
        readiness_status = "incomplete"

    return {
        "has_measured_outcome": has_measured_outcome,
        "has_care_update": has_care_update,
        "has_resolution_evidence": has_resolution_evidence,
        "has_open_work": has_open_work,
        "latest_outcome_at": latest_outcome_at,
        "latest_care_update_at": latest_care_update_at,
        "latest_resolution_at": latest_resolution_at,
        "readiness_status": readiness_status,
    }


def _build_review_checklist(
    *,
    signals: list[PatientSignal],
    escalations: list[PatientEscalation],
    tasks: list[InterventionTask],
    outcomes: list[Outcome],
    care_updates: list[CareUpdate],
    escalation_resolution_summaries: list[dict[str, Any]],
    review_readiness: dict[str, Any],
) -> dict[str, Any]:
    has_resolution = any(
        escalation.status == EscalationStatus.RESOLVED or escalation.resolved_at is not None
        for escalation in escalations
    ) or any(task.status.value == "completed" for task in tasks)
    readiness_status = review_readiness["readiness_status"]
    readiness_item_status = {
        "ready_for_review": "ready",
        "active_open_work": "warning",
        "incomplete": "missing",
    }[readiness_status]
    items = [
        _build_review_checklist_item(
            key="has_signal",
            label="Qualifying signal is documented",
            present=bool(signals),
            ready_reason="At least one patient signal is present.",
            missing_reason="No patient signal is documented.",
        ),
        _build_review_checklist_item(
            key="has_escalation",
            label="Escalation is documented",
            present=bool(escalations),
            ready_reason="At least one escalation is present.",
            missing_reason="No escalation is documented.",
        ),
        _build_review_checklist_item(
            key="has_intervention",
            label="Intervention activity is documented",
            present=bool(tasks),
            ready_reason="At least one intervention task is present.",
            missing_reason="No intervention task is documented.",
        ),
        _build_review_checklist_item(
            key="has_outcome",
            label="Measured outcome is documented",
            present=bool(outcomes),
            ready_reason="At least one outcome is present.",
            missing_reason="No measured outcome is documented.",
        ),
        _build_review_checklist_item(
            key="has_care_update",
            label="Care update is documented",
            present=bool(care_updates),
            ready_reason="At least one care update is present.",
            missing_reason="No care update is documented.",
        ),
        _build_review_checklist_item(
            key="has_resolution",
            label="Resolution evidence is documented",
            present=has_resolution,
            ready_reason="A resolved escalation or completed intervention is present.",
            missing_reason="No resolution indicator is documented.",
        ),
        {
            "key": "review_readiness",
            "label": "Review readiness status supports packet review",
            "status": readiness_item_status,
            "reason": _review_readiness_reason(
                readiness_status=readiness_status,
                escalation_resolution_summaries=escalation_resolution_summaries,
            ),
        },
    ]
    ready_count = sum(1 for item in items if item["status"] == "ready")
    warning_count = sum(1 for item in items if item["status"] == "warning")
    missing_count = sum(1 for item in items if item["status"] == "missing")
    overall_status = "missing" if missing_count else "warning" if warning_count else "ready"
    return {
        "overall_status": overall_status,
        "ready_count": ready_count,
        "warning_count": warning_count,
        "missing_count": missing_count,
        "items": items,
    }


def _build_review_checklist_item(
    *,
    key: str,
    label: str,
    present: bool,
    ready_reason: str,
    missing_reason: str,
) -> dict[str, str]:
    return {
        "key": key,
        "label": label,
        "status": "ready" if present else "missing",
        "reason": ready_reason if present else missing_reason,
    }


def _review_readiness_reason(
    *,
    readiness_status: str,
    escalation_resolution_summaries: list[dict[str, Any]],
) -> str:
    if readiness_status == "ready_for_review":
        return "Existing review_readiness is ready_for_review."
    if readiness_status == "active_open_work":
        return "Existing review_readiness indicates active open work remains."
    if escalation_resolution_summaries:
        return "Existing review_readiness is incomplete because evidence is still missing."
    return "Existing review_readiness is incomplete because resolution evidence is missing."


def _task_timestamp(task: InterventionTask) -> datetime:
    return _normalize_datetime(task.completed_at or task.created_at)


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _build_access_review_action(
    *,
    snapshot: AccessReviewPacketSnapshot,
    review_state: dict[str, Any],
) -> dict[str, str] | None:
    state = review_state["state"]
    if state == "blocked_missing_evidence":
        return {
            "action": "missing_evidence",
            "reason": "Snapshot is blocked by missing evidence.",
            "priority": "high",
        }
    if state != "pending_assigned_ready":
        return None
    snapshot_age_days = (
        datetime.now(timezone.utc).date() - _normalize_datetime(snapshot.created_at).date()
    ).days
    if snapshot_age_days > 7:
        return {
            "action": "stale_review",
            "reason": "Snapshot has been pending reviewer action for more than 7 days.",
            "priority": "high",
        }
    return {
        "action": "ready_to_review",
        "reason": "Snapshot is ready for reviewer approval.",
        "priority": "normal",
    }


def _build_access_review_packet_patient_next_step(
    *,
    review_state: dict[str, Any],
    audit_bundle: dict[str, Any],
) -> dict[str, str]:
    state = review_state["state"]
    if state == "pending_unassigned":
        return {
            "action": "assign_reviewer",
            "reason": "Snapshot is pending review but has no assigned reviewer.",
            "priority": "normal",
        }
    if state == "blocked_missing_evidence":
        return {
            "action": "complete_missing_evidence",
            "reason": "Snapshot cannot be approved until missing evidence is resolved.",
            "priority": "high",
        }
    if state == "pending_assigned_ready":
        return {
            "action": "review_snapshot",
            "reason": "Snapshot is assigned and ready for review.",
            "priority": "normal",
        }
    if state in {"approved", "approved_with_override"}:
        if audit_bundle["exported"]:
            return {
                "action": "no_action_needed",
                "reason": "Approved audit bundle has already been exported.",
                "priority": "normal",
            }
        return {
            "action": "export_audit_bundle",
            "reason": "Snapshot is approved and ready for audit bundle export.",
            "priority": "normal",
        }
    return {
        "action": "create_snapshot",
        "reason": "Latest snapshot was rejected; create a new snapshot when evidence is ready.",
        "priority": "normal",
    }


def _build_access_review_packet_patient_completion_summary(
    *,
    snapshot: AccessReviewPacketSnapshot,
    review_state: dict[str, Any],
    audit_bundle: dict[str, Any],
) -> dict[str, Any]:
    state = review_state["state"]
    checklist = snapshot.packet_json.get("review_checklist") or {}
    missing_count = int(checklist.get("missing_count") or 0)
    if state == "blocked_missing_evidence":
        return {
            "status": "incomplete",
            "missing_evidence_count": missing_count,
            "has_required_evidence": False,
            "has_approval": False,
            "has_export": False,
            "reason": "Snapshot is missing required evidence.",
        }
    if state in {"pending_unassigned", "pending_assigned_ready"}:
        return {
            "status": "review_ready",
            "missing_evidence_count": 0,
            "has_required_evidence": True,
            "has_approval": False,
            "has_export": False,
            "reason": "Snapshot has required evidence and is awaiting review.",
        }
    if state in {"approved", "approved_with_override"}:
        if audit_bundle["exported"]:
            return {
                "status": "audit_ready",
                "missing_evidence_count": 0,
                "has_required_evidence": True,
                "has_approval": True,
                "has_export": True,
                "reason": "Approved audit bundle has been exported and is audit-ready.",
            }
        return {
            "status": "approved_not_exported",
            "missing_evidence_count": 0,
            "has_required_evidence": True,
            "has_approval": True,
            "has_export": False,
            "reason": "Snapshot is approved but audit bundle has not been exported.",
        }
    return {
        "status": "rejected",
        "missing_evidence_count": missing_count,
        "has_required_evidence": False,
        "has_approval": False,
        "has_export": False,
        "reason": "Latest snapshot was rejected.",
    }


def _readiness_reason(
    *,
    code: str,
    severity: str,
    label: str,
    detail: str,
) -> dict[str, str]:
    return {
        "code": code,
        "severity": severity,
        "label": label,
        "detail": detail,
    }


def _readiness_reason_severity(checklist_status: str | None) -> str:
    if checklist_status == "ready":
        return "satisfied"
    if checklist_status == "warning":
        return "partial"
    return "missing"


def _build_access_review_packet_snapshot_event_readiness_reasons(
    *,
    snapshot: AccessReviewPacketSnapshot,
    state: str,
    audit_bundle_available: bool,
    audit_bundle_exported: bool,
) -> list[dict[str, str]]:
    return _build_access_review_packet_patient_readiness_reasons(
        snapshot=snapshot,
        review_state={"state": state},
        audit_bundle={
            "available": audit_bundle_available,
            "exported": audit_bundle_exported,
            "last_exported_at": None,
            "export_formats": [],
        },
    )


def _readiness_reasons_from_event_metadata(
    events: list[dict[str, Any]],
) -> list[dict[str, str]]:
    reasons_by_code: dict[str, dict[str, str]] = {}
    ordered_codes: list[str] = []
    for event in events:
        metadata = event.get("metadata") or {}
        event_reasons = metadata.get("readiness_reasons") or []
        if not isinstance(event_reasons, list):
            continue
        for reason in event_reasons:
            if not isinstance(reason, dict):
                continue
            code = reason.get("code")
            if not code:
                continue
            if code not in reasons_by_code:
                ordered_codes.append(code)
            reasons_by_code[code] = {
                "code": str(code),
                "severity": str(reason.get("severity") or ""),
                "label": str(reason.get("label") or ""),
                "detail": str(reason.get("detail") or ""),
            }
    return [reasons_by_code[code] for code in ordered_codes]


def _build_access_review_packet_patient_readiness_reasons_without_snapshot() -> list[dict[str, str]]:
    return [
        _readiness_reason(
            code="snapshot_present",
            severity="missing",
            label="Review packet snapshot",
            detail="No immutable review packet snapshot exists for this patient.",
        ),
        _readiness_reason(
            code="evidence_present",
            severity="missing",
            label="Required evidence",
            detail="Required proof evidence has not been captured in a review packet snapshot.",
        ),
        _readiness_reason(
            code="audit_bundle_available",
            severity="missing",
            label="Audit bundle available",
            detail="Audit bundle export is unavailable until a review packet snapshot is approved.",
        ),
        _readiness_reason(
            code="audit_bundle_exported",
            severity="missing",
            label="Audit bundle exported",
            detail="No successful audit bundle export is recorded for this patient.",
        ),
    ]


def _build_access_review_packet_patient_readiness_reasons(
    *,
    snapshot: AccessReviewPacketSnapshot,
    review_state: dict[str, Any],
    audit_bundle: dict[str, Any],
) -> list[dict[str, str]]:
    checklist = snapshot.packet_json.get("review_checklist") or {}
    checklist_items = {
        item.get("key"): item for item in checklist.get("items", []) if item.get("key")
    }
    missing_count = int(checklist.get("missing_count") or 0)
    warning_count = int(checklist.get("warning_count") or 0)

    def checklist_reason(*, key: str, code: str, label: str) -> dict[str, str]:
        item = checklist_items.get(key) or {}
        return _readiness_reason(
            code=code,
            severity=_readiness_reason_severity(item.get("status")),
            label=label,
            detail=str(item.get("reason") or f"{label} status is not available."),
        )

    reasons = [
        checklist_reason(
            key="has_signal",
            code="signal_present",
            label="Signal",
        ),
        checklist_reason(
            key="has_escalation",
            code="escalation_present",
            label="Escalation",
        ),
        checklist_reason(
            key="has_intervention",
            code="intervention_present",
            label="Intervention",
        ),
        checklist_reason(
            key="has_outcome",
            code="outcome_present",
            label="Outcome",
        ),
        _readiness_reason(
            code="evidence_present",
            severity=(
                "missing"
                if missing_count > 0
                else "partial"
                if warning_count > 0
                else "satisfied"
            ),
            label="Required evidence",
            detail=(
                "Review packet is missing required evidence."
                if missing_count > 0
                else "Review packet has warning-level evidence gaps."
                if warning_count > 0
                else "Review packet required evidence is satisfied."
            ),
        ),
        _readiness_reason(
            code="snapshot_present",
            severity="satisfied",
            label="Review packet snapshot",
            detail="Immutable review packet snapshot exists for this patient.",
        ),
    ]

    state = review_state["state"]
    if state == "rejected":
        reasons.append(
            _readiness_reason(
                code="review_rejected",
                severity="blocked",
                label="Review rejected",
                detail="Latest review packet snapshot was rejected.",
            )
        )
    elif state == "approved_with_override":
        reasons.append(
            _readiness_reason(
                code="review_override_approved",
                severity="partial",
                label="Override approval",
                detail="Latest review packet snapshot was approved with override or superuser review.",
            )
        )
    elif state == "approved":
        reasons.append(
            _readiness_reason(
                code="review_approved",
                severity="satisfied",
                label="Review approved",
                detail="Latest review packet snapshot is approved.",
            )
        )
    else:
        reasons.append(
            _readiness_reason(
                code="review_approved",
                severity="missing" if state != "blocked_missing_evidence" else "blocked",
                label="Review approved",
                detail="Review packet approval is required before audit bundle export.",
            )
        )

    if audit_bundle["available"]:
        reasons.append(
            _readiness_reason(
                code="audit_bundle_available",
                severity="satisfied",
                label="Audit bundle available",
                detail="Approved review packet snapshot can support audit bundle export.",
            )
        )
    elif state == "blocked_missing_evidence":
        reasons.append(
            _readiness_reason(
                code="audit_bundle_blocked_missing_evidence",
                severity="blocked",
                label="Audit bundle blocked",
                detail="Audit bundle export is blocked until missing evidence is resolved.",
            )
        )
    elif state == "rejected":
        reasons.append(
            _readiness_reason(
                code="audit_bundle_blocked_review_rejected",
                severity="blocked",
                label="Audit bundle blocked",
                detail="Audit bundle export is blocked because the latest review packet was rejected.",
            )
        )
    else:
        reasons.append(
            _readiness_reason(
                code="audit_bundle_available",
                severity="missing",
                label="Audit bundle available",
                detail="Audit bundle export is unavailable until the review packet is approved.",
            )
        )

    reasons.append(
        _readiness_reason(
            code="audit_bundle_exported",
            severity="satisfied" if audit_bundle["exported"] else "missing",
            label="Audit bundle exported",
            detail=(
                "Successful audit bundle export is recorded for this patient."
                if audit_bundle["exported"]
                else "No successful audit bundle export is recorded for this patient."
            ),
        )
    )
    return reasons


def _build_access_review_packet_patient_audit_status_without_snapshot(
    *,
    patient_id: Any,
) -> dict[str, Any]:
    return {
        "patient_id": patient_id,
        "has_snapshot": False,
        "latest_snapshot_id": None,
        "latest_snapshot_created_at": None,
        "review_status": None,
        "review_state": None,
        "assigned_reviewer_user_id": None,
        "review_action": None,
        "audit_bundle": {
            "available": False,
            "exported": False,
            "last_exported_at": None,
            "export_formats": [],
        },
        "next_step": {
            "action": "create_snapshot",
            "priority": "normal",
            "reason": "No review packet snapshot exists for this patient.",
        },
        "completion_summary": {
            "status": "not_started",
            "missing_evidence_count": 0,
            "has_required_evidence": False,
            "has_approval": False,
            "has_export": False,
            "reason": "No review packet snapshot exists for this patient.",
        },
        "readiness_reasons": (
            _build_access_review_packet_patient_readiness_reasons_without_snapshot()
        ),
    }


def _build_access_review_packet_patient_audit_status_for_snapshot(
    db: Session,
    *,
    context: RequestContext,
    snapshot: AccessReviewPacketSnapshot,
) -> dict[str, Any]:
    serialized_snapshot = serialize_access_review_packet_snapshot(
        db=db,
        context=context,
        snapshot=snapshot,
    )
    export_events = db.execute(
        select(AccessReviewPacketSnapshotEvent)
        .where(AccessReviewPacketSnapshotEvent.organization_id == context.organization_id)
        .where(AccessReviewPacketSnapshotEvent.snapshot_id == snapshot.id)
        .where(
            AccessReviewPacketSnapshotEvent.event_type
            == AccessReviewPacketSnapshotEventType.AUDIT_BUNDLE_EXPORTED
        )
        .order_by(
            AccessReviewPacketSnapshotEvent.created_at.asc(),
            AccessReviewPacketSnapshotEvent.id.asc(),
        )
    ).scalars().all()
    export_formats = [
        export_format
        for export_format in ("json", "markdown", "pdf")
        if any((event.metadata_json or {}).get("export_format") == export_format for event in export_events)
    ]
    review_state = serialized_snapshot["review_state"]
    audit_bundle = {
        "available": review_state["state"] in {"approved", "approved_with_override"},
        "exported": bool(export_events),
        "last_exported_at": export_events[-1].created_at if export_events else None,
        "export_formats": export_formats,
    }
    return {
        "patient_id": snapshot.patient_id,
        "has_snapshot": True,
        "latest_snapshot_id": snapshot.id,
        "latest_snapshot_created_at": snapshot.created_at,
        "review_status": serialized_snapshot["review_status"],
        "review_state": review_state,
        "assigned_reviewer_user_id": snapshot.assigned_reviewer_user_id,
        "review_action": serialized_snapshot["review_action"],
        "audit_bundle": audit_bundle,
        "next_step": _build_access_review_packet_patient_next_step(
            review_state=review_state,
            audit_bundle=audit_bundle,
        ),
        "completion_summary": _build_access_review_packet_patient_completion_summary(
            snapshot=snapshot,
            review_state=review_state,
            audit_bundle=audit_bundle,
        ),
        "readiness_reasons": _build_access_review_packet_patient_readiness_reasons(
            snapshot=snapshot,
            review_state=review_state,
            audit_bundle=audit_bundle,
        ),
    }


def _build_access_review_packet_audit_readiness_item(
    *,
    audit_status: dict[str, Any],
) -> dict[str, Any]:
    return {
        "patient_id": audit_status["patient_id"],
        "latest_snapshot_id": audit_status["latest_snapshot_id"],
        "latest_snapshot_created_at": audit_status["latest_snapshot_created_at"],
        "review_status": audit_status["review_status"],
        "review_state": audit_status["review_state"]["state"],
        "completion_status": audit_status["completion_summary"]["status"],
        "assigned_reviewer_user_id": audit_status["assigned_reviewer_user_id"],
        "next_step": audit_status["next_step"],
        "audit_bundle": audit_status["audit_bundle"],
    }


def _build_access_review_packet_audit_readiness_status_counts(
    items: list[dict[str, Any]],
) -> dict[str, int]:
    counts = {
        "incomplete_count": 0,
        "review_ready_count": 0,
        "approved_not_exported_count": 0,
        "audit_ready_count": 0,
        "rejected_count": 0,
    }
    for item in items:
        key = f"{item['completion_status']}_count"
        if key in counts:
            counts[key] += 1
    return counts


def _list_latest_access_review_packet_snapshots_for_organization(
    db: Session,
    *,
    context: RequestContext,
) -> list[AccessReviewPacketSnapshot]:
    backlog_items = list_access_review_packet_snapshot_patient_backlog_for_organization(
        db=db,
        context=context,
        limit=10_000,
        offset=0,
    )
    snapshot_ids = [item["latest_snapshot_id"] for item in backlog_items]
    if not snapshot_ids:
        return []
    snapshots = db.execute(
        select(AccessReviewPacketSnapshot).where(
            AccessReviewPacketSnapshot.organization_id == context.organization_id,
            AccessReviewPacketSnapshot.id.in_(snapshot_ids),
        )
    ).scalars().all()
    snapshots_by_id = {snapshot.id: snapshot for snapshot in snapshots}
    return [
        snapshots_by_id[snapshot_id]
        for snapshot_id in snapshot_ids
        if snapshot_id in snapshots_by_id
    ]


def _bool_label(value: bool) -> str:
    return "yes" if value else "no"


def _title_case(value: str) -> str:
    return value.replace("_", " ").title()


def _render_latest_outcome_line(latest_outcome: dict[str, Any] | None) -> str:
    if latest_outcome is None:
        return "- None"
    return (
        "- "
        f"{latest_outcome['metric_name']}: latest={latest_outcome['latest']}, "
        f"baseline={latest_outcome['baseline']}, "
        f"delta={latest_outcome['delta']}, status={latest_outcome['status']}"
    )


def _render_latest_care_update_line(latest_care_update: dict[str, Any] | None) -> str:
    if latest_care_update is None:
        return "- None"
    return (
        "- "
        f"{_render_datetime(latest_care_update['occurred_at'])}: "
        f"{latest_care_update['summary']} "
        f"({latest_care_update['care_update_type']})"
    )


def _render_latest_resolution_line(latest_resolution: dict[str, Any] | None) -> str:
    if latest_resolution is None:
        return "- None"
    return (
        "- "
        f"{_render_datetime(latest_resolution['resolved_at'])}: "
        f"{latest_resolution['resolution_reason'] or 'unknown_reason'}; "
        f"outcome_id={latest_resolution['outcome_id']}; "
        f"care_update_id={latest_resolution['care_update_id']}"
    )


def _render_datetime(value: datetime | None) -> str:
    if value is None:
        return "none"
    normalized = _normalize_datetime(value).isoformat()
    return normalized.replace("+00:00", "Z")
