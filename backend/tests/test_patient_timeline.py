from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.intervention_task import InterventionTask
from app.services import patient_timeline_read_state_service as read_state_service
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


def _create_signal(
    client: TestClient,
    headers: dict[str, str],
    patient_id: str,
    *,
    recorded_at: datetime | None = None,
    escalation_sla_due_at: datetime | None = None,
    signal_type: str = "symptom_score",
    signal_value_numeric: float | None = 9.5,
) -> dict:
    payload: dict[str, object] = {
        "signal_type": signal_type,
    }
    if signal_value_numeric is not None:
        payload["signal_value_numeric"] = signal_value_numeric
    if recorded_at is not None:
        payload["recorded_at"] = recorded_at.isoformat()
    if escalation_sla_due_at is not None:
        payload["escalation_sla_due_at"] = escalation_sla_due_at.isoformat()
    resp = client.post(
        f"/api/v1/patients/{patient_id}/signals",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def _create_task(
    client: TestClient,
    headers: dict[str, str],
    escalation_id: str,
    *,
    title: str = "Follow up",
    priority: str = "medium",
    due_at: datetime | None = None,
) -> str:
    payload: dict[str, object] = {
        "title": title,
        "description": "Check status",
        "priority": priority,
    }
    if due_at is not None:
        payload["due_at"] = due_at.isoformat()
    resp = client.post(
        f"/api/v1/escalations/{escalation_id}/tasks",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _update_escalation_status(
    client: TestClient,
    headers: dict[str, str],
    escalation_id: str,
    *,
    status: str,
    note: str | None = None,
) -> dict:
    payload: dict[str, object] = {"status": status}
    if note is not None:
        payload["note"] = note
    resp = client.post(
        f"/api/v1/escalations/{escalation_id}/status",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _complete_task_with_outcome(
    client: TestClient,
    headers: dict[str, str],
    task_id: str,
) -> dict:
    resp = client.post(
        f"/api/v1/intervention-tasks/{task_id}/complete-with-outcome",
        json={
            "completion_summary": "Reached patient",
            "intervention_type": "phone_call",
            "outcome_status": "successful",
            "patient_response": "Agreed to plan",
            "follow_up_required": False,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def _create_care_update(
    client: TestClient,
    headers: dict[str, str],
    patient_id: str,
    *,
    summary: str = "Spoke with patient",
    occurred_at: datetime | None = None,
    intervention_task_outcome_id: str | None = None,
) -> dict:
    payload: dict[str, object] = {
        "summary": summary,
        "care_update_type": "outreach",
    }
    if occurred_at is not None:
        payload["occurred_at"] = occurred_at.isoformat()
    if intervention_task_outcome_id is not None:
        payload["intervention_task_outcome_id"] = intervention_task_outcome_id
    resp = client.post(
        f"/api/v1/patients/{patient_id}/care-updates",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def _get_workflow_summary(
    client: TestClient,
    headers: dict[str, str],
    patient_id: str,
) -> dict:
    resp = client.get(
        f"/api/v1/patients/{patient_id}/timeline/workflow-summary",
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _get_inbox_summary(
    client: TestClient,
    headers: dict[str, str],
    patient_id: str,
    params: dict[str, object] | list[tuple[str, object]] | None = None,
) -> dict:
    resp = client.get(
        f"/api/v1/patients/{patient_id}/timeline/inbox-summary",
        params=params,
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _get_worklist_summary(
    client: TestClient,
    headers: dict[str, str],
    params: dict[str, object] | list[tuple[str, object]] | None = None,
    *,
    expect_status: int = 200,
) -> dict:
    resp = client.get(
        "/api/v1/patients/timeline/worklist-summary",
        params=params,
        headers=headers,
    )
    assert resp.status_code == expect_status
    return resp.json()


def _find_worklist_item(payload: dict, patient_id: str) -> dict:
    return next(item for item in payload["items"] if item["patient_id"] == patient_id)


def _get_timeline_detail_payload(
    client: TestClient,
    headers: dict[str, str],
    patient_id: str,
    event_id: str | None = None,
) -> dict:
    target_event_id = event_id
    if target_event_id is None:
        listing = client.get(
            f"/api/v1/patients/{patient_id}/timeline",
            headers=headers,
        )
        assert listing.status_code == 200
        items = listing.json()["items"]
        assert items, "expected at least one timeline event"
        target_event_id = items[0]["event_id"]

    resp = client.get(
        f"/api/v1/patients/{patient_id}/timeline/{target_event_id}",
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _get_escalation_evidence(
    client: TestClient,
    headers: dict[str, str],
    patient_id: str,
    event_id: str | None = None,
) -> dict:
    payload = _get_timeline_detail_payload(
        client,
        headers,
        patient_id,
        event_id=event_id,
    )
    evidence = payload.get("escalation_evidence")
    assert evidence is not None
    return evidence


def _get_task_summary(
    client: TestClient,
    headers: dict[str, str],
    patient_id: str,
    event_id: str | None = None,
) -> dict:
    payload = _get_timeline_detail_payload(
        client,
        headers,
        patient_id,
        event_id=event_id,
    )
    summary = payload.get("task_summary")
    assert summary is not None
    return summary


def _get_workflow_status(
    client: TestClient,
    headers: dict[str, str],
    patient_id: str,
    event_id: str | None = None,
) -> dict:
    payload = _get_timeline_detail_payload(
        client,
        headers,
        patient_id,
        event_id=event_id,
    )
    status = payload.get("workflow_status")
    assert status is not None
    return status


def _get_intervention_evidence_summary(
    client: TestClient,
    headers: dict[str, str],
    patient_id: str,
    event_id: str | None = None,
) -> dict:
    payload = _get_timeline_detail_payload(
        client,
        headers,
        patient_id,
        event_id=event_id,
    )
    summary = payload.get("intervention_evidence_summary")
    assert summary is not None
    return summary


def _get_attention_summary(
    client: TestClient,
    headers: dict[str, str],
    patient_id: str,
    event_id: str | None = None,
) -> dict:
    payload = _get_timeline_detail_payload(
        client,
        headers,
        patient_id,
        event_id=event_id,
    )
    summary = payload.get("attention_summary")
    assert summary is not None
    return summary


def _bootstrap_user_without_patient(
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
    return {
        "organization": organization,
        "user": user,
        "headers": headers,
    }


def _parse_occurred_at(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def test_patient_timeline_returns_combined_feed(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-mixed")

    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    task_id = _create_task(client, env["headers"], escalation_id)
    outcome = _complete_task_with_outcome(client, env["headers"], task_id)
    _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        intervention_task_outcome_id=outcome["id"],
    )

    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] >= 5
    assert payload["limit"] == 50
    assert "next_cursor_event_id" in payload
    assert "next_cursor_occurred_at" in payload
    assert isinstance(payload["has_more"], bool)
    kinds = {item["source_kind"] for item in payload["items"]}
    assert {
        "signal",
        "escalation",
        "intervention_task",
        "intervention_task_outcome",
        "care_update",
    }.issubset(kinds)

    occurred_list = [_parse_occurred_at(item["occurred_at"]) for item in payload["items"]]
    assert occurred_list == sorted(occurred_list, reverse=True)


def test_patient_timeline_includes_escalation_status_events(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-status-events")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]

    _update_escalation_status(
        client,
        env["headers"],
        escalation_id,
        status="in_progress",
        note="evaluating",
    )
    _update_escalation_status(
        client,
        env["headers"],
        escalation_id,
        status="resolved",
        note="closed",
    )

    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    status_events = [item for item in items if item["event_type"] == "escalation_status_changed"]
    assert status_events, "expected escalation status change in timeline feed"
    assert status_events[0]["status"] == "resolved"
    assert status_events[0]["display_text"] == "closed"


def test_patient_timeline_pagination_is_deterministic(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-page")
    base_time = datetime.now(timezone.utc)
    for idx in range(4):
        _create_care_update(
            client,
            env["headers"],
            env["patient_id"],
            summary=f"Note {idx}",
            occurred_at=base_time - timedelta(hours=idx),
        )

    baseline = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"limit": 10},
        headers=env["headers"],
    )
    assert baseline.status_code == 200
    baseline_items = baseline.json()["items"]

    first_page = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"limit": 2},
        headers=env["headers"],
    )
    assert first_page.status_code == 200
    first_payload = first_page.json()
    assert len(first_payload["items"]) == 2
    assert first_payload["has_more"] is True

    second_page = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={
            "limit": 2,
            "cursor_occurred_at": first_payload["next_cursor_occurred_at"],
            "cursor_event_id": first_payload["next_cursor_event_id"],
        },
        headers=env["headers"],
    )
    assert second_page.status_code == 200
    second_payload = second_page.json()
    assert len(second_payload["items"]) == 2
    combined_ids = [item["event_id"] for item in first_payload["items"] + second_payload["items"]]
    assert combined_ids == [item["event_id"] for item in baseline_items[:4]]


def test_patient_timeline_cursor_pages_do_not_duplicate_items(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-cursor-unique")
    base_time = datetime.now(timezone.utc)
    for idx in range(5):
        _create_care_update(
            client,
            env["headers"],
            env["patient_id"],
            summary=f"Cursor {idx}",
            occurred_at=base_time - timedelta(minutes=idx),
        )

    first = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"limit": 2},
        headers=env["headers"],
    ).json()
    second = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={
            "limit": 2,
            "cursor_occurred_at": first["next_cursor_occurred_at"],
            "cursor_event_id": first["next_cursor_event_id"],
        },
        headers=env["headers"],
    ).json()
    if second["next_cursor_event_id"]:
        third = client.get(
            f"/api/v1/patients/{env['patient_id']}/timeline",
            params={
                "limit": 2,
                "cursor_occurred_at": second["next_cursor_occurred_at"],
                "cursor_event_id": second["next_cursor_event_id"],
            },
            headers=env["headers"],
        ).json()
    else:
        third = {"items": []}

    event_ids: list[str] = []
    for payload in (first, second, third):
        event_ids.extend(item["event_id"] for item in payload["items"])
    assert len(event_ids) == len(set(event_ids))


def test_patient_timeline_cursor_with_identical_occurred_at_is_stable(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-cursor-tie")
    occurred_at = datetime.now(timezone.utc)
    for idx in range(3):
        _create_care_update(
            client,
            env["headers"],
            env["patient_id"],
            summary=f"Tie {idx}",
            occurred_at=occurred_at,
        )

    baseline = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"limit": 3},
        headers=env["headers"],
    )
    assert baseline.status_code == 200
    first_order = [item["event_id"] for item in baseline.json()["items"]]

    repeat = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"limit": 3},
        headers=env["headers"],
    )
    assert repeat.status_code == 200
    second_order = [item["event_id"] for item in repeat.json()["items"]]
    assert first_order == second_order


def test_patient_timeline_cursor_same_timestamp_next_page_is_deterministic(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-cursor-boundary")
    occurred_at = datetime.now(timezone.utc)
    for idx in range(5):
        _create_care_update(
            client,
            env["headers"],
            env["patient_id"],
            summary=f"Boundary {idx}",
            occurred_at=occurred_at,
        )

    baseline = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"limit": 5},
        headers=env["headers"],
    ).json()["items"]

    first = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"limit": 2},
        headers=env["headers"],
    ).json()
    second = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={
            "limit": 2,
            "cursor_occurred_at": first["next_cursor_occurred_at"],
            "cursor_event_id": first["next_cursor_event_id"],
        },
        headers=env["headers"],
    ).json()

    combined_ids = [item["event_id"] for item in first["items"] + second["items"]]
    assert combined_ids == [item["event_id"] for item in baseline[:4]]
    assert first["items"][-1]["event_id"] != second["items"][0]["event_id"]


def test_patient_timeline_rejects_partial_cursor_request(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-cursor-invalid")
    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"cursor_event_id": "signal:123"},
        headers=env["headers"],
    )
    assert resp.status_code == 422


def test_patient_timeline_cross_org_forbidden(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-scope")
    other_org = create_organization_record(db_session, slug="timeline-other-org")
    other_user = create_user_for_org(
        db_session,
        organization=other_org,
        email="timeline-other@example.com",
        password="Secret123!",
    )
    other_headers = auth_headers(client, other_user.email, "Secret123!")

    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=other_headers,
    )
    assert resp.status_code == 403


def test_patient_timeline_since_cross_org_forbidden(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-scope-since")
    other_org = create_organization_record(db_session, slug="timeline-since-other-org")
    other_user = create_user_for_org(
        db_session,
        organization=other_org,
        email="timeline-since-other@example.com",
        password="Secret123!",
    )
    other_headers = auth_headers(client, other_user.email, "Secret123!")

    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/since",
        params={"since": datetime.now(timezone.utc).isoformat()},
        headers=other_headers,
    )
    assert resp.status_code == 403


def test_patient_timeline_filters_other_patients(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-filter")
    other_patient_id = create_patient_for_user(client, env["headers"], first_name="timeline-two")
    _create_signal(client, env["headers"], other_patient_id)

    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] == 0
    assert payload["items"] == []


def test_patient_timeline_detail_lookup(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-detail")
    _create_signal(client, env["headers"], env["patient_id"])

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    )
    assert listing.status_code == 200
    event_id = listing.json()["items"][0]["event_id"]

    detail = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/{event_id}",
        headers=env["headers"],
    )
    assert detail.status_code == 200
    payload = detail.json()["item"]
    assert payload["event_id"] == event_id
    assert payload["source_kind"] == "signal"
    assert payload["event_type"] == "signal_recorded"


