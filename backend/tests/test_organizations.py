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
    name: str = "Seed Org",
    slug: str | None = None,
) -> Organization:
    slug_value = slug or f"org-{uuid4().hex[:8]}"
    organization = Organization(name=name, slug=slug_value, is_active=True)
    db.add(organization)
    db.commit()
    db.refresh(organization)
    return organization


def create_superuser(
    db: Session,
    *,
    email: str = "admin@example.com",
    password: str = "Admin123!",
) -> User:
    organization = create_organization_record(db, slug="admin-org")
    user = create_user(
        db=db,
        user_in=UserCreate(
            email=email,
            password=password,
            full_name="Admin User",
            organization_id=organization.id,
        ),
    )
    user.is_superuser = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_regular_user(
    db: Session,
    *,
    email: str = "user@example.com",
    password: str = "Secret123!",
) -> User:
    organization = create_organization_record(db, slug="regular-org")
    user = create_user(
        db=db,
        user_in=UserCreate(
            email=email,
            password=password,
            full_name="Regular User",
            organization_id=organization.id,
        ),
    )
    return user


def auth_headers(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_superuser_can_create_organization(
    client: TestClient, db_session: Session
) -> None:
    admin = create_superuser(db_session)
    headers = auth_headers(client, admin.email, "Admin123!")

    response = client.post(
        "/api/v1/organizations",
        json={"name": "Care Group", "slug": "Care-Group"},
        headers=headers,
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "Care Group"
    assert payload["slug"] == "care-group"


def test_superuser_can_list_organizations(
    client: TestClient, db_session: Session
) -> None:
    admin = create_superuser(db_session)
    create_organization_record(db_session, name="Org A", slug="org-a")
    create_organization_record(db_session, name="Org B", slug="org-b")

    headers = auth_headers(client, admin.email, "Admin123!")
    response = client.get("/api/v1/organizations", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    slugs = {org["slug"] for org in payload}
    assert {"org-a", "org-b"}.issubset(slugs)


def test_superuser_can_get_organization_by_id(
    client: TestClient, db_session: Session
) -> None:
    admin = create_superuser(db_session)
    organization = create_organization_record(
        db_session, name="Target Org", slug="target-org"
    )

    headers = auth_headers(client, admin.email, "Admin123!")
    response = client.get(
        f"/api/v1/organizations/{organization.id}",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(organization.id)
    assert payload["slug"] == "target-org"


def test_non_superuser_cannot_access_organization_routes(
    client: TestClient, db_session: Session
) -> None:
    create_superuser(db_session)
    user = create_regular_user(db_session)

    headers = auth_headers(client, user.email, "Secret123!")
    response = client.get("/api/v1/organizations", headers=headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "Superuser privileges required."


def test_slug_uniqueness_is_enforced(
    client: TestClient, db_session: Session
) -> None:
    admin = create_superuser(db_session)
    headers = auth_headers(client, admin.email, "Admin123!")

    first_resp = client.post(
        "/api/v1/organizations",
        json={"name": "Primary", "slug": "unique-slug"},
        headers=headers,
    )
    assert first_resp.status_code == 201

    dup_resp = client.post(
        "/api/v1/organizations",
        json={"name": "Another", "slug": "unique-slug"},
        headers=headers,
    )
    assert dup_resp.status_code == 409
    assert dup_resp.json()["detail"] == "An organization with this slug already exists."
