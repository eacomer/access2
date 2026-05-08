from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timedelta, timezone
from io import StringIO
from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.access_review_packet_snapshot import (
    AccessReviewPacketSnapshot,
    AccessReviewPacketSnapshotEvent,
    AccessReviewPacketSnapshotEventType,
)
from tests.test_access_case_summary import _create_care_update
from tests.test_care_updates import _bootstrap_patient_env, _create_escalation, _create_task
from tests.test_outcomes import _create_outcome
from tests.test_patients import auth_headers, create_patient_for_user, create_user_for_org


def _get_review_packet(client: TestClient, headers: dict[str, str], patient_id: str) -> dict:
    resp = client.get(
        f"/api/v1/reports/access-review-packet/{patient_id}",
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _get_review_packet_markdown(client: TestClient, headers: dict[str, str], patient_id: str) -> str:
    resp = client.get(
        f"/api/v1/reports/access-review-packet/{patient_id}/markdown",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/markdown")
    return resp.text


def _create_review_packet_snapshot(
    client: TestClient,
    headers: dict[str, str],
    patient_id: str,
) -> dict:
    resp = client.post(
        f"/api/v1/reports/access-review-packet/{patient_id}/snapshots",
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def _get_review_packet_snapshot_detail(
    client: TestClient,
    headers: dict[str, str],
    snapshot_id: str,
) -> dict:
    resp = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot_id}",
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _get_review_packet_snapshot_markdown(
    client: TestClient,
    headers: dict[str, str],
    snapshot_id: str,
) -> str:
    resp = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot_id}/markdown",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/markdown")
    return resp.text


def _get_review_packet_snapshot_events(
    client: TestClient,
    headers: dict[str, str],
    snapshot_id: str,
) -> dict:
    resp = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot_id}/events",
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _get_review_packet_snapshot_audit_bundle(
    client: TestClient,
    headers: dict[str, str],
    snapshot_id: str,
) -> dict:
    resp = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot_id}/audit-bundle",
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _get_review_packet_snapshot_audit_bundle_markdown(
    client: TestClient,
    headers: dict[str, str],
    snapshot_id: str,
) -> str:
    resp = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot_id}/audit-bundle/markdown",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/markdown")
    return resp.text


def _get_review_packet_snapshot_audit_bundle_pdf(
    client: TestClient,
    headers: dict[str, str],
    snapshot_id: str,
):
    resp = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot_id}/audit-bundle/pdf",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")
    return resp


def _verify_review_packet_snapshot_audit_manifest(
    client: TestClient,
    headers: dict[str, str],
    snapshot_id: str,
    audit_manifest: dict,
) -> dict:
    resp = client.post(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot_id}/audit-bundle/verify",
        json={"audit_manifest": audit_manifest},
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _review_checklist_by_key(packet: dict) -> dict[str, dict]:
    return {item["key"]: item for item in packet["review_checklist"]["items"]}


def _expected_missing_checklist_keys(snapshot: dict) -> list[str]:
    return [
        item["key"]
        for item in snapshot["packet_json"]["review_checklist"]["items"]
        if item["status"] == "missing"
    ]


def _readiness_reasons_by_code(payload: dict) -> dict[str, dict]:
    return {item["code"]: item for item in payload["readiness_reasons"]}


def _expected_packet_json_sha256(packet_json: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            packet_json,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _expected_packet_markdown_sha256(packet_markdown: str) -> str:
    return hashlib.sha256(packet_markdown.encode("utf-8")).hexdigest()


def _export_events(payload: dict) -> list[dict]:
    return [event for event in payload["events"] if event["event_type"] == "audit_bundle_exported"]


def _timeline_event_types(snapshot: dict) -> list[str]:
    return [item["event_type"] for item in snapshot["audit_timeline"]]


def _prepare_review_ready_patient(
    client: TestClient,
    headers: dict[str, str],
    patient_id: str,
    *,
    metric_name: str = "systolic_bp",
    value_numeric: float = 120,
    summary: str = "Review-ready care update",
    resolution_reason: str = "clinically_stable",
    resolution_notes: str = "Prepared for review packet.",
) -> dict:
    base = datetime.now(timezone.utc).replace(microsecond=0)
    escalation_id = _create_escalation(client, headers, patient_id)
    task_id = _create_task(client, headers, escalation_id)
    outcome = _create_outcome(
        client,
        headers,
        patient_id,
        intervention_task_id=task_id,
        metric_name=metric_name,
        value_numeric=value_numeric,
        observed_at=base + timedelta(days=1),
    )
    care_update = _create_care_update(
        client,
        headers,
        patient_id,
        summary=summary,
        occurred_at=base + timedelta(days=2),
        escalation_id=escalation_id,
        intervention_task_id=task_id,
        outcome_id=outcome["id"],
    )
    resolve_resp = client.post(
        f"/api/v1/escalations/{escalation_id}/resolve",
        json={
            "resolution_reason": resolution_reason,
            "resolution_notes": resolution_notes,
            "outcome_id": outcome["id"],
            "care_update_id": care_update["id"],
            "resolved_at": (base + timedelta(days=3)).isoformat(),
        },
        headers=headers,
    )
    assert resolve_resp.status_code == 200
    complete_resp = client.post(
        f"/api/v1/tasks/{task_id}/complete",
        json={"completion_note": "Prepared for review packet."},
        headers=headers,
    )
    assert complete_resp.status_code == 200
    return {
        "escalation_id": escalation_id,
        "task_id": task_id,
        "outcome": outcome,
        "care_update": care_update,
    }


def _update_review_packet_snapshot_review(
    client: TestClient,
    headers: dict[str, str],
    snapshot_id: str,
    *,
    review_status: str,
    review_note: str | None = None,
    decision_note: str | None = None,
    override_missing_checklist: bool = False,
    override_reason: str | None = None,
) -> dict:
    resp = client.patch(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot_id}/review",
        json={
            "review_status": review_status,
            "review_note": review_note,
            "decision_note": decision_note,
            "override_missing_checklist": override_missing_checklist,
            "override_reason": override_reason,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _update_review_packet_snapshot_review_raw(
    client: TestClient,
    headers: dict[str, str],
    snapshot_id: str,
    *,
    review_status: str,
    review_note: str | None = None,
    decision_note: str | None = None,
    override_missing_checklist: bool = False,
    override_reason: str | None = None,
):
    return client.patch(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot_id}/review",
        json={
            "review_status": review_status,
            "review_note": review_note,
            "decision_note": decision_note,
            "override_missing_checklist": override_missing_checklist,
            "override_reason": override_reason,
        },
        headers=headers,
    )


def _update_review_packet_snapshot_assignment(
    client: TestClient,
    headers: dict[str, str],
    snapshot_id: str,
    *,
    assigned_reviewer_user_id: str | None,
) -> dict:
    resp = client.patch(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot_id}/assignment",
        json={"assigned_reviewer_user_id": assigned_reviewer_user_id},
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _get_review_packet_snapshot_summary(
    client: TestClient,
    headers: dict[str, str],
    patient_id: str,
) -> dict:
    resp = client.get(
        f"/api/v1/reports/access-review-packet/{patient_id}/snapshots/summary",
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _get_review_packet_snapshot_organization_summary(
    client: TestClient,
    headers: dict[str, str],
) -> dict:
    resp = client.get(
        "/api/v1/reports/access-review-packet/snapshots/summary",
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _get_review_packet_snapshot_organization_list(
    client: TestClient,
    headers: dict[str, str],
    query: str = "",
) -> list[dict]:
    suffix = f"?{query}" if query else ""
    resp = client.get(
        f"/api/v1/reports/access-review-packet/snapshots{suffix}",
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _get_review_packet_snapshot_latest_actionable(
    client: TestClient,
    headers: dict[str, str],
    query: str = "",
) -> list[dict]:
    suffix = f"?{query}" if query else ""
    resp = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/latest-actionable{suffix}",
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _get_review_packet_patient_audit_status(
    client: TestClient,
    headers: dict[str, str],
    patient_id: str,
) -> dict:
    resp = client.get(
        f"/api/v1/reports/access-review-packet/patients/{patient_id}/audit-status",
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _get_review_packet_snapshot_my_pending(
    client: TestClient,
    headers: dict[str, str],
    query: str = "",
) -> list[dict]:
    suffix = f"?{query}" if query else ""
    resp = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/my-pending{suffix}",
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _get_review_packet_reviewer_my_summary(
    client: TestClient,
    headers: dict[str, str],
) -> dict:
    resp = client.get(
        "/api/v1/reports/access-review-packet/reviewer/my-summary",
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _get_review_packet_snapshot_queue_summary(
    client: TestClient,
    headers: dict[str, str],
) -> dict:
    resp = client.get(
        "/api/v1/reports/access-review-packet/snapshots/queue-summary",
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _get_review_packet_audit_readiness(
    client: TestClient,
    headers: dict[str, str],
    query: str = "",
) -> dict:
    suffix = f"?{query}" if query else ""
    resp = client.get(
        f"/api/v1/reports/access-review-packet/audit-readiness{suffix}",
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _get_review_packet_audit_readiness_csv(
    client: TestClient,
    headers: dict[str, str],
    query: str = "",
):
    suffix = f"?{query}" if query else ""
    resp = client.get(
        f"/api/v1/reports/access-review-packet/audit-readiness/export.csv{suffix}",
        headers=headers,
    )
    assert resp.status_code == 200
    return resp


def _get_review_packet_snapshot_patient_backlog(
    client: TestClient,
    headers: dict[str, str],
    query: str = "",
) -> list[dict]:
    suffix = f"?{query}" if query else ""
    resp = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/patient-backlog{suffix}",
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _get_review_packet_snapshot_patient_backlog_detail(
    client: TestClient,
    headers: dict[str, str],
    patient_id: str,
    query: str = "",
) -> dict:
    suffix = f"?{query}" if query else ""
    resp = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/patient-backlog/{patient_id}{suffix}",
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _get_review_packet_snapshot_patient_backlog_latest(
    client: TestClient,
    headers: dict[str, str],
    patient_id: str,
    query: str = "",
) -> dict:
    suffix = f"?{query}" if query else ""
    resp = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/patient-backlog/{patient_id}/latest{suffix}",
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def test_access_review_packet_ready_for_review_matches_underlying_reports(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-ready")
    base = datetime.now(timezone.utc).replace(microsecond=0)

    escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    task_id = _create_task(client, env["headers"], escalation_id)
    outcome = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        intervention_task_id=task_id,
        metric_name="systolic_bp",
        value_numeric=124,
        observed_at=base + timedelta(days=1),
    )
    care_update = _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="Packet-ready follow-up",
        occurred_at=base + timedelta(days=2),
        escalation_id=escalation_id,
        intervention_task_id=task_id,
        outcome_id=outcome["id"],
    )
    resolve_resp = client.post(
        f"/api/v1/escalations/{escalation_id}/resolve",
        json={
            "resolution_reason": "clinically_stable",
            "resolution_notes": "Ready for review packet.",
            "outcome_id": outcome["id"],
            "care_update_id": care_update["id"],
            "resolved_at": (base + timedelta(days=3)).isoformat(),
        },
        headers=env["headers"],
    )
    assert resolve_resp.status_code == 200
    complete_resp = client.post(
        f"/api/v1/tasks/{task_id}/complete",
        json={"completion_note": "Task completed for packet."},
        headers=env["headers"],
    )
    assert complete_resp.status_code == 200

    packet = _get_review_packet(client, env["headers"], env["patient_id"])
    markdown = _get_review_packet_markdown(client, env["headers"], env["patient_id"])
    case_summary = client.get(
        f"/api/v1/reports/access-case-summary/{env['patient_id']}",
        headers=env["headers"],
    ).json()
    evidence_report = client.get(
        f"/api/v1/reports/access-evidence/{env['patient_id']}",
        headers=env["headers"],
    ).json()

    assert packet["patient_id"] == env["patient_id"]
    assert packet["generated_at"] is not None
    assert packet["review_readiness"]["readiness_status"] == "ready_for_review"
    assert packet["review_readiness"] == case_summary["review_readiness"]
    assert packet["review_readiness"] == evidence_report["review_readiness"]
    assert packet["review_checklist"] == case_summary["review_checklist"]
    assert packet["case_summary"] == case_summary
    assert packet["evidence_report"] == evidence_report
    checklist = _review_checklist_by_key(packet)
    assert set(checklist) == {
        "has_signal",
        "has_escalation",
        "has_intervention",
        "has_outcome",
        "has_care_update",
        "has_resolution",
        "review_readiness",
    }
    assert packet["review_checklist"]["overall_status"] == "ready"
    assert packet["review_checklist"]["ready_count"] == len(packet["review_checklist"]["items"])
    assert packet["review_checklist"]["warning_count"] == 0
    assert packet["review_checklist"]["missing_count"] == 0
    assert checklist["has_signal"]["status"] == "ready"
    assert checklist["review_readiness"]["status"] == "ready"
    assert env["patient_id"] in markdown
    assert "Generated At:" in markdown
    assert "Review Readiness: ready_for_review" in markdown
    assert "## Review Checklist" in markdown
    assert "| Qualifying signal is documented | Ready |" in markdown
    assert "Outcome Present: yes" in markdown
    assert "Care Update Present: yes" in markdown
    assert "Resolution Evidence Present: yes" in markdown
    assert "Latest Outcome" in markdown
    assert "systolic_bp" in markdown
    assert "Packet-ready follow-up" in markdown
    assert "clinically_stable" in markdown
    assert "Intervention Summary" in markdown
    assert "Audit Evidence" in markdown


def test_access_review_packet_active_open_work_for_mixed_history(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-mixed")
    base = datetime.now(timezone.utc).replace(microsecond=0)

    resolved_escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    resolved_task_id = _create_task(client, env["headers"], resolved_escalation_id)
    outcome = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        intervention_task_id=resolved_task_id,
        metric_name="systolic_bp",
        value_numeric=126,
        observed_at=base + timedelta(days=1),
    )
    care_update = _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="Resolved history note",
        occurred_at=base + timedelta(days=2),
        escalation_id=resolved_escalation_id,
        intervention_task_id=resolved_task_id,
        outcome_id=outcome["id"],
    )
    resolve_resp = client.post(
        f"/api/v1/escalations/{resolved_escalation_id}/resolve",
        json={
            "resolution_reason": "issue_addressed",
            "resolution_notes": "Resolved before new open work.",
            "outcome_id": outcome["id"],
            "care_update_id": care_update["id"],
        },
        headers=env["headers"],
    )
    assert resolve_resp.status_code == 200
    complete_resp = client.post(
        f"/api/v1/tasks/{resolved_task_id}/complete",
        json={"completion_note": "Resolved task complete."},
        headers=env["headers"],
    )
    assert complete_resp.status_code == 200

    open_escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    _create_task(client, env["headers"], open_escalation_id)

    packet = _get_review_packet(client, env["headers"], env["patient_id"])
    markdown = _get_review_packet_markdown(client, env["headers"], env["patient_id"])

    assert packet["review_readiness"]["readiness_status"] == "active_open_work"
    assert packet["review_readiness"] == packet["case_summary"]["review_readiness"]
    assert packet["review_readiness"] == packet["evidence_report"]["review_readiness"]
    assert packet["case_summary"]["escalation_summary"]["latest_resolution"] is not None
    assert packet["evidence_report"]["escalation_resolution_summaries"]
    assert "Review Readiness: active_open_work" in markdown
    assert "Resolved history note" in markdown
    assert "issue_addressed" in markdown


def test_access_review_packet_incomplete_without_resolution_evidence(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-incomplete")
    base = datetime.now(timezone.utc).replace(microsecond=0)

    outcome = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        metric_name="systolic_bp",
        value_numeric=132,
        observed_at=base,
    )
    _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="Evidence without closure",
        occurred_at=base + timedelta(hours=1),
        outcome_id=outcome["id"],
    )

    packet = _get_review_packet(client, env["headers"], env["patient_id"])
    markdown = _get_review_packet_markdown(client, env["headers"], env["patient_id"])

    assert packet["review_readiness"]["readiness_status"] == "incomplete"
    assert packet["review_readiness"] == packet["case_summary"]["review_readiness"]
    assert packet["review_readiness"] == packet["evidence_report"]["review_readiness"]
    checklist = _review_checklist_by_key(packet)
    assert packet["review_checklist"]["overall_status"] == "missing"
    assert packet["review_checklist"]["missing_count"] >= 1
    assert checklist["has_resolution"]["status"] == "missing"
    assert checklist["review_readiness"]["status"] == "missing"
    assert "Review Readiness: incomplete" in markdown
    assert "## Review Checklist" in markdown
    assert "Resolution Evidence Present: no" in markdown
    assert "Missing Components: resolution_evidence" in markdown


def test_access_review_packet_respects_tenant_scope(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-scope")
    other = _bootstrap_patient_env(client, db_session, slug="review-packet-scope-other")

    resp = client.get(
        f"/api/v1/reports/access-review-packet/{env['patient_id']}",
        headers=other["headers"],
    )
    assert resp.status_code == 403

    markdown_resp = client.get(
        f"/api/v1/reports/access-review-packet/{env['patient_id']}/markdown",
        headers=other["headers"],
    )
    assert markdown_resp.status_code == 403

    snapshot_resp = client.post(
        f"/api/v1/reports/access-review-packet/{env['patient_id']}/snapshots",
        headers=other["headers"],
    )
    assert snapshot_resp.status_code == 403


def test_access_review_packet_snapshot_persists_same_packet_json_and_markdown(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-snapshot")
    base = datetime.now(timezone.utc).replace(microsecond=0)

    escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    task_id = _create_task(client, env["headers"], escalation_id)
    outcome = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        intervention_task_id=task_id,
        metric_name="systolic_bp",
        value_numeric=121,
        observed_at=base + timedelta(days=1),
    )
    care_update = _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="Snapshot care update",
        occurred_at=base + timedelta(days=2),
        escalation_id=escalation_id,
        intervention_task_id=task_id,
        outcome_id=outcome["id"],
    )
    resolve_resp = client.post(
        f"/api/v1/escalations/{escalation_id}/resolve",
        json={
            "resolution_reason": "clinically_stable",
            "resolution_notes": "Snapshot packet ready.",
            "outcome_id": outcome["id"],
            "care_update_id": care_update["id"],
            "resolved_at": (base + timedelta(days=3)).isoformat(),
        },
        headers=env["headers"],
    )
    assert resolve_resp.status_code == 200
    complete_resp = client.post(
        f"/api/v1/tasks/{task_id}/complete",
        json={"completion_note": "Snapshot task completed."},
        headers=env["headers"],
    )
    assert complete_resp.status_code == 200

    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    assert snapshot["patient_id"] == env["patient_id"]
    assert snapshot["organization_id"] == str(env["organization"].id)
    assert snapshot["review_readiness_status"] == "ready_for_review"
    assert snapshot["review_status"] == "pending_review"
    assert snapshot["reviewed_at"] is None
    assert snapshot["reviewed_by_user_id"] is None
    assert snapshot["review_note"] is None
    assert snapshot["packet_json"]["patient_id"] == env["patient_id"]
    assert snapshot["packet_json"]["review_readiness"]["readiness_status"] == "ready_for_review"
    assert snapshot["packet_json"]["review_checklist"]["overall_status"] == "ready"
    assert snapshot["packet_json"]["generated_at"].rstrip("Z") == snapshot["generated_at"].rstrip("Z")
    assert snapshot["packet_json"]["case_summary"]["review_readiness"] == snapshot["packet_json"][
        "review_readiness"
    ]
    assert snapshot["packet_json"]["case_summary"]["review_checklist"] == snapshot["packet_json"][
        "review_checklist"
    ]
    assert snapshot["packet_json"]["evidence_report"]["review_readiness"] == snapshot["packet_json"][
        "review_readiness"
    ]
    assert snapshot["packet_json"]["case_summary"]["latest_care_update"]["summary"] == (
        "Snapshot care update"
    )
    assert "Review Readiness: ready_for_review" in snapshot["packet_markdown"]
    assert "## Review Checklist" in snapshot["packet_markdown"]
    assert env["patient_id"] in snapshot["packet_markdown"]
    assert snapshot["generated_at"] in snapshot["packet_markdown"]
    assert "Snapshot care update" in snapshot["packet_markdown"]
    assert "clinically_stable" in snapshot["packet_markdown"]


def test_access_review_packet_snapshot_creation_writes_snapshot_created_event(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-snapshot-created-event")

    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    payload = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])

    assert payload["snapshot_id"] == snapshot["id"]
    assert payload["patient_id"] == env["patient_id"]
    assert len(payload["events"]) == 1
    event = payload["events"][0]
    assert event["event_type"] == "snapshot_created"
    assert event["actor_user_id"] == str(env["user"].id)
    metadata = event["metadata"]
    assert metadata["review_readiness_status"] == snapshot["review_readiness_status"]
    assert metadata["review_status"] == "pending_review"
    reasons = _readiness_reasons_by_code(metadata)
    assert reasons["snapshot_present"]["severity"] == "satisfied"
    assert reasons["audit_bundle_exported"]["severity"] == "missing"


def test_access_review_packet_snapshot_review_can_be_approved_and_rejected_without_mutating_packet(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-snapshot-review")
    _prepare_review_ready_patient(
        client,
        env["headers"],
        env["patient_id"],
        summary="Review mutation safety packet",
    )
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    original_packet_json = snapshot["packet_json"]
    original_packet_markdown = snapshot["packet_markdown"]

    approved = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
    )
    assert approved["review_status"] == "approved"
    assert approved["reviewed_at"] is not None
    assert approved["reviewed_by_user_id"] == str(env["user"].id)
    assert approved["review_note"] is None
    assert approved["packet_json"] == original_packet_json
    assert approved["packet_markdown"] == original_packet_markdown

    rejected = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="rejected",
        review_note="Needs additional documentation.",
    )
    assert rejected["review_status"] == "rejected"
    assert rejected["reviewed_at"] is not None
    assert rejected["reviewed_by_user_id"] == str(env["user"].id)
    assert rejected["review_note"] == "Needs additional documentation."
    assert rejected["packet_json"] == original_packet_json
    assert rejected["packet_markdown"] == original_packet_markdown

    detail = _get_review_packet_snapshot_detail(client, env["headers"], snapshot["id"])
    assert detail["review_status"] == "rejected"
    assert detail["review_note"] == "Needs additional documentation."
    assert detail["packet_json"] == original_packet_json
    assert detail["packet_markdown"] == original_packet_markdown


def test_access_review_packet_snapshot_review_state_blocked_missing_evidence(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-review-state-blocked")
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    assert snapshot["review_state"]["state"] == "blocked_missing_evidence"
    assert snapshot["review_state"]["is_actionable"] is True
    assert snapshot["review_state"]["is_approvable"] is False
    assert snapshot["review_state"]["requires_override_for_approval"] is True
    assert snapshot["review_state"]["approval_override_used"] is False
    assert snapshot["review_state"]["last_decision_at"] is None
    assert snapshot["review_state"]["last_decision_by_user_id"] is None
    assert snapshot["review_state"]["missing_checklist_items"] == _expected_missing_checklist_keys(snapshot)


def test_access_review_packet_snapshot_review_state_pending_assigned_ready(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-review-state-assigned-ready")
    reviewer = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-review-state-assigned-ready-reviewer@example.com",
        password="Secret123!",
    )
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    assigned = _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        snapshot["id"],
        assigned_reviewer_user_id=str(reviewer.id),
    )

    assert assigned["review_state"]["state"] == "pending_assigned_ready"
    assert assigned["review_state"]["is_approvable"] is True
    assert assigned["review_state"]["requires_override_for_approval"] is False
    assert assigned["review_state"]["approval_override_used"] is False
    assert assigned["review_state"]["assigned_reviewer_user_id"] == str(reviewer.id)
    assert assigned["review_state"]["missing_checklist_items"] == []


def test_access_review_packet_snapshot_review_state_pending_unassigned(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-review-state-unassigned-ready")
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    assert snapshot["review_state"]["state"] == "pending_unassigned"
    assert snapshot["review_state"]["is_approvable"] is True
    assert snapshot["review_state"]["requires_override_for_approval"] is False
    assert snapshot["review_state"]["approval_override_used"] is False
    assert snapshot["review_state"]["assigned_reviewer_user_id"] is None
    assert snapshot["review_state"]["missing_checklist_items"] == []
    assert snapshot["review_action"] is None


def test_access_review_packet_snapshot_review_action_is_null_for_approved_and_rejected_states(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-review-action-terminal")
    _prepare_review_ready_patient(
        client,
        env["headers"],
        env["patient_id"],
        summary="Review action terminal state packet",
    )
    approved = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    approved = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        approved["id"],
        review_status="approved",
    )
    assert approved["review_state"]["state"] == "approved"
    assert approved["review_action"] is None

    rejected = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    rejected = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        rejected["id"],
        review_status="rejected",
        review_note="Rejected review action terminal state packet.",
    )
    assert rejected["review_state"]["state"] == "rejected"
    assert rejected["review_action"] is None


def test_access_review_packet_snapshot_review_action_is_null_for_approved_with_override(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-review-action-override")
    override_user = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-review-action-override-superuser@example.com",
        password="Secret123!",
        is_superuser=True,
    )
    override_headers = auth_headers(client, override_user.email, "Secret123!")
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    approved = _update_review_packet_snapshot_review(
        client,
        override_headers,
        snapshot["id"],
        review_status="approved",
        decision_note="Approved under documented review-action exception.",
        override_missing_checklist=True,
        override_reason="Compliance deadline exception.",
    )

    assert approved["review_state"]["state"] == "approved_with_override"
    assert approved["review_action"] is None


def test_access_review_packet_snapshot_approval_allowed_when_persisted_checklist_has_no_missing_items(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-approval-gate-ready")
    base = datetime.now(timezone.utc).replace(microsecond=0)

    escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    task_id = _create_task(client, env["headers"], escalation_id)
    outcome = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        intervention_task_id=task_id,
        metric_name="systolic_bp",
        value_numeric=119,
        observed_at=base + timedelta(days=1),
    )
    care_update = _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="Approval gate ready packet",
        occurred_at=base + timedelta(days=2),
        escalation_id=escalation_id,
        intervention_task_id=task_id,
        outcome_id=outcome["id"],
    )
    resolve_resp = client.post(
        f"/api/v1/escalations/{escalation_id}/resolve",
        json={
            "resolution_reason": "clinically_stable",
            "resolution_notes": "Approval gate ready.",
            "outcome_id": outcome["id"],
            "care_update_id": care_update["id"],
            "resolved_at": (base + timedelta(days=3)).isoformat(),
        },
        headers=env["headers"],
    )
    assert resolve_resp.status_code == 200
    complete_resp = client.post(
        f"/api/v1/tasks/{task_id}/complete",
        json={"completion_note": "Approval gate task complete."},
        headers=env["headers"],
    )
    assert complete_resp.status_code == 200

    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    assert snapshot["packet_json"]["review_checklist"]["missing_count"] == 0

    approved = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        decision_note="Complete packet approved.",
    )
    events = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])

    assert approved["review_status"] == "approved"
    assert approved["review_state"]["state"] == "approved"
    assert approved["review_state"]["approval_override_used"] is False
    approved_event = next(event for event in events["events"] if event["event_type"] == "snapshot_approved")
    metadata = approved_event["metadata"]
    assert {key: metadata[key] for key in (
        "previous_review_status",
        "new_review_status",
        "decision_note",
        "review_note",
        "approval_override",
        "override_reason",
        "missing_checklist_items",
    )} == {
        "previous_review_status": "pending_review",
        "new_review_status": "approved",
        "decision_note": "Complete packet approved.",
        "review_note": "Complete packet approved.",
        "approval_override": False,
        "override_reason": None,
        "missing_checklist_items": [],
    }
    reasons = _readiness_reasons_by_code(metadata)
    assert reasons["review_approved"]["severity"] == "satisfied"
    assert reasons["audit_bundle_available"]["severity"] == "satisfied"


