from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.test_care_updates import _create_escalation, _create_outcome, _create_task
from tests.test_patients import (
    auth_headers,
    create_organization_record,
    create_patient_for_user,
    create_user_for_org,
)


def _bootstrap_env(client: TestClient, db_session: Session, *, slug: str) -> dict:
    organization = create_organization_record(db_session, slug=f"{slug}-org")
    user = create_user_for_org(
        db_session,
        organization=organization,
        email=f"{slug}@example.com",
        password="Secret123!",
    )
    headers = auth_headers(client, user.email, "Secret123!")
    patient_id = create_patient_for_user(client, headers, first_name=f"{slug}-patient")
    return {"headers": headers, "patient_id": patient_id}


def _create_care_update(
    client: TestClient,
    headers: dict[str, str],
    patient_id: str,
    *,
    escalation_id: str | None = None,
    outcome_id: str | None = None,
) -> dict:
    payload: dict[str, object] = {
        "patient_id": patient_id,
        "summary": "Closure check",
        "care_update_type": "follow_up",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
    if escalation_id is not None:
        payload["escalation_id"] = escalation_id
    if outcome_id is not None:
        payload["outcome_id"] = outcome_id
    resp = client.post("/api/v1/care-updates", json=payload, headers=headers)
    assert resp.status_code == 201
    return resp.json()


def _iso_naive_utc(value: datetime) -> str:
    return value.replace(tzinfo=None).isoformat()


def test_resolve_escalation_records_structured_closure_evidence(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_env(client, db_session, slug="escalation-resolution")
    escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    task_id = _create_task(client, env["headers"], escalation_id)
    outcome = _create_outcome(client, env["headers"], env["patient_id"], task_id)
    care_update = _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        escalation_id=escalation_id,
        outcome_id=outcome["id"],
    )

    resp = client.post(
        f"/api/v1/escalations/{escalation_id}/resolve",
        json={
            "resolution_reason": "issue_addressed",
            "resolution_notes": "Symptoms stabilized after outreach.",
            "outcome_id": outcome["id"],
            "care_update_id": care_update["id"],
        },
        headers=env["headers"],
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "resolved"
    assert payload["resolution_reason"] == "issue_addressed"
    assert payload["resolution_notes"] == "Symptoms stabilized after outreach."
    assert payload["resolution_outcome_id"] == outcome["id"]
    assert payload["resolution_care_update_id"] == care_update["id"]
    assert payload["resolved_at"] is not None


def test_resolve_escalation_rejects_cross_patient_outcome(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_env(client, db_session, slug="escalation-cross-outcome")
    escalation_id = _create_escalation(client, env["headers"], env["patient_id"])

    other_patient_id = create_patient_for_user(client, env["headers"], first_name="other-outcome")
    other_escalation_id = _create_escalation(client, env["headers"], other_patient_id)
    other_task_id = _create_task(client, env["headers"], other_escalation_id)
    other_outcome = _create_outcome(client, env["headers"], other_patient_id, other_task_id)

    resp = client.post(
        f"/api/v1/escalations/{escalation_id}/resolve",
        json={"resolution_reason": "other", "outcome_id": other_outcome["id"]},
        headers=env["headers"],
    )

    assert resp.status_code == 422


def test_resolve_escalation_rejects_care_update_for_different_escalation(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_env(client, db_session, slug="escalation-cross-update")
    escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    other_escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    care_update = _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        escalation_id=other_escalation_id,
    )

    resp = client.post(
        f"/api/v1/escalations/{escalation_id}/resolve",
        json={"resolution_reason": "duplicate", "care_update_id": care_update["id"]},
        headers=env["headers"],
    )

    assert resp.status_code == 422


def test_access_evidence_includes_escalation_resolution_summary(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_env(client, db_session, slug="escalation-evidence")
    escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    task_id = _create_task(client, env["headers"], escalation_id)
    outcome = _create_outcome(client, env["headers"], env["patient_id"], task_id)
    care_update = _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        escalation_id=escalation_id,
        outcome_id=outcome["id"],
    )

    resolve_resp = client.post(
        f"/api/v1/escalations/{escalation_id}/resolve",
        json={
            "resolution_reason": "clinically_stable",
            "resolution_notes": "Vitals improved.",
            "outcome_id": outcome["id"],
            "care_update_id": care_update["id"],
        },
        headers=env["headers"],
    )
    assert resolve_resp.status_code == 200
    complete_resp = client.post(
        f"/api/v1/tasks/{task_id}/complete",
        json={"completion_note": "Closed after review."},
        headers=env["headers"],
    )
    assert complete_resp.status_code == 200

    report = client.get(
        f"/api/v1/reports/access-evidence/{env['patient_id']}",
        headers=env["headers"],
    )
    assert report.status_code == 200
    payload = report.json()
    assert payload["escalation_resolution_summaries"]
    summary = payload["escalation_resolution_summaries"][0]
    assert summary["escalation_id"] == escalation_id
    assert summary["resolution_reason"] == "clinically_stable"
    assert summary["resolution_notes"] == "Vitals improved."
    assert summary["outcome_id"] == outcome["id"]
    assert summary["care_update_id"] == care_update["id"]
    assert payload["review_readiness"] == {
        "has_measured_outcome": True,
        "has_care_update": True,
        "has_resolution_evidence": True,
        "has_open_work": False,
        "latest_outcome_at": payload["review_readiness"]["latest_outcome_at"],
        "latest_care_update_at": payload["review_readiness"]["latest_care_update_at"],
        "latest_resolution_at": payload["review_readiness"]["latest_resolution_at"],
        "readiness_status": "ready_for_review",
    }


def test_access_evidence_orders_resolved_escalations_by_resolved_at_desc(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_env(client, db_session, slug="escalation-evidence-ordered")
    base = datetime.now(timezone.utc).replace(microsecond=0)

    first_escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    first_task_id = _create_task(client, env["headers"], first_escalation_id)
    first_outcome = _create_outcome(client, env["headers"], env["patient_id"], first_task_id)
    first_update = _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        escalation_id=first_escalation_id,
        outcome_id=first_outcome["id"],
    )
    first_resolved_at = base + timedelta(hours=1)
    first_resolve = client.post(
        f"/api/v1/escalations/{first_escalation_id}/resolve",
        json={
            "resolution_reason": "issue_addressed",
            "resolution_notes": "First escalation resolved.",
            "outcome_id": first_outcome["id"],
            "care_update_id": first_update["id"],
            "resolved_at": first_resolved_at.isoformat(),
        },
        headers=env["headers"],
    )
    assert first_resolve.status_code == 200

    second_escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    second_task_id = _create_task(client, env["headers"], second_escalation_id)
    second_outcome = _create_outcome(client, env["headers"], env["patient_id"], second_task_id)
    second_update = _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        escalation_id=second_escalation_id,
        outcome_id=second_outcome["id"],
    )
    second_resolved_at = base + timedelta(hours=2)
    second_resolve = client.post(
        f"/api/v1/escalations/{second_escalation_id}/resolve",
        json={
            "resolution_reason": "clinically_stable",
            "resolution_notes": "Second escalation resolved.",
            "outcome_id": second_outcome["id"],
            "care_update_id": second_update["id"],
            "resolved_at": second_resolved_at.isoformat(),
        },
        headers=env["headers"],
    )
    assert second_resolve.status_code == 200

    report = client.get(
        f"/api/v1/reports/access-evidence/{env['patient_id']}",
        headers=env["headers"],
    )
    assert report.status_code == 200
    summaries = report.json()["escalation_resolution_summaries"]

    assert [item["escalation_id"] for item in summaries] == [
        second_escalation_id,
        first_escalation_id,
    ]
    assert summaries[0]["resolved_at"] == _iso_naive_utc(second_resolved_at)
    assert summaries[0]["outcome_id"] == second_outcome["id"]
    assert summaries[0]["care_update_id"] == second_update["id"]
    assert summaries[1]["resolved_at"] == _iso_naive_utc(first_resolved_at)
    assert summaries[1]["outcome_id"] == first_outcome["id"]
    assert summaries[1]["care_update_id"] == first_update["id"]


def test_access_evidence_review_readiness_is_incomplete_without_case_evidence(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_env(client, db_session, slug="escalation-evidence-incomplete")
    _create_escalation(client, env["headers"], env["patient_id"])

    report = client.get(
        f"/api/v1/reports/access-evidence/{env['patient_id']}",
        headers=env["headers"],
    )
    assert report.status_code == 200
    readiness = report.json()["review_readiness"]

    assert readiness == {
        "has_measured_outcome": False,
        "has_care_update": False,
        "has_resolution_evidence": False,
        "has_open_work": True,
        "latest_outcome_at": None,
        "latest_care_update_at": None,
        "latest_resolution_at": None,
        "readiness_status": "active_open_work",
    }
