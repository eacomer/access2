"""
One-time demo user seed for ACCESS2 Railway deployment.

Creates:
- admin@example.com / Admin123! / superuser
- demo@example.com / Secret123! / regular user

Safe to re-run: it skips users that already exist.
"""

from __future__ import annotations

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.organization import Organization
from app.models.user import User


ORG_SLUG = "access2-demo"
ORG_NAME = "ACCESS2 Demo Organization"


def get_or_create_org(db):
    organization = db.execute(
        select(Organization).where(Organization.slug == ORG_SLUG)
    ).scalar_one_or_none()

    if organization:
        print(f"SKIP existing org: {ORG_SLUG}")
        return organization

    organization = Organization(
        name=ORG_NAME,
        slug=ORG_SLUG,
    )
    db.add(organization)
    db.flush()

    print(f"CREATED org: {ORG_SLUG}")
    return organization


def create_user_if_missing(
    db,
    *,
    organization_id,
    email: str,
    password: str,
    full_name: str,
    is_superuser: bool,
):
    existing_user = db.execute(
        select(User).where(User.email == email)
    ).scalar_one_or_none()

    if existing_user:
        print(f"SKIP existing user: {email}")
        return existing_user

    user = User(
        email=email,
        full_name=full_name,
        hashed_password=get_password_hash(password),
        is_active=True,
        is_superuser=is_superuser,
        organization_id=organization_id,
    )
    db.add(user)
    db.flush()

    print(f"CREATED user: {email}")
    return user


def main():
    with SessionLocal() as db:
        organization = get_or_create_org(db)

        create_user_if_missing(
            db,
            organization_id=organization.id,
            email="admin@example.com",
            password="Admin123!",
            full_name="Admin User",
            is_superuser=True,
        )

        create_user_if_missing(
            db,
            organization_id=organization.id,
            email="demo@example.com",
            password="Secret123!",
            full_name="Demo User",
            is_superuser=False,
        )

        db.commit()

    print("Seed complete.")


if __name__ == "__main__":
    main()