def test_access_review_packet_snapshot_approval_blocked_when_persisted_checklist_has_missing_items(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-approval-gate-missing")
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    original_packet_json = snapshot["packet_json"]
    original_packet_markdown = snapshot["packet_markdown"]

    assert snapshot["packet_json"]["review_checklist"]["missing_count"] > 0

    blocked = _update_review_packet_snapshot_review_raw(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
    )
    detail = _get_review_packet_snapshot_detail(client, env["headers"], snapshot["id"])
    events = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])

    assert blocked.status_code == 409
    assert detail["review_status"] == "pending_review"
    assert detail["packet_json"] == original_packet_json
    assert detail["packet_markdown"] == original_packet_markdown
    assert not any(event["event_type"] == "snapshot_approved" for event in events["events"])


def test_access_review_packet_snapshot_override_approval_requires_override_reason(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-approval-gate-override-reason")
    override_user = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-override-reason@example.com",
        password="Secret123!",
        is_superuser=True,
    )
    override_headers = auth_headers(client, override_user.email, "Secret123!")
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    original_packet_json = snapshot["packet_json"]
    original_packet_markdown = snapshot["packet_markdown"]

    blocked = _update_review_packet_snapshot_review_raw(
        client,
        override_headers,
        snapshot["id"],
        review_status="approved",
        override_missing_checklist=True,
        override_reason="   ",
    )
    detail = _get_review_packet_snapshot_detail(client, env["headers"], snapshot["id"])
    events = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])

    assert blocked.status_code == 409
    assert detail["review_status"] == "pending_review"
    assert detail["packet_json"] == original_packet_json
    assert detail["packet_markdown"] == original_packet_markdown
    assert not any(event["event_type"] == "snapshot_approved" for event in events["events"])


def test_access_review_packet_snapshot_override_approval_requires_superuser(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-approval-gate-override-auth")
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    original_packet_json = snapshot["packet_json"]
    original_packet_markdown = snapshot["packet_markdown"]

    forbidden = _update_review_packet_snapshot_review_raw(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        override_missing_checklist=True,
        override_reason="Operational exception approved.",
    )
    detail = _get_review_packet_snapshot_detail(client, env["headers"], snapshot["id"])
    events = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])

    assert forbidden.status_code == 403
    assert detail["review_status"] == "pending_review"
    assert detail["packet_json"] == original_packet_json
    assert detail["packet_markdown"] == original_packet_markdown
    assert not any(event["event_type"] == "snapshot_approved" for event in events["events"])


def test_access_review_packet_snapshot_override_approval_succeeds_for_superuser_with_reason(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-approval-gate-override-success")
    override_user = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-override-success@example.com",
        password="Secret123!",
        is_superuser=True,
    )
    override_headers = auth_headers(client, override_user.email, "Secret123!")
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    original_packet_json = snapshot["packet_json"]
    original_packet_markdown = snapshot["packet_markdown"]

    approved = _update_review_packet_snapshot_review(
        client,
        override_headers,
        snapshot["id"],
        review_status="approved",
        decision_note="Approved under documented exception.",
        override_missing_checklist=True,
        override_reason="Time-sensitive payer submission with documented missing closure evidence.",
    )
    events = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])
    approved_event = next(event for event in events["events"] if event["event_type"] == "snapshot_approved")

    assert approved["review_status"] == "approved"
    assert approved["review_note"] == "Approved under documented exception."
    assert approved["reviewed_by_user_id"] == str(override_user.id)
    assert approved["review_state"]["state"] == "approved_with_override"
    assert approved["review_state"]["approval_override_used"] is True
    assert approved["packet_json"] == original_packet_json
    assert approved["packet_markdown"] == original_packet_markdown
    metadata = approved_event["metadata"]
    assert {key: metadata[key] for key in (
        "previous_review_status",
        "new_review_status",
        "decision_note",
        "review_note",
        "approval_override",
        "override_reason",
        "missing_checklist_items",
    )} == {
        "previous_review_status": "pending_review",
        "new_review_status": "approved",
        "decision_note": "Approved under documented exception.",
        "review_note": "Approved under documented exception.",
        "approval_override": True,
        "override_reason": "Time-sensitive payer submission with documented missing closure evidence.",
        "missing_checklist_items": ["has_signal", "has_escalation", "has_intervention", "has_outcome", "has_care_update", "has_resolution", "review_readiness"],
    }
    reasons = _readiness_reasons_by_code(metadata)
    assert reasons["review_override_approved"]["severity"] == "partial"
    assert reasons["audit_bundle_available"]["severity"] == "satisfied"


def test_access_review_packet_snapshot_rejection_allowed_when_persisted_checklist_has_missing_items(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-approval-gate-reject")
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    rejected = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="rejected",
        review_note="Checklist evidence missing.",
    )
    events = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])

    assert rejected["review_status"] == "rejected"
    assert rejected["review_state"]["state"] == "rejected"
    assert any(event["event_type"] == "snapshot_rejected" for event in events["events"])


def test_access_review_packet_snapshot_approval_gate_uses_persisted_snapshot_only(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-approval-gate-persisted")
    base = datetime.now(timezone.utc).replace(microsecond=0)
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    assert snapshot["packet_json"]["review_checklist"]["missing_count"] > 0

    escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    task_id = _create_task(client, env["headers"], escalation_id)
    outcome = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        intervention_task_id=task_id,
        metric_name="systolic_bp",
        value_numeric=117,
        observed_at=base + timedelta(days=1),
    )
    care_update = _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="Added after snapshot",
        occurred_at=base + timedelta(days=2),
        escalation_id=escalation_id,
        intervention_task_id=task_id,
        outcome_id=outcome["id"],
    )
    resolve_resp = client.post(
        f"/api/v1/escalations/{escalation_id}/resolve",
        json={
            "resolution_reason": "issue_addressed",
            "resolution_notes": "Evidence added after snapshot.",
            "outcome_id": outcome["id"],
            "care_update_id": care_update["id"],
            "resolved_at": (base + timedelta(days=3)).isoformat(),
        },
        headers=env["headers"],
    )
    assert resolve_resp.status_code == 200
    complete_resp = client.post(
        f"/api/v1/tasks/{task_id}/complete",
        json={"completion_note": "Completed after snapshot."},
        headers=env["headers"],
    )
    assert complete_resp.status_code == 200

    blocked = _update_review_packet_snapshot_review_raw(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
    )
    detail = _get_review_packet_snapshot_detail(client, env["headers"], snapshot["id"])
    events = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])

    assert blocked.status_code == 409
    assert detail["review_status"] == "pending_review"
    assert detail["packet_json"]["review_checklist"]["missing_count"] > 0
    assert not any(event["event_type"] == "snapshot_approved" for event in events["events"])


def test_access_review_packet_snapshot_review_state_uses_persisted_decision_event_metadata(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-review-state-last-decision")
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    approved = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        decision_note="Decision metadata check.",
    )
    payload = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])
    decision_event = payload["events"][-1]

    assert approved["review_state"]["last_decision_at"] == decision_event["created_at"]
    assert approved["review_state"]["last_decision_by_user_id"] == decision_event["actor_user_id"]


def test_access_review_packet_snapshot_review_state_read_does_not_mutate_packet(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-review-state-immutable")
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    original_packet_json = snapshot["packet_json"]
    original_packet_markdown = snapshot["packet_markdown"]

    detail = _get_review_packet_snapshot_detail(client, env["headers"], snapshot["id"])

    assert detail["review_state"]["state"] == "blocked_missing_evidence"
    assert detail["packet_json"] == original_packet_json
    assert detail["packet_markdown"] == original_packet_markdown


def test_access_review_packet_snapshot_detail_includes_audit_timeline(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-timeline-detail")
    reviewer = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-audit-timeline-detail-reviewer@example.com",
        password="Secret123!",
    )
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        snapshot["id"],
        assigned_reviewer_user_id=str(reviewer.id),
    )
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        decision_note="Approved for audit timeline detail.",
    )
    _get_review_packet_snapshot_audit_bundle(client, env["headers"], snapshot["id"])
    _get_review_packet_snapshot_audit_bundle_markdown(client, env["headers"], snapshot["id"])
    _get_review_packet_snapshot_audit_bundle_pdf(client, env["headers"], snapshot["id"])

    detail = _get_review_packet_snapshot_detail(client, env["headers"], snapshot["id"])

    assert detail["audit_timeline"] is not None
    assert _timeline_event_types(detail) == [
        "snapshot_created",
        "snapshot_assigned",
        "snapshot_approved",
        "audit_bundle_exported",
        "audit_bundle_exported",
        "audit_bundle_exported",
    ]
    summaries = [item["summary"] for item in detail["audit_timeline"]]
    assert summaries == [
        "Snapshot created",
        "Snapshot assigned for review",
        "Snapshot approved",
        "Audit bundle exported as JSON",
        "Audit bundle exported as Markdown",
        "Audit bundle exported as PDF",
    ]


def test_access_review_packet_snapshot_detail_audit_timeline_does_not_create_new_events(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-timeline-immutable")
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    events_before = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])

    detail = _get_review_packet_snapshot_detail(client, env["headers"], snapshot["id"])
    events_after = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])

    assert detail["audit_timeline"] is not None
    assert events_after == events_before


def test_access_review_packet_snapshot_audit_bundle_returns_approved_snapshot(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-bundle-approved")
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    approved = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        decision_note="Approved for audit bundle.",
    )

    bundle = _get_review_packet_snapshot_audit_bundle(client, env["headers"], snapshot["id"])

    assert bundle["snapshot_id"] == snapshot["id"]
    assert bundle["patient_id"] == env["patient_id"]
    assert bundle["organization_id"] == str(env["organization"].id)
    assert bundle["review_status"] == "approved"
    assert bundle["review_state"]["state"] == "approved"
    assert bundle["approved_at"] == approved["review_state"]["last_decision_at"]
    assert bundle["approved_by_user_id"] == approved["review_state"]["last_decision_by_user_id"]
    assert bundle["packet_json"] == approved["packet_json"]
    assert bundle["packet_markdown"] == approved["packet_markdown"]
    assert bundle["review_checklist"] == approved["packet_json"]["review_checklist"]
    bundle_reasons = _readiness_reasons_by_code(bundle)
    assert bundle_reasons["signal_present"]["severity"] == "satisfied"
    assert bundle_reasons["evidence_present"]["severity"] == "satisfied"
    assert bundle_reasons["review_approved"]["severity"] == "satisfied"
    assert bundle_reasons["audit_bundle_available"]["severity"] == "satisfied"
    assert bundle_reasons["audit_bundle_exported"]["severity"] == "missing"
    assert [event["event_type"] for event in bundle["decision_events"]] == ["snapshot_approved"]
    assert bundle["approval_event"]["event_type"] == "snapshot_approved"
    assert bundle["approval_event"]["metadata"]["approval_override"] is False
    approval_reasons = _readiness_reasons_by_code(bundle["approval_event"]["metadata"])
    assert approval_reasons["review_approved"]["severity"] == "satisfied"
    assert approval_reasons["audit_bundle_available"]["severity"] == "satisfied"
    assert bundle["export_metadata"]["document_title"] == "ACCESS Review Packet Audit Bundle"
    assert bundle["export_metadata"]["export_kind"] == "approved_snapshot_audit_bundle"
    assert (
        bundle["export_metadata"]["recommended_filename"]
        == f"access-review-packet-audit-bundle-{snapshot['id']}.json"
    )
    assert bundle["export_metadata"]["content_type"] == "application/json"
    assert bundle["export_metadata"]["source"] == "persisted_snapshot"
    assert bundle["export_metadata"]["generated_at"] is not None
    assert (
        bundle["export_metadata"]["verification_endpoint"]
        == f"/reports/access-review-packet/snapshots/{snapshot['id']}/audit-bundle/verify"
    )
    assert (
        bundle["export_metadata"]["verification_method"]
        == "Submit audit_manifest from this bundle to the verification endpoint."
    )
    assert bundle["audit_manifest"] == {
        "snapshot_id": snapshot["id"],
        "patient_id": env["patient_id"],
        "review_status": "approved",
        "generated_from": "persisted_snapshot",
        "packet_json_sha256": _expected_packet_json_sha256(approved["packet_json"]),
        "packet_markdown_sha256": _expected_packet_markdown_sha256(approved["packet_markdown"]),
        "decision_event_count": 1,
        "approval_event_id": bundle["approval_event"]["id"],
        "approval_override_used": False,
    }
    events = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])
    export_metadata = _export_events(events)[-1]["metadata"]
    assert export_metadata["export_format"] == "json"
    assert export_metadata["snapshot_id"] == snapshot["id"]
    assert (
        export_metadata["recommended_filename"]
        == f"access-review-packet-audit-bundle-{snapshot['id']}.json"
    )
    assert export_metadata["content_type"] == "application/json"
    export_reasons = _readiness_reasons_by_code(export_metadata)
    assert export_reasons["audit_bundle_exported"]["severity"] == "satisfied"


