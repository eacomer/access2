from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.test_patients import (
    auth_headers,
    create_organization_record,
    create_patient_for_user,
    create_user_for_org,
)


def _bootstrap_patient_env(
    client: TestClient,
    db_session: Session,
    *,
    slug: str,
) -> dict:
    organization = create_organization_record(db_session, slug=f"{slug}-org")
    user = create_user_for_org(
        db_session,
        organization=organization,
        email=f"{slug}@example.com",
        password="Secret123!",
    )
    headers = auth_headers(client, user.email, "Secret123!")
    patient_id = create_patient_for_user(client, headers, first_name=f"{slug}-patient")
    return {
        "organization": organization,
        "user": user,
        "headers": headers,
        "patient_id": patient_id,
    }


def _create_escalation(
    client: TestClient,
    headers: dict[str, str],
    patient_id: str,
) -> str:
    resp = client.post(
        f"/api/v1/patients/{patient_id}/signals",
        json={
            "signal_type": "symptom_score",
            "signal_value_numeric": 9.5,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["escalation"] is not None
    return payload["escalation"]["id"]


def _create_task(
    client: TestClient,
    headers: dict[str, str],
    escalation_id: str,
) -> str:
    resp = client.post(
        f"/api/v1/escalations/{escalation_id}/tasks",
        json={
            "title": "Follow up",
            "description": "Check status",
            "priority": "medium",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_outcome(
    client: TestClient,
    headers: dict[str, str],
    patient_id: str,
    task_id: str,
) -> dict:
    resp = client.post(
        "/api/v1/outcomes",
        json={
            "patient_id": patient_id,
            "intervention_task_id": task_id,
            "type": "bp",
            "metric_name": "systolic_bp",
            "value_numeric": 128,
            "unit": "mmHg",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "source": "care_team",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def test_create_care_update_for_patient(client: TestClient, db_session: Session) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="care-basic")

    resp = client.post(
        "/api/v1/care-updates",
        json={
            "patient_id": env["patient_id"],
            "summary": "Spoke with patient",
            "details": "Confirmed medication plan",
            "care_update_type": "outreach",
        },
        headers=env["headers"],
    )
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["patient_id"] == env["patient_id"]
    assert payload["care_update_type"] == "outreach"
    assert payload["occurred_at"] is not None


def test_create_care_update_with_escalation(client: TestClient, db_session: Session) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="care-escalation")
    escalation_id = _create_escalation(client, env["headers"], env["patient_id"])

    resp = client.post(
        "/api/v1/care-updates",
        json={
            "patient_id": env["patient_id"],
            "summary": "Escalation reviewed",
            "care_update_type": "coordination",
            "escalation_id": escalation_id,
        },
        headers=env["headers"],
    )
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["escalation_id"] == escalation_id


def test_create_care_update_with_task(client: TestClient, db_session: Session) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="care-task")
    escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    task_id = _create_task(client, env["headers"], escalation_id)

    resp = client.post(
        "/api/v1/care-updates",
        json={
            "patient_id": env["patient_id"],
            "summary": "Task progress noted",
            "care_update_type": "follow_up",
            "intervention_task_id": task_id,
        },
        headers=env["headers"],
    )
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["intervention_task_id"] == task_id
    assert payload["escalation_id"] == escalation_id


def test_create_care_update_with_task_outcome(client: TestClient, db_session: Session) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="care-outcome")
    escalation_id = _create_escalation(client, env["headers"], env["patient_id"])
    task_id = _create_task(client, env["headers"], escalation_id)
    outcome = _create_outcome(client, env["headers"], env["patient_id"], task_id)

    resp = client.post(
        "/api/v1/care-updates",
        json={
            "patient_id": env["patient_id"],
            "summary": "Documented outcome follow-up",
            "care_update_type": "adherence",
            "outcome_id": outcome["id"],
        },
        headers=env["headers"],
    )
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["outcome_id"] == outcome["id"]
    assert payload["intervention_task_id"] == outcome["intervention_task_id"]
    assert payload["escalation_id"] == escalation_id


def test_care_update_creation_blocked_cross_tenant(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="care-tenant")

    other_org = create_organization_record(db_session, slug="care-tenant-other")
    other_user = create_user_for_org(
        db_session,
        organization=other_org,
        email="other-care@example.com",
        password="Secret123!",
    )
    other_headers = auth_headers(client, other_user.email, "Secret123!")

    resp = client.post(
        "/api/v1/care-updates",
        json={
            "patient_id": env["patient_id"],
            "summary": "Unauthorized attempt",
            "care_update_type": "other",
        },
        headers=other_headers,
    )
    assert resp.status_code == 403


def test_care_update_rejects_cross_patient_references(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="care-cross")
    other_patient = create_patient_for_user(client, env["headers"], first_name="care-cross-two")
    other_escalation = _create_escalation(client, env["headers"], other_patient)

    resp = client.post(
        "/api/v1/care-updates",
        json={
            "patient_id": env["patient_id"],
            "summary": "Invalid linkage",
            "care_update_type": "coordination",
            "escalation_id": other_escalation,
        },
        headers=env["headers"],
    )
    assert resp.status_code == 422


def test_care_update_rejects_mismatched_task_outcome(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="care-mismatch")
    escalation_one = _create_escalation(client, env["headers"], env["patient_id"])
    task_one = _create_task(client, env["headers"], escalation_one)
    _create_outcome(client, env["headers"], env["patient_id"], task_one)

    escalation_two = _create_escalation(client, env["headers"], env["patient_id"])
    task_two = _create_task(client, env["headers"], escalation_two)
    outcome_two = _create_outcome(client, env["headers"], env["patient_id"], task_two)

    resp = client.post(
        "/api/v1/care-updates",
        json={
            "patient_id": env["patient_id"],
            "summary": "Mismatch linkage",
            "care_update_type": "coordination",
            "intervention_task_id": task_one,
            "outcome_id": outcome_two["id"],
        },
        headers=env["headers"],
    )
    assert resp.status_code == 422


def test_list_care_updates_for_patient(client: TestClient, db_session: Session) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="care-list")
    older_time = datetime.now(timezone.utc) - timedelta(days=1)

    first = client.post(
        "/api/v1/care-updates",
        json={
            "patient_id": env["patient_id"],
            "summary": "Earlier note",
            "care_update_type": "education",
            "occurred_at": older_time.isoformat(),
        },
        headers=env["headers"],
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/care-updates",
        json={
            "patient_id": env["patient_id"],
            "summary": "Recent note",
            "care_update_type": "follow_up",
        },
        headers=env["headers"],
    )
    assert second.status_code == 201

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/care-updates",
        headers=env["headers"],
    )
    assert listing.status_code == 200
    payload = listing.json()
    assert len(payload) == 2
    assert payload[0]["summary"] == "Recent note"
    assert payload[1]["summary"] == "Earlier note"

