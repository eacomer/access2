from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.intervention_task import InterventionTaskStatus
from app.models.patient_signal import EscalationStatus
from tests.test_patients import (
    auth_headers,
    create_organization_record,
    create_user_for_org,
)


def _admin_headers(client: TestClient, db_session: Session) -> dict[str, str]:
    organization = create_organization_record(db_session, slug="admin-workflow-bootstrap")
    user = create_user_for_org(
        db_session,
        organization=organization,
        email="workflow-admin@example.com",
        password="Secret123!",
        is_superuser=True,
    )
    return auth_headers(client, user.email, "Secret123!")


def _create_scenario(client: TestClient, headers: dict[str, str], scenario: str) -> dict:
    resp = client.post(
        "/api/v1/admin/workflow/bootstrap",
        json={
            "scenario": scenario,
            "first_name": scenario.replace("_", "-"),
            "last_name": "Validation",
            "date_of_birth": "1975-01-01",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def _get_worklist_row(client: TestClient, headers: dict[str, str], patient_id: str) -> dict:
    resp = client.get(
        "/api/v1/patients/timeline/worklist-summary",
        params=[("patient_ids", patient_id)],
        headers=headers,
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    return payload["items"][0]


def _get_timeline_detail(client: TestClient, headers: dict[str, str], patient_id: str) -> dict:
    listing = client.get(
        f"/api/v1/patients/{patient_id}/timeline",
        headers=headers,
    )
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert items

    detail = client.get(
        f"/api/v1/patients/{patient_id}/timeline/{items[0]['event_id']}",
        headers=headers,
    )
    assert detail.status_code == 200
    return detail.json()


def test_admin_bootstrap_supports_manual_validation_scenarios(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = _admin_headers(client, db_session)

    overdue = _create_scenario(client, headers, "overdue_task")
    assert overdue["task_created"] is True
    overdue_patient = client.get(
        f"/api/v1/patients/{overdue['patient_id']}",
        headers=headers,
    ).json()
    assert overdue_patient["external_patient_id"].startswith("validation-scenario:overdue_task:")
    overdue_task = client.get(f"/api/v1/tasks/{overdue['task_id']}", headers=headers).json()
    assert overdue_task["status"] == InterventionTaskStatus.OPEN.value

    in_progress = _create_scenario(client, headers, "in_progress_task")
    in_progress_task = client.get(
        f"/api/v1/tasks/{in_progress['task_id']}",
        headers=headers,
    ).json()
    assert in_progress_task["status"] == InterventionTaskStatus.IN_PROGRESS.value

    no_task = _create_scenario(client, headers, "open_escalation_no_task")
    assert no_task["escalation_id"] is not None
    assert no_task["task_id"] is None
    assert no_task["task_created"] is False

    recent = _create_scenario(client, headers, "recent_completion")
    recent_task = client.get(f"/api/v1/tasks/{recent['task_id']}", headers=headers).json()
    assert recent_task["status"] == InterventionTaskStatus.COMPLETED.value
    escalation = client.get(
        f"/api/v1/escalations/{recent['escalation_id']}",
        headers=headers,
    ).json()
    assert escalation["status"] == EscalationStatus.RESOLVED.value

    routine = _create_scenario(client, headers, "routine")
    assert routine["signal_id"] is None
    assert routine["escalation_id"] is None
    assert routine["task_id"] is None


def test_admin_bootstrap_default_does_not_add_validation_marker(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = _admin_headers(client, db_session)

    resp = client.post(
        "/api/v1/admin/workflow/bootstrap",
        json={
            "first_name": "Default",
            "last_name": "Bootstrap",
            "date_of_birth": "1975-01-01",
        },
        headers=headers,
    )
    assert resp.status_code == 201

    patient = client.get(
        f"/api/v1/patients/{resp.json()['patient_id']}",
        headers=headers,
    ).json()
    assert patient["external_patient_id"] is None


def test_admin_bootstrap_scenarios_align_queue_and_detail_summaries(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = _admin_headers(client, db_session)

    expected_by_scenario = {
        "overdue_task": {
            "attention_reason": "Task overdue",
            "next_step": "Update task disposition",
            "recommended_timeframe": "Today",
            "priority_band": "High",
            "priority_reason": "Task is overdue",
            "status_snapshot": "High priority: task is overdue today",
            "care_gap_label": "Task disposition overdue",
            "blocking_issue_label": "Task not updated",
            "resolution_target_label": "Update or close the task",
            "closure_readiness_label": "Not ready for closure",
            "resolution_confidence_label": "Low confidence",
            "detail_primary_driver": "task",
            "detail_urgency_level": "overdue",
        },
        "in_progress_task": {
            "attention_reason": "Task in progress",
            "next_step": "Continue active intervention",
            "recommended_timeframe": "Today",
            "priority_band": "High",
            "priority_reason": "Action is due today",
            "status_snapshot": "High priority: action is due today",
            "care_gap_label": "Intervention still in progress",
            "blocking_issue_label": "Work not yet completed",
            "resolution_target_label": "Complete the intervention",
            "closure_readiness_label": "Not ready for closure",
            "resolution_confidence_label": "Moderate confidence",
            "detail_primary_driver": "task",
            "detail_urgency_level": "active",
        },
        "open_escalation_no_task": {
            "attention_reason": "Open escalation, no active outreach",
            "next_step": "Start outreach",
            "recommended_timeframe": "Within 24 hours",
            "priority_band": "Medium",
            "priority_reason": "Action is needed within 24 hours",
            "status_snapshot": "Medium priority: action is needed within 24 hours",
            "care_gap_label": "Outreach not started",
            "blocking_issue_label": "No outreach started",
            "resolution_target_label": "Start outreach and document action",
            "closure_readiness_label": "Not ready for closure",
            "resolution_confidence_label": "Low confidence",
            "detail_primary_driver": "escalation",
            "detail_urgency_level": "active",
        },
        "recent_completion": {
            "attention_reason": "Recently completed, monitor",
            "next_step": "Monitor recent completion",
            "recommended_timeframe": "This week",
            "priority_band": "Low",
            "priority_reason": "Work was completed recently",
            "status_snapshot": "Low priority: work was completed recently, monitor recent completion this week",
            "care_gap_label": "Monitoring follow-up pending",
            "blocking_issue_label": "Follow-up window still open",
            "resolution_target_label": "Confirm no new follow-up is needed",
            "closure_readiness_label": "Near closure",
            "resolution_confidence_label": "High confidence",
            "detail_primary_driver": "monitoring",
            "detail_urgency_level": "stable",
        },
        "routine": {
            "attention_reason": "Routine monitoring",
            "next_step": "Routine monitoring",
            "recommended_timeframe": "Routine",
            "priority_band": "Low",
            "priority_reason": "No urgent workflow driver is present",
            "status_snapshot": "Low priority: no urgent workflow driver is present",
            "care_gap_label": "No active care gap",
            "blocking_issue_label": "No active blocker",
            "resolution_target_label": "Continue routine monitoring",
            "closure_readiness_label": "Ready for routine monitoring",
            "resolution_confidence_label": "High confidence",
            "detail_primary_driver": "monitoring",
            "detail_urgency_level": "stable",
        },
    }

    for scenario, expected in expected_by_scenario.items():
        created = _create_scenario(client, headers, scenario)
        patient_id = created["patient_id"]
        row = _get_worklist_row(client, headers, patient_id)

        for field in (
            "attention_reason",
            "next_step",
            "recommended_timeframe",
            "priority_band",
            "priority_reason",
            "status_snapshot",
            "care_gap_label",
            "blocking_issue_label",
            "resolution_target_label",
            "closure_readiness_label",
            "resolution_confidence_label",
        ):
            assert row[field] == expected[field]

        if scenario == "routine":
            continue

        detail = _get_timeline_detail(client, headers, patient_id)

        for field in (
            "status_snapshot",
            "care_gap_label",
            "blocking_issue_label",
            "resolution_target_label",
            "closure_readiness_label",
            "resolution_confidence_label",
        ):
            assert detail[field] == row[field]

        assert detail["attention_summary"]["primary_driver"] == expected["detail_primary_driver"]
        assert detail["attention_summary"]["urgency_level"] == expected["detail_urgency_level"]