def test_patient_timeline_detail_escalation_evidence_absent_without_escalations(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-evidence-none")
    _create_care_update(client, env["headers"], env["patient_id"], summary="No escalations note")

    evidence = _get_escalation_evidence(client, env["headers"], env["patient_id"])
    assert evidence["has_open_escalation"] is False
    assert evidence["open_escalation_count"] == 0
    assert evidence["overdue_escalation_count"] == 0
    assert evidence["at_risk_escalation_count"] == 0
    assert evidence["highest_open_escalation_priority"] is None
    assert evidence["next_open_escalation_sla_due_at"] is None
    assert evidence["latest_open_escalation_id"] is None
    assert evidence["latest_open_escalation_status"] is None
    assert evidence["latest_escalation_event_id"] is None


def test_patient_timeline_detail_escalation_evidence_single_open_without_sla(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-evidence-single")
    signal_payload = _create_signal(
        client,
        env["headers"],
        env["patient_id"],
        escalation_sla_due_at=None,
    )
    escalation = signal_payload["escalation"]

    evidence = _get_escalation_evidence(client, env["headers"], env["patient_id"])
    assert evidence["has_open_escalation"] is True
    assert evidence["open_escalation_count"] == 1
    assert evidence["overdue_escalation_count"] == 0
    assert evidence["at_risk_escalation_count"] == 0
    assert evidence["next_open_escalation_sla_due_at"] is None
    assert evidence["latest_open_escalation_id"] == escalation["id"]
    assert evidence["latest_open_escalation_status"] == escalation["status"]
    assert evidence["latest_escalation_event_type"] == "escalation_triggered"


def test_patient_timeline_detail_escalation_evidence_future_sla_steady(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-evidence-future-sla")
    due_at = datetime.now(timezone.utc) + timedelta(hours=30)
    signal_payload = _create_signal(
        client,
        env["headers"],
        env["patient_id"],
        escalation_sla_due_at=due_at,
    )

    evidence = _get_escalation_evidence(client, env["headers"], env["patient_id"])
    assert evidence["has_open_escalation"] is True
    assert evidence["open_escalation_count"] == 1
    assert evidence["overdue_escalation_count"] == 0
    assert evidence["at_risk_escalation_count"] == 0
    assert (
        _parse_occurred_at(evidence["next_open_escalation_sla_due_at"])
        == _parse_occurred_at(signal_payload["escalation"]["sla_due_at"])
    )


def test_patient_timeline_detail_escalation_evidence_counts_at_risk_and_overdue(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-evidence-sla-states")
    now = datetime.now(timezone.utc)
    overdue_due = now - timedelta(hours=2)
    at_risk_due = now + timedelta(hours=3)

    overdue = _create_signal(
        client,
        env["headers"],
        env["patient_id"],
        recorded_at=now - timedelta(hours=4),
        escalation_sla_due_at=overdue_due,
    )["escalation"]
    _create_signal(
        client,
        env["headers"],
        env["patient_id"],
        recorded_at=now - timedelta(hours=1),
        escalation_sla_due_at=at_risk_due,
        signal_type="missed_check_in",
        signal_value_numeric=None,
    )

    evidence = _get_escalation_evidence(client, env["headers"], env["patient_id"])
    assert evidence["has_open_escalation"] is True
    assert evidence["open_escalation_count"] == 2
    assert evidence["overdue_escalation_count"] == 1
    assert evidence["at_risk_escalation_count"] == 1
    assert evidence["highest_open_escalation_priority"] == overdue["severity"]
    assert (
        _parse_occurred_at(evidence["next_open_escalation_sla_due_at"])
        == _parse_occurred_at(overdue["sla_due_at"])
    )


def test_patient_timeline_detail_escalation_evidence_handles_mixed_priorities(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-evidence-priority")
    _create_signal(
        client,
        env["headers"],
        env["patient_id"],
        signal_type="missed_check_in",
        signal_value_numeric=None,
    )
    high = _create_signal(
        client,
        env["headers"],
        env["patient_id"],
        signal_type="symptom_score",
        signal_value_numeric=10,
    )["escalation"]

    evidence = _get_escalation_evidence(client, env["headers"], env["patient_id"])
    assert evidence["open_escalation_count"] == 2
    assert evidence["highest_open_escalation_priority"] == high["severity"]


def test_patient_timeline_detail_escalation_evidence_latest_open_selection_is_deterministic(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-evidence-latest-open")
    base_time = datetime.now(timezone.utc)
    first = _create_signal(
        client,
        env["headers"],
        env["patient_id"],
        recorded_at=base_time - timedelta(hours=2),
    )["escalation"]
    second = _create_signal(
        client,
        env["headers"],
        env["patient_id"],
        recorded_at=base_time - timedelta(hours=1),
        signal_value_numeric=10.5,
    )["escalation"]

    evidence = _get_escalation_evidence(client, env["headers"], env["patient_id"])
    assert evidence["latest_open_escalation_id"] == second["id"]
    assert evidence["latest_open_escalation_id"] != first["id"]


def test_patient_timeline_detail_escalation_evidence_tracks_status_events(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-evidence-status")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]

    _update_escalation_status(
        client,
        env["headers"],
        escalation_id,
        status="in_progress",
        note="acknowledged",
    )

    evidence = _get_escalation_evidence(client, env["headers"], env["patient_id"])
    assert evidence["latest_open_escalation_status"] == "in_progress"
    assert evidence["latest_escalation_event_type"] == "escalation_status_changed"
    assert evidence["latest_escalation_event_id"].startswith("escalation_status_event:")


def test_patient_timeline_detail_escalation_evidence_uses_derived_sla_events(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-evidence-sla-event")
    due_at = datetime.now(timezone.utc) + timedelta(hours=3)
    signal_payload = _create_signal(
        client,
        env["headers"],
        env["patient_id"],
        escalation_sla_due_at=due_at,
    )
    escalation = signal_payload["escalation"]

    evidence = _get_escalation_evidence(client, env["headers"], env["patient_id"])
    assert evidence["latest_escalation_event_type"] == "escalation_sla_at_risk"
    assert evidence["latest_escalation_event_id"].startswith("escalation_sla_at_risk:")
    assert (
        _parse_occurred_at(evidence["latest_escalation_event_occurred_at"])
        == _parse_occurred_at(escalation["sla_due_at"])
    )


def test_patient_timeline_detail_escalation_evidence_excludes_resolved_escalations(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-evidence-resolved")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]

    resolve_resp = client.post(
        f"/api/v1/escalations/{escalation_id}/resolve",
        json={"resolution_notes": "handled"},
        headers=env["headers"],
    )
    assert resolve_resp.status_code == 200

    evidence = _get_escalation_evidence(client, env["headers"], env["patient_id"])
    assert evidence["has_open_escalation"] is False
    assert evidence["open_escalation_count"] == 0
    assert evidence["latest_open_escalation_id"] is None
    assert evidence["latest_escalation_event_id"] is None


def test_patient_timeline_detail_escalation_evidence_is_patient_scoped(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-evidence-scope")
    other_patient_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="timeline-evidence-other",
    )
    _create_signal(client, env["headers"], env["patient_id"])
    _create_care_update(client, env["headers"], other_patient_id, summary="other patient update")

    evidence = _get_escalation_evidence(client, env["headers"], other_patient_id)
    assert evidence["has_open_escalation"] is False
    assert evidence["open_escalation_count"] == 0
    assert evidence["latest_open_escalation_id"] is None


def test_patient_timeline_detail_task_summary_no_tasks(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-task-evidence-none")
    _create_care_update(client, env["headers"], env["patient_id"], summary="note-only")

    summary = _get_task_summary(client, env["headers"], env["patient_id"])
    assert summary["open_task_count"] == 0
    assert summary["in_progress_task_count"] == 0
    assert summary["overdue_task_count"] == 0
    assert summary["latest_active_task_id"] is None


def test_patient_timeline_detail_task_summary_open_and_completed(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-task-open")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    open_task_id = _create_task(client, env["headers"], escalation_id, title="Stay Open")
    completed_task_id = _create_task(client, env["headers"], escalation_id, title="Finish Soon")
    _complete_task_with_outcome(client, env["headers"], completed_task_id)

    summary = _get_task_summary(client, env["headers"], env["patient_id"])
    assert summary["open_task_count"] == 1
    assert summary["in_progress_task_count"] == 0
    assert summary["overdue_task_count"] == 0
    assert summary["latest_active_task_id"] == open_task_id
    assert summary["latest_active_task_status"] == "open"


def test_patient_timeline_detail_task_summary_overdue_and_in_progress(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-task-overdue")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]

    overdue_due_at = datetime.now(timezone.utc) - timedelta(hours=6)
    overdue_task_id = _create_task(
        client,
        env["headers"],
        escalation_id,
        title="Past Due",
        due_at=overdue_due_at,
    )
    start_resp = client.post(
        f"/api/v1/tasks/{overdue_task_id}/start",
        headers=env["headers"],
    )
    assert start_resp.status_code == 200

    future_due_at = datetime.now(timezone.utc) + timedelta(days=2)
    open_task_id = _create_task(
        client,
        env["headers"],
        escalation_id,
        title="Upcoming",
        due_at=future_due_at,
    )
    open_task = db_session.get(InterventionTask, uuid.UUID(open_task_id))
    assert open_task is not None
    open_task.created_at = datetime.now(timezone.utc) + timedelta(seconds=1)
    db_session.commit()

    summary = _get_task_summary(client, env["headers"], env["patient_id"])
    assert summary["open_task_count"] == 2
    assert summary["in_progress_task_count"] == 1
    assert summary["overdue_task_count"] == 1
    assert summary["latest_active_task_id"] == open_task_id
    assert summary["latest_active_task_priority"] == "medium"
    assert summary["latest_active_task_due_at"] is not None
    latest_due_at = _parse_occurred_at(summary["latest_active_task_due_at"])
    assert abs((latest_due_at - future_due_at).total_seconds()) < 1


def test_patient_timeline_detail_task_summary_deterministic_latest_task(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-task-deterministic")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    first_task_id = _create_task(client, env["headers"], escalation_id, title="First Sequence")
    second_task_id = _create_task(client, env["headers"], escalation_id, title="Second Sequence")

    tie_timestamp = datetime.now(timezone.utc) - timedelta(minutes=5)
    for task_id in (first_task_id, second_task_id):
        task = db_session.get(InterventionTask, uuid.UUID(task_id))
        assert task is not None
        task.created_at = tie_timestamp
    db_session.commit()

    expected_latest = max(first_task_id, second_task_id)
    summary = _get_task_summary(client, env["headers"], env["patient_id"])
    assert summary["latest_active_task_id"] == expected_latest
    expected_task = db_session.get(InterventionTask, uuid.UUID(expected_latest))
    assert expected_task is not None
    assert summary["latest_active_task_title"] == expected_task.title


def test_patient_workflow_status_detail_monitoring(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="workflow-status-monitoring")
    _create_care_update(client, env["headers"], env["patient_id"], summary="routine note")

    status = _get_workflow_status(client, env["headers"], env["patient_id"])
    assert status["status_key"] == "monitoring_stable"
    assert status["has_active_work"] is False
    assert status["primary_driver"] == "monitoring"


def test_patient_workflow_status_detail_task_overdue_precedence(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="workflow-status-task-overdue")
    signal_payload = _create_signal(
        client,
        env["headers"],
        env["patient_id"],
        escalation_sla_due_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    escalation_id = signal_payload["escalation"]["id"]
    overdue_due_at = datetime.now(timezone.utc) - timedelta(hours=4)
    _create_task(client, env["headers"], escalation_id, title="Past due outreach", due_at=overdue_due_at)

    status = _get_workflow_status(client, env["headers"], env["patient_id"])
    assert status["status_key"] == "task_overdue"
    assert status["primary_driver"] == "task"


def test_patient_workflow_status_detail_task_in_progress(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="workflow-status-task-progress")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    future_due_at = datetime.now(timezone.utc) + timedelta(days=1)
    task_id = _create_task(client, env["headers"], escalation_id, due_at=future_due_at)
    start_resp = client.post(f"/api/v1/tasks/{task_id}/start", headers=env["headers"])
    assert start_resp.status_code == 200

    status = _get_workflow_status(client, env["headers"], env["patient_id"])
    assert status["status_key"] == "task_in_progress"
    assert status["has_active_work"] is True


def test_patient_workflow_status_detail_escalation_overdue(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="workflow-status-escalation")
    overdue_due_at = datetime.now(timezone.utc) - timedelta(hours=3)
    _create_signal(
        client,
        env["headers"],
        env["patient_id"],
        escalation_sla_due_at=overdue_due_at,
    )

    status = _get_workflow_status(client, env["headers"], env["patient_id"])
    assert status["status_key"] == "escalation_overdue"
    assert status["primary_driver"] == "escalation"


def test_patient_timeline_detail_includes_intervention_evidence_summary(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="intervention-evidence-summary")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    _create_task(
        client,
        env["headers"],
        escalation_id,
        title="Open outreach",
    )
    in_progress_task_id = _create_task(
        client,
        env["headers"],
        escalation_id,
        title="In progress review",
    )
    start_resp = client.post(
        f"/api/v1/tasks/{in_progress_task_id}/start",
        headers=env["headers"],
    )
    assert start_resp.status_code == 200
    completed_task_id = _create_task(
        client,
        env["headers"],
        escalation_id,
        title="Completed med review",
    )
    _complete_task_with_outcome(client, env["headers"], completed_task_id)
    canceled_task_id = _create_task(
        client,
        env["headers"],
        escalation_id,
        title="Canceled duplicate outreach",
    )
    cancel_resp = client.post(
        f"/api/v1/tasks/{canceled_task_id}/cancel",
        headers=env["headers"],
    )
    assert cancel_resp.status_code == 200
    _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="Documented patient outreach",
    )

    summary = _get_intervention_evidence_summary(
        client,
        env["headers"],
        env["patient_id"],
    )

    assert summary["total_escalations"] == 1
    assert summary["open_escalations"] == 1
    assert summary["total_tasks"] == 4
    assert summary["open_tasks"] == 1
    assert summary["in_progress_tasks"] == 1
    assert summary["completed_tasks"] == 1
    assert summary["canceled_tasks"] == 1
    assert summary["evidence_event_count"] == 7
    assert summary["recent_trigger_reasons"][0]["title"].startswith("Escalation:")
    completed_titles = {
        item["title"] for item in summary["recent_completed_interventions"]
    }
    assert "Documented patient outreach" in completed_titles
    assert any(
        item["title"] == "Open outreach" and item["status"] == "open"
        for item in summary["current_open_work"]
    )
    assert any(
        item["title"] == "In progress review" and item["status"] == "in_progress"
        for item in summary["current_open_work"]
    )


def test_patient_timeline_detail_intervention_evidence_summary_minimal_state(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="intervention-evidence-minimal")
    _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="General care note",
    )

    summary = _get_intervention_evidence_summary(
        client,
        env["headers"],
        env["patient_id"],
    )

    assert summary["total_escalations"] == 0
    assert summary["open_escalations"] == 0
    assert summary["total_tasks"] == 0
    assert summary["open_tasks"] == 0
    assert summary["in_progress_tasks"] == 0
    assert summary["completed_tasks"] == 0
    assert summary["canceled_tasks"] == 0
    assert summary["recent_trigger_reasons"] == []
    assert summary["current_open_work"] == []
    assert summary["evidence_event_count"] == 1
    assert summary["recent_completed_interventions"][0]["title"] == "General care note"


def test_patient_timeline_since_returns_only_newer_items(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-since-newer")
    base_time = datetime.now(timezone.utc)
    _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="old",
        occurred_at=base_time - timedelta(days=1),
    )
    new_event = _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="new",
        occurred_at=base_time,
    )
    since = base_time - timedelta(hours=12)

    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/since",
        params={"since": since.isoformat()},
        headers=env["headers"],
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["returned_count"] == len(payload["items"])
    assert all(_parse_occurred_at(item["occurred_at"]) > since for item in payload["items"])
    assert payload["items"][0]["display_title"] == new_event["summary"]
    assert payload["newest_occurred_at"] == payload["items"][0]["occurred_at"]


def test_patient_timeline_since_respects_event_filter(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-since-event-filter")
    _create_signal(client, env["headers"], env["patient_id"])
    _create_care_update(client, env["headers"], env["patient_id"])
    since = datetime.now(timezone.utc) - timedelta(minutes=5)

    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/since",
        params=[("since", since.isoformat()), ("event_types", "care_update_logged")],
        headers=env["headers"],
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["items"]
    assert {item["event_type"] for item in payload["items"]} == {"care_update_logged"}


def test_patient_timeline_since_respects_related_filters(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-since-related")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    task_id = _create_task(client, env["headers"], escalation_id)
    outcome = _complete_task_with_outcome(client, env["headers"], task_id)
    since = datetime.now(timezone.utc) - timedelta(minutes=5)

    task_filtered = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/since",
        params={"since": since.isoformat(), "related_task_id": task_id},
        headers=env["headers"],
    )
    assert task_filtered.status_code == 200
    task_payload = task_filtered.json()
    assert {item["related_task_id"] for item in task_payload["items"]} == {task_id}

    escalation_filtered = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/since",
        params={"since": since.isoformat(), "related_escalation_id": escalation_id},
        headers=env["headers"],
    )
    assert escalation_filtered.status_code == 200
    escalation_payload = escalation_filtered.json()
    assert {item["related_escalation_id"] for item in escalation_payload["items"]} == {escalation_id}

    assert any(item["related_outcome_id"] == outcome["id"] for item in task_payload["items"])


def test_patient_timeline_since_limit_and_has_more(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-since-limit")
    base_time = datetime.now(timezone.utc)
    for idx in range(3):
        _create_care_update(
            client,
            env["headers"],
            env["patient_id"],
            summary=f"since-{idx}",
            occurred_at=base_time - timedelta(minutes=idx),
        )
    since = base_time - timedelta(hours=1)

    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/since",
        params={"since": since.isoformat(), "limit": 2},
        headers=env["headers"],
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["returned_count"] == 2
    assert payload["has_more"] is True
    assert payload["newest_occurred_at"] == payload["items"][0]["occurred_at"]


def test_patient_timeline_returns_empty_feed(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-empty")
    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["items"] == []
    assert payload["total"] == 0
    assert payload["has_more"] is False
    assert payload["next_cursor_event_id"] is None
    assert payload["next_cursor_occurred_at"] is None


def test_patient_timeline_related_ids_surface(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-related")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    task_id = _create_task(client, env["headers"], escalation_id)
    outcome = _complete_task_with_outcome(client, env["headers"], task_id)

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    )
    assert listing.status_code == 200
    outcome_event = next(
        item for item in listing.json()["items"] if item["source_kind"] == "intervention_task_outcome"
    )

    assert outcome_event["related_escalation_id"] == escalation_id
    assert outcome_event["related_task_id"] == task_id
    assert outcome_event["related_outcome_id"] == outcome["id"]


def test_patient_timeline_filter_by_single_event_type(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-single-filter")
    _create_signal(client, env["headers"], env["patient_id"])
    _create_care_update(client, env["headers"], env["patient_id"])

    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params=[("event_types", "signal_recorded")],
        headers=env["headers"],
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] >= 1
    assert all(item["event_type"] == "signal_recorded" for item in payload["items"])


def test_patient_timeline_filter_by_multiple_event_types(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-multi-filter")
    _create_signal(client, env["headers"], env["patient_id"])
    _create_care_update(client, env["headers"], env["patient_id"])
    signal_params = [
        ("event_types", "signal_recorded"),
        ("event_types", "care_update_logged"),
    ]

    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params=signal_params,
        headers=env["headers"],
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] >= 2
    assert {item["event_type"] for item in payload["items"]}.issubset(
        {"signal_recorded", "care_update_logged"}
    )


def test_patient_timeline_filter_by_date_range(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-date-filter")
    base_time = datetime.now(timezone.utc)
    _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="earliest",
        occurred_at=base_time - timedelta(days=2),
    )
    mid_event = _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="middle",
        occurred_at=base_time - timedelta(days=1),
    )
    _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="latest",
        occurred_at=base_time,
    )

    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={
            "occurred_after": (base_time - timedelta(days=1, hours=3)).isoformat(),
            "occurred_before": (base_time - timedelta(hours=12)).isoformat(),
            "event_types": "care_update_logged",
        },
        headers=env["headers"],
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] == 1
    assert payload["items"][0]["display_title"] == mid_event["summary"]


def test_patient_timeline_filter_by_related_escalation_id(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-escalation-filter")
    first_signal = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = first_signal["escalation"]["id"]
    task_id = _create_task(client, env["headers"], escalation_id)
    _complete_task_with_outcome(client, env["headers"], task_id)
    _create_care_update(client, env["headers"], env["patient_id"])
    # Create second signal to ensure unrelated events exist
    _create_signal(client, env["headers"], env["patient_id"])

    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"related_escalation_id": escalation_id},
        headers=env["headers"],
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] >= 2
    assert {item["related_escalation_id"] for item in payload["items"]} == {escalation_id}


def test_patient_timeline_filter_by_related_task_id(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-task-filter")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    task_id = _create_task(client, env["headers"], escalation_id)
    outcome = _complete_task_with_outcome(client, env["headers"], task_id)
    _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        intervention_task_outcome_id=outcome["id"],
    )

    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"related_task_id": task_id},
        headers=env["headers"],
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] >= 2
    assert {item["related_task_id"] for item in payload["items"]} == {task_id}


def test_patient_timeline_filter_by_task_status_single(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-task-status-single")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    open_task_id = _create_task(client, env["headers"], escalation_id, title="Keep Open")
    closed_task_id = _create_task(client, env["headers"], escalation_id, title="Will Close")
    _complete_task_with_outcome(client, env["headers"], closed_task_id)

    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params=[
            ("event_types", "intervention_task_created"),
            ("task_statuses", "open"),
        ],
        headers=env["headers"],
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["items"]
    assert {item["related_task_id"] for item in payload["items"]} == {open_task_id}


def test_patient_timeline_filter_by_multiple_task_statuses(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-task-status-multi")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    open_task_id = _create_task(client, env["headers"], escalation_id, title="Open Item")
    completed_task_id = _create_task(client, env["headers"], escalation_id, title="Done Item")
    _complete_task_with_outcome(client, env["headers"], completed_task_id)

    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params=[
            ("event_types", "intervention_task_created"),
            ("task_statuses", "open"),
            ("task_statuses", "completed"),
        ],
        headers=env["headers"],
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert {item["related_task_id"] for item in payload["items"]} == {open_task_id, completed_task_id}


def test_patient_timeline_task_status_filter_validates_values(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-task-status-invalid")

    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"task_statuses": "not-a-status"},
        headers=env["headers"],
    )
    assert resp.status_code == 422


def test_patient_timeline_task_status_filter_applies_to_outcome_events(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-task-status-outcomes")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    task_id = _create_task(client, env["headers"], escalation_id, title="Outcome Task")
    outcome = _complete_task_with_outcome(client, env["headers"], task_id)
    _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        intervention_task_outcome_id=outcome["id"],
    )

    outcome_resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params=[
            ("event_types", "intervention_task_outcome_logged"),
            ("task_statuses", "completed"),
        ],
        headers=env["headers"],
    )
    assert outcome_resp.status_code == 200
    outcome_payload = outcome_resp.json()
    assert {item["related_task_id"] for item in outcome_payload["items"]} == {task_id}

    care_update_resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params=[
            ("event_types", "care_update_logged"),
            ("task_statuses", "completed"),
        ],
        headers=env["headers"],
    )
    assert care_update_resp.status_code == 200
    care_update_payload = care_update_resp.json()
    assert care_update_payload["items"]
    assert {item["related_task_id"] for item in care_update_payload["items"]} == {task_id}

    open_filtered = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params=[
            ("event_types", "intervention_task_outcome_logged"),
            ("task_statuses", "open"),
        ],
        headers=env["headers"],
    )
    assert open_filtered.status_code == 200
    assert open_filtered.json()["items"] == []


def test_patient_timeline_include_only_open_work_filters_results(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-open-work")
    first_signal = _create_signal(client, env["headers"], env["patient_id"])
    first_escalation_id = first_signal["escalation"]["id"]
    open_task_id = _create_task(client, env["headers"], first_escalation_id, title="Stay Open")

    second_signal = _create_signal(client, env["headers"], env["patient_id"])
    second_escalation_id = second_signal["escalation"]["id"]
    closed_task_id = _create_task(client, env["headers"], second_escalation_id, title="Close Me")
    outcome = _complete_task_with_outcome(client, env["headers"], closed_task_id)
    _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        intervention_task_outcome_id=outcome["id"],
    )
    resolve_resp = client.post(
        f"/api/v1/escalations/{second_escalation_id}/resolve",
        json={"resolution_notes": "handled"},
        headers=env["headers"],
    )
    assert resolve_resp.status_code == 200

    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"include_only_open_work": "true"},
        headers=env["headers"],
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["items"]
    assert all(
        item.get("related_escalation_id") == first_escalation_id
        or item.get("related_task_id") == open_task_id
        for item in payload["items"]
    )
def test_patient_timeline_summary_reflects_filters(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-summary-filter")
    _create_signal(client, env["headers"], env["patient_id"])
    _create_care_update(client, env["headers"], env["patient_id"])
    params = [("event_types", "signal_recorded")]

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params=params,
        headers=env["headers"],
    )
    assert listing.status_code == 200
    summary = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/summary",
        params=params,
        headers=env["headers"],
    )
    assert summary.status_code == 200
    listing_payload = listing.json()
    summary_payload = summary.json()
    assert summary_payload["total"] == listing_payload["total"]
    assert summary_payload["counts"]["signal_recorded"] == listing_payload["total"]
    assert summary_payload["counts"]["care_update_logged"] == 0


def test_patient_timeline_filtered_results_are_ordered(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-ordered-filter")
    base_time = datetime.now(timezone.utc)
    for offset in range(3):
        _create_care_update(
            client,
            env["headers"],
            env["patient_id"],
            summary=f"ordered-{offset}",
            occurred_at=base_time - timedelta(hours=offset),
        )

    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"event_types": "care_update_logged"},
        headers=env["headers"],
    )
    assert resp.status_code == 200
    payload = resp.json()
    occurred = [_parse_occurred_at(item["occurred_at"]) for item in payload["items"]]
    assert occurred == sorted(occurred, reverse=True)


def test_patient_timeline_read_state_defaults_to_total_unread(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-read-state-default")
    base_time = datetime.now(timezone.utc)
    for idx in range(2):
        _create_care_update(
            client,
            env["headers"],
            env["patient_id"],
            summary=f"note-{idx}",
            occurred_at=base_time - timedelta(minutes=idx),
        )

    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state",
        headers=env["headers"],
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["last_read_event_id"] is None
    assert payload["unread_count"] == 2
    assert payload["newest_event_id"] is not None


def test_patient_timeline_read_state_update_persists_marker_metadata(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-read-state-update")
    base_time = datetime.now(timezone.utc)
    for idx in range(3):
        _create_care_update(
            client,
            env["headers"],
            env["patient_id"],
            summary=f"state-{idx}",
            occurred_at=base_time - timedelta(minutes=idx),
        )

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    )
    assert listing.status_code == 200
    target_event = listing.json()["items"][1]

    resp = client.put(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state",
        json={"last_read_event_id": target_event["event_id"]},
        headers=env["headers"],
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["last_read_event_id"] == target_event["event_id"]
    assert payload["last_read_occurred_at"] == target_event["occurred_at"]
    assert payload["unread_count"] == 1


def test_patient_timeline_read_state_update_newest_event_zero_unread(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-read-state-newest")
    base_time = datetime.now(timezone.utc)
    for idx in range(2):
        _create_care_update(
            client,
            env["headers"],
            env["patient_id"],
            summary=f"newest-{idx}",
            occurred_at=base_time - timedelta(minutes=idx),
        )

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    ).json()
    newest_event = listing["items"][0]

    resp = client.put(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state",
        json={"last_read_event_id": newest_event["event_id"]},
        headers=env["headers"],
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["unread_count"] == 0


def test_patient_timeline_read_state_rejects_invalid_event_id(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-read-state-invalid")
    resp = client.put(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state",
        json={"last_read_event_id": "signal:00000000-0000-0000-0000-000000000000"},
        headers=env["headers"],
    )
    assert resp.status_code == 422


def test_patient_timeline_read_state_rejects_cross_patient_event_id(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-read-state-cross")
    other_patient_id = create_patient_for_user(client, env["headers"], first_name="other-patient")
    _create_care_update(client, env["headers"], other_patient_id)

    other_listing = client.get(
        f"/api/v1/patients/{other_patient_id}/timeline",
        headers=env["headers"],
    ).json()
    other_event_id = other_listing["items"][0]["event_id"]

    resp = client.put(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state",
        json={"last_read_event_id": other_event_id},
        headers=env["headers"],
    )
    assert resp.status_code == 422


def test_patient_timeline_read_state_isolated_per_user(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-read-state-per-user")
    _create_care_update(client, env["headers"], env["patient_id"])

    org = env["organization"]
    second_user = create_user_for_org(
        db_session,
        organization=org,
        email="timeline-reader@example.com",
        password="Secret123!",
    )
    second_headers = auth_headers(client, second_user.email, "Secret123!")

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    ).json()
    event_id = listing["items"][0]["event_id"]

    update_resp = client.put(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state",
        json={"last_read_event_id": event_id},
        headers=env["headers"],
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["unread_count"] == 0

    second_state = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state",
        headers=second_headers,
    )
    assert second_state.status_code == 200
    assert second_state.json()["last_read_event_id"] is None
    assert second_state.json()["unread_count"] == len(listing["items"])


def test_patient_timeline_mark_through_event_sets_marker(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-targeted-mark")
    base_time = datetime.now(timezone.utc)
    for idx in range(3):
        _create_care_update(
            client,
            env["headers"],
            env["patient_id"],
            summary=f"targeted-{idx}",
            occurred_at=base_time - timedelta(minutes=idx),
        )

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    ).json()["items"]
    target_event = listing[1]

    mark_resp = client.post(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/mark-through",
        json={"event_id": target_event["event_id"]},
        headers=env["headers"],
    )
    assert mark_resp.status_code == 200
    payload = mark_resp.json()
    assert payload["last_read_event_id"] == target_event["event_id"]
    assert payload["unread_count"] == 1

    persisted = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state",
        headers=env["headers"],
    ).json()
    assert persisted["last_read_event_id"] == target_event["event_id"]


def test_patient_timeline_mark_through_event_rejects_missing_event(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-targeted-mark-missing")
    resp = client.post(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/mark-through",
        json={"event_id": "signal:00000000-0000-0000-0000-000000000000"},
        headers=env["headers"],
    )
    assert resp.status_code == 422


def test_patient_timeline_mark_all_read_sets_newest_marker(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-read-state-mark-all")
    base_time = datetime.now(timezone.utc)
    for idx in range(3):
        _create_care_update(
            client,
            env["headers"],
            env["patient_id"],
            summary=f"mark-{idx}",
            occurred_at=base_time - timedelta(minutes=idx),
        )

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    ).json()
    newest_event = listing["items"][0]

    resp = client.post(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/mark-all-read",
        headers=env["headers"],
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["last_read_event_id"] == newest_event["event_id"]
    assert payload["unread_count"] == 0


def test_patient_timeline_mark_all_read_without_events_returns_empty_state(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-read-state-empty-mark")
    resp = client.post(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/mark-all-read",
        headers=env["headers"],
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["unread_count"] == 0
    assert payload["last_read_event_id"] is None


def test_patient_timeline_read_state_cross_org_forbidden(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-read-state-scope")
    other_org = create_organization_record(db_session, slug="timeline-read-org")
    other_user = create_user_for_org(
        db_session,
        organization=other_org,
        email="timeline-read-other@example.com",
        password="Secret123!",
    )
    other_headers = auth_headers(client, other_user.email, "Secret123!")

    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state",
        headers=other_headers,
    )
    assert resp.status_code == 403


def test_patient_timeline_filtered_read_state_subset_unread_counts(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-read-filtered-unread")
    base_time = datetime.now(timezone.utc)
    _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="filtered-old",
        occurred_at=base_time - timedelta(minutes=10),
    )
    _create_signal(
        client,
        env["headers"],
        env["patient_id"],
        recorded_at=base_time - timedelta(minutes=5),
    )
    _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="filtered-new",
        occurred_at=base_time - timedelta(minutes=1),
    )

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    ).json()
    signal_event_id = next(
        item["event_id"] for item in listing["items"] if item["event_type"] == "signal_recorded"
    )

    mark_resp = client.put(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state",
        json={"last_read_event_id": signal_event_id},
        headers=env["headers"],
    )
    assert mark_resp.status_code == 200

    filtered_resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/filtered",
        params=[("event_types", "care_update_logged")],
        headers=env["headers"],
    )
    assert filtered_resp.status_code == 200
    filtered_payload = filtered_resp.json()
    assert filtered_payload["unread_count"] == 1

    care_updates = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params=[("event_types", "care_update_logged")],
        headers=env["headers"],
    ).json()
    assert care_updates["items"]
    assert filtered_payload["newest_event_id"] == care_updates["items"][0]["event_id"]


def test_patient_timeline_filtered_mark_read_preview_matches_filtered_state(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-mark-preview")
    _create_signal(client, env["headers"], env["patient_id"])
    _create_care_update(client, env["headers"], env["patient_id"])

    baseline = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/filtered",
        params=[("event_types", "care_update_logged")],
        headers=env["headers"],
    )
    assert baseline.status_code == 200
    preview = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/filtered/preview",
        params=[("event_types", "care_update_logged")],
        headers=env["headers"],
    )
    assert preview.status_code == 200
    assert preview.json() == baseline.json()

    persisted = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state",
        headers=env["headers"],
    ).json()
    assert persisted["last_read_event_id"] is None


def test_patient_timeline_filter_snapshot_without_filters(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-snapshot-all")
    base_time = datetime.now(timezone.utc)
    for idx in range(3):
        _create_care_update(
            client,
            env["headers"],
            env["patient_id"],
            summary=f"snapshot-{idx}",
            occurred_at=base_time - timedelta(minutes=idx),
        )

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    ).json()
    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/filter-set/snapshot",
        headers=env["headers"],
    )
    assert resp.status_code == 200
    snapshot = resp.json()
    assert snapshot["patient_id"] == env["patient_id"]
    assert snapshot["total"] == listing["total"]
    assert snapshot["newest_event_id"] == listing["items"][0]["event_id"]
    assert snapshot["oldest_event_id"] == listing["items"][-1]["event_id"]
    assert snapshot["latest_workflow_event_id"] == snapshot["newest_event_id"]


def test_patient_timeline_filter_snapshot_scoped_by_escalation(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-snapshot-escalation")
    first_signal = _create_signal(client, env["headers"], env["patient_id"])
    second_signal = _create_signal(client, env["headers"], env["patient_id"])
    first_escalation_id = first_signal["escalation"]["id"]
    _create_task(client, env["headers"], first_escalation_id, title="Esc Snapshot Task")
    _create_task(client, env["headers"], second_signal["escalation"]["id"], title="Other Esc Snapshot")

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"related_escalation_id": first_escalation_id},
        headers=env["headers"],
    ).json()
    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/filter-set/snapshot",
        params={"related_escalation_id": first_escalation_id},
        headers=env["headers"],
    )
    assert resp.status_code == 200
    snapshot = resp.json()
    assert snapshot["total"] == listing["total"]
    assert snapshot["newest_event_id"] == listing["items"][0]["event_id"]


def test_patient_timeline_filter_snapshot_scoped_by_task(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-snapshot-task")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    task_id = _create_task(client, env["headers"], escalation_id, title="Snapshot Task")
    _complete_task_with_outcome(client, env["headers"], task_id)

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"related_task_id": task_id},
        headers=env["headers"],
    ).json()
    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/filter-set/snapshot",
        params={"related_task_id": task_id},
        headers=env["headers"],
    )
    assert resp.status_code == 200
    snapshot = resp.json()
    assert snapshot["total"] == listing["total"]
    assert snapshot["oldest_event_id"] == listing["items"][-1]["event_id"]


