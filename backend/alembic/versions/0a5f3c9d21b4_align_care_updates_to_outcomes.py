"""align care updates to outcomes

Revision ID: 0a5f3c9d21b4
Revises: a6d2bdb3a710
Create Date: 2026-04-23

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0a5f3c9d21b4"
down_revision: Union[str, Sequence[str], None] = "a6d2bdb3a710"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(
        op.f("ix_care_updates_intervention_task_outcome_id"),
        table_name="care_updates",
    )
    op.drop_constraint(
        "care_updates_intervention_task_outcome_id_fkey",
        "care_updates",
        type_="foreignkey",
    )
    op.alter_column(
        "care_updates",
        "intervention_task_outcome_id",
        new_column_name="outcome_id",
        existing_type=sa.UUID(),
        existing_nullable=True,
    )
    op.create_foreign_key(
        "care_updates_outcome_id_fkey",
        "care_updates",
        "outcomes",
        ["outcome_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_care_updates_outcome_id"),
        "care_updates",
        ["outcome_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_care_updates_outcome_id"), table_name="care_updates")
    op.drop_constraint("care_updates_outcome_id_fkey", "care_updates", type_="foreignkey")
    op.alter_column(
        "care_updates",
        "outcome_id",
        new_column_name="intervention_task_outcome_id",
        existing_type=sa.UUID(),
        existing_nullable=True,
    )
    op.create_foreign_key(
        "care_updates_intervention_task_outcome_id_fkey",
        "care_updates",
        "intervention_task_outcomes",
        ["intervention_task_outcome_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_care_updates_intervention_task_outcome_id"),
        "care_updates",
        ["intervention_task_outcome_id"],
    )
