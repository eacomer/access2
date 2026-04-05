from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.users import create_user


def create_organization_record(
    db: Session,
    *,
    name: str = "Care Org",
    slug: str | None = None,
) -> Organization:
    slug_value = slug or f"org-{uuid4().hex[:8]}"
    organization = Organization(name=name, slug=slug_value, is_active=True)
    db.add(organization)
    db.commit()
    db.refresh(organization)
    return organization


def create_user_for_org(
    db: Session,
    *,
    organization: Organization,
    email: str,
    password: str,
    is_superuser: bool = False,
) -> User:
    user = create_user(
        db=db,
        user_in=UserCreate(
            email=email,
            password=password,
            full_name="Tenant User",
            organization_id=organization.id,
        ),
    )
    if is_superuser and not user.is_superuser:
        user.is_superuser = True
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def auth_headers(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_and_get_patient(client: TestClient, db_session: Session) -> None:
    organization = create_organization_record(db_session, slug="patients-org")
    user = create_user_for_org(
        db_session,
        organization=organization,
        email="tenant@example.com",
        password="Secret123!",
    )
    headers = auth_headers(client, user.email, "Secret123!")

    create_resp = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Lena",
            "last_name": "Rivera",
            "date_of_birth": "1990-01-01",
            "sex": "female",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    patient_id = create_resp.json()["id"]

    get_resp = client.get(f"/api/v1/patients/{patient_id}", headers=headers)
    assert get_resp.status_code == 200
    payload = get_resp.json()
    assert payload["first_name"] == "Lena"
    assert payload["organization_id"] == str(organization.id)


def test_list_patients_scoped_to_organization(
    client: TestClient, db_session: Session
) -> None:
    org_one = create_organization_record(db_session, slug="org-one")
    org_two = create_organization_record(db_session, slug="org-two")
    user_one = create_user_for_org(
        db_session,
        organization=org_one,
        email="org1@example.com",
        password="Secret123!",
    )
    user_two = create_user_for_org(
        db_session,
        organization=org_two,
        email="org2@example.com",
        password="Secret123!",
    )

    headers_one = auth_headers(client, user_one.email, "Secret123!")
    headers_two = auth_headers(client, user_two.email, "Secret123!")

    client.post(
        "/api/v1/patients",
        json={
            "first_name": "Ari",
            "last_name": "Stone",
            "date_of_birth": "1985-05-05",
        },
        headers=headers_one,
    )
    client.post(
        "/api/v1/patients",
        json={
            "first_name": "Blair",
            "last_name": "Lopez",
            "date_of_birth": "1980-10-10",
        },
        headers=headers_two,
    )

    list_resp = client.get("/api/v1/patients", headers=headers_one)
    assert list_resp.status_code == 200
    payload = list_resp.json()
    assert len(payload) == 1
    assert payload[0]["first_name"] == "Ari"


def test_cross_tenant_patient_access_denied(
    client: TestClient, db_session: Session
) -> None:
    org_one = create_organization_record(db_session, slug="primary-org")
    org_two = create_organization_record(db_session, slug="secondary-org")
    user_one = create_user_for_org(
        db_session,
        organization=org_one,
        email="tenant1@example.com",
        password="Secret123!",
    )
    user_two = create_user_for_org(
        db_session,
        organization=org_two,
        email="tenant2@example.com",
        password="Secret123!",
    )

    headers_one = auth_headers(client, user_one.email, "Secret123!")
    headers_two = auth_headers(client, user_two.email, "Secret123!")

    create_resp = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Tessa",
            "last_name": "Hayes",
            "date_of_birth": "1992-02-02",
        },
        headers=headers_two,
    )
    patient_id = create_resp.json()["id"]

    get_resp = client.get(f"/api/v1/patients/{patient_id}", headers=headers_one)
    assert get_resp.status_code == 403


