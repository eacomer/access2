from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.context import RequestContext


class OrganizationAccessError(Exception):
    """Raised when a user attempts to act outside their organization scope."""


class MissingOrganizationContextError(Exception):
    """Raised when a resource lacks an organization identifier."""


def ensure_organization_access(
    *,
    context: RequestContext,
    organization_id: UUID,
) -> None:
    """Ensure the user can operate on the provided organization identifier."""
    if context.user.is_superuser:
        return

    if context.organization_id != organization_id:
        raise OrganizationAccessError(
            "Operation limited to the authenticated user's organization."
        )


def ensure_tenant_scoped_resource(
    *,
    context: RequestContext,
    resource: Any,
    organization_attr: str = "organization_id",
) -> None:
    """Ensure the user can operate on the provided tenant-scoped resource."""
    resource_org_id = getattr(resource, organization_attr, None)
    if resource_org_id is None:
        raise MissingOrganizationContextError(
            f"Resource is missing {organization_attr} for authorization."
        )

    ensure_organization_access(context=context, organization_id=resource_org_id)