def test_patient_timeline_filter_snapshot_by_task_statuses(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-snapshot-status")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    open_task_id = _create_task(client, env["headers"], escalation_id, title="Snapshot Open Task")
    closed_task_id = _create_task(client, env["headers"], escalation_id, title="Snapshot Closed Task")
    _complete_task_with_outcome(client, env["headers"], closed_task_id)
    assert open_task_id

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params=[("task_statuses", "completed")],
        headers=env["headers"],
    ).json()
    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/filter-set/snapshot",
        params=[("task_statuses", "completed")],
        headers=env["headers"],
    )
    assert resp.status_code == 200
    snapshot = resp.json()
    assert snapshot["total"] == listing["total"]
    assert snapshot["unread_count"] == listing["total"]


def test_patient_timeline_filter_snapshot_include_only_open_work(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-snapshot-open-work")
    open_signal = _create_signal(client, env["headers"], env["patient_id"])
    open_escalation_id = open_signal["escalation"]["id"]
    _create_task(client, env["headers"], open_escalation_id, title="Snapshot Open Work Task")

    closed_signal = _create_signal(client, env["headers"], env["patient_id"])
    closed_escalation_id = closed_signal["escalation"]["id"]
    closed_task_id = _create_task(client, env["headers"], closed_escalation_id, title="Snapshot Closed Work Task")
    _complete_task_with_outcome(client, env["headers"], closed_task_id)
    client.post(
        f"/api/v1/escalations/{closed_escalation_id}/resolve",
        json={"resolution_notes": "done"},
        headers=env["headers"],
    )

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"include_only_open_work": "true"},
        headers=env["headers"],
    ).json()
    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/filter-set/snapshot",
        params={"include_only_open_work": "true"},
        headers=env["headers"],
    )
    assert resp.status_code == 200
    snapshot = resp.json()
    assert snapshot["total"] == listing["total"]
    assert snapshot["unread_count"] == len(listing["items"])


def test_patient_timeline_filter_snapshot_empty_subset(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-snapshot-empty")
    _create_care_update(client, env["headers"], env["patient_id"])
    future_time = datetime.now(timezone.utc) + timedelta(days=1)

    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/filter-set/snapshot",
        params={"occurred_after": future_time.isoformat()},
        headers=env["headers"],
    )
    assert resp.status_code == 200
    snapshot = resp.json()
    assert snapshot["total"] == 0
    assert snapshot["newest_event_id"] is None
    assert snapshot["oldest_event_id"] is None


