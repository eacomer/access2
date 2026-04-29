from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.intervention_task import InterventionTask
from tests.test_care_updates import _bootstrap_patient_env, _create_escalation, _create_task
from tests.test_outcomes import _create_outcome


def _create_care_update(
    client: TestClient,
    headers: dict[str, str],
    patient_id: str,
    *,
    summary: str,
    occurred_at: datetime | None = None,
    escalation_id: str | None = None,
    intervention_task_id: str | None = None,
    outcome_id: str | None = None,
) -> dict:
    payload: dict[str, object] = {
        "patient_id": patient_id,
        "summary": summary,
        "care_update_type": "follow_up",
        "occurred_at": (occurred_at or datetime.now(timezone.utc)).isoformat(),
    }
    if escalation_id is not None:
        payload["escalation_id"] = escalation_id
    if intervention_task_id is not None:
        payload["intervention_task_id"] = intervention_task_id
    if outcome_id is not None:
        payload["outcome_id"] = outcome_id
    resp = client.post("/api/v1/care-updates", json=payload, headers=headers)
    assert resp.status_code == 201
    return resp.json()


def _iso_naive_utc(value: datetime) -> str:
    return value.replace(tzinfo=None).isoformat()


def test_access_case_summary_rolls_up_patient_story_deterministically(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="case-summary")
    base = datetime.now(timezone.utc)

    first_escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    first_task_id = _create_task(client, env["headers"], first_escalation_id)
    baseline = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        metric_name="systolic_bp",
        value_numeric=150,
        observed_at=base,
    )
    latest = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        intervention_task_id=first_task_id,
        metric_name="systolic_bp",
        value_numeric=128,
        observed_at=base + timedelta(days=2),
    )
    older_update = _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="Earlier follow-up",
        occurred_at=base + timedelta(days=1),
        escalation_id=first_escalation_id,
        intervention_task_id=first_task_id,
    )
    latest_update = _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="Most recent care update",
        occurred_at=base + timedelta(days=3),
        escalation_id=first_escalation_id,
        intervention_task_id=first_task_id,
        outcome_id=latest["id"],
    )
    resolve_resp = client.post(
        f"/api/v1/escalations/{first_escalation_id}/resolve",
        json={
            "resolution_reason": "issue_addressed",
            "resolution_notes": "BP improved after intervention.",
            "outcome_id": latest["id"],
            "care_update_id": latest_update["id"],
        },
        headers=env["headers"],
    )
    assert resolve_resp.status_code == 200

    second_escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    second_task_id = _create_task(client, env["headers"], second_escalation_id)
    first_task = db_session.get(InterventionTask, uuid.UUID(first_task_id))
    second_task = db_session.get(InterventionTask, uuid.UUID(second_task_id))
    assert first_task is not None
    assert second_task is not None
    first_task.created_at = base + timedelta(hours=1)
    second_task.created_at = base + timedelta(hours=2)
    db_session.commit()

    summary_resp = client.get(
        f"/api/v1/reports/access-case-summary/{env['patient_id']}",
        headers=env["headers"],
    )
    assert summary_resp.status_code == 200
    payload = summary_resp.json()

    escalation_summary = payload["escalation_summary"]
    assert escalation_summary["open_count"] == 1
    assert escalation_summary["resolved_count"] == 1
    assert escalation_summary["latest_escalation_id"] == second_escalation_id
    assert escalation_summary["latest_status"] == "open"
    assert escalation_summary["latest_resolution"] == {
        "escalation_id": first_escalation_id,
        "resolved_at": payload["escalation_summary"]["latest_resolution"]["resolved_at"],
        "resolution_reason": "issue_addressed",
        "resolution_notes": "BP improved after intervention.",
        "outcome_id": latest["id"],
        "care_update_id": latest_update["id"],
    }

    interventions = payload["interventions"]
    assert [item["intervention_task_id"] for item in interventions] == [second_task_id, first_task_id]
    assert interventions[1]["linked_outcome_ids"] == [latest["id"]]

    outcome_summary = payload["outcome_summaries"][0]
    assert outcome_summary["baseline_outcome_id"] == baseline["id"]
    assert outcome_summary["latest_outcome_id"] == latest["id"]
    assert outcome_summary["delta"] == -22
    assert outcome_summary["status"] == "improved"

    latest_care_update = payload["latest_care_update"]
    assert latest_care_update["care_update_id"] == latest_update["id"]
    assert latest_care_update["summary"] == "Most recent care update"
    assert latest_care_update["outcome_id"] == latest["id"]

    completeness = payload["evidence_completeness"]
    assert completeness["has_outcome"] is True
    assert completeness["has_care_update"] is True
    assert completeness["has_resolution_evidence"] is True
    assert completeness["missing_components"] == []