def test_access_review_packet_snapshot_audit_bundle_returns_override_metadata(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-bundle-override")
    override_user = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-audit-bundle-override-superuser@example.com",
        password="Secret123!",
        is_superuser=True,
    )
    override_headers = auth_headers(client, override_user.email, "Secret123!")
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    _update_review_packet_snapshot_review(
        client,
        override_headers,
        snapshot["id"],
        review_status="approved",
        decision_note="Override approval for audit bundle.",
        override_missing_checklist=True,
        override_reason="Compliance deadline exception.",
    )
    bundle = _get_review_packet_snapshot_audit_bundle(client, env["headers"], snapshot["id"])

    assert bundle["review_state"]["state"] == "approved_with_override"
    assert bundle["approval_event"]["metadata"]["approval_override"] is True
    assert bundle["approval_event"]["metadata"]["override_reason"] == "Compliance deadline exception."
    assert bundle["approval_event"]["metadata"]["missing_checklist_items"] == _expected_missing_checklist_keys(snapshot)
    assert bundle["audit_manifest"]["approval_override_used"] is True
    override_reasons = _readiness_reasons_by_code(bundle)
    assert override_reasons["review_override_approved"]["severity"] == "partial"
    assert override_reasons["audit_bundle_available"]["severity"] == "satisfied"


def test_access_review_packet_snapshot_audit_bundle_manifest_hashes_are_deterministic(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-bundle-manifest-deterministic")
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        decision_note="Deterministic manifest approval.",
    )

    first = _get_review_packet_snapshot_audit_bundle(client, env["headers"], snapshot["id"])
    second = _get_review_packet_snapshot_audit_bundle(client, env["headers"], snapshot["id"])

    assert first["audit_manifest"]["packet_json_sha256"] == second["audit_manifest"]["packet_json_sha256"]
    assert first["audit_manifest"]["packet_markdown_sha256"] == second["audit_manifest"]["packet_markdown_sha256"]
    assert first["audit_manifest"] == second["audit_manifest"]
    assert first["export_metadata"]["generated_at"] != second["export_metadata"]["generated_at"]


def test_access_review_packet_snapshot_audit_bundle_manifest_matches_persisted_snapshot_hashes(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-bundle-manifest-hashes")
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    approved = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        decision_note="Expected manifest hash approval.",
    )

    bundle = _get_review_packet_snapshot_audit_bundle(client, env["headers"], snapshot["id"])

    assert bundle["audit_manifest"]["packet_json_sha256"] == _expected_packet_json_sha256(
        approved["packet_json"]
    )
    assert bundle["audit_manifest"]["packet_markdown_sha256"] == _expected_packet_markdown_sha256(
        approved["packet_markdown"]
    )
    assert bundle["audit_manifest"]["decision_event_count"] == len(bundle["decision_events"])
    assert bundle["audit_manifest"]["approval_event_id"] == bundle["approval_event"]["id"]


def test_access_review_packet_snapshot_audit_manifest_verifies_when_matching(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-verify-match")
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        decision_note="Verify matching manifest approval.",
    )
    bundle = _get_review_packet_snapshot_audit_bundle(client, env["headers"], snapshot["id"])

    result = _verify_review_packet_snapshot_audit_manifest(
        client,
        env["headers"],
        snapshot["id"],
        bundle["audit_manifest"],
    )

    assert result["snapshot_id"] == snapshot["id"]
    assert result["verified"] is True
    assert result["mismatches"] == []
    assert result["expected_manifest"] == bundle["audit_manifest"]
    events = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])
    assert len(_export_events(events)) == 1


def test_access_review_packet_snapshot_audit_manifest_verifies_bundle_manifest_despite_export_metadata_variation(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-verify-export-metadata-variation")
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        decision_note="Verify manifest independent of export metadata.",
    )

    first = _get_review_packet_snapshot_audit_bundle(client, env["headers"], snapshot["id"])
    second = _get_review_packet_snapshot_audit_bundle(client, env["headers"], snapshot["id"])

    assert first["export_metadata"]["generated_at"] != second["export_metadata"]["generated_at"]
    assert first["audit_manifest"] == second["audit_manifest"]

    result = _verify_review_packet_snapshot_audit_manifest(
        client,
        env["headers"],
        snapshot["id"],
        first["audit_manifest"],
    )

    assert result["verified"] is True
    assert result["mismatches"] == []
    assert result["expected_manifest"] == first["audit_manifest"]


def test_access_review_packet_snapshot_audit_manifest_detects_packet_json_hash_mismatch(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-verify-json-hash")
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        decision_note="Verify json hash mismatch approval.",
    )
    bundle = _get_review_packet_snapshot_audit_bundle(client, env["headers"], snapshot["id"])
    submitted = dict(bundle["audit_manifest"])
    submitted["packet_json_sha256"] = "bad-json-hash"

    result = _verify_review_packet_snapshot_audit_manifest(
        client,
        env["headers"],
        snapshot["id"],
        submitted,
    )

    assert result["verified"] is False
    assert result["mismatches"] == [
        {
            "field": "packet_json_sha256",
            "expected": bundle["audit_manifest"]["packet_json_sha256"],
            "actual": "bad-json-hash",
        }
    ]


def test_access_review_packet_snapshot_audit_manifest_detects_packet_markdown_hash_mismatch(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-verify-markdown-hash")
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        decision_note="Verify markdown hash mismatch approval.",
    )
    bundle = _get_review_packet_snapshot_audit_bundle(client, env["headers"], snapshot["id"])
    submitted = dict(bundle["audit_manifest"])
    submitted["packet_markdown_sha256"] = "bad-markdown-hash"

    result = _verify_review_packet_snapshot_audit_manifest(
        client,
        env["headers"],
        snapshot["id"],
        submitted,
    )

    assert result["verified"] is False
    assert result["mismatches"] == [
        {
            "field": "packet_markdown_sha256",
            "expected": bundle["audit_manifest"]["packet_markdown_sha256"],
            "actual": "bad-markdown-hash",
        }
    ]


def test_access_review_packet_snapshot_audit_manifest_detects_decision_event_count_mismatch(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-verify-decision-count")
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        decision_note="Verify decision event count mismatch approval.",
    )
    bundle = _get_review_packet_snapshot_audit_bundle(client, env["headers"], snapshot["id"])
    submitted = dict(bundle["audit_manifest"])
    submitted["decision_event_count"] = bundle["audit_manifest"]["decision_event_count"] + 1

    result = _verify_review_packet_snapshot_audit_manifest(
        client,
        env["headers"],
        snapshot["id"],
        submitted,
    )

    assert result["verified"] is False
    assert result["mismatches"] == [
        {
            "field": "decision_event_count",
            "expected": bundle["audit_manifest"]["decision_event_count"],
            "actual": bundle["audit_manifest"]["decision_event_count"] + 1,
        }
    ]


def test_access_review_packet_snapshot_audit_manifest_detects_approval_event_id_mismatch(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-verify-approval-event")
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        decision_note="Verify approval event mismatch approval.",
    )
    bundle = _get_review_packet_snapshot_audit_bundle(client, env["headers"], snapshot["id"])
    submitted = dict(bundle["audit_manifest"])
    submitted["approval_event_id"] = "00000000-0000-0000-0000-000000000000"

    result = _verify_review_packet_snapshot_audit_manifest(
        client,
        env["headers"],
        snapshot["id"],
        submitted,
    )

    assert result["verified"] is False
    assert result["mismatches"] == [
        {
            "field": "approval_event_id",
            "expected": bundle["audit_manifest"]["approval_event_id"],
            "actual": "00000000-0000-0000-0000-000000000000",
        }
    ]


def test_access_review_packet_snapshot_audit_manifest_verifies_override_approved_snapshot(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-verify-override")
    override_user = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-audit-verify-override-superuser@example.com",
        password="Secret123!",
        is_superuser=True,
    )
    override_headers = auth_headers(client, override_user.email, "Secret123!")
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_review(
        client,
        override_headers,
        snapshot["id"],
        review_status="approved",
        decision_note="Verify override manifest approval.",
        override_missing_checklist=True,
        override_reason="Manifest verification override exception.",
    )
    bundle = _get_review_packet_snapshot_audit_bundle(client, env["headers"], snapshot["id"])

    result = _verify_review_packet_snapshot_audit_manifest(
        client,
        env["headers"],
        snapshot["id"],
        bundle["audit_manifest"],
    )

    assert result["verified"] is True
    assert result["mismatches"] == []
    assert result["expected_manifest"]["approval_override_used"] is True


def test_access_review_packet_snapshot_audit_manifest_pending_snapshot_conflicts(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-verify-pending")
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    resp = client.post(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot['id']}/audit-bundle/verify",
        json={
            "audit_manifest": {
                "snapshot_id": snapshot["id"],
                "patient_id": env["patient_id"],
                "review_status": "approved",
                "generated_from": "persisted_snapshot",
                "packet_json_sha256": "x",
                "packet_markdown_sha256": "y",
                "decision_event_count": 0,
                "approval_event_id": snapshot["id"],
                "approval_override_used": False,
            }
        },
        headers=env["headers"],
    )
    assert resp.status_code == 409


def test_access_review_packet_snapshot_audit_manifest_rejected_snapshot_conflicts(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-verify-rejected")
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="rejected",
        review_note="Rejected manifest verification validation.",
    )

    resp = client.post(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot['id']}/audit-bundle/verify",
        json={
            "audit_manifest": {
                "snapshot_id": snapshot["id"],
                "patient_id": env["patient_id"],
                "review_status": "approved",
                "generated_from": "persisted_snapshot",
                "packet_json_sha256": "x",
                "packet_markdown_sha256": "y",
                "decision_event_count": 0,
                "approval_event_id": snapshot["id"],
                "approval_override_used": False,
            }
        },
        headers=env["headers"],
    )
    assert resp.status_code == 409


def test_access_review_packet_snapshot_audit_manifest_respects_tenant_scope(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-verify-scope")
    other = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-verify-scope-other")
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        decision_note="Scoped manifest verification approval.",
    )
    bundle = _get_review_packet_snapshot_audit_bundle(client, env["headers"], snapshot["id"])

    forbidden = client.post(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot['id']}/audit-bundle/verify",
        json={"audit_manifest": bundle["audit_manifest"]},
        headers=other["headers"],
    )
    assert forbidden.status_code == 403


def test_access_review_packet_snapshot_audit_manifest_read_does_not_mutate_packet(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-verify-immutable")
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    approved = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        decision_note="Immutable manifest verification approval.",
    )
    original_packet_json = approved["packet_json"]
    original_packet_markdown = approved["packet_markdown"]
    bundle = _get_review_packet_snapshot_audit_bundle(client, env["headers"], snapshot["id"])

    result = _verify_review_packet_snapshot_audit_manifest(
        client,
        env["headers"],
        snapshot["id"],
        bundle["audit_manifest"],
    )
    detail = _get_review_packet_snapshot_detail(client, env["headers"], snapshot["id"])

    assert result["verified"] is True
    assert detail["packet_json"] == original_packet_json
    assert detail["packet_markdown"] == original_packet_markdown


def test_access_review_packet_snapshot_audit_bundle_pending_snapshot_conflicts(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-bundle-pending")
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    resp = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot['id']}/audit-bundle",
        headers=env["headers"],
    )
    assert resp.status_code == 409
    events = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])
    assert _export_events(events) == []


def test_access_review_packet_snapshot_audit_bundle_rejected_snapshot_conflicts(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-bundle-rejected")
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="rejected",
        review_note="Rejected for audit bundle validation.",
    )

    resp = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot['id']}/audit-bundle",
        headers=env["headers"],
    )
    assert resp.status_code == 409
    events = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])
    assert _export_events(events) == []
    rejected_event = next(event for event in events["events"] if event["event_type"] == "snapshot_rejected")
    rejected_reasons = _readiness_reasons_by_code(rejected_event["metadata"])
    assert rejected_reasons["review_rejected"]["severity"] == "blocked"
    assert rejected_reasons["audit_bundle_blocked_review_rejected"]["severity"] == "blocked"


def test_access_review_packet_snapshot_audit_bundle_respects_tenant_scope(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-bundle-scope")
    other = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-bundle-scope-other")
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        decision_note="Scoped bundle approval.",
    )

    forbidden = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot['id']}/audit-bundle",
        headers=other["headers"],
    )
    assert forbidden.status_code == 403
    events = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])
    assert _export_events(events) == []


def test_access_review_packet_snapshot_audit_bundle_read_does_not_mutate_packet(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-bundle-immutable")
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    approved = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        decision_note="Immutable audit bundle approval.",
    )
    original_packet_json = approved["packet_json"]
    original_packet_markdown = approved["packet_markdown"]
    post_snapshot_escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    _create_task(client, env["headers"], post_snapshot_escalation_id)
    current_packet = _get_review_packet(client, env["headers"], env["patient_id"])

    bundle = _get_review_packet_snapshot_audit_bundle(client, env["headers"], snapshot["id"])
    detail = _get_review_packet_snapshot_detail(client, env["headers"], snapshot["id"])
    bundle_reasons = _readiness_reasons_by_code(bundle)

    assert current_packet["review_readiness"]["readiness_status"] == "active_open_work"
    assert bundle["packet_json"] == original_packet_json
    assert bundle["packet_markdown"] == original_packet_markdown
    assert bundle_reasons["evidence_present"]["severity"] == "satisfied"
    assert bundle_reasons["review_approved"]["severity"] == "satisfied"
    assert bundle["export_metadata"]["generated_at"] is not None
    assert detail["packet_json"] == original_packet_json
    assert detail["packet_markdown"] == original_packet_markdown


def test_access_review_packet_snapshot_audit_bundle_readiness_reasons_ignore_live_patient_changes(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(
        client,
        db_session,
        slug="review-packet-audit-bundle-readiness-reasons-immutable",
    )
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    approved = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        decision_note="Persisted readiness reasons approval.",
    )
    original_packet_json = approved["packet_json"]
    original_packet_markdown = approved["packet_markdown"]

    _get_review_packet_snapshot_audit_bundle(client, env["headers"], snapshot["id"])
    persisted_bundle = _get_review_packet_snapshot_audit_bundle(
        client,
        env["headers"],
        snapshot["id"],
    )
    persisted_reasons = persisted_bundle["readiness_reasons"]

    post_snapshot_escalation_id = _create_escalation(
        client,
        env["headers"],
        env["patient_id"],
    )
    _create_task(client, env["headers"], post_snapshot_escalation_id)
    current_packet = _get_review_packet(client, env["headers"], env["patient_id"])
    updated_bundle = _get_review_packet_snapshot_audit_bundle(
        client,
        env["headers"],
        snapshot["id"],
    )
    updated_reasons = _readiness_reasons_by_code(updated_bundle)

    assert current_packet["review_readiness"]["readiness_status"] == "active_open_work"
    assert updated_bundle["readiness_reasons"] == persisted_reasons
    assert updated_reasons["evidence_present"]["severity"] == "satisfied"
    assert updated_reasons["review_approved"]["severity"] == "satisfied"
    assert updated_reasons["audit_bundle_available"]["severity"] == "satisfied"
    assert updated_reasons["audit_bundle_exported"]["severity"] == "satisfied"
    assert updated_bundle["packet_json"] == original_packet_json
    assert updated_bundle["packet_markdown"] == original_packet_markdown
    detail = _get_review_packet_snapshot_detail(client, env["headers"], snapshot["id"])
    assert detail["packet_json"] == original_packet_json
    assert detail["packet_markdown"] == original_packet_markdown


def test_access_review_packet_snapshot_audit_bundle_events_are_deterministically_ordered(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-bundle-order")
    reviewer = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-audit-bundle-order-reviewer@example.com",
        password="Secret123!",
    )
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        snapshot["id"],
        assigned_reviewer_user_id=str(reviewer.id),
    )
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        decision_note="Ordered audit bundle approval.",
    )

    for event in db_session.execute(
        select(AccessReviewPacketSnapshotEvent).where(
            AccessReviewPacketSnapshotEvent.snapshot_id == UUID(snapshot["id"])
        )
    ).scalars():
        event.created_at = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    db_session.commit()
    ordered_ids = [
        str(event.id)
        for event in db_session.execute(
            select(AccessReviewPacketSnapshotEvent)
            .where(AccessReviewPacketSnapshotEvent.snapshot_id == UUID(snapshot["id"]))
            .order_by(
                AccessReviewPacketSnapshotEvent.created_at.asc(),
                AccessReviewPacketSnapshotEvent.id.asc(),
            )
        ).scalars().all()
        if event.event_type.value in {"snapshot_approved", "snapshot_rejected"}
    ]

    bundle = _get_review_packet_snapshot_audit_bundle(client, env["headers"], snapshot["id"])

    assert [event["id"] for event in bundle["decision_events"]] == ordered_ids


def test_access_review_packet_snapshot_audit_bundle_markdown_returns_approved_snapshot(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-bundle-markdown-approved")
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    approved = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        decision_note="Approved for markdown audit bundle.",
    )

    markdown = _get_review_packet_snapshot_audit_bundle_markdown(client, env["headers"], snapshot["id"])

    assert "# ACCESS Review Packet Audit Bundle" in markdown
    assert snapshot["id"] in markdown
    assert "Review Status: approved" in markdown
    assert "Review State: approved" in markdown
    assert "Approval Override Used: no" in markdown
    assert "## Export Metadata" in markdown
    assert (
        f"Recommended Filename: access-review-packet-audit-bundle-{snapshot['id']}.md"
        in markdown
    )
    assert "Content Type: text/markdown" in markdown
    assert "## Audit Manifest" in markdown
    assert f"Packet JSON SHA-256: {_expected_packet_json_sha256(approved['packet_json'])}" in markdown
    assert f"Packet Markdown SHA-256: {_expected_packet_markdown_sha256(approved['packet_markdown'])}" in markdown
    assert "## Approval Event" in markdown
    assert "## Review Checklist" in markdown
    assert "## Decision Event Trail" in markdown
    assert "## Immutable Review Packet" in markdown
    assert approved["packet_markdown"] in markdown
    events = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])
    export_metadata = _export_events(events)[-1]["metadata"]
    assert export_metadata["export_format"] == "markdown"
    assert export_metadata["snapshot_id"] == snapshot["id"]
    assert (
        export_metadata["recommended_filename"]
        == f"access-review-packet-audit-bundle-{snapshot['id']}.md"
    )
    assert export_metadata["content_type"] == "text/markdown"
    export_reasons = _readiness_reasons_by_code(export_metadata)
    assert export_reasons["audit_bundle_exported"]["severity"] == "satisfied"


def test_access_review_packet_snapshot_audit_bundle_markdown_returns_override_metadata(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-bundle-markdown-override")
    override_user = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-audit-bundle-markdown-override-superuser@example.com",
        password="Secret123!",
        is_superuser=True,
    )
    override_headers = auth_headers(client, override_user.email, "Secret123!")
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    _update_review_packet_snapshot_review(
        client,
        override_headers,
        snapshot["id"],
        review_status="approved",
        decision_note="Override approval for markdown audit bundle.",
        override_missing_checklist=True,
        override_reason="Urgent compliance exception.",
    )
    markdown = _get_review_packet_snapshot_audit_bundle_markdown(client, env["headers"], snapshot["id"])

    assert "Review State: approved_with_override" in markdown
    assert "Approval Override Used: yes" in markdown
    assert "## Audit Manifest" in markdown
    assert "Override Reason: Urgent compliance exception." in markdown
    for key in _expected_missing_checklist_keys(snapshot):
        assert key in markdown


def test_access_review_packet_snapshot_audit_bundle_pdf_returns_approved_snapshot(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-bundle-pdf-approved")
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    approved = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        decision_note="Approved for PDF audit bundle.",
    )
    original_packet_json = approved["packet_json"]
    original_packet_markdown = approved["packet_markdown"]

    response = _get_review_packet_snapshot_audit_bundle_pdf(client, env["headers"], snapshot["id"])

    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 1000
    assert (
        response.headers["content-disposition"]
        == f'attachment; filename="access-review-packet-audit-bundle-{snapshot["id"]}.pdf"'
    )

    detail = _get_review_packet_snapshot_detail(client, env["headers"], snapshot["id"])
    assert detail["packet_json"] == original_packet_json
    assert detail["packet_markdown"] == original_packet_markdown
    events = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])
    export_metadata = _export_events(events)[-1]["metadata"]
    assert export_metadata["export_format"] == "pdf"
    assert export_metadata["snapshot_id"] == snapshot["id"]
    assert (
        export_metadata["recommended_filename"]
        == f"access-review-packet-audit-bundle-{snapshot['id']}.pdf"
    )
    assert export_metadata["content_type"] == "application/pdf"
    export_reasons = _readiness_reasons_by_code(export_metadata)
    assert export_reasons["audit_bundle_exported"]["severity"] == "satisfied"


def test_access_review_packet_snapshot_audit_bundle_pdf_returns_override_approved_snapshot(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-bundle-pdf-override")
    override_user = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-audit-bundle-pdf-override-superuser@example.com",
        password="Secret123!",
        is_superuser=True,
    )
    override_headers = auth_headers(client, override_user.email, "Secret123!")
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    _update_review_packet_snapshot_review(
        client,
        override_headers,
        snapshot["id"],
        review_status="approved",
        decision_note="Override approved for PDF audit bundle.",
        override_missing_checklist=True,
        override_reason="Urgent payer exception.",
    )

    response = _get_review_packet_snapshot_audit_bundle_pdf(client, env["headers"], snapshot["id"])

    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 1000