def create_patient_for_user(
    client: TestClient,
    headers: dict[str, str],
    first_name: str = "Mara",
) -> str:
    resp = client.post(
        "/api/v1/patients",
        json={
            "first_name": first_name,
            "last_name": "Quinn",
            "date_of_birth": "1993-03-03",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_create_enrollment_for_patient(client: TestClient, db_session: Session) -> None:
    organization = create_organization_record(db_session, slug="enroll-org")
    user = create_user_for_org(
        db_session,
        organization=organization,
        email="enroll@example.com",
        password="Secret123!",
    )
    headers = auth_headers(client, user.email, "Secret123!")
    patient_id = create_patient_for_user(client, headers)

    enroll_resp = client.post(
        f"/api/v1/patients/{patient_id}/enrollments",
        json={
            "track_code": "access-track",
            "enrollment_status": "pending",
        },
        headers=headers,
    )

    assert enroll_resp.status_code == 201
    payload = enroll_resp.json()
    assert payload["track_code"] == "access-track"
    assert payload["patient_id"] == patient_id


def test_cross_tenant_enrollment_blocked(
    client: TestClient, db_session: Session
) -> None:
    org_one = create_organization_record(db_session, slug="enroll-tenant-one")
    org_two = create_organization_record(db_session, slug="enroll-tenant-two")
    user_one = create_user_for_org(
        db_session,
        organization=org_one,
        email="enroll1@example.com",
        password="Secret123!",
    )
    user_two = create_user_for_org(
        db_session,
        organization=org_two,
        email="enroll2@example.com",
        password="Secret123!",
    )

    headers_one = auth_headers(client, user_one.email, "Secret123!")
    headers_two = auth_headers(client, user_two.email, "Secret123!")
    patient_id = create_patient_for_user(client, headers_two, first_name="Noah")

    enroll_resp = client.post(
        f"/api/v1/patients/{patient_id}/enrollments",
        json={"track_code": "access-track"},
        headers=headers_one,
    )

    assert enroll_resp.status_code == 403


def test_consent_timestamp_set_on_consented(
    client: TestClient, db_session: Session
) -> None:
    organization = create_organization_record(db_session, slug="consent-org")
    user = create_user_for_org(
        db_session,
        organization=organization,
        email="consent@example.com",
        password="Secret123!",
    )
    headers = auth_headers(client, user.email, "Secret123!")
    patient_id = create_patient_for_user(client, headers)

    enroll_resp = client.post(
        f"/api/v1/patients/{patient_id}/enrollments",
        json={"track_code": "signal-track"},
        headers=headers,
    )
    enrollment_id = enroll_resp.json()["id"]

    update_resp = client.patch(
        f"/api/v1/patients/enrollments/{enrollment_id}",
        json={"consent_status": "consented"},
        headers=headers,
    )

    assert update_resp.status_code == 200
    assert update_resp.json()["consented_at"] is not None


def test_enrollment_status_timestamps(client: TestClient, db_session: Session) -> None:
    organization = create_organization_record(db_session, slug="status-org")
    user = create_user_for_org(
        db_session,
        organization=organization,
        email="status@example.com",
        password="Secret123!",
    )
    headers = auth_headers(client, user.email, "Secret123!")
    patient_id = create_patient_for_user(client, headers)

    enroll_resp = client.post(
        f"/api/v1/patients/{patient_id}/enrollments",
        json={"track_code": "care-track"},
        headers=headers,
    )
    enrollment_id = enroll_resp.json()["id"]

    activate_resp = client.patch(
        f"/api/v1/patients/enrollments/{enrollment_id}",
        json={"enrollment_status": "active"},
        headers=headers,
    )
    assert activate_resp.status_code == 200
    assert activate_resp.json()["enrollment_started_at"] is not None

    complete_resp = client.patch(
        f"/api/v1/patients/enrollments/{enrollment_id}",
        json={"enrollment_status": "completed"},
        headers=headers,
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["enrollment_ended_at"] is not None
