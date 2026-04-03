from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.users import create_user


def create_organization_record(
    db: Session,
    *,
    name: str = "Test Organization",
    slug: str | None = None,
) -> Organization:
    slug_value = slug or f"org-{uuid4().hex[:8]}"
    organization = Organization(name=name, slug=slug_value, is_active=True)
    db.add(organization)
    db.commit()
    db.refresh(organization)
    return organization


def create_user_record(
    db: Session,
    *,
    email: str,
    password: str,
    full_name: str | None = None,
    is_superuser: bool = False,
    is_active: bool = True,
    organization_id: UUID | None = None,
) -> User:
    organization_id = organization_id or create_organization_record(db).id

    user = create_user(
        db=db,
        user_in=UserCreate(
            email=email,
            password=password,
            full_name=full_name,
            organization_id=organization_id,
        ),
    )
    changed = False
    if is_superuser and not user.is_superuser:
        user.is_superuser = True
        changed = True
    if not is_active and user.is_active:
        user.is_active = False
        changed = True

    if changed:
        db.add(user)
        db.commit()
        db.refresh(user)

    return user


def login_and_get_token(client: TestClient, email: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_non_superuser_cannot_list_users(
    client: TestClient, db_session: Session
) -> None:
    create_user_record(
        db_session,
        email="regular@example.com",
        password="Secret123!",
        full_name="Regular User",
    )

    token = login_and_get_token(
        client, email="regular@example.com", password="Secret123!"
    )

    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Superuser privileges required."


def test_superuser_can_list_users(client: TestClient, db_session: Session) -> None:
    organization = create_organization_record(db_session, slug="list-org")
    create_user_record(
        db_session,
        email="demo@example.com",
        password="Secret123!",
        full_name="Demo User",
        organization_id=organization.id,
    )
    create_user_record(
        db_session,
        email="admin@example.com",
        password="Admin123!",
        full_name="Admin User",
        is_superuser=True,
        organization_id=organization.id,
    )

    token = login_and_get_token(
        client,
        email="admin@example.com",
        password="Admin123!",
    )

    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert any(user["email"] == "demo@example.com" for user in payload)


def test_superuser_can_update_full_name(
    client: TestClient, db_session: Session
) -> None:
    organization = create_organization_record(db_session, slug="update-org")
    target_user = create_user_record(
        db_session,
        email="demo@example.com",
        password="Secret123!",
        full_name="Demo User",
        organization_id=organization.id,
    )
    create_user_record(
        db_session,
        email="admin@example.com",
        password="Admin123!",
        full_name="Admin User",
        is_superuser=True,
        organization_id=organization.id,
    )

    token = login_and_get_token(
        client,
        email="admin@example.com",
        password="Admin123!",
    )

    response = client.patch(
        f"/api/v1/users/{target_user.id}",
        json={"full_name": "Updated Name"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated Name"


def test_superuser_can_deactivate_user(
    client: TestClient, db_session: Session
) -> None:
    organization = create_organization_record(db_session, slug="deactivate-org")
    target_user = create_user_record(
        db_session,
        email="demo@example.com",
        password="Secret123!",
        full_name="Demo User",
        organization_id=organization.id,
    )
    create_user_record(
        db_session,
        email="admin@example.com",
        password="Admin123!",
        full_name="Admin User",
        is_superuser=True,
        organization_id=organization.id,
    )

    token = login_and_get_token(
        client,
        email="admin@example.com",
        password="Admin123!",
    )

    response = client.patch(
        f"/api/v1/users/{target_user.id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@example.com", "password": "Secret123!"},
    )
    assert login_response.status_code == 403
    assert login_response.json()["detail"] == "User account is inactive."


def test_deactivated_user_token_is_blocked(
    client: TestClient, db_session: Session
) -> None:
    organization = create_organization_record(db_session, slug="block-org")
    target_user = create_user_record(
        db_session,
        email="demo@example.com",
        password="Secret123!",
        full_name="Demo User",
        organization_id=organization.id,
    )
    create_user_record(
        db_session,
        email="admin@example.com",
        password="Admin123!",
        full_name="Admin User",
        is_superuser=True,
        organization_id=organization.id,
    )

    target_token = login_and_get_token(
        client,
        email="demo@example.com",
        password="Secret123!",
    )

    admin_token = login_and_get_token(
        client,
        email="admin@example.com",
        password="Admin123!",
    )

    deactivate_resp = client.patch(
        f"/api/v1/users/{target_user.id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert deactivate_resp.status_code == 200

    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {target_token}"},
    )

    assert me_resp.status_code == 403
    assert me_resp.json()["detail"] == "User account is inactive."


def test_create_user_requires_valid_organization_id(
    client: TestClient, db_session: Session
) -> None:
    organization = create_organization_record(db_session, slug="admin-org")
    admin_user = create_user_record(
        db_session,
        email="admin@example.com",
        password="Admin123!",
        is_superuser=True,
        organization_id=organization.id,
    )

    token = login_and_get_token(
        client,
        email=admin_user.email,
        password="Admin123!",
    )

    response = client.post(
        "/api/v1/users",
        json={
            "email": "new@example.com",
            "password": "Secret123!",
            "organization_id": str(uuid4()),
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Organization not found or inactive."