def test_access_review_packet_snapshot_audit_bundle_pdf_pending_snapshot_conflicts(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-bundle-pdf-pending")
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    response = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot['id']}/audit-bundle/pdf",
        headers=env["headers"],
    )

    assert response.status_code == 409
    events = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])
    assert _export_events(events) == []


def test_access_review_packet_snapshot_audit_bundle_pdf_rejected_snapshot_conflicts(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-bundle-pdf-rejected")
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="rejected",
        review_note="Rejected for PDF audit bundle validation.",
    )

    response = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot['id']}/audit-bundle/pdf",
        headers=env["headers"],
    )

    assert response.status_code == 409
    events = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])
    assert _export_events(events) == []


def test_access_review_packet_snapshot_audit_bundle_pdf_respects_tenant_scope(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-bundle-pdf-scope")
    other = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-bundle-pdf-scope-other")
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        decision_note="Approved for PDF tenant scope validation.",
    )

    forbidden = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot['id']}/audit-bundle/pdf",
        headers=other["headers"],
    )

    assert forbidden.status_code == 403
    events = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])
    assert _export_events(events) == []


def test_access_review_packet_snapshot_audit_bundle_pdf_read_does_not_mutate_packet(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-bundle-pdf-immutable")
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    approved = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        decision_note="Approved for immutable PDF audit bundle.",
    )
    original_packet_json = approved["packet_json"]
    original_packet_markdown = approved["packet_markdown"]

    response = _get_review_packet_snapshot_audit_bundle_pdf(client, env["headers"], snapshot["id"])
    detail = _get_review_packet_snapshot_detail(client, env["headers"], snapshot["id"])

    assert response.content.startswith(b"%PDF")
    assert detail["packet_json"] == original_packet_json
    assert detail["packet_markdown"] == original_packet_markdown


def test_access_review_packet_snapshot_audit_bundle_markdown_pending_snapshot_conflicts(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-bundle-markdown-pending")
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    resp = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot['id']}/audit-bundle/markdown",
        headers=env["headers"],
    )
    assert resp.status_code == 409


def test_access_review_packet_snapshot_audit_bundle_markdown_rejected_snapshot_conflicts(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-bundle-markdown-rejected")
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="rejected",
        review_note="Rejected markdown audit bundle validation.",
    )

    resp = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot['id']}/audit-bundle/markdown",
        headers=env["headers"],
    )
    assert resp.status_code == 409


def test_access_review_packet_snapshot_audit_bundle_markdown_respects_tenant_scope(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-bundle-markdown-scope")
    other = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-bundle-markdown-scope-other")
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        decision_note="Scoped markdown bundle approval.",
    )

    forbidden = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot['id']}/audit-bundle/markdown",
        headers=other["headers"],
    )
    assert forbidden.status_code == 403


def test_access_review_packet_snapshot_audit_bundle_markdown_read_does_not_mutate_packet(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-bundle-markdown-immutable")
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    approved = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        decision_note="Immutable markdown audit bundle approval.",
    )
    original_packet_json = approved["packet_json"]
    original_packet_markdown = approved["packet_markdown"]

    markdown = _get_review_packet_snapshot_audit_bundle_markdown(client, env["headers"], snapshot["id"])
    detail = _get_review_packet_snapshot_detail(client, env["headers"], snapshot["id"])

    assert original_packet_markdown in markdown
    assert detail["packet_json"] == original_packet_json
    assert detail["packet_markdown"] == original_packet_markdown


def test_access_review_packet_snapshot_audit_bundle_markdown_decision_events_are_deterministically_ordered(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-bundle-markdown-order")
    reviewer = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-audit-bundle-markdown-order-reviewer@example.com",
        password="Secret123!",
    )
    _prepare_review_ready_patient(client, env["headers"], env["patient_id"])
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        snapshot["id"],
        assigned_reviewer_user_id=str(reviewer.id),
    )
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
        decision_note="Ordered markdown audit bundle approval.",
    )

    for event in db_session.execute(
        select(AccessReviewPacketSnapshotEvent).where(
            AccessReviewPacketSnapshotEvent.snapshot_id == UUID(snapshot["id"])
        )
    ).scalars():
        event.created_at = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    db_session.commit()
    ordered_events = [
        event
        for event in db_session.execute(
            select(AccessReviewPacketSnapshotEvent)
            .where(AccessReviewPacketSnapshotEvent.snapshot_id == UUID(snapshot["id"]))
            .order_by(
                AccessReviewPacketSnapshotEvent.created_at.asc(),
                AccessReviewPacketSnapshotEvent.id.asc(),
            )
        ).scalars().all()
        if event.event_type.value in {"snapshot_approved", "snapshot_rejected"}
    ]

    markdown = _get_review_packet_snapshot_audit_bundle_markdown(client, env["headers"], snapshot["id"])
    positions = [
        markdown.index(f"id={event.id}")
        for event in ordered_events
    ]
    assert positions == sorted(positions)


def test_access_review_packet_snapshot_assignment_writes_event_with_assignment_metadata(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-snapshot-assigned-event")
    reviewer = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-snapshot-assigned-event-reviewer@example.com",
        password="Secret123!",
    )
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        snapshot["id"],
        assigned_reviewer_user_id=str(reviewer.id),
    )
    payload = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])

    assert [event["event_type"] for event in payload["events"]] == [
        "snapshot_created",
        "snapshot_assigned",
    ]
    event = payload["events"][-1]
    assert event["actor_user_id"] == str(env["user"].id)
    assert event["metadata"] == {
        "previous_assigned_reviewer_user_id": None,
        "assigned_reviewer_user_id": str(reviewer.id),
    }


def test_access_review_packet_snapshot_approval_writes_event_with_review_status_metadata(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-snapshot-approved-event")
    _prepare_review_ready_patient(
        client,
        env["headers"],
        env["patient_id"],
        summary="Approved event review-ready packet",
    )
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
    )
    payload = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])

    assert [event["event_type"] for event in payload["events"]] == [
        "snapshot_created",
        "snapshot_approved",
    ]
    event = payload["events"][-1]
    assert event["actor_user_id"] == str(env["user"].id)
    metadata = event["metadata"]
    assert {key: metadata[key] for key in (
        "previous_review_status",
        "new_review_status",
        "decision_note",
        "review_note",
        "approval_override",
        "override_reason",
        "missing_checklist_items",
    )} == {
        "previous_review_status": "pending_review",
        "new_review_status": "approved",
        "decision_note": None,
        "review_note": None,
        "approval_override": False,
        "override_reason": None,
        "missing_checklist_items": [],
    }
    reasons = _readiness_reasons_by_code(metadata)
    assert reasons["review_approved"]["severity"] == "satisfied"
    assert reasons["audit_bundle_available"]["severity"] == "satisfied"


def test_access_review_packet_snapshot_rejection_writes_event_with_review_status_metadata(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-snapshot-rejected-event")
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="rejected",
        review_note="Missing closure note.",
    )
    payload = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])

    assert [event["event_type"] for event in payload["events"]] == [
        "snapshot_created",
        "snapshot_rejected",
    ]
    event = payload["events"][-1]
    assert event["actor_user_id"] == str(env["user"].id)
    metadata = event["metadata"]
    assert {key: metadata[key] for key in (
        "previous_review_status",
        "new_review_status",
        "decision_note",
        "review_note",
        "approval_override",
        "override_reason",
        "missing_checklist_items",
    )} == {
        "previous_review_status": "pending_review",
        "new_review_status": "rejected",
        "decision_note": "Missing closure note.",
        "review_note": "Missing closure note.",
        "approval_override": False,
        "override_reason": None,
        "missing_checklist_items": [],
    }
    reasons = _readiness_reasons_by_code(metadata)
    assert reasons["review_rejected"]["severity"] == "blocked"
    assert reasons["audit_bundle_blocked_review_rejected"]["severity"] == "blocked"


def test_access_review_packet_snapshot_assignment_can_be_set_changed_and_cleared_without_mutating_packet(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-snapshot-assignment")
    other_same_org_user = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-snapshot-assignment-second@example.com",
        password="Secret123!",
    )
    same_org_headers = auth_headers(client, other_same_org_user.email, "Secret123!")
    other = _bootstrap_patient_env(
        client,
        db_session,
        slug="review-packet-snapshot-assignment-other",
    )
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    original_packet_json = snapshot["packet_json"]
    original_packet_markdown = snapshot["packet_markdown"]
    assert snapshot["assigned_reviewer_user_id"] is None

    assigned = _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        snapshot["id"],
        assigned_reviewer_user_id=str(env["user"].id),
    )
    assert assigned["assigned_reviewer_user_id"] == str(env["user"].id)
    assert assigned["packet_json"] == original_packet_json
    assert assigned["packet_markdown"] == original_packet_markdown

    reassigned = _update_review_packet_snapshot_assignment(
        client,
        same_org_headers,
        snapshot["id"],
        assigned_reviewer_user_id=str(other_same_org_user.id),
    )
    assert reassigned["assigned_reviewer_user_id"] == str(other_same_org_user.id)
    assert reassigned["packet_json"] == original_packet_json
    assert reassigned["packet_markdown"] == original_packet_markdown

    cleared = _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        snapshot["id"],
        assigned_reviewer_user_id=None,
    )
    assert cleared["assigned_reviewer_user_id"] is None
    assert cleared["packet_json"] == original_packet_json
    assert cleared["packet_markdown"] == original_packet_markdown

    detail = _get_review_packet_snapshot_detail(client, env["headers"], snapshot["id"])
    assert detail["assigned_reviewer_user_id"] is None
    assert detail["packet_json"] == original_packet_json
    assert detail["packet_markdown"] == original_packet_markdown


def test_access_review_packet_snapshot_events_endpoint_respects_tenant_scope(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-snapshot-events-scope")
    other = _bootstrap_patient_env(client, db_session, slug="review-packet-snapshot-events-scope-other")
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    forbidden = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot['id']}/events",
        headers=other["headers"],
    )
    assert forbidden.status_code == 403


def test_access_review_packet_snapshot_events_endpoint_does_not_rebuild_or_mutate_packet(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-snapshot-events-immutable")
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    original_detail = _get_review_packet_snapshot_detail(client, env["headers"], snapshot["id"])

    _create_escalation(client, env["headers"], env["patient_id"])

    payload = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])
    detail_after = _get_review_packet_snapshot_detail(client, env["headers"], snapshot["id"])

    assert payload["snapshot_id"] == snapshot["id"]
    assert detail_after["packet_json"] == original_detail["packet_json"]
    assert detail_after["packet_markdown"] == original_detail["packet_markdown"]


def test_access_review_packet_snapshot_events_are_returned_in_deterministic_created_at_and_id_order(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-snapshot-events-order")
    reviewer = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-snapshot-events-order-reviewer@example.com",
        password="Secret123!",
    )
    _prepare_review_ready_patient(
        client,
        env["headers"],
        env["patient_id"],
        summary="Ordered events review-ready packet",
    )
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        snapshot["id"],
        assigned_reviewer_user_id=str(reviewer.id),
    )
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        snapshot["id"],
        review_status="approved",
    )

    for event in db_session.execute(
        select(AccessReviewPacketSnapshotEvent).where(
            AccessReviewPacketSnapshotEvent.snapshot_id == UUID(snapshot["id"])
        )
    ).scalars():
        event.created_at = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    db_session.commit()
    ordered_events = list(
        db_session.execute(
            select(AccessReviewPacketSnapshotEvent)
            .where(AccessReviewPacketSnapshotEvent.snapshot_id == UUID(snapshot["id"]))
            .order_by(
                AccessReviewPacketSnapshotEvent.created_at.asc(),
                AccessReviewPacketSnapshotEvent.id.asc(),
            )
        ).scalars().all()
    )

    payload = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])

    assert [event["id"] for event in payload["events"]] == [str(event.id) for event in ordered_events]
    assert [event["event_type"] for event in payload["events"]] == [
        event.event_type.value for event in ordered_events
    ]
    assert {event["event_type"] for event in payload["events"]} == {
        "snapshot_created",
        "snapshot_assigned",
        "snapshot_approved",
    }


def test_access_review_packet_active_open_work_checklist_has_warning_review_readiness(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-checklist-warning")
    escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    _create_task(client, env["headers"], escalation_id)

    packet = _get_review_packet(client, env["headers"], env["patient_id"])

    checklist = _review_checklist_by_key(packet)
    assert packet["review_checklist"]["overall_status"] == "missing"
    assert packet["review_checklist"]["warning_count"] >= 1
    assert packet["review_checklist"]["missing_count"] >= 1
    assert checklist["review_readiness"]["status"] == "warning"
    assert checklist["has_signal"]["status"] == "ready"


def test_access_review_packet_snapshot_list_is_paginated_and_deterministic(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-snapshot-list")
    other = _bootstrap_patient_env(client, db_session, slug="review-packet-snapshot-list-other")

    first = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    second = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    third = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    resp = client.get(
        f"/api/v1/reports/access-review-packet/{env['patient_id']}/snapshots",
        headers=env["headers"],
    )
    assert resp.status_code == 200
    payload = resp.json()

    assert [item["id"] for item in payload] == [third["id"], second["id"], first["id"]]
    assert all(
        payload[index]["created_at"] >= payload[index + 1]["created_at"]
        for index in range(len(payload) - 1)
    )
    for earlier, later in zip(payload, payload[1:]):
        if earlier["created_at"] == later["created_at"] and earlier["generated_at"] == later["generated_at"]:
            assert earlier["id"] > later["id"]
    assert all(item["patient_id"] == env["patient_id"] for item in payload)
    assert all(item["organization_id"] == str(env["organization"].id) for item in payload)

    limited = client.get(
        f"/api/v1/reports/access-review-packet/{env['patient_id']}/snapshots?limit=2",
        headers=env["headers"],
    )
    assert limited.status_code == 200
    assert [item["id"] for item in limited.json()] == [third["id"], second["id"]]

    offset = client.get(
        f"/api/v1/reports/access-review-packet/{env['patient_id']}/snapshots?limit=1&offset=1",
        headers=env["headers"],
    )
    assert offset.status_code == 200
    assert [item["id"] for item in offset.json()] == [second["id"]]

    forbidden = client.get(
        f"/api/v1/reports/access-review-packet/{env['patient_id']}/snapshots",
        headers=other["headers"],
    )
    assert forbidden.status_code == 403


def test_access_review_packet_snapshot_list_can_filter_by_review_status(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-snapshot-filter")
    _prepare_review_ready_patient(
        client,
        env["headers"],
        env["patient_id"],
        summary="Snapshot filter approved packet",
    )

    pending_one = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    approved = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    approved = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        approved["id"],
        review_status="approved",
    )
    rejected = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    rejected = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        rejected["id"],
        review_status="rejected",
        review_note="Rejected for missing context.",
    )
    pending_two = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    pending_resp = client.get(
        f"/api/v1/reports/access-review-packet/{env['patient_id']}/snapshots?review_status=pending_review",
        headers=env["headers"],
    )
    assert pending_resp.status_code == 200
    pending_payload = pending_resp.json()
    assert [item["id"] for item in pending_payload] == [pending_two["id"], pending_one["id"]]
    assert all(item["review_status"] == "pending_review" for item in pending_payload)

    approved_resp = client.get(
        f"/api/v1/reports/access-review-packet/{env['patient_id']}/snapshots?review_status=approved",
        headers=env["headers"],
    )
    assert approved_resp.status_code == 200
    approved_payload = approved_resp.json()
    assert [item["id"] for item in approved_payload] == [approved["id"]]
    assert all(item["review_status"] == "approved" for item in approved_payload)

    rejected_resp = client.get(
        f"/api/v1/reports/access-review-packet/{env['patient_id']}/snapshots?review_status=rejected",
        headers=env["headers"],
    )
    assert rejected_resp.status_code == 200
    rejected_payload = rejected_resp.json()
    assert [item["id"] for item in rejected_payload] == [rejected["id"]]
    assert rejected_payload[0]["review_note"] == "Rejected for missing context."

    pending_limited = client.get(
        f"/api/v1/reports/access-review-packet/{env['patient_id']}/snapshots?review_status=pending_review&limit=1",
        headers=env["headers"],
    )
    assert pending_limited.status_code == 200
    assert [item["id"] for item in pending_limited.json()] == [pending_two["id"]]

    pending_offset = client.get(
        (
            f"/api/v1/reports/access-review-packet/{env['patient_id']}/snapshots"
            "?review_status=pending_review&limit=1&offset=1"
        ),
        headers=env["headers"],
    )
    assert pending_offset.status_code == 200
    assert [item["id"] for item in pending_offset.json()] == [pending_one["id"]]

    invalid = client.get(
        f"/api/v1/reports/access-review-packet/{env['patient_id']}/snapshots?review_status=not_a_status",
        headers=env["headers"],
    )
    assert invalid.status_code == 422


def test_access_review_packet_snapshot_summary_counts_are_patient_scoped(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-snapshot-summary")
    other_patient_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-snapshot-summary-other",
    )
    _prepare_review_ready_patient(
        client,
        env["headers"],
        env["patient_id"],
        summary="Snapshot summary approved packet",
    )

    pending = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    approved = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        approved["id"],
        review_status="approved",
    )
    rejected = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        rejected["id"],
        review_status="rejected",
        review_note="Rejected in summary test.",
    )
    _create_review_packet_snapshot(client, env["headers"], other_patient_id)

    summary = _get_review_packet_snapshot_summary(client, env["headers"], env["patient_id"])
    other_summary = _get_review_packet_snapshot_summary(client, env["headers"], other_patient_id)

    assert summary == {
        "total": 3,
        "pending_review": 1,
        "approved": 1,
        "rejected": 1,
        "ready_for_review": 0,
        "active_open_work": 0,
        "incomplete": 0,
    }
    assert other_summary == {
        "total": 1,
        "pending_review": 1,
        "approved": 0,
        "rejected": 0,
        "ready_for_review": 0,
        "active_open_work": 0,
        "incomplete": 0,
    }


