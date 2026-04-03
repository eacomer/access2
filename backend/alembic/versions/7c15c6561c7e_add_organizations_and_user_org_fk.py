"""add organizations and user organization fk

Revision ID: 7c15c6561c7e
Revises: 4243ca3ef2c3
Create Date: 2026-04-03

"""
from __future__ import annotations

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "7c15c6561c7e"
down_revision: Union[str, Sequence[str], None] = "4243ca3ef2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_organizations_slug"),
        "organizations",
        ["slug"],
        unique=True,
    )

    default_org_id = uuid.uuid4()
    organizations_table = sa.table(
        "organizations",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String(length=255)),
        sa.column("slug", sa.String(length=255)),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        organizations_table,
        [
            {
                "id": default_org_id,
                "name": "Default Organization",
                "slug": "default",
                "is_active": True,
            }
        ],
    )

    op.add_column(
        "users",
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.execute(
        sa.text("UPDATE users SET organization_id = :org_id").bindparams(
            org_id=default_org_id
        )
    )
    op.alter_column(
        "users",
        "organization_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.create_foreign_key(
        "users_organization_id_fkey",
        "users",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "users_organization_id_fkey",
        "users",
        type_="foreignkey",
    )
    op.drop_column("users", "organization_id")
    op.drop_index(op.f("ix_organizations_slug"), table_name="organizations")
    op.drop_table("organizations")