def test_patient_timeline_filter_snapshot_validation_errors(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-snapshot-validation")
    other_patient_id = create_patient_for_user(client, env["headers"], first_name="snapshot-other")
    other_signal = _create_signal(client, env["headers"], other_patient_id)
    other_escalation_id = other_signal["escalation"]["id"]
    other_task_id = _create_task(client, env["headers"], other_escalation_id, title="Snapshot Other Task")

    missing_resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/filter-set/snapshot",
        params={"related_escalation_id": other_escalation_id},
        headers=env["headers"],
    )
    assert missing_resp.status_code == 404

    patient_signal_one = _create_signal(client, env["headers"], env["patient_id"])
    patient_signal_two = _create_signal(client, env["headers"], env["patient_id"])
    patient_task = _create_task(client, env["headers"], patient_signal_two["escalation"]["id"])

    mismatch_resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/filter-set/snapshot",
        params={
            "related_escalation_id": patient_signal_one["escalation"]["id"],
            "related_task_id": patient_task,
        },
        headers=env["headers"],
    )
    assert mismatch_resp.status_code == 422


def test_patient_timeline_filter_snapshot_same_timestamp_ordering(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-snapshot-tie")
    occurred_at = datetime.now(timezone.utc)
    for idx in range(3):
        _create_care_update(
            client,
            env["headers"],
            env["patient_id"],
            summary=f"snapshot-tie-{idx}",
            occurred_at=occurred_at,
        )

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"event_types": "care_update_logged"},
        headers=env["headers"],
    ).json()
    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/filter-set/snapshot",
        params={"event_types": "care_update_logged"},
        headers=env["headers"],
    )
    assert resp.status_code == 200
    snapshot = resp.json()
    assert snapshot["newest_event_id"] == listing["items"][0]["event_id"]
    assert snapshot["oldest_event_id"] == listing["items"][-1]["event_id"]


def test_patient_timeline_inbox_summary_empty(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-inbox-empty")
    summary = _get_inbox_summary(client, env["headers"], env["patient_id"])
    assert summary["patient_id"] == env["patient_id"]
    assert summary["has_unread_events"] is False
    assert summary["unread_count"] == 0
    assert summary["total_events"] == 0
    assert summary["latest_event_id"] is None
    assert summary["latest_unread_event_id"] is None
    assert summary["oldest_unread_event_id"] is None


def test_patient_timeline_inbox_summary_all_unread(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-inbox-unread")
    base_time = datetime.now(timezone.utc)
    for idx in range(3):
        _create_care_update(
            client,
            env["headers"],
            env["patient_id"],
            summary=f"inbox-{idx}",
            occurred_at=base_time - timedelta(minutes=idx),
        )

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    ).json()
    summary = _get_inbox_summary(client, env["headers"], env["patient_id"])

    assert summary["total_events"] == listing["total"] == 3
    assert summary["unread_count"] == summary["total_events"]
    assert summary["has_unread_events"] is True
    assert summary["latest_event_id"] == listing["items"][0]["event_id"]
    assert summary["latest_event_title"] == listing["items"][0]["display_title"]
    assert summary["latest_unread_event_id"] == summary["latest_event_id"]
    assert summary["oldest_unread_event_id"] == listing["items"][-1]["event_id"]


def test_patient_timeline_inbox_summary_partial_read_state(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-inbox-partial")
    base_time = datetime.now(timezone.utc)
    for idx in range(3):
        _create_care_update(
            client,
            env["headers"],
            env["patient_id"],
            summary=f"partial-{idx}",
            occurred_at=base_time - timedelta(minutes=idx),
        )

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    ).json()
    second_event_id = listing["items"][1]["event_id"]

    mark_resp = client.post(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/mark-through",
        json={"event_id": second_event_id},
        headers=env["headers"],
    )
    assert mark_resp.status_code == 200

    summary = _get_inbox_summary(client, env["headers"], env["patient_id"])
    assert summary["has_unread_events"] is True
    assert summary["unread_count"] == 1
    assert summary["latest_event_id"] == listing["items"][0]["event_id"]
    assert summary["latest_unread_event_id"] == listing["items"][0]["event_id"]
    assert summary["oldest_unread_event_id"] == listing["items"][0]["event_id"]
    assert summary["total_events"] == listing["total"]


def test_patient_timeline_inbox_summary_all_read_still_returns_latest_event(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-inbox-all-read")
    base_time = datetime.now(timezone.utc)
    for idx in range(2):
        _create_care_update(
            client,
            env["headers"],
            env["patient_id"],
            summary=f"read-{idx}",
            occurred_at=base_time - timedelta(minutes=idx),
        )

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    ).json()
    mark_all = client.post(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/mark-all-read",
        headers=env["headers"],
    )
    assert mark_all.status_code == 200

    summary = _get_inbox_summary(client, env["headers"], env["patient_id"])
    assert summary["has_unread_events"] is False
    assert summary["unread_count"] == 0
    assert summary["latest_event_id"] == listing["items"][0]["event_id"]
    assert summary["latest_unread_event_id"] is None
    assert summary["oldest_unread_event_id"] is None


def test_patient_timeline_inbox_summary_filtered_subset(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-inbox-filtered")
    first_signal = _create_signal(client, env["headers"], env["patient_id"])
    first_escalation_id = first_signal["escalation"]["id"]
    _create_task(client, env["headers"], first_escalation_id, title="Inbox Filter Task")
    _create_care_update(client, env["headers"], env["patient_id"], summary="Filter Note")

    second_signal = _create_signal(client, env["headers"], env["patient_id"])
    second_escalation_id = second_signal["escalation"]["id"]
    _create_task(client, env["headers"], second_escalation_id, title="Other Task")

    scoped_listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"related_escalation_id": first_escalation_id},
        headers=env["headers"],
    )
    assert scoped_listing.status_code == 200
    scoped_items = scoped_listing.json()["items"]
    assert scoped_items

    summary = _get_inbox_summary(
        client,
        env["headers"],
        env["patient_id"],
        params={"related_escalation_id": first_escalation_id},
    )
    assert summary["total_events"] == len(scoped_items)
    assert summary["unread_count"] == len(scoped_items)
    assert summary["latest_event_id"] == scoped_items[0]["event_id"]
    assert summary["latest_unread_event_id"] == scoped_items[0]["event_id"]


def test_patient_timeline_inbox_summary_invalid_filters(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-inbox-invalid")
    other_patient_id = create_patient_for_user(client, env["headers"], first_name="timeline-inbox-other")
    other_signal = _create_signal(client, env["headers"], other_patient_id)
    other_escalation_id = other_signal["escalation"]["id"]
    other_task_id = _create_task(client, env["headers"], other_escalation_id, title="Inbox Other Task")

    esc_resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/inbox-summary",
        params={"related_escalation_id": other_escalation_id},
        headers=env["headers"],
    )
    assert esc_resp.status_code == 404

    task_resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/inbox-summary",
        params={"related_task_id": other_task_id},
        headers=env["headers"],
    )
    assert task_resp.status_code == 404

    first_signal = _create_signal(client, env["headers"], env["patient_id"])
    first_escalation_id = first_signal["escalation"]["id"]
    second_signal = _create_signal(client, env["headers"], env["patient_id"])
    second_escalation_id = second_signal["escalation"]["id"]
    second_task_id = _create_task(client, env["headers"], second_escalation_id, title="Inbox Mismatch Task")

    mismatch_resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/inbox-summary",
        params={"related_escalation_id": first_escalation_id, "related_task_id": second_task_id},
        headers=env["headers"],
    )
    assert mismatch_resp.status_code == 422


def test_patient_timeline_inbox_summary_identical_timestamps(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-inbox-tie")
    occurred_at = datetime.now(timezone.utc)
    for idx in range(4):
        _create_care_update(
            client,
            env["headers"],
            env["patient_id"],
            summary=f"inbox-tie-{idx}",
            occurred_at=occurred_at,
        )

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    ).json()

    summary = _get_inbox_summary(client, env["headers"], env["patient_id"])
    assert summary["latest_event_id"] == listing["items"][0]["event_id"]
    assert summary["latest_unread_event_id"] == listing["items"][0]["event_id"]
    assert summary["oldest_unread_event_id"] == listing["items"][-1]["event_id"]


def test_patient_timeline_inbox_summary_matches_filtered_read_state_counts(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-inbox-read-match")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    open_task_id = _create_task(client, env["headers"], escalation_id, title="Inbox Match Task")
    _create_care_update(client, env["headers"], env["patient_id"], summary="Match Care Update")

    mark_resp = client.post(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/filtered/mark-through",
        params={"related_escalation_id": escalation_id},
        json={"event_id": f"intervention_task:{open_task_id}"},
        headers=env["headers"],
    )
    assert mark_resp.status_code == 200

    read_state = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/filtered",
        params={"related_escalation_id": escalation_id},
        headers=env["headers"],
    ).json()

    summary = _get_inbox_summary(
        client,
        env["headers"],
        env["patient_id"],
        params={"related_escalation_id": escalation_id},
    )

    assert summary["unread_count"] == read_state["unread_count"]
    assert summary["latest_event_id"] == read_state["newest_event_id"]