def test_access_review_packet_snapshot_summary_respects_tenant_scope_and_missing_patient(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(
        client,
        db_session,
        slug="review-packet-snapshot-summary-scope",
    )
    other = _bootstrap_patient_env(
        client,
        db_session,
        slug="review-packet-snapshot-summary-scope-other",
    )
    _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    forbidden = client.get(
        f"/api/v1/reports/access-review-packet/{env['patient_id']}/snapshots/summary",
        headers=other["headers"],
    )
    assert forbidden.status_code == 403

    missing = client.get(
        "/api/v1/reports/access-review-packet/00000000-0000-0000-0000-000000000000/snapshots/summary",
        headers=env["headers"],
    )
    assert missing.status_code == 404


def test_access_review_packet_patient_audit_status_returns_no_snapshot_state(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-status-empty")

    payload = _get_review_packet_patient_audit_status(client, env["headers"], env["patient_id"])

    assert payload == {
        "patient_id": env["patient_id"],
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
            "reason": "No review packet snapshot exists for this patient.",
            "priority": "normal",
        },
        "completion_summary": {
            "status": "not_started",
            "missing_evidence_count": 0,
            "has_required_evidence": False,
            "has_approval": False,
            "has_export": False,
            "reason": "No review packet snapshot exists for this patient.",
        },
        "readiness_reasons": [
            {
                "code": "snapshot_present",
                "severity": "missing",
                "label": "Review packet snapshot",
                "detail": "No immutable review packet snapshot exists for this patient.",
            },
            {
                "code": "evidence_present",
                "severity": "missing",
                "label": "Required evidence",
                "detail": (
                    "Required proof evidence has not been captured in a review packet snapshot."
                ),
            },
            {
                "code": "audit_bundle_available",
                "severity": "missing",
                "label": "Audit bundle available",
                "detail": (
                    "Audit bundle export is unavailable until a review packet snapshot is approved."
                ),
            },
            {
                "code": "audit_bundle_exported",
                "severity": "missing",
                "label": "Audit bundle exported",
                "detail": "No successful audit bundle export is recorded for this patient.",
            },
        ],
    }


def test_access_review_packet_patient_audit_status_uses_latest_snapshot_and_export_status(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-status-latest")
    reviewer = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-audit-status-latest-reviewer@example.com",
        password="Secret123!",
    )
    base = datetime.now(timezone.utc).replace(microsecond=0)

    _prepare_review_ready_patient(
        client,
        env["headers"],
        env["patient_id"],
        summary="Patient audit-status approved packet",
    )
    older_approved = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        older_approved["id"],
        assigned_reviewer_user_id=str(reviewer.id),
    )
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        older_approved["id"],
        review_status="approved",
    )
    _get_review_packet_snapshot_audit_bundle(client, env["headers"], older_approved["id"])

    latest_approved = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    latest_approved = _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        latest_approved["id"],
        assigned_reviewer_user_id=str(reviewer.id),
    )
    latest_approved = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        latest_approved["id"],
        review_status="approved",
    )
    _get_review_packet_snapshot_audit_bundle_pdf(client, env["headers"], latest_approved["id"])
    _get_review_packet_snapshot_audit_bundle_markdown(client, env["headers"], latest_approved["id"])
    _get_review_packet_snapshot_audit_bundle_markdown(client, env["headers"], latest_approved["id"])
    _get_review_packet_snapshot_audit_bundle(client, env["headers"], latest_approved["id"])

    tracked_snapshots = {
        snapshot.id: snapshot
        for snapshot in db_session.execute(
            select(AccessReviewPacketSnapshot).where(
                AccessReviewPacketSnapshot.id.in_(
                    [UUID(older_approved["id"]), UUID(latest_approved["id"])]
                )
            )
        ).scalars()
    }
    tracked_snapshots[UUID(older_approved["id"])].created_at = base - timedelta(days=3)
    tracked_snapshots[UUID(latest_approved["id"])].created_at = base
    db_session.commit()
    db_session.expire_all()

    export_events = [
        event
        for event in db_session.execute(
            select(AccessReviewPacketSnapshotEvent)
            .where(AccessReviewPacketSnapshotEvent.snapshot_id == UUID(latest_approved["id"]))
            .where(
                AccessReviewPacketSnapshotEvent.event_type
                == AccessReviewPacketSnapshotEventType.AUDIT_BUNDLE_EXPORTED
            )
            .order_by(
                AccessReviewPacketSnapshotEvent.created_at.asc(),
                AccessReviewPacketSnapshotEvent.id.asc(),
            )
        ).scalars()
    ]
    for event, created_at in zip(
        export_events,
        [
            base + timedelta(hours=1),
            base + timedelta(hours=2),
            base + timedelta(hours=3),
            base + timedelta(hours=4),
        ],
        strict=False,
    ):
        event.created_at = created_at
    db_session.commit()
    db_session.expire_all()

    events_before = _get_review_packet_snapshot_events(client, env["headers"], latest_approved["id"])
    payload = _get_review_packet_patient_audit_status(client, env["headers"], env["patient_id"])
    events_after = _get_review_packet_snapshot_events(client, env["headers"], latest_approved["id"])

    assert payload["patient_id"] == env["patient_id"]
    assert payload["has_snapshot"] is True
    assert payload["latest_snapshot_id"] == latest_approved["id"]
    assert payload["latest_snapshot_created_at"] == base.strftime("%Y-%m-%dT%H:%M:%S")
    assert payload["review_status"] == "approved"
    assert payload["review_state"]["state"] == "approved"
    assert payload["assigned_reviewer_user_id"] == str(reviewer.id)
    assert payload["review_action"] is None
    assert payload["audit_bundle"] == {
        "available": True,
        "exported": True,
        "last_exported_at": (base + timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%S"),
        "export_formats": ["json", "markdown", "pdf"],
    }
    assert payload["next_step"] == {
        "action": "no_action_needed",
        "reason": "Approved audit bundle has already been exported.",
        "priority": "normal",
    }
    assert payload["completion_summary"] == {
        "status": "audit_ready",
        "missing_evidence_count": 0,
        "has_required_evidence": True,
        "has_approval": True,
        "has_export": True,
        "reason": "Approved audit bundle has been exported and is audit-ready.",
    }
    reasons = _readiness_reasons_by_code(payload)
    assert reasons["signal_present"]["severity"] == "satisfied"
    assert reasons["escalation_present"]["severity"] == "satisfied"
    assert reasons["intervention_present"]["severity"] == "satisfied"
    assert reasons["outcome_present"]["severity"] == "satisfied"
    assert reasons["evidence_present"]["severity"] == "satisfied"
    assert reasons["snapshot_present"]["severity"] == "satisfied"
    assert reasons["review_approved"]["severity"] == "satisfied"
    assert reasons["audit_bundle_available"]["severity"] == "satisfied"
    assert reasons["audit_bundle_exported"]["severity"] == "satisfied"
    assert events_after == events_before


def test_access_review_packet_patient_audit_status_override_approval_marks_bundle_available(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-status-override")
    reviewer = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-audit-status-override-reviewer@example.com",
        password="Secret123!",
    )
    override_user = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-audit-status-override-superuser@example.com",
        password="Secret123!",
        is_superuser=True,
    )
    override_headers = auth_headers(client, override_user.email, "Secret123!")

    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        snapshot["id"],
        assigned_reviewer_user_id=str(reviewer.id),
    )
    _update_review_packet_snapshot_review(
        client,
        override_headers,
        snapshot["id"],
        review_status="approved",
        decision_note="Approved under audit-status exception.",
        override_missing_checklist=True,
        override_reason="Audit-status compliance exception.",
    )

    events_before = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])
    payload = _get_review_packet_patient_audit_status(client, env["headers"], env["patient_id"])
    events_after = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])

    assert payload["patient_id"] == env["patient_id"]
    assert payload["has_snapshot"] is True
    assert payload["latest_snapshot_id"] == snapshot["id"]
    assert payload["review_status"] == "approved"
    assert payload["review_state"]["state"] == "approved_with_override"
    assert payload["assigned_reviewer_user_id"] == str(reviewer.id)
    assert payload["review_action"] is None
    assert payload["audit_bundle"] == {
        "available": True,
        "exported": False,
        "last_exported_at": None,
        "export_formats": [],
    }
    assert payload["next_step"] == {
        "action": "export_audit_bundle",
        "reason": "Snapshot is approved and ready for audit bundle export.",
        "priority": "normal",
    }
    assert payload["completion_summary"] == {
        "status": "approved_not_exported",
        "missing_evidence_count": 0,
        "has_required_evidence": True,
        "has_approval": True,
        "has_export": False,
        "reason": "Snapshot is approved but audit bundle has not been exported.",
    }
    reasons = _readiness_reasons_by_code(payload)
    assert reasons["snapshot_present"]["severity"] == "satisfied"
    assert reasons["review_override_approved"] == {
        "code": "review_override_approved",
        "severity": "partial",
        "label": "Override approval",
        "detail": (
            "Latest review packet snapshot was approved with override or superuser review."
        ),
    }
    assert reasons["audit_bundle_available"]["severity"] == "satisfied"
    assert reasons["audit_bundle_exported"]["severity"] == "missing"
    assert events_after == events_before


def test_access_review_packet_patient_audit_status_pending_and_rejected_disable_audit_bundle(
    client: TestClient,
    db_session: Session,
) -> None:
    pending_env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-status-pending")
    _prepare_review_ready_patient(
        client,
        pending_env["headers"],
        pending_env["patient_id"],
        summary="Patient audit-status pending packet",
    )
    pending_snapshot = _create_review_packet_snapshot(
        client,
        pending_env["headers"],
        pending_env["patient_id"],
    )
    pending_events_before = _get_review_packet_snapshot_events(
        client,
        pending_env["headers"],
        pending_snapshot["id"],
    )
    pending_payload = _get_review_packet_patient_audit_status(
        client,
        pending_env["headers"],
        pending_env["patient_id"],
    )
    pending_events_after = _get_review_packet_snapshot_events(
        client,
        pending_env["headers"],
        pending_snapshot["id"],
    )
    assert pending_payload["review_state"]["state"] == "pending_unassigned"
    assert pending_payload["review_action"] is None
    assert pending_payload["audit_bundle"] == {
        "available": False,
        "exported": False,
        "last_exported_at": None,
        "export_formats": [],
    }
    assert pending_payload["next_step"] == {
        "action": "assign_reviewer",
        "reason": "Snapshot is pending review but has no assigned reviewer.",
        "priority": "normal",
    }
    assert pending_payload["completion_summary"] == {
        "status": "review_ready",
        "missing_evidence_count": 0,
        "has_required_evidence": True,
        "has_approval": False,
        "has_export": False,
        "reason": "Snapshot has required evidence and is awaiting review.",
    }
    pending_reasons = _readiness_reasons_by_code(pending_payload)
    assert pending_reasons["snapshot_present"]["severity"] == "satisfied"
    assert pending_reasons["evidence_present"]["severity"] == "satisfied"
    assert pending_reasons["review_approved"]["severity"] == "missing"
    assert pending_reasons["audit_bundle_available"]["severity"] == "missing"
    assert pending_reasons["audit_bundle_exported"]["severity"] == "missing"
    assert pending_events_after == pending_events_before

    rejected_env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-status-rejected")
    rejected_snapshot = _create_review_packet_snapshot(
        client,
        rejected_env["headers"],
        rejected_env["patient_id"],
    )
    _update_review_packet_snapshot_review(
        client,
        rejected_env["headers"],
        rejected_snapshot["id"],
        review_status="rejected",
        review_note="Rejected patient audit-status packet.",
    )
    rejected_events_before = _get_review_packet_snapshot_events(
        client,
        rejected_env["headers"],
        rejected_snapshot["id"],
    )
    rejected_payload = _get_review_packet_patient_audit_status(
        client,
        rejected_env["headers"],
        rejected_env["patient_id"],
    )
    rejected_events_after = _get_review_packet_snapshot_events(
        client,
        rejected_env["headers"],
        rejected_snapshot["id"],
    )
    assert rejected_payload["review_state"]["state"] == "rejected"
    assert rejected_payload["review_action"] is None
    assert rejected_payload["audit_bundle"] == {
        "available": False,
        "exported": False,
        "last_exported_at": None,
        "export_formats": [],
    }
    assert rejected_payload["next_step"] == {
        "action": "create_snapshot",
        "reason": "Latest snapshot was rejected; create a new snapshot when evidence is ready.",
        "priority": "normal",
    }
    assert rejected_payload["completion_summary"] == {
        "status": "rejected",
        "missing_evidence_count": rejected_snapshot["packet_json"]["review_checklist"]["missing_count"],
        "has_required_evidence": False,
        "has_approval": False,
        "has_export": False,
        "reason": "Latest snapshot was rejected.",
    }
    rejected_reasons = _readiness_reasons_by_code(rejected_payload)
    assert rejected_reasons["snapshot_present"]["severity"] == "satisfied"
    assert rejected_reasons["review_rejected"] == {
        "code": "review_rejected",
        "severity": "blocked",
        "label": "Review rejected",
        "detail": "Latest review packet snapshot was rejected.",
    }
    assert rejected_reasons["audit_bundle_blocked_review_rejected"] == {
        "code": "audit_bundle_blocked_review_rejected",
        "severity": "blocked",
        "label": "Audit bundle blocked",
        "detail": (
            "Audit bundle export is blocked because the latest review packet was rejected."
        ),
    }
    assert rejected_events_after == rejected_events_before


def test_access_review_packet_patient_audit_status_next_step_covers_reviewer_ready_and_missing_evidence(
    client: TestClient,
    db_session: Session,
) -> None:
    ready_env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-status-next-step-ready")
    reviewer = create_user_for_org(
        db_session,
        organization=ready_env["organization"],
        email="review-packet-audit-status-next-step-ready-reviewer@example.com",
        password="Secret123!",
    )
    _prepare_review_ready_patient(
        client,
        ready_env["headers"],
        ready_env["patient_id"],
        summary="Patient audit-status next-step ready packet",
    )
    ready_snapshot = _create_review_packet_snapshot(client, ready_env["headers"], ready_env["patient_id"])
    _update_review_packet_snapshot_assignment(
        client,
        ready_env["headers"],
        ready_snapshot["id"],
        assigned_reviewer_user_id=str(reviewer.id),
    )
    ready_events_before = _get_review_packet_snapshot_events(
        client,
        ready_env["headers"],
        ready_snapshot["id"],
    )
    ready_payload = _get_review_packet_patient_audit_status(
        client,
        ready_env["headers"],
        ready_env["patient_id"],
    )
    ready_events_after = _get_review_packet_snapshot_events(
        client,
        ready_env["headers"],
        ready_snapshot["id"],
    )
    assert ready_payload["review_state"]["state"] == "pending_assigned_ready"
    assert ready_payload["review_action"] == {
        "action": "ready_to_review",
        "reason": "Snapshot is ready for reviewer approval.",
        "priority": "normal",
    }
    assert ready_payload["next_step"] == {
        "action": "review_snapshot",
        "reason": "Snapshot is assigned and ready for review.",
        "priority": "normal",
    }
    assert ready_payload["completion_summary"] == {
        "status": "review_ready",
        "missing_evidence_count": 0,
        "has_required_evidence": True,
        "has_approval": False,
        "has_export": False,
        "reason": "Snapshot has required evidence and is awaiting review.",
    }
    ready_reasons = _readiness_reasons_by_code(ready_payload)
    assert ready_reasons["signal_present"]["severity"] == "satisfied"
    assert ready_reasons["evidence_present"]["severity"] == "satisfied"
    assert ready_reasons["review_approved"]["severity"] == "missing"
    assert ready_events_after == ready_events_before

    blocked_env = _bootstrap_patient_env(
        client,
        db_session,
        slug="review-packet-audit-status-next-step-blocked",
    )
    blocked_reviewer = create_user_for_org(
        db_session,
        organization=blocked_env["organization"],
        email="review-packet-audit-status-next-step-blocked-reviewer@example.com",
        password="Secret123!",
    )
    blocked_snapshot = _create_review_packet_snapshot(
        client,
        blocked_env["headers"],
        blocked_env["patient_id"],
    )
    _update_review_packet_snapshot_assignment(
        client,
        blocked_env["headers"],
        blocked_snapshot["id"],
        assigned_reviewer_user_id=str(blocked_reviewer.id),
    )
    blocked_events_before = _get_review_packet_snapshot_events(
        client,
        blocked_env["headers"],
        blocked_snapshot["id"],
    )
    blocked_payload = _get_review_packet_patient_audit_status(
        client,
        blocked_env["headers"],
        blocked_env["patient_id"],
    )
    blocked_events_after = _get_review_packet_snapshot_events(
        client,
        blocked_env["headers"],
        blocked_snapshot["id"],
    )
    assert blocked_payload["review_state"]["state"] == "blocked_missing_evidence"
    assert blocked_payload["review_action"] == {
        "action": "missing_evidence",
        "reason": "Snapshot is blocked by missing evidence.",
        "priority": "high",
    }
    assert blocked_payload["next_step"] == {
        "action": "complete_missing_evidence",
        "reason": "Snapshot cannot be approved until missing evidence is resolved.",
        "priority": "high",
    }
    assert blocked_payload["completion_summary"] == {
        "status": "incomplete",
        "missing_evidence_count": blocked_snapshot["packet_json"]["review_checklist"]["missing_count"],
        "has_required_evidence": False,
        "has_approval": False,
        "has_export": False,
        "reason": "Snapshot is missing required evidence.",
    }
    blocked_reasons = _readiness_reasons_by_code(blocked_payload)
    assert blocked_reasons["snapshot_present"]["severity"] == "satisfied"
    assert blocked_reasons["evidence_present"]["severity"] == "missing"
    assert blocked_reasons["review_approved"]["severity"] == "blocked"
    assert blocked_reasons["audit_bundle_blocked_missing_evidence"] == {
        "code": "audit_bundle_blocked_missing_evidence",
        "severity": "blocked",
        "label": "Audit bundle blocked",
        "detail": "Audit bundle export is blocked until missing evidence is resolved.",
    }
    assert blocked_reasons["audit_bundle_exported"]["severity"] == "missing"
    assert blocked_events_after == blocked_events_before


def test_access_review_packet_patient_audit_status_is_tenant_scoped(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-status-scope")
    other = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-status-scope-other")
    _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    forbidden = client.get(
        f"/api/v1/reports/access-review-packet/patients/{env['patient_id']}/audit-status",
        headers=other["headers"],
    )
    assert forbidden.status_code == 403

    missing = client.get(
        "/api/v1/reports/access-review-packet/patients/00000000-0000-0000-0000-000000000000/audit-status",
        headers=env["headers"],
    )
    assert missing.status_code == 404


def test_access_review_packet_snapshot_organization_summary_counts_across_patients(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-org-summary")
    other_patient_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-org-summary-other",
    )
    other_org = _bootstrap_patient_env(client, db_session, slug="review-packet-org-summary-external")
    _prepare_review_ready_patient(
        client,
        env["headers"],
        env["patient_id"],
        summary="Org summary ready approved packet",
    )

    ready_pending = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    ready_approved = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        ready_approved["id"],
        review_status="approved",
    )

    mixed_patient_snapshot = _create_review_packet_snapshot(client, env["headers"], other_patient_id)

    open_escalation_id = _create_escalation(client, env["headers"], other_patient_id)
    _create_task(client, env["headers"], open_escalation_id)
    active_open_work_snapshot = _create_review_packet_snapshot(client, env["headers"], other_patient_id)
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        active_open_work_snapshot["id"],
        review_status="rejected",
        review_note="Still open work.",
    )

    incomplete_patient_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-org-summary-incomplete",
    )
    _create_review_packet_snapshot(client, env["headers"], incomplete_patient_id)

    _create_review_packet_snapshot(
        client,
        other_org["headers"],
        other_org["patient_id"],
    )

    summary = _get_review_packet_snapshot_organization_summary(client, env["headers"])

    assert summary == {
        "total": 5,
        "pending_review": 3,
        "approved": 1,
        "rejected": 1,
        "ready_for_review": 2,
        "active_open_work": 1,
        "incomplete": 2,
    }


