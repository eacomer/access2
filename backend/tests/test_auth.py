from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.schemas.user import UserCreate
from app.services.users import create_user


def create_demo_user(
    db: Session,
    *,
    email: str = "demo@example.com",
    password: str = "Secret123!",
    full_name: str | None = "Demo User",
    is_active: bool = True,
) -> None:
    user = create_user(
        db=db,
        user_in=UserCreate(
            email=email,
            password=password,
            full_name=full_name,
        ),
    )

    if not is_active:
        user.is_active = False
        db.add(user)
        db.commit()
        db.refresh(user)


def test_login_success_returns_token(client: TestClient, db_session: Session) -> None:
    create_demo_user(db_session)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@example.com", "password": "Secret123!"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "access_token" in payload
    assert payload["token_type"] == "bearer"


def test_login_with_wrong_password_returns_401(
    client: TestClient, db_session: Session
) -> None:
    create_demo_user(db_session)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@example.com", "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_me_requires_bearer_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated."


def test_me_with_valid_token_returns_user(
    client: TestClient, db_session: Session
) -> None:
    create_demo_user(db_session)

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@example.com", "password": "Secret123!"},
    )
    token = login_resp.json()["access_token"]

    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_resp.status_code == 200
    body = me_resp.json()
    assert body["email"] == "demo@example.com"
    assert "hashed_password" not in body


def test_inactive_user_login_returns_403(
    client: TestClient, db_session: Session
) -> None:
    create_demo_user(db_session, is_active=False)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@example.com", "password": "Secret123!"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "User account is inactive."