def test_patient_timeline_worklist_summary_empty_org(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_user_without_patient(client, db_session, slug="worklist-empty")
    payload = _get_worklist_summary(client, env["headers"])
    assert payload["total"] == 0
    assert payload["items"] == []
    assert payload["impact_snapshot"] == {
        "patients_needing_attention": 0,
        "open_escalations": 0,
        "tasks_in_progress": 0,
        "completed_tasks_recently": 0,
        "completed_tasks_recently_window_days": 7,
        "operational_summary": "Queue is currently quiet.",
    }


def test_patient_timeline_worklist_summary_impact_snapshot_counts_mixed_queue(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-impact-mixed")
    second_patient_id = create_patient_for_user(client, env["headers"], first_name="worklist-impact-second")
    third_patient_id = create_patient_for_user(client, env["headers"], first_name="worklist-impact-third")

    active_signal = _create_signal(client, env["headers"], env["patient_id"])
    active_task_id = _create_task(
        client,
        env["headers"],
        active_signal["escalation"]["id"],
        title="Active outreach",
    )
    start_resp = client.post(f"/api/v1/tasks/{active_task_id}/start", headers=env["headers"])
    assert start_resp.status_code == 200

    completed_signal = _create_signal(client, env["headers"], second_patient_id)
    completed_task_id = _create_task(
        client,
        env["headers"],
        completed_signal["escalation"]["id"],
        title="Completed outreach",
    )
    _complete_task_with_outcome(client, env["headers"], completed_task_id)
    resolve_resp = client.post(
        f"/api/v1/escalations/{completed_signal['escalation']['id']}/resolve",
        json={"resolution_notes": "closed"},
        headers=env["headers"],
    )
    assert resolve_resp.status_code == 200

    _create_care_update(client, env["headers"], third_patient_id, summary="Routine update")

    payload = _get_worklist_summary(client, env["headers"])
    snapshot = payload["impact_snapshot"]

    assert payload["total"] == 3
    assert snapshot["patients_needing_attention"] == 1
    assert snapshot["open_escalations"] == 1
    assert snapshot["tasks_in_progress"] == 1
    assert snapshot["completed_tasks_recently"] == 1
    assert snapshot["completed_tasks_recently_window_days"] == 7
    assert snapshot["operational_summary"] == "Queue has active work requiring follow-up."


def test_patient_timeline_worklist_summary_impact_snapshot_recent_completed_window(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-impact-recent")
    old_patient_id = create_patient_for_user(client, env["headers"], first_name="worklist-impact-old")

    recent_signal = _create_signal(client, env["headers"], env["patient_id"])
    recent_task_id = _create_task(client, env["headers"], recent_signal["escalation"]["id"])
    _complete_task_with_outcome(client, env["headers"], recent_task_id)

    old_signal = _create_signal(client, env["headers"], old_patient_id)
    old_task_id = _create_task(client, env["headers"], old_signal["escalation"]["id"])
    _complete_task_with_outcome(client, env["headers"], old_task_id)
    old_task = db_session.get(InterventionTask, uuid.UUID(old_task_id))
    assert old_task is not None
    old_task.completed_at = datetime.now(timezone.utc) - timedelta(days=8)
    db_session.add(old_task)
    db_session.commit()

    payload = _get_worklist_summary(client, env["headers"])

    assert payload["impact_snapshot"]["completed_tasks_recently"] == 1


def test_patient_timeline_worklist_summary_impact_snapshot_low_activity(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-impact-low")
    _create_care_update(client, env["headers"], env["patient_id"], summary="Stable check-in")

    payload = _get_worklist_summary(client, env["headers"])
    snapshot = payload["impact_snapshot"]

    assert snapshot["patients_needing_attention"] == 0
    assert snapshot["open_escalations"] == 0
    assert snapshot["tasks_in_progress"] == 0
    assert snapshot["completed_tasks_recently"] == 0
    assert snapshot["operational_summary"] == "Queue is currently quiet."


def test_patient_timeline_worklist_summary_includes_patients_without_events(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-no-events")
    second_patient_id = create_patient_for_user(client, env["headers"], first_name="worklist-second")

    payload = _get_worklist_summary(client, env["headers"])
    assert payload["total"] >= 2
    summary_map = {item["patient_id"]: item for item in payload["items"]}
    assert env["patient_id"] in summary_map
    assert second_patient_id in summary_map
    assert summary_map[env["patient_id"]]["total_events"] == 0
    assert summary_map[second_patient_id]["total_events"] == 0


def test_patient_timeline_worklist_summary_escalations_absent_when_none_exist(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-no-escalations")
    payload = _get_worklist_summary(client, env["headers"])
    row = _find_worklist_item(payload, env["patient_id"])

    assert row["open_escalation_count"] == 0
    assert row["overdue_escalation_count"] == 0
    assert row["at_risk_escalation_count"] == 0
    assert row["highest_escalation_priority"] is None
    assert row["next_escalation_sla_due_at"] is None
    assert row["latest_open_escalation_id"] is None


def test_patient_timeline_worklist_summary_single_open_escalation_without_sla(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-one-escalation")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"], escalation_sla_due_at=None)
    escalation = signal_payload["escalation"]

    payload = _get_worklist_summary(client, env["headers"])
    row = _find_worklist_item(payload, env["patient_id"])

    assert row["open_escalation_count"] == 1
    assert row["overdue_escalation_count"] == 0
    assert row["at_risk_escalation_count"] == 0
    assert row["highest_escalation_priority"] == escalation["severity"]
    assert row["next_escalation_sla_due_at"] is None
    assert row["latest_open_escalation_id"] == escalation["id"]


def test_patient_timeline_worklist_summary_classifies_sla_states_and_priority(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-escalation-states")
    now = datetime.now(timezone.utc)

    overdue = _create_signal(
        client,
        env["headers"],
        env["patient_id"],
        recorded_at=now - timedelta(hours=3),
        escalation_sla_due_at=now - timedelta(minutes=30),
    )["escalation"]
    at_risk = _create_signal(
        client,
        env["headers"],
        env["patient_id"],
        recorded_at=now - timedelta(hours=2),
        escalation_sla_due_at=now + timedelta(hours=2),
        signal_type="missed_check_in",
        signal_value_numeric=None,
    )["escalation"]
    future = _create_signal(
        client,
        env["headers"],
        env["patient_id"],
        recorded_at=now - timedelta(hours=1),
        escalation_sla_due_at=now + timedelta(hours=30),
    )["escalation"]
    latest = _create_signal(
        client,
        env["headers"],
        env["patient_id"],
        recorded_at=now,
        escalation_sla_due_at=None,
    )["escalation"]

    payload = _get_worklist_summary(client, env["headers"])
    row = _find_worklist_item(payload, env["patient_id"])

    assert row["open_escalation_count"] == 4
    assert row["overdue_escalation_count"] == 1
    assert row["at_risk_escalation_count"] == 1
    assert row["latest_open_escalation_id"] == latest["id"]
    assert row["highest_escalation_priority"] == overdue["severity"]
    assert _parse_occurred_at(row["next_escalation_sla_due_at"]) == _parse_occurred_at(overdue["sla_due_at"])
    assert _parse_occurred_at(future["sla_due_at"]) > _parse_occurred_at(row["next_escalation_sla_due_at"])
    assert at_risk["id"] != latest["id"]


def test_patient_timeline_worklist_summary_excludes_closed_escalations(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-closed-escalations")
    open_escalation = _create_signal(
        client,
        env["headers"],
        env["patient_id"],
        escalation_sla_due_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )["escalation"]
    closed_escalation = _create_signal(
        client,
        env["headers"],
        env["patient_id"],
        recorded_at=datetime.now(timezone.utc) + timedelta(minutes=1),
        escalation_sla_due_at=datetime.now(timezone.utc) + timedelta(hours=2),
    )["escalation"]
    _update_escalation_status(
        client,
        env["headers"],
        closed_escalation["id"],
        status="resolved",
    )

    payload = _get_worklist_summary(client, env["headers"])
    row = _find_worklist_item(payload, env["patient_id"])

    assert row["open_escalation_count"] == 1
    assert row["overdue_escalation_count"] == 0
    assert row["latest_open_escalation_id"] == open_escalation["id"]
    assert _parse_occurred_at(row["next_escalation_sla_due_at"]) == _parse_occurred_at(
        open_escalation["sla_due_at"]
    )


def test_patient_timeline_worklist_summary_escalation_fields_multi_patient_scope(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-multi-escalation")
    second_patient_id = create_patient_for_user(client, env["headers"], first_name="worklist-multi-second")
    _create_signal(client, env["headers"], env["patient_id"], escalation_sla_due_at=None)
    _create_signal(
        client,
        env["headers"],
        second_patient_id,
        escalation_sla_due_at=datetime.now(timezone.utc) + timedelta(hours=3),
    )

    payload = _get_worklist_summary(client, env["headers"])
    first_row = _find_worklist_item(payload, env["patient_id"])
    second_row = _find_worklist_item(payload, second_patient_id)

    assert first_row["open_escalation_count"] == 1
    assert second_row["open_escalation_count"] == 1
    assert first_row["next_escalation_sla_due_at"] is None
    assert second_row["next_escalation_sla_due_at"] is not None


def test_patient_timeline_worklist_summary_default_sorting_prioritizes_unread(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-sort")
    second_patient_id = create_patient_for_user(client, env["headers"], first_name="worklist-second")
    third_patient_id = create_patient_for_user(client, env["headers"], first_name="worklist-third")
    base_time = datetime.now(timezone.utc)

    _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="first patient event",
        occurred_at=base_time - timedelta(hours=2),
    )
    _create_care_update(
        client,
        env["headers"],
        second_patient_id,
        summary="second patient event",
        occurred_at=base_time - timedelta(hours=1),
    )
    _create_care_update(
        client,
        env["headers"],
        third_patient_id,
        summary="third patient event",
        occurred_at=base_time,
    )

    mark_resp = client.post(
        f"/api/v1/patients/{third_patient_id}/timeline/read-state/mark-all-read",
        headers=env["headers"],
    )
    assert mark_resp.status_code == 200

    payload = _get_worklist_summary(client, env["headers"])
    ids_in_order = [item["patient_id"] for item in payload["items"] if item["patient_id"] in {env["patient_id"], second_patient_id, third_patient_id}]
    assert ids_in_order[:3] == [second_patient_id, env["patient_id"], third_patient_id]
    assert payload["items"][0]["has_unread_events"] is True
    assert payload["items"][2]["has_unread_events"] is False


def test_patient_timeline_worklist_summary_pagination(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-page")
    extra_ids = [
        create_patient_for_user(client, env["headers"], first_name=f"worklist-page-{idx}")
        for idx in range(2)
    ]
    base_time = datetime.now(timezone.utc)
    for patient_id in [env["patient_id"], *extra_ids]:
        _create_care_update(
            client,
            env["headers"],
            patient_id,
            summary=f"event-{patient_id}",
            occurred_at=base_time - timedelta(minutes=len(extra_ids)),
        )

    payload = _get_worklist_summary(
        client,
        env["headers"],
        params={"skip": 1, "limit": 1},
    )
    assert payload["total"] == 3
    assert len(payload["items"]) == 1


def test_patient_timeline_worklist_summary_pagination_limits_processed_patients(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-page-limited")
    extra_ids = [
        create_patient_for_user(client, env["headers"], first_name=f"worklist-page-limited-{idx}")
        for idx in range(3)
    ]
    base_time = datetime.now(timezone.utc)
    for offset, patient_id in enumerate([env["patient_id"], *extra_ids]):
        _create_care_update(
            client,
            env["headers"],
            patient_id,
            summary=f"page-limited-{patient_id}",
            occurred_at=base_time - timedelta(minutes=offset),
        )

    call_count = 0
    original = read_state_service.get_sorted_patient_timeline_events

    def _tracking_get_sorted(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original(*args, **kwargs)

    event_call_count = 0
    original_event = read_state_service.get_patient_timeline_event

    def _tracking_get_event(*args, **kwargs):
        nonlocal event_call_count
        event_call_count += 1
        return original_event(*args, **kwargs)

    monkeypatch.setattr(
        read_state_service,
        "get_sorted_patient_timeline_events",
        _tracking_get_sorted,
    )
    monkeypatch.setattr(
        read_state_service,
        "get_patient_timeline_event",
        _tracking_get_event,
    )

    payload = _get_worklist_summary(
        client,
        env["headers"],
        params={"limit": 1},
    )
    assert payload["total"] == len(extra_ids) + 1
    assert len(payload["items"]) == 1
    assert call_count == 0
    assert 1 <= event_call_count <= 2


def test_patient_timeline_worklist_summary_general_path_avoids_full_hydration(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-general-fastpath")
    additional_ids = [
        create_patient_for_user(client, env["headers"], first_name=f"worklist-general-fastpath-{idx}")
        for idx in range(2)
    ]
    all_ids = [env["patient_id"], *additional_ids]
    base_time = datetime.now(timezone.utc)
    for offset, patient_id in enumerate(all_ids):
        _create_care_update(
            client,
            env["headers"],
            patient_id,
            summary=f"fastpath-{patient_id}",
            occurred_at=base_time - timedelta(minutes=offset),
        )

    def _fail_sorted(*args, **kwargs):
        raise AssertionError("general worklist path should not hydrate full timelines")

    original_get_event = read_state_service.get_patient_timeline_event
    event_count = 0

    def _tracking_get_event(*args, **kwargs):
        nonlocal event_count
        event_count += 1
        return original_get_event(*args, **kwargs)

    monkeypatch.setattr(
        read_state_service,
        "get_sorted_patient_timeline_events",
        _fail_sorted,
    )
    monkeypatch.setattr(
        read_state_service,
        "get_patient_timeline_event",
        _tracking_get_event,
    )

    payload = _get_worklist_summary(client, env["headers"])
    assert payload["total"] >= len(all_ids)
    assert event_count <= len(payload["items"]) * 2


def test_patient_timeline_worklist_summary_general_path_respects_skip_window(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-general-skip")
    additional_ids = [
        create_patient_for_user(client, env["headers"], first_name=f"worklist-general-skip-{idx}")
        for idx in range(3)
    ]
    base_time = datetime.now(timezone.utc)
    for offset, patient_id in enumerate([env["patient_id"], *additional_ids]):
        _create_care_update(
            client,
            env["headers"],
            patient_id,
            summary=f"skip-{patient_id}",
            occurred_at=base_time - timedelta(minutes=offset),
        )

    def _fail_sorted(*args, **kwargs):  # pragma: no cover
        raise AssertionError("later-page general path should not hydrate full timelines")

    monkeypatch.setattr(
        read_state_service,
        "get_sorted_patient_timeline_events",
        _fail_sorted,
    )

    original_get_event = read_state_service.get_patient_timeline_event
    event_count = 0

    def _tracking_get_event(*args, **kwargs):
        nonlocal event_count
        event_count += 1
        return original_get_event(*args, **kwargs)

    monkeypatch.setattr(
        read_state_service,
        "get_patient_timeline_event",
        _tracking_get_event,
    )

    payload = _get_worklist_summary(
        client,
        env["headers"],
        params={"skip": 2, "limit": 1},
    )
    assert len(payload["items"]) == 1
    assert 1 <= event_count <= 2


def test_patient_timeline_worklist_summary_filtered_path_still_materializes(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-filtered-full")
    second_patient_id = create_patient_for_user(client, env["headers"], first_name="worklist-filtered-full")
    base_time = datetime.now(timezone.utc)
    for patient_id in (env["patient_id"], second_patient_id):
        _create_care_update(
            client,
            env["headers"],
            patient_id,
            summary=f"filtered-{patient_id}",
            occurred_at=base_time,
        )

    call_count = 0
    original_sorted = read_state_service.get_sorted_patient_timeline_events

    def _tracking_sorted(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original_sorted(*args, **kwargs)

    monkeypatch.setattr(
        read_state_service,
        "get_sorted_patient_timeline_events",
        _tracking_sorted,
    )

    payload = _get_worklist_summary(
        client,
        env["headers"],
        params={"event_types": "care_update_logged"},
    )
    assert payload["items"]
    assert call_count == len(payload["items"])


def test_patient_timeline_worklist_summary_deterministic_tie_breaker(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-tie")
    second_patient_id = create_patient_for_user(client, env["headers"], first_name="worklist-tie-second")
    occurred_at = datetime.now(timezone.utc)
    for patient_id in (env["patient_id"], second_patient_id):
        _create_care_update(
            client,
            env["headers"],
            patient_id,
            summary=f"tie-{patient_id}",
            occurred_at=occurred_at,
        )

    payload = _get_worklist_summary(
        client,
        env["headers"],
        params={"patient_ids": [env["patient_id"], second_patient_id]},
    )
    ids_in_order = [item["patient_id"] for item in payload["items"]]
    assert ids_in_order == sorted([env["patient_id"], second_patient_id])


def test_patient_timeline_worklist_summary_has_unread_filter(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-unread-filter")
    second_patient_id = create_patient_for_user(client, env["headers"], first_name="worklist-filter-second")
    _create_care_update(client, env["headers"], env["patient_id"])
    _create_care_update(client, env["headers"], second_patient_id)
    client.post(
        f"/api/v1/patients/{second_patient_id}/timeline/read-state/mark-all-read",
        headers=env["headers"],
    )
    payload = _get_worklist_summary(
        client,
        env["headers"],
        params={"has_unread_events": "true"},
    )
    assert payload["total"] == 1
    assert payload["items"][0]["patient_id"] == env["patient_id"]


def test_patient_timeline_worklist_summary_patient_ids_filter(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-ids")
    second_patient_id = create_patient_for_user(client, env["headers"], first_name="worklist-ids-second")
    third_patient_id = create_patient_for_user(client, env["headers"], first_name="worklist-ids-third")
    _create_care_update(client, env["headers"], env["patient_id"])
    _create_care_update(client, env["headers"], second_patient_id)
    _create_care_update(client, env["headers"], third_patient_id)

    payload = _get_worklist_summary(
        client,
        env["headers"],
        params=[("patient_ids", env["patient_id"]), ("patient_ids", third_patient_id)],
    )
    ids_in_order = [item["patient_id"] for item in payload["items"]]
    assert set(ids_in_order) == {env["patient_id"], third_patient_id}


def test_patient_timeline_worklist_summary_matches_inbox_summary_endpoint(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-inbox-parity")
    _create_care_update(client, env["headers"], env["patient_id"])
    worklist = _get_worklist_summary(client, env["headers"])
    row = next(item for item in worklist["items"] if item["patient_id"] == env["patient_id"])
    inbox = _get_inbox_summary(client, env["headers"], env["patient_id"])

    for field in (
        "has_unread_events",
        "unread_count",
        "total_events",
        "latest_event_id",
        "latest_event_type",
        "latest_event_occurred_at",
    ):
        assert row[field] == inbox[field]


def test_patient_timeline_worklist_summary_cross_org_scope(
    client: TestClient,
    db_session: Session,
) -> None:
    env_one = _bootstrap_patient_env(client, db_session, slug="worklist-scope-one")
    _create_care_update(client, env_one["headers"], env_one["patient_id"])

    env_two = _bootstrap_patient_env(client, db_session, slug="worklist-scope-two")
    _create_care_update(client, env_two["headers"], env_two["patient_id"])

    payload_one = _get_worklist_summary(client, env_one["headers"])
    ids_one = {item["patient_id"] for item in payload_one["items"]}
    assert env_one["patient_id"] in ids_one
    assert env_two["patient_id"] not in ids_one

    payload_two = _get_worklist_summary(client, env_two["headers"])
    ids_two = {item["patient_id"] for item in payload_two["items"]}
    assert env_two["patient_id"] in ids_two
    assert env_one["patient_id"] not in ids_two


def test_patient_workflow_status_worklist_summary_includes_status(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="workflow-status-worklist")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    overdue_due_at = datetime.now(timezone.utc) - timedelta(hours=5)
    _create_task(client, env["headers"], escalation_id, title="Queue task overdue", due_at=overdue_due_at)

    payload = _get_worklist_summary(client, env["headers"])
    row = _find_worklist_item(payload, env["patient_id"])
    status = row.get("workflow_status")
    assert status is not None
    assert status["status_key"] == "task_overdue"
    assert status["has_active_work"] is True
    assert row["attention_reason"] == "Task overdue"
    assert row["next_step"] == "Update task disposition"
    assert row["next_step_reason"] == "Task is overdue and needs disposition"
    assert row["active_owner_label"] == "Care team queue"
    assert row["waiting_on_label"] == "Task start"
    assert row["care_gap_label"] == "Task disposition overdue"
    assert row["blocking_issue_label"] == "Task not updated"
    assert row["resolution_target_label"] == "Update or close the task"
    assert row["closure_readiness_label"] == "Not ready for closure"
    assert row["resolution_confidence_label"] == "Low confidence"
    assert row["recommended_timeframe"] == "Today"
    assert row["priority_band"] == "High"
    assert row["priority_reason"] == "Task is overdue"
    assert row["status_snapshot"] == "High priority: task is overdue today"


def test_patient_worklist_attention_reason_open_escalation_without_task(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-attention-escalation")
    _create_signal(client, env["headers"], env["patient_id"])

    payload = _get_worklist_summary(client, env["headers"])
    row = _find_worklist_item(payload, env["patient_id"])

    assert row["attention_reason"] == "Open escalation, no active outreach"
    assert row["next_step"] == "Start outreach"
    assert row["next_step_reason"] == "Escalation is open and no active task exists"
    assert row["active_owner_label"] == "Clinical review"
    assert row["waiting_on_label"] == "Task creation"
    assert row["care_gap_label"] == "Outreach not started"
    assert row["blocking_issue_label"] == "No outreach started"
    assert row["resolution_target_label"] == "Start outreach and document action"
    assert row["closure_readiness_label"] == "Not ready for closure"
    assert row["resolution_confidence_label"] == "Low confidence"
    assert row["recommended_timeframe"] == "Within 24 hours"
    assert row["priority_band"] == "Medium"
    assert row["priority_reason"] == "Action is needed within 24 hours"
    assert row["status_snapshot"] == "Medium priority: action is needed within 24 hours"


def test_patient_worklist_attention_reason_in_progress_task(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-attention-progress")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    task_id = _create_task(client, env["headers"], signal_payload["escalation"]["id"])
    start_resp = client.post(
        f"/api/v1/tasks/{task_id}/start",
        headers=env["headers"],
    )
    assert start_resp.status_code == 200

    payload = _get_worklist_summary(client, env["headers"])
    row = _find_worklist_item(payload, env["patient_id"])
    detail_payload = _get_timeline_detail_payload(client, env["headers"], env["patient_id"])

    assert row["attention_reason"] == "Task in progress"
    assert row["next_step"] == "Continue active intervention"
    assert row["next_step_reason"] == "An intervention is already underway"
    assert row["active_owner_label"] == "Assigned care team"
    assert row["waiting_on_label"] == "Task completion"
    assert detail_payload["active_owner_label"] == row["active_owner_label"]
    assert detail_payload["waiting_on_label"] == row["waiting_on_label"]
    assert row["care_gap_label"] == "Intervention still in progress"
    assert row["blocking_issue_label"] == "Work not yet completed"
    assert row["resolution_target_label"] == "Complete the intervention"
    assert row["closure_readiness_label"] == "Not ready for closure"
    assert row["resolution_confidence_label"] == "Moderate confidence"
    assert row["recommended_timeframe"] == "Today"
    assert row["priority_band"] == "High"
    assert row["priority_reason"] == "Action is due today"
    assert row["status_snapshot"] == "High priority: action is due today"


def test_patient_worklist_blocking_issue_open_task_pending_work(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-blocking-open-task")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    _create_task(client, env["headers"], signal_payload["escalation"]["id"], title="Assigned outreach")

    payload = _get_worklist_summary(client, env["headers"])
    row = _find_worklist_item(payload, env["patient_id"])

    assert row["attention_reason"] == "Open task needs start/completion"
    assert row["next_step"] == "Complete assigned task"
    assert row["next_step_reason"] == "Assigned task is still open"
    assert row["active_owner_label"] == "Care team queue"
    assert row["waiting_on_label"] == "Task start"
    assert row["care_gap_label"] == "Assigned intervention not completed"
    assert row["blocking_issue_label"] == "Assigned task still open"
    assert row["resolution_target_label"] == "Finish the assigned intervention"
    assert row["closure_readiness_label"] == "Not ready for closure"
    assert row["resolution_confidence_label"] == "Low confidence"
    assert row["recommended_timeframe"] == "Within 24 hours"


def test_patient_worklist_attention_reason_recent_completion_monitor(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-attention-complete")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    task_id = _create_task(client, env["headers"], escalation_id)
    _complete_task_with_outcome(client, env["headers"], task_id)
    resolve_resp = client.post(
        f"/api/v1/escalations/{escalation_id}/resolve",
        json={"resolution_notes": "Handled"},
        headers=env["headers"],
    )
    assert resolve_resp.status_code == 200

    payload = _get_worklist_summary(client, env["headers"])
    row = _find_worklist_item(payload, env["patient_id"])

    assert row["attention_reason"] == "Recently completed, monitor"
    assert row["next_step"] == "Monitor recent completion"
    assert row["next_step_reason"] == "Work was completed recently; monitor for follow-up"
    assert row["active_owner_label"] == "Monitoring"
    assert row["waiting_on_label"] == "Next signal or follow-up"
    assert row["care_gap_label"] == "Monitoring follow-up pending"
    assert row["blocking_issue_label"] == "Follow-up window still open"
    assert row["resolution_target_label"] == "Confirm no new follow-up is needed"
    assert row["closure_readiness_label"] == "Near closure"
    assert row["resolution_confidence_label"] == "High confidence"
    assert row["recommended_timeframe"] == "This week"
    assert row["priority_band"] == "Low"
    assert row["priority_reason"] == "Work was completed recently"
    assert row["status_snapshot"] == "Low priority: work was completed recently, monitor recent completion this week"


def test_patient_worklist_next_step_reason_routine_monitoring(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-next-step-routine")
    _create_care_update(client, env["headers"], env["patient_id"], summary="Routine note")

    payload = _get_worklist_summary(client, env["headers"])
    row = _find_worklist_item(payload, env["patient_id"])

    assert row["attention_reason"] == "Routine monitoring"
    assert row["next_step"] == "Routine monitoring"
    assert row["next_step_reason"] == "No urgent workflow driver is present"
    assert row["active_owner_label"] == "Routine monitoring"
    assert row["waiting_on_label"] == "No immediate action"
    assert row["care_gap_label"] == "No active care gap"
    assert row["blocking_issue_label"] == "No active blocker"
    assert row["resolution_target_label"] == "Continue routine monitoring"
    assert row["closure_readiness_label"] == "Ready for routine monitoring"
    assert row["resolution_confidence_label"] == "High confidence"
    assert row["recommended_timeframe"] == "Routine"
    assert row["priority_band"] == "Low"
    assert row["priority_reason"] == "No urgent workflow driver is present"
    assert row["status_snapshot"] == "Low priority: no urgent workflow driver is present"


@pytest.mark.parametrize(
    ("days_old", "expected_label", "expected_staleness", "expected_priority_band", "expected_priority_reason"),
    [
        (0, "New today", "Fresh", "Medium", "Action is needed within 24 hours"),
        (1, "1–3 days open", "Fresh", "Medium", "Action is needed within 24 hours"),
        (2, "1–3 days open", "Fresh", "Medium", "Action is needed within 24 hours"),
        (5, "4–7 days open", "Aging", "Medium", "Action is needed within 24 hours"),
        (8, "Over 7 days open", "Stale", "High", "Workflow has become stale"),
    ],
)
def test_patient_worklist_workflow_age_label_for_open_task(
    client: TestClient,
    db_session: Session,
    days_old: int,
    expected_label: str,
    expected_staleness: str,
    expected_priority_band: str,
    expected_priority_reason: str,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug=f"worklist-age-{days_old}")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    task_id = _create_task(client, env["headers"], signal_payload["escalation"]["id"])
    task = db_session.get(InterventionTask, uuid.UUID(task_id))
    assert task is not None
    task.created_at = datetime.now(timezone.utc) - timedelta(days=days_old)
    db_session.commit()

    payload = _get_worklist_summary(client, env["headers"])
    row = _find_worklist_item(payload, env["patient_id"])

    assert row["workflow_age_label"] == expected_label
    if days_old == 0:
        assert row["recent_change_label"] == "Updated today"
    elif days_old == 1:
        assert row["recent_change_label"] == "Updated yesterday"
    else:
        assert row["recent_change_label"] is None
    assert row["staleness_indicator"] == expected_staleness
    assert row["priority_band"] == expected_priority_band
    assert row["priority_reason"] == expected_priority_reason


def test_patient_worklist_staleness_indicator_omitted_without_age_source(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-staleness-none")
    _create_care_update(client, env["headers"], env["patient_id"], summary="Routine note")

    payload = _get_worklist_summary(client, env["headers"])
    row = _find_worklist_item(payload, env["patient_id"])

    assert row["workflow_age_label"] is None
    assert row["staleness_indicator"] is None
    assert row["priority_band"] == "Low"
    assert row["priority_reason"] == "No urgent workflow driver is present"


def test_patient_workflow_status_worklist_cross_org_isolation(
    client: TestClient,
    db_session: Session,
) -> None:
    env_one = _bootstrap_patient_env(client, db_session, slug="workflow-status-scope-one")
    env_two = _bootstrap_patient_env(client, db_session, slug="workflow-status-scope-two")
    signal_payload = _create_signal(client, env_two["headers"], env_two["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    _create_task(client, env_two["headers"], escalation_id, title="Other org task")

    _get_worklist_summary(
        client,
        env_one["headers"],
        params=[("patient_ids", env_two["patient_id"])],
        expect_status=404,
    )

    payload_two = _get_worklist_summary(
        client,
        env_two["headers"],
        params=[("patient_ids", env_two["patient_id"])],
    )
    status = payload_two["items"][0].get("workflow_status")
    assert status is not None
    assert status["status_key"].startswith("task_")


def test_patient_timeline_worklist_summary_task_summary_respects_tenant_scope(
    client: TestClient,
    db_session: Session,
) -> None:
    env_one = _bootstrap_patient_env(client, db_session, slug="worklist-task-scope-one")
    signal_one = _create_signal(client, env_one["headers"], env_one["patient_id"])
    escalation_one = signal_one["escalation"]["id"]
    open_task_id = _create_task(client, env_one["headers"], escalation_one, title="Org One Task")

    env_two = _bootstrap_patient_env(client, db_session, slug="worklist-task-scope-two")
    signal_two = _create_signal(client, env_two["headers"], env_two["patient_id"])
    escalation_two = signal_two["escalation"]["id"]
    _create_task(client, env_two["headers"], escalation_two, title="Org Two Task")

    payload = _get_worklist_summary(
        client,
        env_one["headers"],
        params=[("patient_ids", env_one["patient_id"]), ("patient_ids", env_two["patient_id"])],
    )
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    row = payload["items"][0]
    assert row["patient_id"] == env_one["patient_id"]
    summary = row["task_summary"]
    assert summary is not None
    assert summary["open_task_count"] == 1
    assert summary["latest_active_task_id"] == open_task_id


def test_patient_timeline_worklist_summary_related_filters_reject_cross_org_context(
    client: TestClient,
    db_session: Session,
) -> None:
    env_one = _bootstrap_patient_env(client, db_session, slug="worklist-cross-tenant-one")
    env_two = _bootstrap_patient_env(client, db_session, slug="worklist-cross-tenant-two")
    signal_payload = _create_signal(client, env_two["headers"], env_two["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    task_id = _create_task(client, env_two["headers"], escalation_id)

    _get_worklist_summary(
        client,
        env_one["headers"],
        params={"related_escalation_id": escalation_id},
        expect_status=404,
    )
    _get_worklist_summary(
        client,
        env_one["headers"],
        params={"related_task_id": task_id},
        expect_status=404,
    )


def test_patient_timeline_filtered_read_state_scoped_by_related_escalation(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-read-filtered-escalation")
    first_signal = _create_signal(client, env["headers"], env["patient_id"])
    second_signal = _create_signal(client, env["headers"], env["patient_id"])
    first_escalation_id = first_signal["escalation"]["id"]
    _create_task(client, env["headers"], first_escalation_id, title="Esc Task")
    _create_task(client, env["headers"], second_signal["escalation"]["id"], title="Other Esc Task")

    scoped_listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"related_escalation_id": first_escalation_id},
        headers=env["headers"],
    ).json()
    assert scoped_listing["items"]

    filtered = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/filtered",
        params={"related_escalation_id": first_escalation_id},
        headers=env["headers"],
    )
    assert filtered.status_code == 200
    payload = filtered.json()
    assert payload["newest_event_id"] == scoped_listing["items"][0]["event_id"]
    assert payload["unread_count"] == len(scoped_listing["items"])


def test_patient_timeline_filtered_mark_read_action_succeeds_with_event_filters(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-targeted-filtered")
    _create_signal(client, env["headers"], env["patient_id"])
    care_update = _create_care_update(client, env["headers"], env["patient_id"], summary="Filtered Event")

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params=[("event_types", "care_update_logged")],
        headers=env["headers"],
    ).json()
    assert listing["items"]
    target_event_id = listing["items"][0]["event_id"]
    assert target_event_id.endswith(care_update["id"])

    resp = client.post(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/filtered/mark-through",
        params=[("event_types", "care_update_logged")],
        json={"event_id": target_event_id},
        headers=env["headers"],
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["last_read_event_id"] == target_event_id

    filtered_state = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/filtered",
        params=[("event_types", "care_update_logged")],
        headers=env["headers"],
    ).json()
    assert filtered_state["last_read_event_id"] == target_event_id


def test_patient_timeline_filtered_mark_read_action_rejects_event_outside_subset(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-targeted-filtered-reject")
    _create_signal(client, env["headers"], env["patient_id"])
    _create_care_update(client, env["headers"], env["patient_id"])

    signal_listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params=[("event_types", "signal_recorded")],
        headers=env["headers"],
    ).json()
    signal_event_id = signal_listing["items"][0]["event_id"]

    resp = client.post(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/filtered/mark-through",
        params=[("event_types", "care_update_logged")],
        json={"event_id": signal_event_id},
        headers=env["headers"],
    )
    assert resp.status_code == 422


def test_patient_timeline_filtered_mark_read_action_scoped_by_related_escalation(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-targeted-filtered-escalation")
    signal_one = _create_signal(client, env["headers"], env["patient_id"])
    signal_two = _create_signal(client, env["headers"], env["patient_id"])
    first_escalation_id = signal_one["escalation"]["id"]

    scoped = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"related_escalation_id": first_escalation_id},
        headers=env["headers"],
    ).json()
    assert scoped["items"]
    target_event_id = scoped["items"][0]["event_id"]

    resp = client.post(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/filtered/mark-through",
        params={"related_escalation_id": first_escalation_id},
        json={"event_id": target_event_id},
        headers=env["headers"],
    )
    assert resp.status_code == 200

    mismatch = client.post(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/filtered/mark-through",
        params={"related_escalation_id": signal_two["escalation"]["id"]},
        json={"event_id": target_event_id},
        headers=env["headers"],
    )
    assert mismatch.status_code == 422


def test_patient_timeline_filtered_mark_read_action_scoped_by_related_task(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-targeted-filtered-task")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    task_id = _create_task(client, env["headers"], escalation_id, title="Scoped Task")
    _create_task(client, env["headers"], escalation_id, title="Other Task")

    scoped_listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"related_task_id": task_id},
        headers=env["headers"],
    ).json()
    assert scoped_listing["items"]
    event_id = scoped_listing["items"][0]["event_id"]

    resp = client.post(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/filtered/mark-through",
        params={"related_task_id": task_id},
        json={"event_id": event_id},
        headers=env["headers"],
    )
    assert resp.status_code == 200


def test_patient_timeline_filtered_mark_read_action_respects_task_status_filters(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-targeted-filtered-status")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    open_task_id = _create_task(client, env["headers"], escalation_id, title="Open Filter Task")
    closed_task_id = _create_task(client, env["headers"], escalation_id, title="Closed Filter Task")
    _complete_task_with_outcome(client, env["headers"], closed_task_id)

    open_listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"related_task_id": open_task_id},
        headers=env["headers"],
    ).json()
    assert open_listing["items"]
    open_event_id = open_listing["items"][0]["event_id"]

    open_resp = client.post(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/filtered/mark-through",
        params={"task_statuses": "open"},
        json={"event_id": open_event_id},
        headers=env["headers"],
    )
    assert open_resp.status_code == 200

    closed_listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"related_task_id": closed_task_id},
        headers=env["headers"],
    ).json()
    closed_event_id = closed_listing["items"][0]["event_id"]

    closed_resp = client.post(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/filtered/mark-through",
        params={"task_statuses": "open"},
        json={"event_id": closed_event_id},
        headers=env["headers"],
    )
    assert closed_resp.status_code == 422


def test_patient_timeline_filtered_mark_read_action_respects_include_only_open_work(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-targeted-filtered-open-work")
    open_signal = _create_signal(client, env["headers"], env["patient_id"])
    open_escalation_id = open_signal["escalation"]["id"]
    _create_task(client, env["headers"], open_escalation_id, title="Stay Open")

    closed_signal = _create_signal(client, env["headers"], env["patient_id"])
    closed_escalation_id = closed_signal["escalation"]["id"]
    closed_task_id = _create_task(client, env["headers"], closed_escalation_id, title="Close Me")
    _complete_task_with_outcome(client, env["headers"], closed_task_id)
    client.post(
        f"/api/v1/escalations/{closed_escalation_id}/resolve",
        json={"resolution_notes": "done"},
        headers=env["headers"],
    )

    open_scoped = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"include_only_open_work": "true"},
        headers=env["headers"],
    ).json()
    assert open_scoped["items"]
    open_event_id = open_scoped["items"][0]["event_id"]

    success = client.post(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/filtered/mark-through",
        params={"include_only_open_work": "true"},
        json={"event_id": open_event_id},
        headers=env["headers"],
    )
    assert success.status_code == 200

    closed_listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"related_escalation_id": closed_escalation_id},
        headers=env["headers"],
    ).json()
    closed_event_id = closed_listing["items"][0]["event_id"]

    reject = client.post(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/filtered/mark-through",
        params={"include_only_open_work": "true"},
        json={"event_id": closed_event_id},
        headers=env["headers"],
    )
    assert reject.status_code == 422


def test_patient_timeline_filtered_mark_read_action_respects_occurred_filters(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-targeted-filtered-occurred")
    base_time = datetime.now(timezone.utc)
    _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="older-note",
        occurred_at=base_time - timedelta(minutes=5),
    )
    _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="target-note",
        occurred_at=base_time,
    )

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    ).json()
    target_event_id = listing["items"][0]["event_id"]

    allowed = client.post(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/filtered/mark-through",
        params={"occurred_after": (base_time - timedelta(minutes=4)).isoformat()},
        json={"event_id": target_event_id},
        headers=env["headers"],
    )
    assert allowed.status_code == 200

    rejected = client.post(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/filtered/mark-through",
        params={"occurred_after": (base_time + timedelta(minutes=1)).isoformat()},
        json={"event_id": target_event_id},
        headers=env["headers"],
    )
    assert rejected.status_code == 422


def test_patient_timeline_mark_through_same_timestamp_is_deterministic(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-targeted-tie")
    occurred_at = datetime.now(timezone.utc)
    for idx in range(3):
        _create_care_update(
            client,
            env["headers"],
            env["patient_id"],
            summary=f"Tie Mark {idx}",
            occurred_at=occurred_at,
        )

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    ).json()["items"]
    target_event_id = listing[1]["event_id"]

    resp = client.post(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/mark-through",
        json={"event_id": target_event_id},
        headers=env["headers"],
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["last_read_event_id"] == target_event_id
    assert payload["unread_count"] == 1

def test_patient_timeline_filtered_read_state_scoped_by_related_task_and_status(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-read-filtered-task")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    open_task_id = _create_task(client, env["headers"], escalation_id, title="Stay Open")
    completed_task_id = _create_task(client, env["headers"], escalation_id, title="Finish Me")
    _complete_task_with_outcome(client, env["headers"], completed_task_id)

    related_task_listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"related_task_id": completed_task_id},
        headers=env["headers"],
    ).json()
    assert related_task_listing["items"]

    filtered_task = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/filtered",
        params={"related_task_id": completed_task_id},
        headers=env["headers"],
    )
    assert filtered_task.status_code == 200
    task_payload = filtered_task.json()
    assert task_payload["newest_event_id"] == related_task_listing["items"][0]["event_id"]

    open_listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params=[("task_statuses", "open")],
        headers=env["headers"],
    ).json()
    completed_listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params=[("task_statuses", "completed")],
        headers=env["headers"],
    ).json()

    open_filtered = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/filtered",
        params=[("task_statuses", "open")],
        headers=env["headers"],
    )
    completed_filtered = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/filtered",
        params=[("task_statuses", "completed")],
        headers=env["headers"],
    )
    assert open_filtered.status_code == 200
    assert completed_filtered.status_code == 200
    assert open_listing["items"]
    assert completed_listing["items"]
    assert open_filtered.json()["newest_event_id"] == open_listing["items"][0]["event_id"]
    assert completed_filtered.json()["newest_event_id"] == completed_listing["items"][0]["event_id"]


def test_patient_timeline_filtered_read_state_include_only_open_work(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-read-filtered-open-work")
    open_signal = _create_signal(client, env["headers"], env["patient_id"])
    open_escalation_id = open_signal["escalation"]["id"]
    _create_task(client, env["headers"], open_escalation_id, title="Open Task")

    closed_signal = _create_signal(client, env["headers"], env["patient_id"])
    closed_escalation_id = closed_signal["escalation"]["id"]
    closed_task_id = _create_task(client, env["headers"], closed_escalation_id, title="Closed Task")
    _complete_task_with_outcome(client, env["headers"], closed_task_id)
    client.post(
        f"/api/v1/escalations/{closed_escalation_id}/resolve",
        json={"resolution_notes": "done"},
        headers=env["headers"],
    )

    open_timeline = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"include_only_open_work": "true"},
        headers=env["headers"],
    ).json()
    assert open_timeline["items"]

    open_read_state = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/filtered",
        params={"include_only_open_work": "true"},
        headers=env["headers"],
    )
    assert open_read_state.status_code == 200
    payload = open_read_state.json()
    assert payload["newest_event_id"] == open_timeline["items"][0]["event_id"]
    assert payload["unread_count"] == len(open_timeline["items"])


def test_patient_timeline_filtered_read_state_rejects_invalid_filters(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-read-filtered-invalid")
    other_patient_id = create_patient_for_user(client, env["headers"], first_name="filtered-other")
    other_signal = _create_signal(client, env["headers"], other_patient_id)
    other_escalation_id = other_signal["escalation"]["id"]
    other_task_id = _create_task(client, env["headers"], other_escalation_id, title="Other Task")

    resp_escalation = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/filtered",
        params={"related_escalation_id": other_escalation_id},
        headers=env["headers"],
    )
    assert resp_escalation.status_code == 404

    resp_task = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/filtered",
        params={"related_task_id": other_task_id},
        headers=env["headers"],
    )
    assert resp_task.status_code == 404

    patient_signal_one = _create_signal(client, env["headers"], env["patient_id"])
    patient_signal_two = _create_signal(client, env["headers"], env["patient_id"])
    escalation_one = patient_signal_one["escalation"]["id"]
    escalation_two = patient_signal_two["escalation"]["id"]
    second_task = _create_task(client, env["headers"], escalation_two, title="Mismatch Task")

    mismatch_resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/filtered",
        params={"related_escalation_id": escalation_one, "related_task_id": second_task},
        headers=env["headers"],
    )
    assert mismatch_resp.status_code == 422


def test_patient_timeline_workflow_summary_empty(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-workflow-empty")

    summary = _get_workflow_summary(client, env["headers"], env["patient_id"])
    assert summary["patient_id"] == env["patient_id"]
    assert summary["open_task_count"] == 0
    assert summary["has_open_escalation"] is False
    assert summary["latest_workflow_event_id"] is None
    assert summary["unread_count"] == 0


def test_patient_timeline_workflow_summary_escalation_only(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-workflow-escalation")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation = signal_payload["escalation"]

    summary = _get_workflow_summary(client, env["headers"], env["patient_id"])
    assert summary["has_open_escalation"] is True
    assert summary["open_escalation_id"] == escalation["id"]
    assert summary["open_escalation_severity"] == escalation["severity"]
    assert summary["open_task_count"] == 0


def test_patient_timeline_workflow_summary_counts_open_tasks(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-workflow-tasks")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    first_task_id = _create_task(
        client,
        env["headers"],
        escalation_id,
        title="First Task",
    )
    second_task_id = _create_task(
        client,
        env["headers"],
        escalation_id,
        title="Second Task",
        priority="high",
    )

    summary = _get_workflow_summary(client, env["headers"], env["patient_id"])
    assert summary["open_task_count"] == 2
    assert summary["newest_open_task_id"] in {first_task_id, second_task_id}
    expected_titles = {
        first_task_id: "First Task",
        second_task_id: "Second Task",
    }
    expected_priorities = {
        first_task_id: "medium",
        second_task_id: "high",
    }
    newest_task_id = summary["newest_open_task_id"]
    assert summary["newest_open_task_title"] == expected_titles[newest_task_id]
    assert summary["newest_open_task_priority"] == expected_priorities[newest_task_id]
    assert summary["newest_open_task_status"] == "open"

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    ).json()
    newest_task_event = next(
        item for item in listing["items"] if item["source_kind"] == "intervention_task"
    )
    assert newest_task_event["source_id"] == summary["newest_open_task_id"]


def test_patient_timeline_workflow_summary_newest_task_updates_when_closed(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-workflow-newest")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    first_task_id = _create_task(client, env["headers"], escalation_id, title="First Task")
    second_task_id = _create_task(client, env["headers"], escalation_id, title="Second Task")

    summary = _get_workflow_summary(client, env["headers"], env["patient_id"])
    assert summary["newest_open_task_id"] in {first_task_id, second_task_id}
    assert summary["open_task_count"] == 2

    newest_task_id = summary["newest_open_task_id"]
    _complete_task_with_outcome(client, env["headers"], newest_task_id)
    remaining_task_id = first_task_id if newest_task_id == second_task_id else second_task_id

    updated = _get_workflow_summary(client, env["headers"], env["patient_id"])
    assert updated["open_task_count"] == 1
    assert updated["newest_open_task_id"] == remaining_task_id


def test_patient_timeline_workflow_summary_handles_resolved_escalation(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-workflow-resolve")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]

    before = _get_workflow_summary(client, env["headers"], env["patient_id"])
    assert before["has_open_escalation"] is True

    resolve_resp = client.post(
        f"/api/v1/escalations/{escalation_id}/resolve",
        json={"resolution_notes": "Handled"},
        headers=env["headers"],
    )
    assert resolve_resp.status_code == 200

    after = _get_workflow_summary(client, env["headers"], env["patient_id"])
    assert after["has_open_escalation"] is False
    assert after["open_escalation_id"] is None


def test_patient_timeline_workflow_summary_latest_event_matches_feed(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-workflow-latest")
    base_time = datetime.now(timezone.utc)
    _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        summary="latest-summary",
        occurred_at=base_time,
    )

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    )
    assert listing.status_code == 200
    list_payload = listing.json()
    assert list_payload["items"]

    summary = _get_workflow_summary(client, env["headers"], env["patient_id"])
    assert summary["latest_workflow_event_id"] == list_payload["items"][0]["event_id"]
    assert summary["latest_workflow_event_type"] == list_payload["items"][0]["event_type"]
    assert summary["latest_workflow_event_occurred_at"] == list_payload["items"][0]["occurred_at"]


def test_patient_timeline_workflow_summary_scoped_by_related_escalation(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-workflow-scope-escalation")
    first_signal = _create_signal(client, env["headers"], env["patient_id"])
    first_escalation_id = first_signal["escalation"]["id"]
    second_signal = _create_signal(client, env["headers"], env["patient_id"])
    second_escalation_id = second_signal["escalation"]["id"]

    first_open_task_id = _create_task(client, env["headers"], first_escalation_id, title="First Open")
    first_closed_task_id = _create_task(client, env["headers"], first_escalation_id, title="First Done")
    _complete_task_with_outcome(client, env["headers"], first_closed_task_id)

    _create_task(client, env["headers"], second_escalation_id, title="Second One")
    _create_task(client, env["headers"], second_escalation_id, title="Second Two")

    scoped_listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"related_escalation_id": first_escalation_id},
        headers=env["headers"],
    )
    assert scoped_listing.status_code == 200
    scoped_items = scoped_listing.json()["items"]
    assert scoped_items

    summary = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/workflow-summary",
        params={"related_escalation_id": first_escalation_id},
        headers=env["headers"],
    )
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["open_escalation_id"] == first_escalation_id
    assert payload["open_task_count"] == 1
    assert payload["newest_open_task_id"] == first_open_task_id
    assert payload["latest_workflow_event_id"] == scoped_items[0]["event_id"]


def test_patient_timeline_workflow_summary_scoped_by_related_task(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-workflow-scope-task")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    open_task_id = _create_task(client, env["headers"], escalation_id, title="Stay Open")
    completed_task_id = _create_task(client, env["headers"], escalation_id, title="Complete Me")
    _complete_task_with_outcome(client, env["headers"], completed_task_id)

    open_summary = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/workflow-summary",
        params={"related_task_id": open_task_id},
        headers=env["headers"],
    )
    assert open_summary.status_code == 200
    open_payload = open_summary.json()
    assert open_payload["open_task_count"] == 1
    assert open_payload["newest_open_task_id"] == open_task_id

    completed_summary = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/workflow-summary",
        params={"related_task_id": completed_task_id},
        headers=env["headers"],
    )
    assert completed_summary.status_code == 200
    completed_payload = completed_summary.json()
    assert completed_payload["open_task_count"] == 0
    assert completed_payload["newest_open_task_id"] is None

    completed_listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"related_task_id": completed_task_id},
        headers=env["headers"],
    )
    assert completed_listing.status_code == 200
    completed_items = completed_listing.json()["items"]
    assert completed_items
    assert completed_payload["latest_workflow_event_id"] == completed_items[0]["event_id"]


def test_patient_timeline_workflow_summary_rejects_invalid_context(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-workflow-context-invalid")
    other_patient_id = create_patient_for_user(client, env["headers"], first_name="workflow-other")
    other_signal = _create_signal(client, env["headers"], other_patient_id)
    other_escalation_id = other_signal["escalation"]["id"]
    other_task_id = _create_task(client, env["headers"], other_escalation_id, title="Other Task")

    resp_escalation = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/workflow-summary",
        params={"related_escalation_id": other_escalation_id},
        headers=env["headers"],
    )
    assert resp_escalation.status_code == 404

    resp_task = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/workflow-summary",
        params={"related_task_id": other_task_id},
        headers=env["headers"],
    )
    assert resp_task.status_code == 404

    first_signal = _create_signal(client, env["headers"], env["patient_id"])
    first_escalation_id = first_signal["escalation"]["id"]
    second_signal = _create_signal(client, env["headers"], env["patient_id"])
    second_escalation_id = second_signal["escalation"]["id"]
    second_task_id = _create_task(client, env["headers"], second_escalation_id, title="Second Task")

    mismatch_resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/workflow-summary",
        params={
            "related_escalation_id": first_escalation_id,
            "related_task_id": second_task_id,
        },
        headers=env["headers"],
    )
    assert mismatch_resp.status_code == 422


def test_patient_timeline_workflow_summary_include_only_open_work_focuses_latest_event(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-workflow-open-only")
    open_signal = _create_signal(client, env["headers"], env["patient_id"])
    open_escalation_id = open_signal["escalation"]["id"]
    _create_task(client, env["headers"], open_escalation_id, title="Open Workflow Task")

    closed_signal = _create_signal(client, env["headers"], env["patient_id"])
    closed_escalation_id = closed_signal["escalation"]["id"]
    closed_task_id = _create_task(client, env["headers"], closed_escalation_id, title="Closed Workflow Task")
    outcome = _complete_task_with_outcome(client, env["headers"], closed_task_id)
    _create_care_update(
        client,
        env["headers"],
        env["patient_id"],
        intervention_task_outcome_id=outcome["id"],
    )
    resolve_resp = client.post(
        f"/api/v1/escalations/{closed_escalation_id}/resolve",
        json={"resolution_notes": "closed"},
        headers=env["headers"],
    )
    assert resolve_resp.status_code == 200

    full_summary = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/workflow-summary",
        headers=env["headers"],
    ).json()

    open_summary_resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/workflow-summary",
        params={"include_only_open_work": "true"},
        headers=env["headers"],
    )
    assert open_summary_resp.status_code == 200
    open_summary = open_summary_resp.json()

    assert open_summary["latest_workflow_event_id"] is not None
    assert full_summary["latest_workflow_event_id"] != open_summary["latest_workflow_event_id"]
    assert open_summary["unread_count"] < full_summary["unread_count"]

    open_timeline = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        params={"include_only_open_work": "true"},
        headers=env["headers"],
    ).json()
    assert open_timeline["items"]
    assert open_summary["latest_workflow_event_id"] == open_timeline["items"][0]["event_id"]


def test_patient_timeline_workflow_summary_matches_read_state(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-workflow-read-state")
    base_time = datetime.now(timezone.utc)
    for idx in range(2):
        _create_care_update(
            client,
            env["headers"],
            env["patient_id"],
            summary=f"rs-{idx}",
            occurred_at=base_time - timedelta(minutes=idx),
        )

    read_state_resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state",
        headers=env["headers"],
    )
    assert read_state_resp.status_code == 200
    read_state = read_state_resp.json()

    summary = _get_workflow_summary(client, env["headers"], env["patient_id"])
    assert summary["unread_count"] == read_state["unread_count"]
    assert summary["last_read_event_id"] == read_state["last_read_event_id"]
    assert summary["last_read_occurred_at"] == read_state["last_read_occurred_at"]


def test_patient_timeline_workflow_summary_updates_after_mark_all_read(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-workflow-mark-read")
    base_time = datetime.now(timezone.utc)
    for idx in range(2):
        _create_care_update(
            client,
            env["headers"],
            env["patient_id"],
            summary=f"mark-{idx}",
            occurred_at=base_time - timedelta(minutes=idx),
        )

    before = _get_workflow_summary(client, env["headers"], env["patient_id"])
    assert before["unread_count"] == 2

    mark_resp = client.post(
        f"/api/v1/patients/{env['patient_id']}/timeline/read-state/mark-all-read",
        headers=env["headers"],
    )
    assert mark_resp.status_code == 200

    after = _get_workflow_summary(client, env["headers"], env["patient_id"])
    assert after["unread_count"] == 0
    assert after["last_read_event_id"] == after["latest_workflow_event_id"]
    assert after["last_read_occurred_at"] == after["latest_workflow_event_occurred_at"]


def test_patient_timeline_workflow_summary_cross_org_forbidden(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-workflow-scope")
    other_org = create_organization_record(db_session, slug="timeline-workflow-other-org")
    other_user = create_user_for_org(
        db_session,
        organization=other_org,
        email="timeline-workflow-other@example.com",
        password="Secret123!",
    )
    other_headers = auth_headers(client, other_user.email, "Secret123!")

    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline/workflow-summary",
        headers=other_headers,
    )
    assert resp.status_code == 403
@pytest.mark.parametrize("filter_name", ["related_escalation_id", "related_task_id"])
def test_patient_timeline_worklist_summary_filters_scope_to_owning_patient(
    client: TestClient,
    db_session: Session,
    filter_name: str,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug=f"worklist-scope-{filter_name}")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    task_id = _create_task(client, env["headers"], escalation_id)

    filter_value = escalation_id if filter_name == "related_escalation_id" else task_id

    other_patient_id = create_patient_for_user(
        client,
        env["headers"],
        first_name=f"worklist-{filter_name}-other",
    )
    _create_care_update(client, env["headers"], other_patient_id, summary="other patient event")

    payload = _get_worklist_summary(
        client,
        env["headers"],
        params={filter_name: filter_value},
    )
    assert payload["total"] == 1
    row = payload["items"][0]
    assert row["patient_id"] == env["patient_id"]

    inbox = _get_inbox_summary(
        client,
        env["headers"],
        env["patient_id"],
        params={filter_name: filter_value},
    )
    for field in (
        "has_unread_events",
        "unread_count",
        "total_events",
        "latest_event_id",
        "latest_event_type",
        "latest_event_occurred_at",
    ):
        assert row[field] == inbox[field]


def test_patient_timeline_worklist_summary_related_escalation_multi_patient(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-related-escalation")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]

    other_patient_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="worklist-related-escalation-other",
    )
    _create_care_update(client, env["headers"], other_patient_id, summary="other patient noise")

    def _fail_fetch(*args, **kwargs):
        raise AssertionError("worklist rows fetch should not run for derived filters")

    monkeypatch.setattr(
        read_state_service,
        "_fetch_worklist_patient_rows",
        _fail_fetch,
    )

    payload = _get_worklist_summary(
        client,
        env["headers"],
        params={"related_escalation_id": escalation_id},
    )
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["patient_id"] == env["patient_id"]


def test_patient_timeline_worklist_summary_related_task_multi_patient(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-related-task")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    task_id = _create_task(client, env["headers"], escalation_id)

    other_patient_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="worklist-related-task-other",
    )
    _create_care_update(client, env["headers"], other_patient_id, summary="other patient noise")

    def _fail_fetch(*args, **kwargs):
        raise AssertionError("worklist rows fetch should not run for derived filters")

    monkeypatch.setattr(
        read_state_service,
        "_fetch_worklist_patient_rows",
        _fail_fetch,
    )

    payload = _get_worklist_summary(
        client,
        env["headers"],
        params={"related_task_id": task_id},
    )
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["patient_id"] == env["patient_id"]


def test_patient_timeline_worklist_summary_related_filter_pagination(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-related-page")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    task_id = _create_task(client, env["headers"], escalation_id)

    # Introduce additional patients so that pagination would normally have to skip them
    for idx in range(3):
        extra_id = create_patient_for_user(
            client,
            env["headers"],
            first_name=f"worklist-related-page-{idx}",
        )
        _create_care_update(client, env["headers"], extra_id, summary=f"extra-{idx}")

    def _fail_fetch(*args, **kwargs):
        raise AssertionError("worklist rows fetch should not run for derived filters")

    monkeypatch.setattr(
        read_state_service,
        "_fetch_worklist_patient_rows",
        _fail_fetch,
    )

    first_page = _get_worklist_summary(
        client,
        env["headers"],
        params=[
            ("related_task_id", task_id),
            ("limit", 1),
        ],
    )
    assert first_page["total"] == 1
    assert len(first_page["items"]) == 1
    assert first_page["items"][0]["patient_id"] == env["patient_id"]

    second_page = _get_worklist_summary(
        client,
        env["headers"],
        params=[
            ("related_task_id", task_id),
            ("limit", 1),
            ("skip", 1),
        ],
    )
    assert second_page["total"] == 1
    assert second_page["items"] == []


def test_patient_timeline_worklist_summary_unfiltered_still_fetches_rows(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="worklist-unfiltered")
    second_patient_id = create_patient_for_user(
        client,
        env["headers"],
        first_name="worklist-unfiltered-second",
    )
    base_time = datetime.now(timezone.utc)
    for idx, patient_id in enumerate((env["patient_id"], second_patient_id)):
        _create_care_update(
            client,
            env["headers"],
            patient_id,
            summary=f"unfiltered-{idx}",
            occurred_at=base_time - timedelta(minutes=idx),
        )

    original_fetch = read_state_service._fetch_worklist_patient_rows
    call_count = 0

    def _spy_fetch(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original_fetch(*args, **kwargs)

    monkeypatch.setattr(
        read_state_service,
        "_fetch_worklist_patient_rows",
        _spy_fetch,
    )

    payload = _get_worklist_summary(client, env["headers"])
    assert payload["total"] == 2
    ids = [item["patient_id"] for item in payload["items"]]
    assert env["patient_id"] in ids
    assert second_patient_id in ids
    assert call_count == 1


def test_patient_timeline_includes_due_upcoming_event(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-due-upcoming")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    due_at = datetime.now(timezone.utc) + timedelta(hours=6)
    task_id = _create_task(
        client,
        env["headers"],
        escalation_id,
        title="Follow-up call",
        due_at=due_at,
    )
    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    )
    assert resp.status_code == 200
    listing = resp.json()
    due_events = [
        item
        for item in listing["items"]
        if item["event_type"] == "intervention_task_due_upcoming" and item["related_task_id"] == task_id
    ]
    assert due_events
    due_event = due_events[0]
    assert due_event["occurred_at"] == due_at.replace(tzinfo=None).isoformat()
    assert due_event["metadata"]["due_state"] == "due_upcoming"


def test_patient_timeline_includes_due_overdue_event(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-due-overdue")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    due_at = datetime.now(timezone.utc) - timedelta(hours=2)
    task_id = _create_task(
        client,
        env["headers"],
        escalation_id,
        title="Retro review",
        due_at=due_at,
    )
    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    )
    assert resp.status_code == 200
    listing = resp.json()
    due_events = [
        item
        for item in listing["items"]
        if item["event_type"] == "intervention_task_due_overdue" and item["related_task_id"] == task_id
    ]
    assert due_events
    due_event = due_events[0]
    assert due_event["occurred_at"] == due_at.replace(tzinfo=None).isoformat()
    assert due_event["metadata"]["due_state"] == "overdue"


def test_patient_timeline_due_events_skip_terminal_tasks(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-due-terminal")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    due_at = datetime.now(timezone.utc) + timedelta(days=1)
    task_id = _create_task(
        client,
        env["headers"],
        escalation_id,
        title="Close out",
        due_at=due_at,
    )
    complete_resp = client.post(
        f"/api/v1/tasks/{task_id}/complete",
        json={"completion_note": "Handled"},
        headers=env["headers"],
    )
    assert complete_resp.status_code == 200
    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    )
    assert resp.status_code == 200
    listing = resp.json()
    assert not any(
        item["event_type"].startswith("intervention_task_due_") and item["related_task_id"] == task_id
        for item in listing["items"]
    )


def test_patient_timeline_worklist_summary_surfaces_due_events(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-due-worklist")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    due_at = datetime.now(timezone.utc) + timedelta(hours=8)
    _create_task(
        client,
        env["headers"],
        escalation_id,
        title="Monitor labs",
        due_at=due_at,
    )
    payload = _get_worklist_summary(
        client,
        env["headers"],
        params=[("patient_ids", env["patient_id"])],
    )
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    row = payload["items"][0]
    assert row["latest_event_type"] == "intervention_task_due_upcoming"
    assert row["latest_event_occurred_at"] == due_at.replace(tzinfo=None).isoformat()


def test_patient_timeline_includes_escalation_sla_at_risk_event(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-sla-at-risk")
    sla_due_at = datetime.now(timezone.utc) + timedelta(hours=6)
    signal_payload = _create_signal(
        client,
        env["headers"],
        env["patient_id"],
        escalation_sla_due_at=sla_due_at,
    )
    escalation_id = signal_payload["escalation"]["id"]

    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    sla_events = [
        item
        for item in items
        if item["event_type"] == "escalation_sla_at_risk" and item["related_escalation_id"] == escalation_id
    ]
    assert sla_events
    event = sla_events[0]
    assert event["occurred_at"] == sla_due_at.replace(tzinfo=None).isoformat()
    assert event["metadata"]["sla_state"] == "sla_at_risk"


def test_patient_timeline_includes_escalation_sla_overdue_event(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-sla-overdue")
    sla_due_at = datetime.now(timezone.utc) - timedelta(hours=2)
    signal_payload = _create_signal(
        client,
        env["headers"],
        env["patient_id"],
        escalation_sla_due_at=sla_due_at,
    )
    escalation_id = signal_payload["escalation"]["id"]

    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    sla_events = [
        item
        for item in items
        if item["event_type"] == "escalation_sla_overdue" and item["related_escalation_id"] == escalation_id
    ]
    assert sla_events
    event = sla_events[0]
    assert event["occurred_at"] == sla_due_at.replace(tzinfo=None).isoformat()
    assert event["metadata"]["sla_state"] == "sla_overdue"


def test_patient_timeline_escalation_sla_events_skip_resolved(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-sla-resolved")
    sla_due_at = datetime.now(timezone.utc) + timedelta(hours=3)
    signal_payload = _create_signal(
        client,
        env["headers"],
        env["patient_id"],
        escalation_sla_due_at=sla_due_at,
    )
    escalation_id = signal_payload["escalation"]["id"]
    resolve_resp = client.post(
        f"/api/v1/escalations/{escalation_id}/resolve",
        json={"resolution_notes": "Handled"},
        headers=env["headers"],
    )
    assert resolve_resp.status_code == 200

    resp = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert not any(
        item["event_type"].startswith("escalation_sla_") and item["related_escalation_id"] == escalation_id
        for item in items
    )


def test_patient_timeline_worklist_summary_surfaces_escalation_sla_events(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="timeline-sla-worklist")
    sla_due_at = datetime.now(timezone.utc) + timedelta(hours=5)
    _create_signal(
        client,
        env["headers"],
        env["patient_id"],
        escalation_sla_due_at=sla_due_at,
    )

    payload = _get_worklist_summary(
        client,
        env["headers"],
        params=[("patient_ids", env["patient_id"])],
    )
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    row = payload["items"][0]
    assert row["latest_event_type"] == "escalation_sla_at_risk"
    assert row["latest_event_occurred_at"] == sla_due_at.replace(tzinfo=None).isoformat()


def test_patient_attention_summary_recommends_task_for_open_escalation_without_active_task(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="attention-open-escalation")
    _create_signal(client, env["headers"], env["patient_id"])

    summary = _get_attention_summary(client, env["headers"], env["patient_id"])
    payload = _get_timeline_detail_payload(client, env["headers"], env["patient_id"])

    assert summary["primary_driver"] == "escalation"
    assert summary["urgency_level"] == "active"
    assert payload["status_snapshot"] == "Medium priority: action is needed within 24 hours"
    assert payload["care_gap_label"] == "Outreach not started"
    assert payload["blocking_issue_label"] == "No outreach started"
    assert payload["resolution_target_label"] == "Start outreach and document action"
    assert payload["closure_readiness_label"] == "Not ready for closure"
    assert payload["resolution_confidence_label"] == "Low confidence"
    assert summary["why_now"] == "There is an open escalation with no active intervention task."
    assert summary["recommended_next_action"] == "Assign and start an outreach task."
    assert any("open escalation" in item for item in summary["supporting_evidence"])


def test_patient_attention_summary_recommends_follow_through_for_in_progress_task(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="attention-in-progress")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    task_id = _create_task(client, env["headers"], signal_payload["escalation"]["id"])

    start_resp = client.post(
        f"/api/v1/tasks/{task_id}/start",
        headers=env["headers"],
    )
    assert start_resp.status_code == 200

    summary = _get_attention_summary(client, env["headers"], env["patient_id"])
    payload = _get_timeline_detail_payload(client, env["headers"], env["patient_id"])

    assert summary["primary_driver"] == "task"
    assert summary["urgency_level"] == "active"
    assert payload["care_gap_label"] == "Intervention still in progress"
    assert payload["blocking_issue_label"] == "Work not yet completed"
    assert payload["resolution_target_label"] == "Complete the intervention"
    assert payload["closure_readiness_label"] == "Not ready for closure"
    assert payload["resolution_confidence_label"] == "Moderate confidence"
    assert summary["why_now"] == "Active intervention work is already in progress."
    assert summary["recommended_next_action"] == (
        "Follow through on the current task and document the outcome."
    )
    assert any("task in progress" in item for item in summary["supporting_evidence"])


def test_patient_attention_summary_prioritizes_overdue_task(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="attention-overdue-task")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    _create_task(
        client,
        env["headers"],
        signal_payload["escalation"]["id"],
        due_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )

    summary = _get_attention_summary(client, env["headers"], env["patient_id"])
    payload = _get_timeline_detail_payload(client, env["headers"], env["patient_id"])

    assert summary["primary_driver"] == "task"
    assert summary["urgency_level"] == "overdue"
    assert payload["status_snapshot"] == "High priority: task is overdue today"
    assert payload["care_gap_label"] == "Task disposition overdue"
    assert payload["blocking_issue_label"] == "Task not updated"
    assert payload["resolution_target_label"] == "Update or close the task"
    assert payload["closure_readiness_label"] == "Not ready for closure"
    assert payload["resolution_confidence_label"] == "Low confidence"
    assert summary["why_now"] == "One or more active intervention tasks are overdue."
    assert summary["recommended_next_action"] == (
        "Complete immediate follow-up or update the task disposition."
    )
    assert any("task overdue" in item for item in summary["supporting_evidence"])


def test_patient_attention_summary_summarizes_completed_workflow(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="attention-completed")
    signal_payload = _create_signal(client, env["headers"], env["patient_id"])
    escalation_id = signal_payload["escalation"]["id"]
    task_id = _create_task(client, env["headers"], escalation_id)
    _complete_task_with_outcome(client, env["headers"], task_id)
    resolve_resp = client.post(
        f"/api/v1/escalations/{escalation_id}/resolve",
        json={"resolution_notes": "Handled"},
        headers=env["headers"],
    )
    assert resolve_resp.status_code == 200

    summary = _get_attention_summary(client, env["headers"], env["patient_id"])
    payload = _get_timeline_detail_payload(client, env["headers"], env["patient_id"])

    assert summary["primary_driver"] == "monitoring"
    assert summary["urgency_level"] == "stable"
    assert payload["care_gap_label"] == "Monitoring follow-up pending"
    assert payload["blocking_issue_label"] == "Follow-up window still open"
    assert payload["resolution_target_label"] == "Confirm no new follow-up is needed"
    assert payload["closure_readiness_label"] == "Near closure"
    assert payload["resolution_confidence_label"] == "High confidence"
    assert summary["why_now"] == (
        "Recent intervention work is completed and no escalation is currently open."
    )
    assert summary["recommended_next_action"] == (
        "Continue monitoring and review new timeline evidence as it arrives."
    )
    assert any("completed intervention" in item for item in summary["supporting_evidence"])


def test_patient_attention_summary_handles_minimal_workflow_state(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_patient_env(client, db_session, slug="attention-minimal")
    _create_care_update(client, env["headers"], env["patient_id"], summary="Routine note")

    summary = _get_attention_summary(client, env["headers"], env["patient_id"])
    payload = _get_timeline_detail_payload(client, env["headers"], env["patient_id"])

    assert summary["primary_driver"] == "monitoring"
    assert summary["urgency_level"] == "stable"
    assert payload["status_snapshot"] == "Low priority: no urgent workflow driver is present"
    assert payload["care_gap_label"] == "No active care gap"
    assert payload["blocking_issue_label"] == "No active blocker"
    assert payload["resolution_target_label"] == "Continue routine monitoring"
    assert payload["closure_readiness_label"] == "Ready for routine monitoring"
    assert payload["resolution_confidence_label"] == "High confidence"
    assert payload["active_owner_label"] == "Routine monitoring"
    assert payload["waiting_on_label"] == "No immediate action"
    assert summary["why_now"] == "No active escalation or intervention task is currently recorded."
    assert summary["recommended_next_action"] == "Continue routine monitoring."
    assert summary["supporting_evidence"] == ["1 timeline evidence event"]


@pytest.mark.parametrize(
    (
        "scenario",
        "expected_label",
        "expected_reason_label",
        "expected_timeframe_reason_label",
        "expected_next_step_reason_detail_label",
        "expected_status_snapshot_reason_label",
        "expected_closure_readiness_reason_label",
        "expected_resolution_confidence_reason_label",
    ),
    [
        (
            "overdue_task",
            "Task created today",
            "Created when task was opened",
            "Urgent because task is overdue",
            "Because the overdue task still needs disposition",
            "Because an overdue task is still open",
            "Because an overdue task is still open",
            "Because overdue work still remains open",
        ),
        (
            "in_progress_task",
            "Task started today",
            "Started when task moved to in progress",
            "Soon because work is already in progress",
            "Because work has started but is not complete",
            "Because work is in progress",
            "Because work remains in progress",
            "Because active work is still in progress",
        ),
        (
            "open_escalation_no_task",
            "Escalation opened today",
            "Opened from escalation",
            "Soon because escalation is open with no task",
            "Because the escalation is open and no task exists yet",
            "Because an escalation is open without a task",
            "Because the escalation is still unresolved",
            "Because an escalation is unresolved without a task",
        ),
        (
            "recent_completion",
            "Task completed today",
            "Completed by task outcome",
            "Routine because no unresolved workflow remains",
            "Because no unresolved workflow remains",
            "Because no unresolved workflow remains",
            "Because no unresolved workflow remains",
            "Because no unresolved workflow remains",
        ),
        (
            "routine",
            "Care update added today",
            "Added by care update",
            "Routine because no immediate action is required",
            "Because no immediate workflow action is required",
            "Because no immediate workflow action is required",
            "Because no immediate workflow closure is needed",
            "Because no immediate workflow action is pending",
        ),
    ],
)
def test_patient_last_operational_change_label_matches_worklist_and_detail(
    client: TestClient,
    db_session: Session,
    scenario: str,
    expected_label: str,
    expected_reason_label: str,
    expected_timeframe_reason_label: str,
    expected_next_step_reason_detail_label: str,
    expected_status_snapshot_reason_label: str,
    expected_closure_readiness_reason_label: str,
    expected_resolution_confidence_reason_label: str,
) -> None:
    env = _bootstrap_patient_env(
        client,
        db_session,
        slug=f"last-operational-{scenario.replace('_', '-')}",
    )

    if scenario == "routine":
        _create_care_update(
            client,
            env["headers"],
            env["patient_id"],
            summary="Routine monitoring note",
        )
    else:
        signal_payload = _create_signal(client, env["headers"], env["patient_id"])
        escalation_id = signal_payload["escalation"]["id"]

        if scenario == "overdue_task":
            task_id = _create_task(
                client,
                env["headers"],
                escalation_id,
                due_at=datetime.now(timezone.utc) - timedelta(hours=2),
            )
            task = db_session.get(InterventionTask, uuid.UUID(task_id))
            assert task is not None
            task.created_at = datetime.now(timezone.utc) + timedelta(minutes=5)
            db_session.commit()
        elif scenario == "in_progress_task":
            task_id = _create_task(client, env["headers"], escalation_id)
            start_resp = client.post(
                f"/api/v1/tasks/{task_id}/start",
                headers=env["headers"],
            )
            assert start_resp.status_code == 200
            task = db_session.get(InterventionTask, uuid.UUID(task_id))
            assert task is not None
            task.updated_at = datetime.now(timezone.utc) + timedelta(minutes=5)
            db_session.commit()
        elif scenario == "recent_completion":
            task_id = _create_task(client, env["headers"], escalation_id)
            _complete_task_with_outcome(client, env["headers"], task_id)
            resolve_resp = client.post(
                f"/api/v1/escalations/{escalation_id}/resolve",
                json={"resolution_notes": "Handled"},
                headers=env["headers"],
            )
            assert resolve_resp.status_code == 200
            task = db_session.get(InterventionTask, uuid.UUID(task_id))
            assert task is not None
            task.completed_at = datetime.now(timezone.utc) + timedelta(minutes=5)
            db_session.commit()
        else:
            assert scenario == "open_escalation_no_task"

    worklist = _get_worklist_summary(
        client,
        env["headers"],
        params=[("patient_ids", env["patient_id"]), ("active_only", False)],
    )
    row = _find_worklist_item(worklist, env["patient_id"])
    detail = _get_timeline_detail_payload(client, env["headers"], env["patient_id"])

    assert row["last_operational_change_label"] == expected_label
    assert row["last_operational_change_reason_label"] == expected_reason_label
    assert row["recommended_timeframe_reason_label"] == expected_timeframe_reason_label
    assert row["next_step_reason_detail_label"] == expected_next_step_reason_detail_label
    assert row["status_snapshot_reason_label"] == expected_status_snapshot_reason_label
    assert row["closure_readiness_reason_label"] == expected_closure_readiness_reason_label
    assert row["resolution_confidence_reason_label"] == expected_resolution_confidence_reason_label
    assert detail["last_operational_change_label"] == expected_label
    assert detail["last_operational_change_reason_label"] == expected_reason_label
    assert detail["recommended_timeframe_reason_label"] == expected_timeframe_reason_label
    assert detail["next_step_reason_detail_label"] == expected_next_step_reason_detail_label
    assert detail["status_snapshot_reason_label"] == expected_status_snapshot_reason_label
    assert detail["closure_readiness_reason_label"] == expected_closure_readiness_reason_label
    assert detail["resolution_confidence_reason_label"] == expected_resolution_confidence_reason_label