def test_access_review_packet_snapshot_organization_summary_returns_zero_counts_when_empty(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-org-summary-empty")

    summary = _get_review_packet_snapshot_organization_summary(client, env["headers"])

    assert summary == {
        "total": 0,
        "pending_review": 0,
        "approved": 0,
        "rejected": 0,
        "ready_for_review": 0,
        "active_open_work": 0,
        "incomplete": 0,
    }


def test_access_review_packet_snapshot_organization_list_supports_filters_and_pagination(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-org-list")
    reviewer_one = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-org-list-reviewer-one@example.com",
        password="Secret123!",
    )
    reviewer_two = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-org-list-reviewer-two@example.com",
        password="Secret123!",
    )
    patient_two_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-org-list-two",
    )
    patient_three_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-org-list-three",
    )
    patient_four_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-org-list-four",
    )
    other_org = _bootstrap_patient_env(client, db_session, slug="review-packet-org-list-external")

    base = datetime.now(timezone.utc).replace(microsecond=0)
    ready_escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    ready_task_id = _create_task(client, env["headers"], ready_escalation_id)
    ready_outcome = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        intervention_task_id=ready_task_id,
        metric_name="systolic_bp",
        value_numeric=122,
        observed_at=base + timedelta(days=1),
    )
    ready_care_update = _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="Org backlog ready snapshot",
        occurred_at=base + timedelta(days=2),
        escalation_id=ready_escalation_id,
        intervention_task_id=ready_task_id,
        outcome_id=ready_outcome["id"],
    )
    ready_resolve = client.post(
        f"/api/v1/escalations/{ready_escalation_id}/resolve",
        json={
            "resolution_reason": "clinically_stable",
            "resolution_notes": "Ready packet for org backlog test.",
            "outcome_id": ready_outcome["id"],
            "care_update_id": ready_care_update["id"],
            "resolved_at": (base + timedelta(days=3)).isoformat(),
        },
        headers=env["headers"],
    )
    assert ready_resolve.status_code == 200
    ready_complete = client.post(
        f"/api/v1/tasks/{ready_task_id}/complete",
        json={"completion_note": "Ready task complete."},
        headers=env["headers"],
    )
    assert ready_complete.status_code == 200

    pending_ready = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        pending_ready["id"],
        assigned_reviewer_user_id=str(reviewer_one.id),
    )
    _prepare_review_ready_patient(
        client,
        env["headers"],
        patient_two_id,
        summary="Org list approved packet",
    )
    approved_incomplete = _create_review_packet_snapshot(client, env["headers"], patient_two_id)
    approved_incomplete = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        approved_incomplete["id"],
        review_status="approved",
    )
    _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        approved_incomplete["id"],
        assigned_reviewer_user_id=str(reviewer_two.id),
    )

    open_escalation_id = _create_escalation(client, env["headers"], patient_three_id)
    _create_task(client, env["headers"], open_escalation_id)
    rejected_active = _create_review_packet_snapshot(client, env["headers"], patient_three_id)
    rejected_active = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        rejected_active["id"],
        review_status="rejected",
        review_note="Still active open work.",
    )
    _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        rejected_active["id"],
        assigned_reviewer_user_id=str(reviewer_one.id),
    )

    pending_incomplete = _create_review_packet_snapshot(client, env["headers"], patient_four_id)

    _create_review_packet_snapshot(client, other_org["headers"], other_org["patient_id"])

    full_list = _get_review_packet_snapshot_organization_list(client, env["headers"])
    assert [item["id"] for item in full_list] == [
        pending_incomplete["id"],
        rejected_active["id"],
        approved_incomplete["id"],
        pending_ready["id"],
    ]
    assert all(item["organization_id"] == str(env["organization"].id) for item in full_list)

    pending_list = _get_review_packet_snapshot_organization_list(
        client,
        env["headers"],
        "review_status=pending_review",
    )
    assert [item["id"] for item in pending_list] == [pending_incomplete["id"], pending_ready["id"]]
    assert all(item["review_status"] == "pending_review" for item in pending_list)

    approved_list = _get_review_packet_snapshot_organization_list(
        client,
        env["headers"],
        "review_status=approved",
    )
    assert [item["id"] for item in approved_list] == [approved_incomplete["id"]]

    rejected_list = _get_review_packet_snapshot_organization_list(
        client,
        env["headers"],
        "review_status=rejected",
    )
    assert [item["id"] for item in rejected_list] == [rejected_active["id"]]

    ready_list = _get_review_packet_snapshot_organization_list(
        client,
        env["headers"],
        "review_readiness_status=ready_for_review",
    )
    assert [item["id"] for item in ready_list] == [approved_incomplete["id"], pending_ready["id"]]

    active_list = _get_review_packet_snapshot_organization_list(
        client,
        env["headers"],
        "review_readiness_status=active_open_work",
    )
    assert [item["id"] for item in active_list] == [rejected_active["id"]]

    incomplete_list = _get_review_packet_snapshot_organization_list(
        client,
        env["headers"],
        "review_readiness_status=incomplete",
    )
    assert [item["id"] for item in incomplete_list] == [pending_incomplete["id"]]

    combined = _get_review_packet_snapshot_organization_list(
        client,
        env["headers"],
        "review_status=approved&review_readiness_status=incomplete",
    )
    assert combined == []

    paged = _get_review_packet_snapshot_organization_list(
        client,
        env["headers"],
        "limit=2&offset=1",
    )
    assert [item["id"] for item in paged] == [rejected_active["id"], approved_incomplete["id"]]

    unassigned_list = _get_review_packet_snapshot_organization_list(
        client,
        env["headers"],
        "unassigned=true",
    )
    assert [item["id"] for item in unassigned_list] == [pending_incomplete["id"]]
    assert all(item["assigned_reviewer_user_id"] is None for item in unassigned_list)

    reviewer_one_list = _get_review_packet_snapshot_organization_list(
        client,
        env["headers"],
        f"assigned_reviewer_user_id={reviewer_one.id}",
    )
    assert [item["id"] for item in reviewer_one_list] == [rejected_active["id"], pending_ready["id"]]
    assert all(item["assigned_reviewer_user_id"] == str(reviewer_one.id) for item in reviewer_one_list)

    reviewer_two_pending = _get_review_packet_snapshot_organization_list(
        client,
        env["headers"],
        f"assigned_reviewer_user_id={reviewer_two.id}&review_status=pending_review",
    )
    assert reviewer_two_pending == []

    reviewer_one_pending = _get_review_packet_snapshot_organization_list(
        client,
        env["headers"],
        f"assigned_reviewer_user_id={reviewer_one.id}&review_status=pending_review",
    )
    assert [item["id"] for item in reviewer_one_pending] == [pending_ready["id"]]

    external_reviewer = _get_review_packet_snapshot_organization_list(
        client,
        env["headers"],
        f"assigned_reviewer_user_id={other_org['user'].id}",
    )
    assert external_reviewer == []


def test_access_review_packet_snapshot_latest_actionable_returns_one_pending_snapshot_per_patient(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-latest-actionable")
    reviewer_one = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-latest-actionable-reviewer-one@example.com",
        password="Secret123!",
    )
    patient_two_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-latest-actionable-two",
    )
    patient_three_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-latest-actionable-three",
    )
    patient_four_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-latest-actionable-four",
    )
    other_org = _bootstrap_patient_env(
        client,
        db_session,
        slug="review-packet-latest-actionable-external",
    )

    base = datetime.now(timezone.utc).replace(microsecond=0)
    ready_escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    ready_task_id = _create_task(client, env["headers"], ready_escalation_id)
    ready_outcome = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        intervention_task_id=ready_task_id,
        metric_name="systolic_bp",
        value_numeric=117,
        observed_at=base + timedelta(days=1),
    )
    ready_care_update = _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="Latest actionable ready snapshot",
        occurred_at=base + timedelta(days=2),
        escalation_id=ready_escalation_id,
        intervention_task_id=ready_task_id,
        outcome_id=ready_outcome["id"],
    )
    ready_resolve = client.post(
        f"/api/v1/escalations/{ready_escalation_id}/resolve",
        json={
            "resolution_reason": "clinically_stable",
            "resolution_notes": "Ready packet for latest actionable test.",
            "outcome_id": ready_outcome["id"],
            "care_update_id": ready_care_update["id"],
            "resolved_at": (base + timedelta(days=3)).isoformat(),
        },
        headers=env["headers"],
    )
    assert ready_resolve.status_code == 200
    ready_complete = client.post(
        f"/api/v1/tasks/{ready_task_id}/complete",
        json={"completion_note": "Latest actionable ready task complete."},
        headers=env["headers"],
    )
    assert ready_complete.status_code == 200

    patient_one_pending_ready = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        patient_one_pending_ready["id"],
        assigned_reviewer_user_id=str(reviewer_one.id),
    )

    _prepare_review_ready_patient(
        client,
        env["headers"],
        patient_two_id,
        summary="Latest actionable approved packet",
    )
    patient_two_pending_initial = _create_review_packet_snapshot(client, env["headers"], patient_two_id)
    patient_two_approved_latest = _create_review_packet_snapshot(client, env["headers"], patient_two_id)
    patient_two_approved_latest = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        patient_two_approved_latest["id"],
        review_status="approved",
    )

    open_escalation_id = _create_escalation(client, env["headers"], patient_three_id)
    _create_task(client, env["headers"], open_escalation_id)
    patient_three_pending_active = _create_review_packet_snapshot(client, env["headers"], patient_three_id)

    patient_four_pending = _create_review_packet_snapshot(client, env["headers"], patient_four_id)
    patient_four_rejected_latest = _create_review_packet_snapshot(client, env["headers"], patient_four_id)
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        patient_four_rejected_latest["id"],
        review_status="rejected",
        review_note="Rejected latest actionable test snapshot.",
    )

    _create_review_packet_snapshot(client, other_org["headers"], other_org["patient_id"])

    full_list = _get_review_packet_snapshot_latest_actionable(client, env["headers"])
    assert {item["patient_id"] for item in full_list} == {env["patient_id"], patient_three_id}
    assert all(item["review_status"] == "pending_review" for item in full_list)
    full_by_patient = {item["patient_id"]: item for item in full_list}
    assert full_by_patient[env["patient_id"]]["id"] == patient_one_pending_ready["id"]
    assert full_by_patient[patient_three_id]["id"] == patient_three_pending_active["id"]
    assert all(
        full_list[index]["created_at"] >= full_list[index + 1]["created_at"]
        for index in range(len(full_list) - 1)
    )
    for earlier, later in zip(full_list, full_list[1:]):
        if earlier["created_at"] == later["created_at"]:
            assert earlier["patient_id"] > later["patient_id"]

    ready_only = _get_review_packet_snapshot_latest_actionable(
        client,
        env["headers"],
        "review_readiness_status=ready_for_review",
    )
    assert [item["id"] for item in ready_only] == [patient_one_pending_ready["id"]]

    active_only = _get_review_packet_snapshot_latest_actionable(
        client,
        env["headers"],
        "review_readiness_status=active_open_work",
    )
    assert [item["id"] for item in active_only] == [patient_three_pending_active["id"]]

    assigned_only = _get_review_packet_snapshot_latest_actionable(
        client,
        env["headers"],
        f"assigned_reviewer_user_id={reviewer_one.id}",
    )
    assert [item["id"] for item in assigned_only] == [patient_one_pending_ready["id"]]

    unassigned_only = _get_review_packet_snapshot_latest_actionable(
        client,
        env["headers"],
        "unassigned=true",
    )
    assert [item["id"] for item in unassigned_only] == [patient_three_pending_active["id"]]

    approved_only = _get_review_packet_snapshot_latest_actionable(
        client,
        env["headers"],
        "review_status=approved",
    )
    assert [item["id"] for item in approved_only] == [patient_two_approved_latest["id"]]

    paged = _get_review_packet_snapshot_latest_actionable(
        client,
        env["headers"],
        "limit=1&offset=1",
    )
    assert [item["id"] for item in paged] == [full_list[1]["id"]]

    external_reviewer = _get_review_packet_snapshot_latest_actionable(
        client,
        env["headers"],
        f"assigned_reviewer_user_id={other_org['user'].id}",
    )
    assert external_reviewer == []


def test_access_review_packet_snapshot_my_pending_returns_only_current_reviewers_pending_snapshots(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-my-pending")
    reviewer_two = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-my-pending-reviewer-two@example.com",
        password="Secret123!",
    )
    reviewer_two_headers = auth_headers(client, reviewer_two.email, "Secret123!")
    patient_two_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-my-pending-two",
    )
    patient_three_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-my-pending-three",
    )
    other_org = _bootstrap_patient_env(client, db_session, slug="review-packet-my-pending-external")

    base = datetime.now(timezone.utc).replace(microsecond=0)
    ready_escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    ready_task_id = _create_task(client, env["headers"], ready_escalation_id)
    ready_outcome = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        intervention_task_id=ready_task_id,
        metric_name="systolic_bp",
        value_numeric=116,
        observed_at=base + timedelta(days=1),
    )
    ready_care_update = _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="My pending ready snapshot",
        occurred_at=base + timedelta(days=2),
        escalation_id=ready_escalation_id,
        intervention_task_id=ready_task_id,
        outcome_id=ready_outcome["id"],
    )
    ready_resolve = client.post(
        f"/api/v1/escalations/{ready_escalation_id}/resolve",
        json={
            "resolution_reason": "clinically_stable",
            "resolution_notes": "Ready packet for my-pending test.",
            "outcome_id": ready_outcome["id"],
            "care_update_id": ready_care_update["id"],
            "resolved_at": (base + timedelta(days=3)).isoformat(),
        },
        headers=env["headers"],
    )
    assert ready_resolve.status_code == 200
    ready_complete = client.post(
        f"/api/v1/tasks/{ready_task_id}/complete",
        json={"completion_note": "My-pending ready task complete."},
        headers=env["headers"],
    )
    assert ready_complete.status_code == 200

    my_pending_ready = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        my_pending_ready["id"],
        assigned_reviewer_user_id=str(env["user"].id),
    )

    _prepare_review_ready_patient(
        client,
        env["headers"],
        patient_two_id,
        summary="My pending approved packet",
    )
    my_approved = _create_review_packet_snapshot(client, env["headers"], patient_two_id)
    my_approved = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        my_approved["id"],
        review_status="approved",
    )
    _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        my_approved["id"],
        assigned_reviewer_user_id=str(env["user"].id),
    )

    reviewer_two_pending = _create_review_packet_snapshot(client, env["headers"], patient_three_id)
    _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        reviewer_two_pending["id"],
        assigned_reviewer_user_id=str(reviewer_two.id),
    )

    unassigned_pending = _create_review_packet_snapshot(client, env["headers"], patient_two_id)
    _create_review_packet_snapshot(client, other_org["headers"], other_org["patient_id"])

    tracked_snapshots = {
        snapshot.id: snapshot
        for snapshot in db_session.execute(
            select(AccessReviewPacketSnapshot).where(
                AccessReviewPacketSnapshot.id.in_(
                    [
                        UUID(my_pending_ready["id"]),
                        UUID(reviewer_two_pending["id"]),
                    ]
                )
            )
        ).scalars()
    }
    tracked_snapshots[UUID(my_pending_ready["id"])].created_at = base - timedelta(days=8)
    tracked_snapshots[UUID(reviewer_two_pending["id"])].created_at = base
    db_session.commit()
    db_session.expire_all()

    events_before = _get_review_packet_snapshot_events(client, env["headers"], my_pending_ready["id"])
    my_pending = _get_review_packet_snapshot_my_pending(client, env["headers"])
    events_after = _get_review_packet_snapshot_events(client, env["headers"], my_pending_ready["id"])
    assert [item["id"] for item in my_pending] == [my_pending_ready["id"]]
    assert all(item["assigned_reviewer_user_id"] == str(env["user"].id) for item in my_pending)
    assert all(item["review_status"] == "pending_review" for item in my_pending)
    assert my_pending[0]["review_action"] == {
        "action": "stale_review",
        "reason": "Snapshot has been pending reviewer action for more than 7 days.",
        "priority": "high",
    }
    assert events_after == events_before

    ready_only = _get_review_packet_snapshot_my_pending(
        client,
        env["headers"],
        "review_readiness_status=ready_for_review",
    )
    assert [item["id"] for item in ready_only] == [my_pending_ready["id"]]

    incomplete_only = _get_review_packet_snapshot_my_pending(
        client,
        env["headers"],
        "review_readiness_status=incomplete",
    )
    assert incomplete_only == []

    include_approved = _get_review_packet_snapshot_my_pending(
        client,
        env["headers"],
        "review_status=approved",
    )
    assert [item["id"] for item in include_approved] == [my_approved["id"]]

    reviewer_two_pending_list = _get_review_packet_snapshot_my_pending(client, reviewer_two_headers)
    assert [item["id"] for item in reviewer_two_pending_list] == [reviewer_two_pending["id"]]
    assert all(item["assigned_reviewer_user_id"] == str(reviewer_two.id) for item in reviewer_two_pending_list)
    assert reviewer_two_pending_list[0]["review_action"] == {
        "action": "missing_evidence",
        "reason": "Snapshot is blocked by missing evidence.",
        "priority": "high",
    }

    paged = _get_review_packet_snapshot_my_pending(
        client,
        env["headers"],
        "review_status=approved&limit=1&offset=0",
    )
    assert [item["id"] for item in paged] == [my_approved["id"]]


def test_access_review_packet_snapshot_my_pending_ready_review_action_is_normal_when_not_stale(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-my-pending-ready-action")
    _prepare_review_ready_patient(
        client,
        env["headers"],
        env["patient_id"],
        summary="My pending ready action packet",
    )
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        snapshot["id"],
        assigned_reviewer_user_id=str(env["user"].id),
    )

    tracked_snapshot = db_session.execute(
        select(AccessReviewPacketSnapshot).where(
            AccessReviewPacketSnapshot.id == UUID(snapshot["id"])
        )
    ).scalar_one()
    tracked_snapshot.created_at = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=7)
    db_session.commit()
    db_session.expire_all()

    events_before = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])
    payload = _get_review_packet_snapshot_my_pending(client, env["headers"])
    events_after = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])

    assert [item["id"] for item in payload] == [snapshot["id"]]
    assert payload[0]["review_action"] == {
        "action": "ready_to_review",
        "reason": "Snapshot is ready for reviewer approval.",
        "priority": "normal",
    }
    assert payload[0]["packet_json"] == snapshot["packet_json"]
    assert payload[0]["packet_markdown"] == snapshot["packet_markdown"]
    assert events_after == events_before