def test_access_case_summary_flags_missing_evidence_components(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="case-summary-missing")
    _create_escalation(client, env["headers"], env["patient_id"])

    summary_resp = client.get(
        f"/api/v1/reports/access-case-summary/{env['patient_id']}",
        headers=env["headers"],
    )
    assert summary_resp.status_code == 200
    payload = summary_resp.json()

    completeness = payload["evidence_completeness"]
    assert completeness["has_outcome"] is False
    assert completeness["has_care_update"] is False
    assert completeness["has_resolution_evidence"] is False
    assert payload["review_readiness"] == {
        "has_measured_outcome": False,
        "has_care_update": False,
        "has_resolution_evidence": False,
        "has_open_work": True,
        "latest_outcome_at": None,
        "latest_care_update_at": None,
        "latest_resolution_at": None,
        "readiness_status": "active_open_work",
    }
    assert completeness["missing_components"] == [
        "outcome",
        "care_update",
        "resolution_evidence",
    ]


def test_access_case_summary_review_readiness_is_incomplete_without_closure_evidence(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="case-summary-incomplete")
    base = datetime.now(timezone.utc).replace(microsecond=0)

    outcome = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        metric_name="systolic_bp",
        value_numeric=132,
        observed_at=base,
    )
    care_update = _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="Monitoring note without escalation closure",
        occurred_at=base + timedelta(hours=1),
        outcome_id=outcome["id"],
    )

    summary_resp = client.get(
        f"/api/v1/reports/access-case-summary/{env['patient_id']}",
        headers=env["headers"],
    )
    assert summary_resp.status_code == 200
    readiness = summary_resp.json()["review_readiness"]

    assert readiness == {
        "has_measured_outcome": True,
        "has_care_update": True,
        "has_resolution_evidence": False,
        "has_open_work": False,
        "latest_outcome_at": _iso_naive_utc(base),
        "latest_care_update_at": _iso_naive_utc(base + timedelta(hours=1)),
        "latest_resolution_at": None,
        "readiness_status": "incomplete",
    }


def test_access_case_summary_respects_tenant_scope(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="case-summary-scope")
    other = _bootstrap_patient_env(client, db_session, slug="case-summary-scope-other")

    _create_escalation(client, env["headers"], env["patient_id"])

    resp = client.get(
        f"/api/v1/reports/access-case-summary/{env['patient_id']}",
        headers=other["headers"],
    )
    assert resp.status_code == 403


def test_access_case_summary_surfaces_latest_resolved_escalation_evidence(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="case-summary-resolved")
    base = datetime.now(timezone.utc).replace(microsecond=0)

    escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    task_id = _create_task(client, env["headers"], escalation_id)
    outcome = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        intervention_task_id=task_id,
        metric_name="systolic_bp",
        value_numeric=126,
        observed_at=base + timedelta(days=1),
    )
    care_update = _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="Resolved escalation with documented follow-up",
        occurred_at=base + timedelta(days=2),
        escalation_id=escalation_id,
        intervention_task_id=task_id,
        outcome_id=outcome["id"],
    )
    resolved_at = base + timedelta(days=3)

    resolve_resp = client.post(
        f"/api/v1/escalations/{escalation_id}/resolve",
        json={
            "resolution_reason": "clinically_stable",
            "resolution_notes": "Escalation closed after improvement and follow-up.",
            "outcome_id": outcome["id"],
            "care_update_id": care_update["id"],
            "resolved_at": resolved_at.isoformat(),
        },
        headers=env["headers"],
    )
    assert resolve_resp.status_code == 200
    complete_resp = client.post(
        f"/api/v1/tasks/{task_id}/complete",
        json={"completion_note": "Closed after documented follow-up."},
        headers=env["headers"],
    )
    assert complete_resp.status_code == 200

    summary_resp = client.get(
        f"/api/v1/reports/access-case-summary/{env['patient_id']}",
        headers=env["headers"],
    )
    assert summary_resp.status_code == 200
    payload = summary_resp.json()

    escalation_summary = payload["escalation_summary"]
    assert escalation_summary["open_count"] == 0
    assert escalation_summary["resolved_count"] == 1
    assert escalation_summary["latest_escalation_id"] == escalation_id
    assert escalation_summary["latest_status"] == "resolved"
    assert escalation_summary["latest_resolution"] == {
        "escalation_id": escalation_id,
        "resolved_at": _iso_naive_utc(resolved_at),
        "resolution_reason": "clinically_stable",
        "resolution_notes": "Escalation closed after improvement and follow-up.",
        "outcome_id": outcome["id"],
        "care_update_id": care_update["id"],
    }

    interventions = payload["interventions"]
    assert len(interventions) == 1
    assert interventions[0]["intervention_task_id"] == task_id
    assert interventions[0]["linked_outcome_ids"] == [outcome["id"]]

    latest_care_update = payload["latest_care_update"]
    assert latest_care_update["care_update_id"] == care_update["id"]
    assert latest_care_update["escalation_id"] == escalation_id
    assert latest_care_update["outcome_id"] == outcome["id"]

    completeness = payload["evidence_completeness"]
    assert completeness == {
        "has_outcome": True,
        "has_care_update": True,
        "has_resolution_evidence": True,
        "missing_components": [],
    }
    assert payload["review_readiness"] == {
        "has_measured_outcome": True,
        "has_care_update": True,
        "has_resolution_evidence": True,
        "has_open_work": False,
        "latest_outcome_at": _iso_naive_utc(base + timedelta(days=1)),
        "latest_care_update_at": _iso_naive_utc(base + timedelta(days=2)),
        "latest_resolution_at": _iso_naive_utc(resolved_at),
        "readiness_status": "ready_for_review",
    }


