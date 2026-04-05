from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_organization, get_request_context
from app.core.context import RequestContext
from app.models.organization import Organization
from app.models.user import User
from app.services.authz import (
    MissingOrganizationContextError,
    OrganizationAccessError,
    ensure_organization_access,
    ensure_tenant_scoped_resource,
)


def create_organization(db: Session, slug: str) -> Organization:
    organization = Organization(name="Tenant", slug=slug, is_active=True)
    db.add(organization)
    db.commit()
    db.refresh(organization)
    return organization


def create_user(
    db: Session,
    *,
    organization: Organization,
    email: str = "user@example.com",
    is_superuser: bool = False,
) -> User:
    user = User(
        email=email,
        full_name="Tenant User",
        hashed_password="hashed-password",
        is_active=True,
        is_superuser=is_superuser,
        organization_id=organization.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_get_current_organization_returns_active_org(db_session: Session) -> None:
    organization = create_organization(db_session, slug="ctx-org")
    user = create_user(db_session, organization=organization)

    current_org = get_current_organization(current_user=user, db=db_session)

    assert current_org.id == organization.id


def test_get_current_organization_rejects_inactive_org(db_session: Session) -> None:
    organization = create_organization(db_session, slug="inactive-org")
    organization.is_active = False
    db_session.add(organization)
    db_session.commit()
    user = create_user(db_session, organization=organization)

    with pytest.raises(HTTPException) as exc:
        get_current_organization(current_user=user, db=db_session)

    assert exc.value.status_code == 403
    assert exc.value.detail == "Organization is not available."


def test_get_request_context_includes_user_and_org(db_session: Session) -> None:
    organization = create_organization(db_session, slug="context-org")
    user = create_user(db_session, organization=organization)

    context = get_request_context(current_user=user, organization=organization)

    assert context.user.id == user.id
    assert context.organization.id == organization.id


def test_ensure_organization_access_allows_superuser(db_session: Session) -> None:
    organization = create_organization(db_session, slug="superuser-org")
    user = create_user(db_session, organization=organization, is_superuser=True)
    context = RequestContext(user=user, organization=organization)

    ensure_organization_access(
        context=context,
        organization_id=uuid4(),
    )


def test_ensure_organization_access_blocks_cross_org(db_session: Session) -> None:
    organization = create_organization(db_session, slug="primary-org")
    user = create_user(db_session, organization=organization)
    context = RequestContext(user=user, organization=organization)

    with pytest.raises(OrganizationAccessError):
        ensure_organization_access(
            context=context,
            organization_id=uuid4(),
        )


def test_ensure_tenant_scoped_resource_validates_attribute(db_session: Session) -> None:
    organization = create_organization(db_session, slug="resource-org")
    user = create_user(db_session, organization=organization)
    context = RequestContext(user=user, organization=organization)

    class ResourceWithoutOrg:
        pass

    with pytest.raises(MissingOrganizationContextError):
        ensure_tenant_scoped_resource(context=context, resource=ResourceWithoutOrg())


def test_ensure_tenant_scoped_resource_enforces_scope(db_session: Session) -> None:
    organization = create_organization(db_session, slug="resource-scope-org")
    user = create_user(db_session, organization=organization)
    context = RequestContext(user=user, organization=organization)

    class OtherResource:
        def __init__(self, organization_id: UUID):
            self.organization_id = organization_id

    resource = OtherResource(uuid4())

    with pytest.raises(OrganizationAccessError):
        ensure_tenant_scoped_resource(context=context, resource=resource)


def test_ensure_tenant_scoped_resource_allows_same_org(db_session: Session) -> None:
    organization = create_organization(db_session, slug="resource-allow-org")
    user = create_user(db_session, organization=organization)
    context = RequestContext(user=user, organization=organization)

    class Resource:
        def __init__(self, organization_id: UUID):
            self.organization_id = organization_id

    resource = Resource(organization.id)

    ensure_tenant_scoped_resource(context=context, resource=resource)