def test_access_review_packet_reviewer_my_summary_counts_only_assigned_pending_workload(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-reviewer-summary")
    reviewer_two = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-reviewer-summary-reviewer-two@example.com",
        password="Secret123!",
    )
    reviewer_two_headers = auth_headers(client, reviewer_two.email, "Secret123!")
    patient_two_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-reviewer-summary-two",
    )
    patient_three_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-reviewer-summary-three",
    )
    patient_four_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-reviewer-summary-four",
    )
    patient_five_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-reviewer-summary-five",
    )
    other_org = _bootstrap_patient_env(client, db_session, slug="review-packet-reviewer-summary-external")

    base = datetime.now(timezone.utc).replace(microsecond=0)
    _prepare_review_ready_patient(
        client,
        env["headers"],
        env["patient_id"],
        summary="Reviewer summary assigned ready packet",
    )
    assigned_ready = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        assigned_ready["id"],
        assigned_reviewer_user_id=str(env["user"].id),
    )

    blocked_escalation_id = _create_escalation(client, env["headers"], patient_two_id)
    _create_task(client, env["headers"], blocked_escalation_id)
    blocked_missing = _create_review_packet_snapshot(client, env["headers"], patient_two_id)
    _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        blocked_missing["id"],
        assigned_reviewer_user_id=str(env["user"].id),
    )

    _prepare_review_ready_patient(
        client,
        env["headers"],
        patient_three_id,
        summary="Reviewer summary approved packet",
    )
    approved = _create_review_packet_snapshot(client, env["headers"], patient_three_id)
    _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        approved["id"],
        assigned_reviewer_user_id=str(env["user"].id),
    )
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        approved["id"],
        review_status="approved",
    )

    rejected = _create_review_packet_snapshot(client, env["headers"], patient_four_id)
    _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        rejected["id"],
        assigned_reviewer_user_id=str(env["user"].id),
    )
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        rejected["id"],
        review_status="rejected",
        review_note="Rejected from reviewer summary test.",
    )

    assigned_to_other = _create_review_packet_snapshot(client, env["headers"], patient_five_id)
    _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        assigned_to_other["id"],
        assigned_reviewer_user_id=str(reviewer_two.id),
    )

    unassigned = _create_review_packet_snapshot(client, env["headers"], patient_three_id)
    _create_review_packet_snapshot(client, other_org["headers"], other_org["patient_id"])

    tracked_snapshots = {
        snapshot.id: snapshot
        for snapshot in db_session.execute(
            select(AccessReviewPacketSnapshot).where(
                AccessReviewPacketSnapshot.id.in_(
                    [
                        UUID(assigned_ready["id"]),
                        UUID(blocked_missing["id"]),
                        UUID(approved["id"]),
                        UUID(rejected["id"]),
                        UUID(assigned_to_other["id"]),
                        UUID(unassigned["id"]),
                    ]
                )
            )
        ).scalars()
    }
    tracked_snapshots[UUID(assigned_ready["id"])].created_at = base
    tracked_snapshots[UUID(blocked_missing["id"])].created_at = base - timedelta(days=2)
    tracked_snapshots[UUID(approved["id"])].created_at = base - timedelta(days=5)
    tracked_snapshots[UUID(rejected["id"])].created_at = base - timedelta(days=9)
    db_session.commit()
    db_session.expire_all()

    events_before = _get_review_packet_snapshot_events(client, env["headers"], assigned_ready["id"])
    summary = _get_review_packet_reviewer_my_summary(client, env["headers"])
    events_after = _get_review_packet_snapshot_events(client, env["headers"], assigned_ready["id"])

    assert summary == {
        "assigned_to_me_count": 2,
        "pending_assigned_ready_count": 1,
        "blocked_missing_evidence_count": 1,
        "oldest_pending_snapshot_created_at": (base - timedelta(days=2)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "pending_review_age": {
            "new_today_count": 1,
            "one_to_three_days_count": 1,
            "four_to_seven_days_count": 0,
            "over_seven_days_count": 0,
        },
    }
    assert events_after == events_before

    reviewer_two_summary = _get_review_packet_reviewer_my_summary(client, reviewer_two_headers)
    assert reviewer_two_summary == {
        "assigned_to_me_count": 1,
        "pending_assigned_ready_count": 0,
        "blocked_missing_evidence_count": 1,
        "oldest_pending_snapshot_created_at": tracked_snapshots[UUID(assigned_to_other["id"])].created_at.strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "pending_review_age": {
            "new_today_count": 1,
            "one_to_three_days_count": 0,
            "four_to_seven_days_count": 0,
            "over_seven_days_count": 0,
        },
    }

    detail = _get_review_packet_snapshot_detail(client, env["headers"], assigned_ready["id"])
    assert detail["packet_json"] == assigned_ready["packet_json"]
    assert detail["packet_markdown"] == assigned_ready["packet_markdown"]


def test_access_review_packet_snapshot_patient_backlog_returns_latest_snapshot_and_counts_per_patient(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-patient-backlog")
    patient_two_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-patient-backlog-two",
    )
    patient_three_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-patient-backlog-three",
    )
    other_org = _bootstrap_patient_env(
        client,
        db_session,
        slug="review-packet-patient-backlog-external",
    )

    base = datetime.now(timezone.utc).replace(microsecond=0)
    ready_escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    ready_task_id = _create_task(client, env["headers"], ready_escalation_id)
    ready_outcome = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        intervention_task_id=ready_task_id,
        metric_name="systolic_bp",
        value_numeric=119,
        observed_at=base + timedelta(days=1),
    )
    ready_care_update = _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="Patient backlog ready snapshot",
        occurred_at=base + timedelta(days=2),
        escalation_id=ready_escalation_id,
        intervention_task_id=ready_task_id,
        outcome_id=ready_outcome["id"],
    )
    ready_resolve = client.post(
        f"/api/v1/escalations/{ready_escalation_id}/resolve",
        json={
            "resolution_reason": "clinically_stable",
            "resolution_notes": "Ready packet for patient backlog test.",
            "outcome_id": ready_outcome["id"],
            "care_update_id": ready_care_update["id"],
            "resolved_at": (base + timedelta(days=3)).isoformat(),
        },
        headers=env["headers"],
    )
    assert ready_resolve.status_code == 200
    ready_complete = client.post(
        f"/api/v1/tasks/{ready_task_id}/complete",
        json={"completion_note": "Ready task complete for backlog."},
        headers=env["headers"],
    )
    assert ready_complete.status_code == 200

    patient_one_pending = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _prepare_review_ready_patient(
        client,
        env["headers"],
        patient_two_id,
        summary="Patient backlog approved packet",
    )
    patient_two_approved = _create_review_packet_snapshot(client, env["headers"], patient_two_id)
    patient_two_approved = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        patient_two_approved["id"],
        review_status="approved",
    )

    open_escalation_id = _create_escalation(client, env["headers"], patient_three_id)
    _create_task(client, env["headers"], open_escalation_id)
    patient_three_rejected = _create_review_packet_snapshot(client, env["headers"], patient_three_id)
    patient_three_rejected = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        patient_three_rejected["id"],
        review_status="rejected",
        review_note="Patient still has open work.",
    )

    patient_two_pending = _create_review_packet_snapshot(client, env["headers"], patient_two_id)

    _create_review_packet_snapshot(client, other_org["headers"], other_org["patient_id"])

    full_backlog = _get_review_packet_snapshot_patient_backlog(client, env["headers"])

    assert {item["patient_id"] for item in full_backlog} == {
        env["patient_id"],
        patient_two_id,
        patient_three_id,
    }
    backlog_by_patient = {item["patient_id"]: item for item in full_backlog}

    assert backlog_by_patient[patient_two_id]["latest_snapshot_id"] == patient_two_pending["id"]
    assert backlog_by_patient[patient_two_id]["latest_review_status"] == "pending_review"
    assert backlog_by_patient[patient_two_id]["latest_review_readiness_status"] == "ready_for_review"
    assert backlog_by_patient[patient_two_id]["pending_review_count"] == 1
    assert backlog_by_patient[patient_two_id]["approved_count"] == 1
    assert backlog_by_patient[patient_two_id]["rejected_count"] == 0
    assert backlog_by_patient[patient_two_id]["total_snapshot_count"] == 2

    assert backlog_by_patient[patient_three_id]["latest_snapshot_id"] == patient_three_rejected["id"]
    assert backlog_by_patient[patient_three_id]["latest_review_status"] == "rejected"
    assert backlog_by_patient[patient_three_id]["latest_review_readiness_status"] == "active_open_work"
    assert backlog_by_patient[patient_three_id]["pending_review_count"] == 0
    assert backlog_by_patient[patient_three_id]["approved_count"] == 0
    assert backlog_by_patient[patient_three_id]["rejected_count"] == 1
    assert backlog_by_patient[patient_three_id]["total_snapshot_count"] == 1

    assert backlog_by_patient[env["patient_id"]]["latest_snapshot_id"] == patient_one_pending["id"]
    assert backlog_by_patient[env["patient_id"]]["latest_review_status"] == "pending_review"
    assert (
        backlog_by_patient[env["patient_id"]]["latest_review_readiness_status"]
        == "ready_for_review"
    )
    assert backlog_by_patient[env["patient_id"]]["pending_review_count"] == 1
    assert backlog_by_patient[env["patient_id"]]["approved_count"] == 0
    assert backlog_by_patient[env["patient_id"]]["rejected_count"] == 0
    assert backlog_by_patient[env["patient_id"]]["total_snapshot_count"] == 1
    assert all(
        full_backlog[index]["latest_snapshot_created_at"]
        >= full_backlog[index + 1]["latest_snapshot_created_at"]
        for index in range(len(full_backlog) - 1)
    )
    for earlier, later in zip(full_backlog, full_backlog[1:]):
        if earlier["latest_snapshot_created_at"] == later["latest_snapshot_created_at"]:
            assert earlier["patient_id"] > later["patient_id"]

    pending_backlog = _get_review_packet_snapshot_patient_backlog(
        client,
        env["headers"],
        "review_status=pending_review",
    )
    assert {item["patient_id"] for item in pending_backlog} == {patient_two_id, env["patient_id"]}
    assert all(item["latest_review_status"] == "pending_review" for item in pending_backlog)
    for earlier, later in zip(pending_backlog, pending_backlog[1:]):
        if earlier["latest_snapshot_created_at"] == later["latest_snapshot_created_at"]:
            assert earlier["patient_id"] > later["patient_id"]

    rejected_backlog = _get_review_packet_snapshot_patient_backlog(
        client,
        env["headers"],
        "review_status=rejected",
    )
    assert [item["patient_id"] for item in rejected_backlog] == [patient_three_id]

    ready_backlog = _get_review_packet_snapshot_patient_backlog(
        client,
        env["headers"],
        "review_readiness_status=ready_for_review",
    )
    assert {item["patient_id"] for item in ready_backlog} == {env["patient_id"], patient_two_id}

    active_backlog = _get_review_packet_snapshot_patient_backlog(
        client,
        env["headers"],
        "review_readiness_status=active_open_work",
    )
    assert [item["patient_id"] for item in active_backlog] == [patient_three_id]

    incomplete_backlog = _get_review_packet_snapshot_patient_backlog(
        client,
        env["headers"],
        "review_readiness_status=incomplete",
    )
    assert incomplete_backlog == []

    paged = _get_review_packet_snapshot_patient_backlog(
        client,
        env["headers"],
        "limit=1&offset=1",
    )
    assert [item["patient_id"] for item in paged] == [full_backlog[1]["patient_id"]]


def test_access_review_packet_snapshot_patient_backlog_detail_returns_filtered_snapshots_for_one_patient(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-patient-backlog-detail")
    patient_two_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-patient-backlog-detail-two",
    )
    other_org = _bootstrap_patient_env(
        client,
        db_session,
        slug="review-packet-patient-backlog-detail-external",
    )
    _prepare_review_ready_patient(
        client,
        env["headers"],
        env["patient_id"],
        summary="Patient backlog detail approved packet",
    )

    approved = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    approved = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        approved["id"],
        review_status="approved",
    )

    rejected = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    rejected = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        rejected["id"],
        review_status="rejected",
        review_note="Rejected in patient backlog detail test.",
    )

    pending = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _create_review_packet_snapshot(client, env["headers"], patient_two_id)
    _create_review_packet_snapshot(client, other_org["headers"], other_org["patient_id"])

    full_list = _get_review_packet_snapshot_patient_backlog_detail(
        client,
        env["headers"],
        env["patient_id"],
    )
    standalone_audit_status = _get_review_packet_patient_audit_status(
        client,
        env["headers"],
        env["patient_id"],
    )
    assert isinstance(full_list, dict)
    assert set(full_list.keys()) == {"patient_id", "audit_status", "snapshots"}
    assert full_list["patient_id"] == env["patient_id"]
    assert full_list["audit_status"] == standalone_audit_status
    assert "completion_summary" in full_list["audit_status"]
    assert [item["id"] for item in full_list["snapshots"]] == [pending["id"], rejected["id"], approved["id"]]
    assert all(item["patient_id"] == env["patient_id"] for item in full_list["snapshots"])
    assert all(
        item["organization_id"] == str(env["organization"].id) for item in full_list["snapshots"]
    )
    assert all(
        {
            "id",
            "patient_id",
            "organization_id",
            "generated_at",
            "created_at",
            "updated_at",
            "review_readiness_status",
            "review_status",
            "review_state",
            "review_action",
            "packet_json",
            "packet_markdown",
        }.issubset(item.keys())
        for item in full_list["snapshots"]
    )
    assert full_list["snapshots"][0]["packet_json"] == pending["packet_json"]
    assert full_list["snapshots"][0]["packet_markdown"] == pending["packet_markdown"]

    pending_list = _get_review_packet_snapshot_patient_backlog_detail(
        client,
        env["headers"],
        env["patient_id"],
        "review_status=pending_review",
    )
    assert isinstance(pending_list, dict)
    assert set(pending_list.keys()) == {"patient_id", "audit_status", "snapshots"}
    assert pending_list["audit_status"] == standalone_audit_status
    assert [item["id"] for item in pending_list["snapshots"]] == [pending["id"]]

    rejected_list = _get_review_packet_snapshot_patient_backlog_detail(
        client,
        env["headers"],
        env["patient_id"],
        "review_status=rejected",
    )
    assert isinstance(rejected_list, dict)
    assert set(rejected_list.keys()) == {"patient_id", "audit_status", "snapshots"}
    assert rejected_list["audit_status"] == standalone_audit_status
    assert [item["id"] for item in rejected_list["snapshots"]] == [rejected["id"]]

    incomplete_list = _get_review_packet_snapshot_patient_backlog_detail(
        client,
        env["headers"],
        env["patient_id"],
        "review_readiness_status=incomplete",
    )
    assert isinstance(incomplete_list, dict)
    assert set(incomplete_list.keys()) == {"patient_id", "audit_status", "snapshots"}
    assert incomplete_list["patient_id"] == env["patient_id"]
    assert incomplete_list["audit_status"] == standalone_audit_status
    assert incomplete_list["snapshots"] == []

    ready_list = _get_review_packet_snapshot_patient_backlog_detail(
        client,
        env["headers"],
        env["patient_id"],
        "review_readiness_status=ready_for_review",
    )
    assert isinstance(ready_list, dict)
    assert set(ready_list.keys()) == {"patient_id", "audit_status", "snapshots"}
    assert ready_list["audit_status"] == standalone_audit_status
    assert [item["id"] for item in ready_list["snapshots"]] == [
        pending["id"],
        rejected["id"],
        approved["id"],
    ]

    paged = _get_review_packet_snapshot_patient_backlog_detail(
        client,
        env["headers"],
        env["patient_id"],
        "limit=1&offset=1",
    )
    assert isinstance(paged, dict)
    assert set(paged.keys()) == {"patient_id", "audit_status", "snapshots"}
    assert paged["audit_status"] == standalone_audit_status
    assert [item["id"] for item in paged["snapshots"]] == [rejected["id"]]

    other_patient = _get_review_packet_snapshot_patient_backlog_detail(
        client,
        env["headers"],
        patient_two_id,
    )
    assert isinstance(other_patient, dict)
    assert set(other_patient.keys()) == {"patient_id", "audit_status", "snapshots"}
    assert other_patient["patient_id"] == patient_two_id
    assert len(other_patient["snapshots"]) == 1

    forbidden = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/patient-backlog/{env['patient_id']}",
        headers=other_org["headers"],
    )
    assert forbidden.status_code == 403

    missing = client.get(
        "/api/v1/reports/access-review-packet/snapshots/patient-backlog/00000000-0000-0000-0000-000000000000",
        headers=env["headers"],
    )
    assert missing.status_code == 404


def test_access_review_packet_snapshot_patient_backlog_detail_includes_audit_status_for_no_snapshot_patient(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-patient-backlog-detail-empty")

    payload = _get_review_packet_snapshot_patient_backlog_detail(
        client,
        env["headers"],
        env["patient_id"],
    )

    assert isinstance(payload, dict)
    assert set(payload.keys()) == {"patient_id", "audit_status", "snapshots"}
    assert payload["patient_id"] == env["patient_id"]
    assert payload["snapshots"] == []
    standalone = _get_review_packet_patient_audit_status(
        client,
        env["headers"],
        env["patient_id"],
    )
    assert payload["audit_status"] == standalone
    assert payload["audit_status"]["has_snapshot"] is False
    assert payload["audit_status"]["completion_summary"]["status"] == "not_started"


def test_access_review_packet_snapshot_patient_backlog_latest_returns_latest_matching_snapshot(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-patient-backlog-latest")
    other = _bootstrap_patient_env(
        client,
        db_session,
        slug="review-packet-patient-backlog-latest-other",
    )
    _prepare_review_ready_patient(
        client,
        env["headers"],
        env["patient_id"],
        summary="Patient backlog latest approved packet",
    )

    approved = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    approved = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        approved["id"],
        review_status="approved",
    )
    rejected = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    rejected = _update_review_packet_snapshot_review(
        client,
        env["headers"],
        rejected["id"],
        review_status="rejected",
        review_note="Rejected in latest backlog test.",
    )
    pending = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    latest = _get_review_packet_snapshot_patient_backlog_latest(
        client,
        env["headers"],
        env["patient_id"],
    )
    assert latest["id"] == pending["id"]
    assert latest["packet_json"] == pending["packet_json"]
    assert latest["packet_markdown"] == pending["packet_markdown"]
    assert latest["audit_timeline"] is not None
    assert _timeline_event_types(latest) == ["snapshot_created"]

    latest_rejected = _get_review_packet_snapshot_patient_backlog_latest(
        client,
        env["headers"],
        env["patient_id"],
        "review_status=rejected",
    )
    assert latest_rejected["id"] == rejected["id"]
    assert latest_rejected["audit_timeline"] is not None
    assert _timeline_event_types(latest_rejected) == ["snapshot_created", "snapshot_rejected"]

    latest_ready = _get_review_packet_snapshot_patient_backlog_latest(
        client,
        env["headers"],
        env["patient_id"],
        "review_readiness_status=ready_for_review",
    )
    assert latest_ready["id"] == pending["id"]

    no_match = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/patient-backlog/{env['patient_id']}/latest?review_readiness_status=incomplete",
        headers=env["headers"],
    )
    assert no_match.status_code == 404

    forbidden = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/patient-backlog/{env['patient_id']}/latest",
        headers=other["headers"],
    )
    assert forbidden.status_code == 403

    missing = client.get(
        "/api/v1/reports/access-review-packet/snapshots/patient-backlog/00000000-0000-0000-0000-000000000000/latest",
        headers=env["headers"],
    )
    assert missing.status_code == 404


def test_access_review_packet_snapshot_queue_summary_groups_counts_for_org_backlog(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-queue-summary")
    reviewer = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-queue-summary-reviewer@example.com",
        password="Secret123!",
    )
    override_user = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-queue-summary-superuser@example.com",
        password="Secret123!",
        is_superuser=True,
    )
    override_headers = auth_headers(client, override_user.email, "Secret123!")
    patient_two_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-queue-summary-two",
    )
    patient_three_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-queue-summary-three",
    )
    patient_four_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-queue-summary-four",
    )
    other_org = _bootstrap_patient_env(client, db_session, slug="review-packet-queue-summary-external")

    base = datetime.now(timezone.utc).replace(microsecond=0)
    ready_escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    ready_task_id = _create_task(client, env["headers"], ready_escalation_id)
    ready_outcome = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        intervention_task_id=ready_task_id,
        metric_name="systolic_bp",
        value_numeric=120,
        observed_at=base + timedelta(days=1),
    )
    ready_care_update = _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="Queue summary ready snapshot",
        occurred_at=base + timedelta(days=2),
        escalation_id=ready_escalation_id,
        intervention_task_id=ready_task_id,
        outcome_id=ready_outcome["id"],
    )
    resolve_resp = client.post(
        f"/api/v1/escalations/{ready_escalation_id}/resolve",
        json={
            "resolution_reason": "clinically_stable",
            "resolution_notes": "Ready packet for queue summary.",
            "outcome_id": ready_outcome["id"],
            "care_update_id": ready_care_update["id"],
            "resolved_at": (base + timedelta(days=3)).isoformat(),
        },
        headers=env["headers"],
    )
    assert resolve_resp.status_code == 200
    complete_resp = client.post(
        f"/api/v1/tasks/{ready_task_id}/complete",
        json={"completion_note": "Queue summary task complete."},
        headers=env["headers"],
    )
    assert complete_resp.status_code == 200

    pending_ready = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        pending_ready["id"],
        assigned_reviewer_user_id=str(reviewer.id),
    )

    _prepare_review_ready_patient(
        client,
        env["headers"],
        patient_two_id,
        summary="Queue summary approved exported packet",
    )
    approved_exported = _create_review_packet_snapshot(client, env["headers"], patient_two_id)
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        approved_exported["id"],
        review_status="approved",
    )
    _get_review_packet_snapshot_audit_bundle(client, env["headers"], approved_exported["id"])
    _get_review_packet_snapshot_audit_bundle_markdown(client, env["headers"], approved_exported["id"])
    _get_review_packet_snapshot_audit_bundle_pdf(client, env["headers"], approved_exported["id"])

    open_escalation_id = _create_escalation(client, env["headers"], patient_three_id)
    _create_task(client, env["headers"], open_escalation_id)
    pending_active = _create_review_packet_snapshot(client, env["headers"], patient_three_id)

    pending_incomplete = _create_review_packet_snapshot(client, env["headers"], patient_four_id)
    _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        pending_incomplete["id"],
        assigned_reviewer_user_id=str(reviewer.id),
    )

    patient_seven_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-queue-summary-seven",
    )
    _prepare_review_ready_patient(
        client,
        env["headers"],
        patient_seven_id,
        summary="Queue summary pending unassigned packet",
    )
    pending_unassigned_ready = _create_review_packet_snapshot(client, env["headers"], patient_seven_id)

    rejected_incomplete = _create_review_packet_snapshot(client, env["headers"], patient_four_id)
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        rejected_incomplete["id"],
        review_status="rejected",
        review_note="Rejected from queue summary test.",
    )

    patient_five_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-queue-summary-five",
    )
    _prepare_review_ready_patient(
        client,
        env["headers"],
        patient_five_id,
        summary="Queue summary approved not exported packet",
    )
    approved_not_exported = _create_review_packet_snapshot(client, env["headers"], patient_five_id)
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        approved_not_exported["id"],
        review_status="approved",
    )

    patient_six_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-queue-summary-six",
    )
    approved_with_override = _create_review_packet_snapshot(client, env["headers"], patient_six_id)
    _update_review_packet_snapshot_review(
        client,
        override_headers,
        approved_with_override["id"],
        review_status="approved",
        decision_note="Queue summary override approval.",
        override_missing_checklist=True,
        override_reason="Queue summary documented exception.",
    )

    _create_review_packet_snapshot(client, other_org["headers"], other_org["patient_id"])

    pending_snapshots_by_id = {
        snapshot.id: snapshot
        for snapshot in db_session.execute(
            select(AccessReviewPacketSnapshot).where(
                AccessReviewPacketSnapshot.id.in_(
                    [
                        UUID(pending_ready["id"]),
                        UUID(pending_active["id"]),
                        UUID(pending_incomplete["id"]),
                        UUID(pending_unassigned_ready["id"]),
                    ]
                )
            )
        ).scalars()
    }
    for snapshot_id, created_at in (
        (UUID(pending_ready["id"]), base),
        (UUID(pending_active["id"]), base - timedelta(days=2)),
        (UUID(pending_incomplete["id"]), base - timedelta(days=5)),
        (UUID(pending_unassigned_ready["id"]), base - timedelta(days=9)),
    ):
        pending_snapshots_by_id[snapshot_id].created_at = created_at
    db_session.commit()
    db_session.expire_all()

    events_before = _get_review_packet_snapshot_events(client, env["headers"], approved_exported["id"])
    summary = _get_review_packet_snapshot_queue_summary(client, env["headers"])
    events_after = _get_review_packet_snapshot_events(client, env["headers"], approved_exported["id"])

    assert summary == {
        "total": 8,
        "review_status": {
            "pending_review": 4,
            "approved": 3,
            "rejected": 1,
        },
        "review_readiness_status": {
            "ready_for_review": 4,
            "active_open_work": 1,
            "incomplete": 3,
        },
        "assigned": 2,
        "unassigned": 6,
        "pending_review_assigned": 2,
        "pending_review_unassigned": 2,
        "pending_review_ready_for_review": 2,
        "pending_review_active_open_work": 1,
        "pending_review_incomplete": 1,
        "snapshot_audit_lifecycle": {
            "pending_unassigned_count": 1,
            "pending_assigned_ready_count": 1,
            "blocked_missing_evidence_count": 2,
            "approved_count": 2,
            "approved_with_override_count": 1,
            "rejected_count": 1,
            "approved_not_exported_count": 2,
            "exported_count": 1,
            "pending_review_age": {
                "new_today_count": 1,
                "one_to_three_days_count": 1,
                "four_to_seven_days_count": 1,
                "over_seven_days_count": 1,
            },
        },
        "audit_readiness_rollup": {
            "incomplete_count": 1,
            "review_ready_count": 2,
            "approved_not_exported_count": 2,
            "audit_ready_count": 1,
            "rejected_count": 1,
        },
    }
    assert events_after == events_before


