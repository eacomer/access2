from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.models.organization import Organization
from app.models.user import User


@dataclass(slots=True)
class RequestContext:
    """Carries the authenticated principal and their active organization."""

    user: User
    organization: Organization

    @property
    def is_superuser(self) -> bool:
        return self.user.is_superuser

    @property
    def organization_id(self) -> UUID:
        return self.organization.id

