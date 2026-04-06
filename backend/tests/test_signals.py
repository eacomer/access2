from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.test_patients import (
    auth_headers,
    create_organization_record,
    create_patient_for_user,
    create_user_for_org,
)


def test_signal_creation_triggers_escalation(
    client: TestClient,
    db_session: Session,
) -> None:
    organization = create_organization_record(db_session, slug="signal-escalate")
    user = create_user_for_org(
        db_session,
        organization=organization,
        email="signal1@example.com",
        password="Secret123!",
    )
    headers = auth_headers(client, user.email, "Secret123!")
    patient_id = create_patient_for_user(client, headers, first_name="Signal")

    resp = client.post(
        f"/api/v1/patients/{patient_id}/signals",
        json={
            "signal_type": "symptom_score",
            "signal_value_numeric": 9.5,
            "recorded_at": "2026-04-01T12:00:00Z",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["escalation"] is not None
    assert payload["escalation"]["status"] == "open"
    assert payload["escalation"]["severity"] == "high"

    escalations_resp = client.get(
        f"/api/v1/patients/{patient_id}/escalations",
        headers=headers,
    )
    assert escalations_resp.status_code == 200
    assert len(escalations_resp.json()) == 1


def test_signal_below_threshold_does_not_escalate(
    client: TestClient,
    db_session: Session,
) -> None:
    organization = create_organization_record(db_session, slug="signal-no-escalate")
    user = create_user_for_org(
        db_session,
        organization=organization,
        email="signal2@example.com",
        password="Secret123!",
    )
    headers = auth_headers(client, user.email, "Secret123!")
    patient_id = create_patient_for_user(client, headers, first_name="Baseline")

    resp = client.post(
        f"/api/v1/patients/{patient_id}/signals",
        json={
            "signal_type": "blood_pressure_systolic",
            "signal_value_numeric": 140,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["escalation"] is None


def test_signal_listing_scoped_to_organization(
    client: TestClient,
    db_session: Session,
) -> None:
    org_one = create_organization_record(db_session, slug="signal-org-one")
    org_two = create_organization_record(db_session, slug="signal-org-two")
    user_one = create_user_for_org(
        db_session,
        organization=org_one,
        email="signal3@example.com",
        password="Secret123!",
    )
    user_two = create_user_for_org(
        db_session,
        organization=org_two,
        email="signal4@example.com",
        password="Secret123!",
    )
    headers_one = auth_headers(client, user_one.email, "Secret123!")
    headers_two = auth_headers(client, user_two.email, "Secret123!")

    patient_one = create_patient_for_user(client, headers_one, first_name="TenantA")
    patient_two = create_patient_for_user(client, headers_two, first_name="TenantB")

    client.post(
        f"/api/v1/patients/{patient_one}/signals",
        json={
            "signal_type": "missed_check_in",
        },
        headers=headers_one,
    )
    client.post(
        f"/api/v1/patients/{patient_two}/signals",
        json={
            "signal_type": "symptom_score",
            "signal_value_numeric": 9,
        },
        headers=headers_two,
    )

    list_resp = client.get(
        f"/api/v1/patients/{patient_one}/signals",
        headers=headers_one,
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    denied_resp = client.get(
        f"/api/v1/patients/{patient_one}/signals",
        headers=headers_two,
    )
    assert denied_resp.status_code == 403


def test_enrollment_mismatch_blocked(
    client: TestClient,
    db_session: Session,
) -> None:
    organization = create_organization_record(db_session, slug="signal-enrollment")
    user = create_user_for_org(
        db_session,
        organization=organization,
        email="signal5@example.com",
        password="Secret123!",
    )
    headers = auth_headers(client, user.email, "Secret123!")
    patient_one = create_patient_for_user(client, headers, first_name="SignalOne")
    patient_two = create_patient_for_user(client, headers, first_name="SignalTwo")

    enrollment_resp = client.post(
        f"/api/v1/patients/{patient_two}/enrollments",
        json={"track_code": "track-a"},
        headers=headers,
    )
    enrollment_id = enrollment_resp.json()["id"]

    resp = client.post(
        f"/api/v1/patients/{patient_one}/signals",
        json={
            "signal_type": "symptom_score",
            "signal_value_numeric": 10,
            "enrollment_id": enrollment_id,
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_acknowledge_and_resolve_escalation_flow(
    client: TestClient,
    db_session: Session,
) -> None:
    organization = create_organization_record(db_session, slug="signal-escalation-flow")
    user = create_user_for_org(
        db_session,
        organization=organization,
        email="signal6@example.com",
        password="Secret123!",
    )
    headers = auth_headers(client, user.email, "Secret123!")
    patient_id = create_patient_for_user(client, headers, first_name="Workflow")

    create_resp = client.post(
        f"/api/v1/patients/{patient_id}/signals",
        json={
            "signal_type": "symptom_score",
            "signal_value_numeric": 12,
        },
        headers=headers,
    )
    escalation_id = create_resp.json()["escalation"]["id"]

    ack_resp = client.post(
        f"/api/v1/escalations/{escalation_id}/acknowledge",
        headers=headers,
    )
    assert ack_resp.status_code == 200
    assert ack_resp.json()["in_progress_at"] is not None
    assert ack_resp.json()["status"] == "in_progress"

    resolve_resp = client.post(
        f"/api/v1/escalations/{escalation_id}/resolve",
        json={"resolution_notes": "Reviewed by clinician"},
        headers=headers,
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["status"] == "resolved"
    assert resolve_resp.json()["resolution_notes"] == "Reviewed by clinician"
    assert resolve_resp.json()["resolved_at"] is not None

    repeat_resp = client.post(
        f"/api/v1/escalations/{escalation_id}/resolve",
        json={"resolution_notes": "Duplicate"},
        headers=headers,
    )
    assert repeat_resp.status_code == 409


def test_cross_tenant_signal_creation_blocked(
    client: TestClient,
    db_session: Session,
) -> None:
    org_one = create_organization_record(db_session, slug="signal-cross-tenant-a")
    org_two = create_organization_record(db_session, slug="signal-cross-tenant-b")
    user_one = create_user_for_org(
        db_session,
        organization=org_one,
        email="signal7@example.com",
        password="Secret123!",
    )
    user_two = create_user_for_org(
        db_session,
        organization=org_two,
        email="signal8@example.com",
        password="Secret123!",
    )
    headers_one = auth_headers(client, user_one.email, "Secret123!")
    headers_two = auth_headers(client, user_two.email, "Secret123!")
    patient_id = create_patient_for_user(client, headers_one, first_name="Protected")

    resp = client.post(
        f"/api/v1/patients/{patient_id}/signals",
        json={
            "signal_type": "symptom_score",
            "signal_value_numeric": 8,
        },
        headers=headers_two,
    )
    assert resp.status_code == 403


def test_escalation_status_endpoint_allows_cancellation_with_note(
    client: TestClient,
    db_session: Session,
) -> None:
    organization = create_organization_record(db_session, slug="signal-status-cancel")
    user = create_user_for_org(
        db_session,
        organization=organization,
        email="status-cancel@example.com",
        password="Secret123!",
    )
    headers = auth_headers(client, user.email, "Secret123!")
    patient_id = create_patient_for_user(client, headers, first_name="StatusFlow")

    create_resp = client.post(
        f"/api/v1/patients/{patient_id}/signals",
        json={"signal_type": "symptom_score", "signal_value_numeric": 10},
        headers=headers,
    )
    escalation_id = create_resp.json()["escalation"]["id"]

    cancel_resp = client.post(
        f"/api/v1/escalations/{escalation_id}/status",
        json={"status": "canceled", "note": "Duplicate report"},
        headers=headers,
    )
    assert cancel_resp.status_code == 200
    payload = cancel_resp.json()
    assert payload["status"] == "canceled"
    assert payload["canceled_at"] is not None
    assert payload["cancellation_notes"] == "Duplicate report"


def test_escalation_status_endpoint_blocks_invalid_transition(
    client: TestClient,
    db_session: Session,
) -> None:
    organization = create_organization_record(db_session, slug="signal-status-invalid")
    user = create_user_for_org(
        db_session,
        organization=organization,
        email="status-invalid@example.com",
        password="Secret123!",
    )
    headers = auth_headers(client, user.email, "Secret123!")
    patient_id = create_patient_for_user(client, headers, first_name="InvalidStatus")

    create_resp = client.post(
        f"/api/v1/patients/{patient_id}/signals",
        json={"signal_type": "symptom_score", "signal_value_numeric": 10},
        headers=headers,
    )
    escalation_id = create_resp.json()["escalation"]["id"]

    client.post(
        f"/api/v1/escalations/{escalation_id}/status",
        json={"status": "resolved", "note": "Handled"},
        headers=headers,
    )
    revert_resp = client.post(
        f"/api/v1/escalations/{escalation_id}/status",
        json={"status": "in_progress"},
        headers=headers,
    )
    assert revert_resp.status_code == 409


def test_escalation_status_endpoint_rejects_cross_tenant_updates(
    client: TestClient,
    db_session: Session,
) -> None:
    org_one = create_organization_record(db_session, slug="signal-status-tenant-a")
    org_two = create_organization_record(db_session, slug="signal-status-tenant-b")
    user_one = create_user_for_org(
        db_session,
        organization=org_one,
        email="status-tenant-a@example.com",
        password="Secret123!",
    )
    user_two = create_user_for_org(
        db_session,
        organization=org_two,
        email="status-tenant-b@example.com",
        password="Secret123!",
    )
    headers_one = auth_headers(client, user_one.email, "Secret123!")
    headers_two = auth_headers(client, user_two.email, "Secret123!")
    patient_id = create_patient_for_user(client, headers_one, first_name="TenantProtected")

    create_resp = client.post(
        f"/api/v1/patients/{patient_id}/signals",
        json={"signal_type": "symptom_score", "signal_value_numeric": 10},
        headers=headers_one,
    )
    escalation_id = create_resp.json()["escalation"]["id"]

    resp = client.post(
        f"/api/v1/escalations/{escalation_id}/status",
        json={"status": "in_progress"},
        headers=headers_two,
    )
    assert resp.status_code == 403