def test_patient_care_update_listing_scoped_to_org(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="care-scope")
    create = client.post(
        "/api/v1/care-updates",
        json={
            "patient_id": env["patient_id"],
            "summary": "Scoped note",
            "care_update_type": "outreach",
        },
        headers=env["headers"],
    )
    assert create.status_code == 201

    other_org = create_organization_record(db_session, slug="care-scope-other")
    other_user = create_user_for_org(
        db_session,
        organization=other_org,
        email="scope-care@example.com",
        password="Secret123!",
    )
    other_headers = auth_headers(client, other_user.email, "Secret123!")

    denied = client.get(
        f"/api/v1/patients/{env['patient_id']}/care-updates",
        headers=other_headers,
    )
    assert denied.status_code == 403


def test_care_update_requires_same_patient_for_outcome_reference(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="care-outcome-cross-patient")
    other_patient_id = create_patient_for_user(client, env["headers"], first_name="other-patient")
    other_escalation_id = _create_escalation(client, env["headers"], other_patient_id)
    other_task_id = _create_task(client, env["headers"], other_escalation_id)
    other_outcome = _create_outcome(client, env["headers"], other_patient_id, other_task_id)

    resp = client.post(
        "/api/v1/care-updates",
        json={
            "patient_id": env["patient_id"],
            "summary": "Cross patient outcome",
            "care_update_type": "coordination",
            "outcome_id": other_outcome["id"],
        },
        headers=env["headers"],
    )

    assert resp.status_code == 422


def test_care_update_list_is_deterministic_for_same_occurred_at(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="care-deterministic")
    occurred_at = datetime.now(timezone.utc).replace(microsecond=0)

    first = client.post(
        "/api/v1/care-updates",
        json={
            "patient_id": env["patient_id"],
            "summary": "First note",
            "care_update_type": "outreach",
            "occurred_at": occurred_at.isoformat(),
        },
        headers=env["headers"],
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/care-updates",
        json={
            "patient_id": env["patient_id"],
            "summary": "Second note",
            "care_update_type": "follow_up",
            "occurred_at": occurred_at.isoformat(),
        },
        headers=env["headers"],
    )
    assert second.status_code == 201

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/care-updates",
        headers=env["headers"],
    )
    assert listing.status_code == 200

    ordered_ids = [item["id"] for item in listing.json()]
    expected_ids = sorted(
        [first.json()["id"], second.json()["id"]],
        reverse=True,
    )
    assert ordered_ids == expected_ids