def test_access_review_packet_snapshot_queue_summary_returns_zero_groups_when_empty(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-queue-summary-empty")

    summary = _get_review_packet_snapshot_queue_summary(client, env["headers"])

    assert summary == {
        "total": 0,
        "review_status": {
            "pending_review": 0,
            "approved": 0,
            "rejected": 0,
        },
        "review_readiness_status": {
            "ready_for_review": 0,
            "active_open_work": 0,
            "incomplete": 0,
        },
        "assigned": 0,
        "unassigned": 0,
        "pending_review_assigned": 0,
        "pending_review_unassigned": 0,
        "pending_review_ready_for_review": 0,
        "pending_review_active_open_work": 0,
        "pending_review_incomplete": 0,
        "snapshot_audit_lifecycle": {
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
        },
        "audit_readiness_rollup": {
            "incomplete_count": 0,
            "review_ready_count": 0,
            "approved_not_exported_count": 0,
            "audit_ready_count": 0,
            "rejected_count": 0,
        },
    }


def test_access_review_packet_audit_readiness_returns_latest_per_patient_worklist(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-readiness")
    reviewer = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-audit-readiness-reviewer@example.com",
        password="Secret123!",
    )
    override_user = create_user_for_org(
        db_session,
        organization=env["organization"],
        email="review-packet-audit-readiness-superuser@example.com",
        password="Secret123!",
        is_superuser=True,
    )
    override_headers = auth_headers(client, override_user.email, "Secret123!")
    patient_two_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-audit-readiness-two",
    )
    patient_three_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-audit-readiness-three",
    )
    patient_four_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-audit-readiness-four",
    )
    patient_five_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-audit-readiness-five",
    )
    patient_six_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-audit-readiness-six",
    )
    patient_seven_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="review-packet-audit-readiness-seven",
    )
    other_org = _bootstrap_patient_env(client, db_session, slug="review-packet-audit-readiness-other")
    base = datetime.now(timezone.utc).replace(microsecond=0)

    blocked_latest = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])
    _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        blocked_latest["id"],
        assigned_reviewer_user_id=str(reviewer.id),
    )

    _prepare_review_ready_patient(
        client,
        env["headers"],
        patient_two_id,
        summary="Audit readiness review ready assigned",
    )
    review_ready_assigned = _create_review_packet_snapshot(client, env["headers"], patient_two_id)
    _update_review_packet_snapshot_assignment(
        client,
        env["headers"],
        review_ready_assigned["id"],
        assigned_reviewer_user_id=str(reviewer.id),
    )

    _prepare_review_ready_patient(
        client,
        env["headers"],
        patient_three_id,
        summary="Audit readiness approved not exported",
    )
    approved_not_exported = _create_review_packet_snapshot(client, env["headers"], patient_three_id)
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        approved_not_exported["id"],
        review_status="approved",
    )

    _prepare_review_ready_patient(
        client,
        env["headers"],
        patient_four_id,
        summary="Audit readiness approved exported",
    )
    approved_exported = _create_review_packet_snapshot(client, env["headers"], patient_four_id)
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        approved_exported["id"],
        review_status="approved",
    )
    _get_review_packet_snapshot_audit_bundle(client, env["headers"], approved_exported["id"])
    _get_review_packet_snapshot_audit_bundle_markdown(client, env["headers"], approved_exported["id"])
    _get_review_packet_snapshot_audit_bundle_pdf(client, env["headers"], approved_exported["id"])

    _prepare_review_ready_patient(
        client,
        env["headers"],
        patient_five_id,
        summary="Audit readiness historical approved before rejected latest",
    )
    historical_old = _create_review_packet_snapshot(client, env["headers"], patient_five_id)
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        historical_old["id"],
        review_status="approved",
    )
    rejected_latest = _create_review_packet_snapshot(client, env["headers"], patient_five_id)
    _update_review_packet_snapshot_review(
        client,
        env["headers"],
        rejected_latest["id"],
        review_status="rejected",
        review_note="Audit readiness rejected latest snapshot.",
    )

    approved_with_override = _create_review_packet_snapshot(client, env["headers"], patient_six_id)
    _update_review_packet_snapshot_review(
        client,
        override_headers,
        approved_with_override["id"],
        review_status="approved",
        decision_note="Audit readiness override approval.",
        override_missing_checklist=True,
        override_reason="Audit readiness documented exception.",
    )

    _prepare_review_ready_patient(
        client,
        env["headers"],
        patient_seven_id,
        summary="Audit readiness pending unassigned latest",
    )
    review_ready_unassigned = _create_review_packet_snapshot(client, env["headers"], patient_seven_id)

    _get_review_packet_snapshot_audit_bundle(client, env["headers"], historical_old["id"])

    _create_review_packet_snapshot(client, other_org["headers"], other_org["patient_id"])

    tracked_snapshots = {
        snapshot.id: snapshot
        for snapshot in db_session.execute(
            select(AccessReviewPacketSnapshot).where(
                AccessReviewPacketSnapshot.id.in_(
                    [
                        UUID(blocked_latest["id"]),
                        UUID(review_ready_assigned["id"]),
                        UUID(approved_not_exported["id"]),
                        UUID(approved_exported["id"]),
                        UUID(rejected_latest["id"]),
                        UUID(approved_with_override["id"]),
                        UUID(review_ready_unassigned["id"]),
                        UUID(historical_old["id"]),
                    ]
                )
            )
        ).scalars()
    }
    tracked_snapshots[UUID(approved_exported["id"])].created_at = base + timedelta(minutes=5)
    tracked_snapshots[UUID(approved_not_exported["id"])].created_at = base + timedelta(minutes=4)
    tracked_snapshots[UUID(rejected_latest["id"])].created_at = base + timedelta(minutes=3)
    tracked_snapshots[UUID(review_ready_assigned["id"])].created_at = base + timedelta(minutes=2)
    tracked_snapshots[UUID(review_ready_unassigned["id"])].created_at = base + timedelta(minutes=1, seconds=30)
    tracked_snapshots[UUID(approved_with_override["id"])].created_at = base + timedelta(minutes=1)
    tracked_snapshots[UUID(blocked_latest["id"])].created_at = base
    tracked_snapshots[UUID(historical_old["id"])].created_at = base - timedelta(days=1)
    db_session.commit()
    db_session.expire_all()

    events_before = _get_review_packet_snapshot_events(client, env["headers"], approved_exported["id"])
    full_payload = _get_review_packet_audit_readiness(client, env["headers"])
    events_after = _get_review_packet_snapshot_events(client, env["headers"], approved_exported["id"])

    assert full_payload["total_count"] == 7
    assert full_payload["limit"] == 50
    assert full_payload["offset"] == 0
    expected_status_counts = {
        "incomplete_count": 1,
        "review_ready_count": 2,
        "approved_not_exported_count": 2,
        "audit_ready_count": 1,
        "rejected_count": 1,
    }
    assert full_payload["status_counts"] == expected_status_counts
    assert full_payload["status_counts"] == _get_review_packet_snapshot_queue_summary(
        client,
        env["headers"],
    )["audit_readiness_rollup"]
    assert [item["latest_snapshot_id"] for item in full_payload["items"]] == [
        approved_exported["id"],
        approved_not_exported["id"],
        rejected_latest["id"],
        review_ready_assigned["id"],
        review_ready_unassigned["id"],
        approved_with_override["id"],
        blocked_latest["id"],
    ]
    assert [item["completion_status"] for item in full_payload["items"]] == [
        "audit_ready",
        "approved_not_exported",
        "rejected",
        "review_ready",
        "review_ready",
        "approved_not_exported",
        "incomplete",
    ]

    def expected_csv_row(item: dict[str, Any]) -> dict[str, str]:
        audit_bundle = item["audit_bundle"]
        next_step = item["next_step"]
        return {
            "patient_id": item["patient_id"],
            "latest_snapshot_id": item["latest_snapshot_id"],
            "latest_snapshot_created_at": item["latest_snapshot_created_at"],
            "review_status": item["review_status"],
            "review_state": item["review_state"],
            "completion_status": item["completion_status"],
            "assigned_reviewer_user_id": item["assigned_reviewer_user_id"] or "",
            "next_step_action": next_step["action"],
            "next_step_priority": next_step["priority"],
            "next_step_reason": next_step["reason"],
            "audit_bundle_available": str(audit_bundle["available"]),
            "audit_bundle_exported": str(audit_bundle["exported"]),
            "audit_bundle_last_exported_at": audit_bundle["last_exported_at"] or "",
            "audit_bundle_export_formats": "|".join(audit_bundle["export_formats"]),
        }

    csv_response = _get_review_packet_audit_readiness_csv(client, env["headers"])
    assert csv_response.headers["content-type"].startswith("text/csv; charset=utf-8")
    assert csv_response.headers["content-disposition"] == (
        'attachment; filename="access-review-packet-audit-readiness.csv"'
    )
    csv_rows = list(csv.DictReader(StringIO(csv_response.text)))
    assert list(csv_rows[0].keys()) == [
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
    assert csv_rows == [expected_csv_row(item) for item in full_payload["items"]]
    assert [row["latest_snapshot_id"] for row in csv_rows] == [
        item["latest_snapshot_id"] for item in full_payload["items"]
    ]
    assert [row["completion_status"] for row in csv_rows] == [
        item["completion_status"] for item in full_payload["items"]
    ]
    exported_csv_row = next(
        row for row in csv_rows if row["latest_snapshot_id"] == approved_exported["id"]
    )
    assert exported_csv_row["audit_bundle_exported"] == "True"
    assert exported_csv_row["audit_bundle_export_formats"] == "json|markdown|pdf"
    approved_exported_item = next(
        item for item in full_payload["items"] if item["latest_snapshot_id"] == approved_exported["id"]
    )
    assert approved_exported_item["review_state"] == "approved"
    assert approved_exported_item["audit_bundle"]["exported"] is True
    assert approved_exported_item["audit_bundle"]["export_formats"] == ["json", "markdown", "pdf"]
    assert approved_exported_item["next_step"] == _get_review_packet_patient_audit_status(
        client,
        env["headers"],
        patient_four_id,
    )["next_step"]
    assert approved_exported_item["completion_status"] == _get_review_packet_patient_audit_status(
        client,
        env["headers"],
        patient_four_id,
    )["completion_summary"]["status"]

    override_item = next(
        item
        for item in full_payload["items"]
        if item["latest_snapshot_id"] == approved_with_override["id"]
    )
    assert override_item["review_state"] == "approved_with_override"
    assert override_item["completion_status"] == "approved_not_exported"
    assert override_item["audit_bundle"]["exported"] is False

    blocked_item = next(
        item for item in full_payload["items"] if item["latest_snapshot_id"] == blocked_latest["id"]
    )
    assert blocked_item["completion_status"] == "incomplete"
    assert blocked_item["next_step"] == _get_review_packet_patient_audit_status(
        client,
        env["headers"],
        env["patient_id"],
    )["next_step"]
    assert historical_old["id"] not in [item["latest_snapshot_id"] for item in full_payload["items"]]
    assert events_after == events_before

    incomplete_payload = _get_review_packet_audit_readiness(
        client,
        env["headers"],
        "status=incomplete",
    )
    assert incomplete_payload["status_counts"] == expected_status_counts
    assert incomplete_payload["total_count"] == 1
    assert [
        item["latest_snapshot_id"]
        for item in incomplete_payload["items"]
    ] == [blocked_latest["id"]]
    review_ready_payload = _get_review_packet_audit_readiness(
        client,
        env["headers"],
        "status=review_ready",
    )
    assert review_ready_payload["status_counts"] == expected_status_counts
    assert review_ready_payload["total_count"] == 2
    assert {
        item["latest_snapshot_id"]
        for item in review_ready_payload["items"]
    } == {review_ready_assigned["id"], review_ready_unassigned["id"]}
    approved_not_exported_payload = _get_review_packet_audit_readiness(
        client,
        env["headers"],
        "status=approved_not_exported",
    )
    assert approved_not_exported_payload["status_counts"] == expected_status_counts
    assert approved_not_exported_payload["total_count"] == 2
    assert {
        item["latest_snapshot_id"]
        for item in approved_not_exported_payload["items"]
    } == {approved_not_exported["id"], approved_with_override["id"]}
    audit_ready_payload = _get_review_packet_audit_readiness(
        client,
        env["headers"],
        "status=audit_ready",
    )
    assert audit_ready_payload["status_counts"] == expected_status_counts
    assert audit_ready_payload["total_count"] == 1
    assert [
        item["latest_snapshot_id"]
        for item in audit_ready_payload["items"]
    ] == [approved_exported["id"]]
    audit_ready_csv = _get_review_packet_audit_readiness_csv(
        client,
        env["headers"],
        "status=audit_ready",
    )
    assert audit_ready_csv.headers["content-disposition"] == (
        'attachment; filename="access-review-packet-audit-readiness-audit_ready.csv"'
    )
    audit_ready_csv_rows = list(csv.DictReader(StringIO(audit_ready_csv.text)))
    assert audit_ready_csv_rows == [expected_csv_row(item) for item in audit_ready_payload["items"]]
    assert [row["latest_snapshot_id"] for row in audit_ready_csv_rows] == [approved_exported["id"]]
    assert [row["completion_status"] for row in audit_ready_csv_rows] == ["audit_ready"]
    rejected_payload = _get_review_packet_audit_readiness(
        client,
        env["headers"],
        "status=rejected",
    )
    assert rejected_payload["status_counts"] == expected_status_counts
    assert rejected_payload["total_count"] == 1
    assert [
        item["latest_snapshot_id"]
        for item in rejected_payload["items"]
    ] == [rejected_latest["id"]]

    paged = _get_review_packet_audit_readiness(client, env["headers"], "limit=2&offset=1")
    assert paged["total_count"] == 7
    assert paged["limit"] == 2
    assert paged["offset"] == 1
    assert paged["status_counts"] == expected_status_counts
    assert [item["latest_snapshot_id"] for item in paged["items"]] == [
        approved_not_exported["id"],
        rejected_latest["id"],
    ]
    assert len(csv_rows) == full_payload["total_count"]
    assert [row["latest_snapshot_id"] for row in csv_rows] == [
        item["latest_snapshot_id"] for item in full_payload["items"]
    ]
    assert [row["latest_snapshot_id"] for row in csv_rows] != [
        item["latest_snapshot_id"] for item in paged["items"]
    ]

    events_after_csv = _get_review_packet_snapshot_events(client, env["headers"], approved_exported["id"])
    detail_after_csv = _get_review_packet_snapshot_detail(client, env["headers"], approved_exported["id"])
    assert events_after_csv == events_before
    assert detail_after_csv["packet_json"] == approved_exported["packet_json"]
    assert detail_after_csv["packet_markdown"] == approved_exported["packet_markdown"]

    other_payload = _get_review_packet_audit_readiness(client, other_org["headers"])
    assert other_payload["total_count"] == 1
    assert other_payload["status_counts"] == {
        "incomplete_count": 1,
        "review_ready_count": 0,
        "approved_not_exported_count": 0,
        "audit_ready_count": 0,
        "rejected_count": 0,
    }
    assert len(other_payload["items"]) == 1
    assert other_payload["items"][0]["patient_id"] == other_org["patient_id"]
    other_csv_rows = list(
        csv.DictReader(StringIO(_get_review_packet_audit_readiness_csv(client, other_org["headers"]).text))
    )
    assert len(other_csv_rows) == 1
    assert other_csv_rows[0]["patient_id"] == other_org["patient_id"]


def test_access_review_packet_snapshot_detail_returns_immutable_stored_packet(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-snapshot-detail")
    base = datetime.now(timezone.utc).replace(microsecond=0)

    escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    task_id = _create_task(client, env["headers"], escalation_id)
    outcome = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        intervention_task_id=task_id,
        metric_name="systolic_bp",
        value_numeric=118,
        observed_at=base + timedelta(days=1),
    )
    care_update = _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="Immutable snapshot note",
        occurred_at=base + timedelta(days=2),
        escalation_id=escalation_id,
        intervention_task_id=task_id,
        outcome_id=outcome["id"],
    )
    resolve_resp = client.post(
        f"/api/v1/escalations/{escalation_id}/resolve",
        json={
            "resolution_reason": "clinically_stable",
            "resolution_notes": "Immutable snapshot created.",
            "outcome_id": outcome["id"],
            "care_update_id": care_update["id"],
            "resolved_at": (base + timedelta(days=3)).isoformat(),
        },
        headers=env["headers"],
    )
    assert resolve_resp.status_code == 200
    complete_resp = client.post(
        f"/api/v1/tasks/{task_id}/complete",
        json={"completion_note": "Snapshot detail task complete."},
        headers=env["headers"],
    )
    assert complete_resp.status_code == 200

    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    post_snapshot_escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    _create_task(client, env["headers"], post_snapshot_escalation_id)

    detail = _get_review_packet_snapshot_detail(client, env["headers"], snapshot["id"])
    snapshot_markdown = _get_review_packet_snapshot_markdown(client, env["headers"], snapshot["id"])
    current_packet = _get_review_packet(client, env["headers"], env["patient_id"])
    current_markdown = _get_review_packet_markdown(client, env["headers"], env["patient_id"])

    assert detail["id"] == snapshot["id"]
    assert detail["packet_json"] == snapshot["packet_json"]
    assert detail["packet_markdown"] == snapshot["packet_markdown"]
    assert detail["audit_timeline"] is not None
    assert _timeline_event_types(detail) == ["snapshot_created"]
    events = _get_review_packet_snapshot_events(client, env["headers"], snapshot["id"])
    created_reasons = _readiness_reasons_by_code(events["events"][0]["metadata"])
    assert created_reasons["signal_present"]["severity"] == "satisfied"
    assert created_reasons["outcome_present"]["severity"] == "satisfied"
    assert created_reasons["evidence_present"]["severity"] == "satisfied"
    assert created_reasons["snapshot_present"]["severity"] == "satisfied"
    assert created_reasons["audit_bundle_exported"]["severity"] == "missing"
    assert detail["packet_json"]["review_readiness"]["readiness_status"] == "ready_for_review"
    assert detail["packet_json"]["case_summary"]["escalation_summary"]["open_count"] == 0
    assert "Review Readiness: ready_for_review" in detail["packet_markdown"]
    assert "Immutable snapshot note" in detail["packet_markdown"]
    assert snapshot_markdown == snapshot["packet_markdown"]
    assert snapshot_markdown == detail["packet_markdown"]
    assert current_packet["review_readiness"]["readiness_status"] == "active_open_work"
    assert current_packet["case_summary"]["escalation_summary"]["open_count"] == 1
    assert current_packet["generated_at"] != detail["generated_at"]
    assert "Review Readiness: active_open_work" in current_markdown
    assert current_markdown != snapshot_markdown


def test_access_review_packet_snapshot_detail_respects_tenant_scope(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-snapshot-detail-scope")
    other = _bootstrap_patient_env(
        client,
        db_session,
        slug="review-packet-snapshot-detail-scope-other",
    )
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    forbidden = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot['id']}",
        headers=other["headers"],
    )
    assert forbidden.status_code == 403
    own_detail = _get_review_packet_snapshot_detail(client, env["headers"], snapshot["id"])
    assert own_detail["audit_timeline"] is not None

    markdown_forbidden = client.get(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot['id']}/markdown",
        headers=other["headers"],
    )
    assert markdown_forbidden.status_code == 403

    missing = client.get(
        "/api/v1/reports/access-review-packet/snapshots/00000000-0000-0000-0000-000000000000",
        headers=env["headers"],
    )
    assert missing.status_code == 404

    missing_markdown = client.get(
        "/api/v1/reports/access-review-packet/snapshots/00000000-0000-0000-0000-000000000000/markdown",
        headers=env["headers"],
    )
    assert missing_markdown.status_code == 404


def test_access_review_packet_snapshot_review_respects_tenant_scope_and_missing_snapshot(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="review-packet-snapshot-review-scope")
    other = _bootstrap_patient_env(
        client,
        db_session,
        slug="review-packet-snapshot-review-scope-other",
    )
    snapshot = _create_review_packet_snapshot(client, env["headers"], env["patient_id"])

    forbidden = client.patch(
        f"/api/v1/reports/access-review-packet/snapshots/{snapshot['id']}/review",
        json={"review_status": "approved"},
        headers=other["headers"],
    )
    assert forbidden.status_code == 403

    missing = client.patch(
        "/api/v1/reports/access-review-packet/snapshots/00000000-0000-0000-0000-000000000000/review",
        json={"review_status": "approved"},
        headers=env["headers"],
    )
    assert missing.status_code == 404
