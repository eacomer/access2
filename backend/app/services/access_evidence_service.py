from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import RequestContext
from app.models.intervention_task import InterventionTask
from app.models.outcome import Outcome
from app.models.patient import Patient
from app.services.authz import ensure_tenant_scoped_resource

LOWER_IS_BETTER = {"systolic_bp", "diastolic_bp", "a1c", "missed_days"}
HIGHER_IS_BETTER = {"completed_checkins", "completed_checkin", "adherence_rate"}


def build_access_evidence_report(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
) -> dict[str, Any]:
    ensure_tenant_scoped_resource(context=context, resource=patient)
    outcomes = _load_outcomes(db=db, patient=patient)
    tasks = _load_tasks(db=db, patient=patient)
    return {
        "patient_id": patient.id,
        "outcome_summaries": _summarize_outcomes(outcomes),
        "intervention_outcome_links": _derive_intervention_outcome_links(
            tasks=tasks,
            outcomes=outcomes,
        ),
    }


def _load_outcomes(*, db: Session, patient: Patient) -> list[Outcome]:
    stmt = (
        select(Outcome)
        .where(Outcome.patient_id == patient.id)
        .order_by(Outcome.observed_at, Outcome.id)
    )
    return list(db.execute(stmt).scalars().all())


def _load_tasks(*, db: Session, patient: Patient) -> list[InterventionTask]:
    stmt = select(InterventionTask).where(InterventionTask.patient_id == patient.id)
    return list(db.execute(stmt).scalars().all())


def _summarize_outcomes(outcomes: list[Outcome]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Outcome]] = defaultdict(list)
    for outcome in outcomes:
        grouped[outcome.metric_name].append(outcome)

    summaries: list[dict[str, Any]] = []
    for metric_name in sorted(grouped):
        metric_outcomes = sorted(
            grouped[metric_name],
            key=lambda outcome: (_normalize_datetime(outcome.observed_at), str(outcome.id)),
        )
        baseline = metric_outcomes[0]
        latest = metric_outcomes[-1]
        numeric = baseline.value_numeric is not None and latest.value_numeric is not None
        delta = latest.value_numeric - baseline.value_numeric if numeric else None
        summaries.append(
            {
                "metric_name": metric_name,
                "baseline": baseline.value_numeric
                if baseline.value_numeric is not None
                else baseline.value_text,
                "latest": latest.value_numeric if latest.value_numeric is not None else latest.value_text,
                "delta": delta,
                "status": _trend_status(
                    metric_name=metric_name,
                    outcome_count=len(metric_outcomes),
                    delta=delta,
                    numeric=numeric,
                ),
                "direction": _metric_direction(metric_name),
                "baseline_outcome_id": baseline.id,
                "latest_outcome_id": latest.id,
            }
        )
    return summaries


def _trend_status(
    *,
    metric_name: str,
    outcome_count: int,
    delta: float | None,
    numeric: bool,
) -> str:
    if outcome_count < 2:
        return "insufficient_data"
    if not numeric or delta is None:
        return "insufficient_data"
    if delta == 0:
        return "stable"

    direction = _metric_direction(metric_name)
    if direction == "lower_is_better":
        return "improved" if delta < 0 else "worsened"
    if direction == "higher_is_better":
        return "improved" if delta > 0 else "worsened"
    return "stable"


def _metric_direction(metric_name: str) -> str:
    normalized = metric_name.strip().lower()
    if normalized in LOWER_IS_BETTER:
        return "lower_is_better"
    if normalized in HIGHER_IS_BETTER:
        return "higher_is_better"
    return "unknown_direction"


def _derive_intervention_outcome_links(
    *,
    tasks: list[InterventionTask],
    outcomes: list[Outcome],
) -> list[dict[str, Any]]:
    outcomes_by_task: dict[Any, list[Outcome]] = defaultdict(list)
    for outcome in outcomes:
        if outcome.intervention_task_id is not None:
            outcomes_by_task[outcome.intervention_task_id].append(outcome)

    links: list[dict[str, Any]] = []
    for task in sorted(tasks, key=lambda item: (_task_timestamp(item), str(item.id))):
        linked = sorted(
            outcomes_by_task.get(task.id, []),
            key=lambda outcome: (_normalize_datetime(outcome.observed_at), str(outcome.id)),
        )
        if not linked:
            continue

        intervention_timestamp = task.completed_at or task.created_at
        after_flags = [
            _normalize_datetime(outcome.observed_at) >= _normalize_datetime(intervention_timestamp)
            for outcome in linked
            if intervention_timestamp is not None
        ]
        first_lag_hours = None
        if intervention_timestamp is not None:
            first_lag = _normalize_datetime(linked[0].observed_at) - _normalize_datetime(
                intervention_timestamp
            )
            first_lag_hours = first_lag.total_seconds() / 3600

        links.append(
            {
                "intervention_task_id": task.id,
                "intervention_timestamp": intervention_timestamp,
                "linked_outcome_ids": [outcome.id for outcome in linked],
                "linked_outcome_metric_names": sorted({outcome.metric_name for outcome in linked}),
                "outcomes_after_intervention": bool(after_flags) and all(after_flags),
                "first_outcome_lag_hours": first_lag_hours,
                "first_outcome_lag_days": first_lag_hours / 24 if first_lag_hours is not None else None,
            }
        )
    return links


def _task_timestamp(task: InterventionTask) -> datetime:
    return _normalize_datetime(task.completed_at or task.created_at)


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
