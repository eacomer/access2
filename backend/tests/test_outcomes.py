from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.test_intervention_tasks import _bootstrap_task


def _create_outcome(
    client: TestClient,
    headers: dict[str, str],
    patient_id: str,
    *,
    intervention_task_id: str | None = None,
    metric_name: str = "systolic_bp",
    value_numeric: float | None = 140,
    value_text: str | None = None,
    observed_at: datetime | None = None,
) -> dict:
    payload: dict[str, object] = {
        "patient_id": patient_id,
        "type": "bp",
        "metric_name": metric_name,
        "observed_at": (observed_at or datetime.now(timezone.utc)).isoformat(),
        "source": "home_monitor",
    }
    if intervention_task_id is not None:
        payload["intervention_task_id"] = intervention_task_id
    if value_numeric is not None:
        payload["value_numeric"] = value_numeric
        payload["unit"] = "mmHg"
    if value_text is not None:
        payload["value_text"] = value_text

    resp = client.post("/api/v1/outcomes", json=payload, headers=headers)
    assert resp.status_code == 201
    return resp.json()


def test_create_numeric_outcome(client: TestClient, db_session: Session) -> None:
    env = _bootstrap_task(client, db_session, slug="outcome-numeric")

    outcome = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        intervention_task_id=env["task"]["id"],
        value_numeric=132,
    )

    assert outcome["patient_id"] == env["patient_id"]
    assert outcome["intervention_task_id"] == env["task"]["id"]
    assert outcome["metric_name"] == "systolic_bp"
    assert outcome["value_numeric"] == 132


def test_create_text_outcome(client: TestClient, db_session: Session) -> None:
    env = _bootstrap_task(client, db_session, slug="outcome-text")

    outcome = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        metric_name="completed_checkin",
        value_numeric=None,
        value_text="completed",
    )

    assert outcome["value_numeric"] is None
    assert outcome["value_text"] == "completed"


def test_outcome_rejects_missing_value(client: TestClient, db_session: Session) -> None:
    env = _bootstrap_task(client, db_session, slug="outcome-missing")

    resp = client.post(
        "/api/v1/outcomes",
        json={
            "patient_id": env["patient_id"],
            "type": "bp",
            "metric_name": "systolic_bp",
            "observed_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=env["headers"],
    )

    assert resp.status_code == 422


def test_patient_outcomes_are_ordered_by_observed_at_then_id(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_task(client, db_session, slug="outcome-order")
    base = datetime.now(timezone.utc)

    later = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        value_numeric=130,
        observed_at=base + timedelta(days=1),
    )
    earlier = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        value_numeric=140,
        observed_at=base,
    )

    listing = client.get(
        f"/api/v1/patients/{env['patient_id']}/outcomes",
        headers=env["headers"],
    )

    assert listing.status_code == 200
    ids = [item["id"] for item in listing.json()]
    assert ids == [earlier["id"], later["id"]]


def test_outcome_creation_adds_timeline_event(client: TestClient, db_session: Session) -> None:
    env = _bootstrap_task(client, db_session, slug="outcome-timeline")
    outcome = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        intervention_task_id=env["task"]["id"],
    )

    timeline = client.get(
        f"/api/v1/patients/{env['patient_id']}/timeline",
        headers=env["headers"],
    )

    assert timeline.status_code == 200
    outcome_events = [
        item for item in timeline.json()["items"] if item["event_type"] == "outcome"
    ]
    assert len(outcome_events) == 1
    assert outcome_events[0]["source_id"] == outcome["id"]
    assert outcome_events[0]["related_task_id"] == env["task"]["id"]


def test_access_evidence_summarizes_metric_trend_and_links_intervention(
    client: TestClient,
    db_session: Session,
) -> None:
    env = _bootstrap_task(client, db_session, slug="outcome-evidence")
    base = datetime.now(timezone.utc)

    baseline = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        value_numeric=150,
        observed_at=base,
    )
    latest = _create_outcome(
        client,
        env["headers"],
        env["patient_id"],
        intervention_task_id=env["task"]["id"],
        value_numeric=130,
        observed_at=base + timedelta(days=3),
    )

    report = client.get(
        f"/api/v1/reports/access-evidence/{env['patient_id']}",
        headers=env["headers"],
    )

    assert report.status_code == 200
    payload = report.json()
    summary = payload["outcome_summaries"][0]
    assert summary["metric_name"] == "systolic_bp"
    assert summary["baseline"] == 150
    assert summary["latest"] == 130
    assert summary["delta"] == -20
    assert summary["status"] == "improved"
    assert summary["baseline_outcome_id"] == baseline["id"]
    assert summary["latest_outcome_id"] == latest["id"]

    links = payload["intervention_outcome_links"]
    assert len(links) == 1
    assert links[0]["intervention_task_id"] == env["task"]["id"]
    assert links[0]["linked_outcome_ids"] == [latest["id"]]
    assert links[0]["linked_outcome_metric_names"] == ["systolic_bp"]
    assert links[0]["outcomes_after_intervention"] is True
    assert links[0]["first_outcome_lag_hours"] is not None
