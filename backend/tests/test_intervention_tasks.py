from __future__ import annotations

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
