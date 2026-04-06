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


def _bootstrap_task(
    client: TestClient,
    db_session: Session,
    *,
    slug: str,
) -> dict:
    organization = create_organization_record(db_session, slug=slug)
    primary_user = create_user_for_org(
        db_session,
        organization=organization,
        email=f"{slug}@example.com",
        password="Secret123!",
    )
    headers = auth_headers(client, primary_user.email, "Secret123!")
    patient_id = create_patient_for_user(client, headers, first_name=f"{slug}-patient")
    escalation_id = _create_escalation(client, headers, patient_id)

    resp = client.post(
        f"/api/v1/escalations/{escalation_id}/tasks",
        json={
            "title": "Call patient",
            "description": "Confirm status",
            "priority": "high",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    task = resp.json()
    return {
        "organization": organization,
        "user": primary_user,
        "headers": headers,
        "patient_id": patient_id,
        "escalation_id": escalation_id,
        "task": task,
    }


def _create_escalation(client: TestClient, headers: dict[str, str], patient_id: str) -> str:
    resp = client.post(
        f"/api/v1/patients/{patient_id}/signals",
        json={
            "signal_type": "symptom_score",
            "signal_value_numeric": 10.5,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["escalation"] is not None
    return payload["escalation"]["id"]


def _complete_task_with_outcome(
    client: TestClient,
    headers: dict[str, str],
    task_id: str,
    *,
    summary: str = "Patient reached",
    outcome_status: str = "successful",
):
    return client.post(
        f"/api/v1/intervention-tasks/{task_id}/complete-with-outcome",
        json={
            "completion_summary": summary,
            "intervention_type": "phone_call",
            "outcome_status": outcome_status,
            "patient_response": "Acknowledged plan",
            "follow_up_required": True,
            "follow_up_notes": "Schedule check-in",
        },
        headers=headers,
    )


def test_create_and_list_tasks(client: TestClient, db_session: Session) -> None:
    env = _bootstrap_task(client, db_session, slug="task-list")
    headers = env["headers"]

    patient_list = client.get(
        f"/api/v1/patients/{env['patient_id']}/tasks",
        headers=headers,
    )
    assert patient_list.status_code == 200
    assert len(patient_list.json()) == 1

    escalation_list = client.get(
        f"/api/v1/escalations/{env['escalation_id']}/tasks",
        headers=headers,
    )
    assert escalation_list.status_code == 200
    assert len(escalation_list.json()) == 1

    task_detail = client.get(
        f"/api/v1/tasks/{env['task']['id']}",
        headers=headers,
    )
    assert task_detail.status_code == 200
    assert task_detail.json()["title"] == "Call patient"


def test_task_listing_blocked_cross_tenant(client: TestClient, db_session: Session) -> None:
    env = _bootstrap_task(client, db_session, slug="task-tenant")

    other_org = create_organization_record(db_session, slug="task-tenant-other")
    other_user = create_user_for_org(
        db_session,
        organization=other_org,
        email="other-task@example.com",
        password="Secret123!",
    )
    other_headers = auth_headers(client, other_user.email, "Secret123!")

    denied = client.get(
        f"/api/v1/patients/{env['patient_id']}/tasks",
        headers=other_headers,
    )
    assert denied.status_code == 403


def test_task_assignment_within_org(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_task(client, db_session, slug="task-assign")
    organization = env["organization"]

    second_user = create_user_for_org(
        db_session,
        organization=organization,
        email="assignee@example.com",
        password="Secret123!",
    )

    resp = client.post(
        f"/api/v1/tasks/{env['task']['id']}/assign",
        json={"assigned_user_id": str(second_user.id)},
        headers=env["headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["assigned_user_id"] == str(second_user.id)


def test_task_assignment_rejects_other_org_user(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_task(client, db_session, slug="task-assign-deny")

    other_org = create_organization_record(db_session, slug="task-assign-foreign")
    other_user = create_user_for_org(
        db_session,
        organization=other_org,
        email="foreign@example.com",
        password="Secret123!",
    )

    resp = client.post(
        f"/api/v1/tasks/{env['task']['id']}/assign",
        json={"assigned_user_id": str(other_user.id)},
        headers=env["headers"],
    )
    assert resp.status_code == 400


def test_start_task_transitions_status(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_task(client, db_session, slug="task-start")

    start_resp = client.post(
        f"/api/v1/tasks/{env['task']['id']}/start",
        headers=env["headers"],
    )
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "in_progress"


def test_complete_task_and_prevent_duplicate_completion(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_task(client, db_session, slug="task-complete")

    complete_resp = client.post(
        f"/api/v1/tasks/{env['task']['id']}/complete",
        json={"completion_note": "Called patient"},
        headers=env["headers"],
    )
    assert complete_resp.status_code == 200
    payload = complete_resp.json()
    assert payload["status"] == "completed"
    assert payload["completion_note"] == "Called patient"
    assert payload["completed_by_user_id"] == str(env["user"].id)
    assert payload["completed_at"] is not None

    duplicate_resp = client.post(
        f"/api/v1/tasks/{env['task']['id']}/complete",
        json={},
        headers=env["headers"],
    )
    assert duplicate_resp.status_code == 409


def test_cancel_task_flow(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_task(client, db_session, slug="task-cancel")

    cancel_resp = client.post(
        f"/api/v1/tasks/{env['task']['id']}/cancel",
        headers=env["headers"],
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    repeat_cancel = client.post(
        f"/api/v1/tasks/{env['task']['id']}/cancel",
        headers=env["headers"],
    )
    assert repeat_cancel.status_code == 409


def test_complete_task_with_outcome_records_evidence(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_task(client, db_session, slug="task-outcome")

    resp = _complete_task_with_outcome(
        client,
        env["headers"],
        env["task"]["id"],
        summary="Documented escalation response",
    )
    assert resp.status_code == 201
    outcome = resp.json()
    assert outcome["intervention_task_id"] == env["task"]["id"]
    assert outcome["outcome_status"] == "successful"
    assert outcome["follow_up_required"] is True

    task_detail = client.get(
        f"/api/v1/tasks/{env['task']['id']}",
        headers=env["headers"],
    )
    assert task_detail.status_code == 200
    assert task_detail.json()["status"] == "completed"

    fetch = client.get(
        f"/api/v1/intervention-tasks/{env['task']['id']}/outcome",
        headers=env["headers"],
    )
    assert fetch.status_code == 200
    assert fetch.json()["id"] == outcome["id"]


def test_duplicate_task_outcome_rejected(client: TestClient, db_session: Session) -> None:
    env = _bootstrap_task(client, db_session, slug="task-outcome-dup")
    first = _complete_task_with_outcome(client, env["headers"], env["task"]["id"])
    assert first.status_code == 201

    duplicate = _complete_task_with_outcome(client, env["headers"], env["task"]["id"])
    assert duplicate.status_code == 409


def test_task_outcome_cross_tenant_denied(client: TestClient, db_session: Session) -> None:
    env = _bootstrap_task(client, db_session, slug="task-outcome-scope")
    resp = _complete_task_with_outcome(client, env["headers"], env["task"]["id"])
    assert resp.status_code == 201

    other_org = create_organization_record(db_session, slug="task-outcome-scope-other")
    other_user = create_user_for_org(
        db_session,
        organization=other_org,
        email="scope-outcome@example.com",
        password="Secret123!",
    )
    other_headers = auth_headers(client, other_user.email, "Secret123!")

    denied = client.get(
        f"/api/v1/patients/{env['patient_id']}/task-outcomes",
        headers=other_headers,
    )
    assert denied.status_code == 403


def test_list_task_outcomes_for_patient(client: TestClient, db_session: Session) -> None:
    env = _bootstrap_task(client, db_session, slug="task-outcome-patient")
    resp = _complete_task_with_outcome(client, env["headers"], env["task"]["id"])
    assert resp.status_code == 201

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/task-outcomes",
        headers=env["headers"],
    )
    assert listing.status_code == 200
    payload = listing.json()
    assert len(payload) == 1
    assert payload[0]["intervention_task_id"] == env["task"]["id"]


def test_list_task_outcomes_for_escalation(client: TestClient, db_session: Session) -> None:
    env = _bootstrap_task(client, db_session, slug="task-outcome-escalation")
    resp = _complete_task_with_outcome(client, env["headers"], env["task"]["id"], outcome_status="deferred")
    assert resp.status_code == 201

    listing = client.get(
        f"/api/v1/escalations/{env['escalation_id']}/task-outcomes",
        headers=env["headers"],
    )
    assert listing.status_code == 200
    payload = listing.json()
    assert len(payload) == 1
    assert payload[0]["outcome_status"] == "deferred"


def test_outcome_completion_rejected_for_terminal_task(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_task(client, db_session, slug="task-outcome-terminal")

    complete_resp = client.post(
        f"/api/v1/tasks/{env['task']['id']}/complete",
        json={"completion_note": "Finished elsewhere"},
        headers=env["headers"],
    )
    assert complete_resp.status_code == 200

    term_attempt = _complete_task_with_outcome(client, env["headers"], env["task"]["id"])
    assert term_attempt.status_code == 409

    env_cancel = _bootstrap_task(client, db_session, slug="task-outcome-cancelled")
    cancel_resp = client.post(
        f"/api/v1/tasks/{env_cancel['task']['id']}/cancel",
        headers=env_cancel["headers"],
    )
    assert cancel_resp.status_code == 200

    cancel_attempt = _complete_task_with_outcome(
        client,
        env_cancel["headers"],
        env_cancel["task"]["id"],
    )
    assert cancel_attempt.status_code == 409


def test_completion_summary_required(client: TestClient, db_session: Session) -> None:
    env = _bootstrap_task(client, db_session, slug="task-outcome-validation")
    resp = _complete_task_with_outcome(
        client,
        env["headers"],
        env["task"]["id"],
        summary="   ",
    )
    assert resp.status_code == 422


def test_task_due_date_update_flow(client: TestClient, db_session: Session) -> None:
    env = _bootstrap_task(client, db_session, slug="task-due-date")
    task_id = env["task"]["id"]
    headers = env["headers"]
    first_due_at = datetime.now(timezone.utc) + timedelta(days=3)

    create_due = client.post(
        f"/api/v1/tasks/{task_id}/due-date",
        json={"due_at": first_due_at.isoformat()},
        headers=headers,
    )
    assert create_due.status_code == 200
    payload = create_due.json()
    expected_due_at = first_due_at.replace(tzinfo=None)
    assert datetime.fromisoformat(payload["due_at"]) == expected_due_at

    detail = client.get(f"/api/v1/tasks/{task_id}", headers=headers)
    assert detail.status_code == 200
    assert datetime.fromisoformat(detail.json()["due_at"]) == expected_due_at

    clear_due = client.post(
        f"/api/v1/tasks/{task_id}/due-date",
        json={"due_at": None},
        headers=headers,
    )
    assert clear_due.status_code == 200
    assert clear_due.json()["due_at"] is None
