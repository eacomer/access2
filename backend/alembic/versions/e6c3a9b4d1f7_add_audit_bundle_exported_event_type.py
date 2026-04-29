"""add audit bundle exported event type

Revision ID: e6c3a9b4d1f7
Revises: d4a1b7c3e9f2
Create Date: 2026-04-26 09:30:00.000000
"""

from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "e6c3a9b4d1f7"
down_revision = "d4a1b7c3e9f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_enum e ON e.enumtypid = t.oid
                WHERE t.typname = 'accessreviewpacketsnapshoteventtype'
                  AND e.enumlabel = 'audit_bundle_exported'
            ) THEN
                ALTER TYPE accessreviewpacketsnapshoteventtype
                ADD VALUE 'audit_bundle_exported';
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    # PostgreSQL enum value removal is intentionally left as a no-op.
    # Existing rows may already reference this immutable audit event type.
    pass