def test_mixed_history_review_state_is_consistent_across_case_summary_evidence_and_timeline(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="case-summary-mixed-review")
    base = datetime.now(timezone.utc).replace(microsecond=0)

    resolved_escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    resolved_task_id = _create_task(client, env["headers"], resolved_escalation_id)
    baseline = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        metric_name="systolic_bp",
        value_numeric=150,
        observed_at=base,
    )
    latest_outcome = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        intervention_task_id=resolved_task_id,
        metric_name="systolic_bp",
        value_numeric=126,
        observed_at=base + timedelta(days=1),
    )
    latest_care_update = _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="Resolved escalation follow-up completed",
        occurred_at=base + timedelta(days=2),
        escalation_id=resolved_escalation_id,
        intervention_task_id=resolved_task_id,
        outcome_id=latest_outcome["id"],
    )
    resolved_at = base + timedelta(days=3)
    resolved_resp = client.post(
        f"/api/v1/escalations/{resolved_escalation_id}/resolve",
        json={
            "resolution_reason": "clinically_stable",
            "resolution_notes": "Closed after documented improvement and follow-up.",
            "outcome_id": latest_outcome["id"],
            "care_update_id": latest_care_update["id"],
            "resolved_at": resolved_at.isoformat(),
        },
        headers=env["headers"],
    )
    assert resolved_resp.status_code == 200

    open_escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    open_task_id = _create_task(client, env["headers"], open_escalation_id)
    open_task = db_session.get(InterventionTask, uuid.UUID(open_task_id))
    assert open_task is not None
    open_task.created_at = base + timedelta(days=4)
    db_session.commit()

    case_summary = client.get(
        f"/api/v1/reports/access-case-summary/{env['patient_id']}",
        headers=env["headers"],
    )
    evidence_report = client.get(
        f"/api/v1/reports/access-evidence/{env['patient_id']}",
        headers=env["headers"],
    )
    timeline = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    )
    assert case_summary.status_code == 200
    assert evidence_report.status_code == 200
    assert timeline.status_code == 200

    case_payload = case_summary.json()
    evidence_payload = evidence_report.json()
    timeline_payload = timeline.json()

    resolution_summary = case_payload["escalation_summary"]["latest_resolution"]
    assert case_payload["escalation_summary"]["open_count"] == 1
    assert case_payload["escalation_summary"]["resolved_count"] == 1
    assert case_payload["escalation_summary"]["latest_escalation_id"] == open_escalation_id
    assert case_payload["escalation_summary"]["latest_status"] == "open"
    assert resolution_summary is not None
    assert resolution_summary["escalation_id"] == resolved_escalation_id
    assert resolution_summary["resolution_reason"] == "clinically_stable"
    assert resolution_summary["outcome_id"] == latest_outcome["id"]
    assert resolution_summary["care_update_id"] == latest_care_update["id"]

    assert case_payload["latest_care_update"]["care_update_id"] == latest_care_update["id"]
    assert case_payload["latest_care_update"]["outcome_id"] == latest_outcome["id"]
    assert case_payload["latest_care_update"]["escalation_id"] == resolved_escalation_id
    assert case_payload["outcome_summaries"][0]["baseline_outcome_id"] == baseline["id"]
    assert case_payload["outcome_summaries"][0]["latest_outcome_id"] == latest_outcome["id"]
    assert case_payload["evidence_completeness"] == {
        "has_outcome": True,
        "has_care_update": True,
        "has_resolution_evidence": True,
        "missing_components": [],
    }
    assert case_payload["review_readiness"] == {
        "has_measured_outcome": True,
        "has_care_update": True,
        "has_resolution_evidence": True,
        "has_open_work": True,
        "latest_outcome_at": _iso_naive_utc(base + timedelta(days=1)),
        "latest_care_update_at": _iso_naive_utc(base + timedelta(days=2)),
        "latest_resolution_at": _iso_naive_utc(resolved_at),
        "readiness_status": "active_open_work",
    }

    evidence_resolution = evidence_payload["escalation_resolution_summaries"][0]
    assert evidence_resolution == resolution_summary
    assert evidence_payload["outcome_summaries"][0]["latest_outcome_id"] == latest_outcome["id"]
    assert evidence_payload["review_readiness"] == case_payload["review_readiness"]

    resolved_event = next(
        item
        for item in timeline_payload["items"]
        if item["event_type"] == "escalation_status_changed"
        and item["status"] == "resolved"
        and item["related_escalation_id"] == resolved_escalation_id
    )
    care_update_event = next(
        item
        for item in timeline_payload["items"]
        if item["event_type"] == "care_update_logged"
        and item["source_id"] == latest_care_update["id"]
    )

    assert resolved_event["related_outcome_id"] == latest_outcome["id"]
    assert resolved_event["metadata"]["resolution_reason"] == resolution_summary["resolution_reason"]
    assert (
        resolved_event["metadata"]["resolution_care_update_id"]
        == resolution_summary["care_update_id"]
    )
    assert (
        resolved_event["metadata"]["resolution_outcome_id"]
        == resolution_summary["outcome_id"]
    )

    care_update_detail = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/{care_update_event['event_id']}",
        headers=env["headers"],
    )
    assert care_update_detail.status_code == 200
    care_update_detail_payload = care_update_detail.json()
    assert care_update_detail_payload["item"]["source_id"] == latest_care_update["id"]
    assert care_update_detail_payload["item"]["related_outcome_id"] == latest_outcome["id"]
    assert care_update_detail_payload["item"]["related_escalation_id"] == resolved_escalation_id

    latest_detail = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/{timeline_payload['items'][0]['event_id']}",
        headers=env["headers"],
    )
    assert latest_detail.status_code == 200
    latest_detail_payload = latest_detail.json()
    assert latest_detail_payload["workflow_status"]["has_active_work"] is True
    assert latest_detail_payload["workflow_status"]["primary_driver"] in {"escalation", "task"}
    assert latest_detail_payload["closure_readiness_label"] == "Not ready for closure"
    assert latest_detail_payload["review_readiness"] == case_payload["review_readiness"]


def test_mixed_history_review_state_views_remain_tenant_scoped(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="case-summary-mixed-scope")
    other = _bootstrap_patient_env(client, db_session, slug="case-summary-mixed-scope-other")

    escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    task_id = _create_task(client, env["headers"], escalation_id)
    outcome = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        intervention_task_id=task_id,
    )
    care_update = _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="Scoped mixed-history update",
        escalation_id=escalation_id,
        intervention_task_id=task_id,
        outcome_id=outcome["id"],
    )
    resolve_resp = client.post(
        f"/api/v1/escalations/{escalation_id}/resolve",
        json={
            "resolution_reason": "issue_addressed",
            "outcome_id": outcome["id"],
            "care_update_id": care_update["id"],
        },
        headers=env["headers"],
    )
    assert resolve_resp.status_code == 200

    denied_case_summary = client.get(
        f"/api/v1/reports/access-case-summary/{env['patient_id']}",
        headers=other["headers"],
    )
    denied_evidence = client.get(
        f"/api/v1/reports/access-evidence/{env['patient_id']}",
        headers=other["headers"],
    )
    denied_timeline = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=other["headers"],
    )

    assert denied_case_summary.status_code == 403
    assert denied_evidence.status_code == 403
    assert denied_timeline.status_code == 403
