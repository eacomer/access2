import { pluralize } from "../../lib/format";
import type { PatientQueueImpactSnapshot as PatientQueueImpactSnapshotType } from "../../types/patient";

type Props = {
  snapshot?: PatientQueueImpactSnapshotType | null;
};

const defaultSnapshot: PatientQueueImpactSnapshotType = {
  patients_needing_attention: 0,
  open_escalations: 0,
  tasks_in_progress: 0,
  completed_tasks_recently: 0,
  completed_tasks_recently_window_days: 7,
  operational_summary: "Queue is currently quiet.",
};

const getSnapshot = (snapshot?: PatientQueueImpactSnapshotType | null): PatientQueueImpactSnapshotType => ({
  ...defaultSnapshot,
  ...(snapshot ?? {}),
});

export default function PatientQueueImpactSnapshot({ snapshot }: Props) {
  const resolved = getSnapshot(snapshot);
  const recentWindowDays = Math.max(1, resolved.completed_tasks_recently_window_days);
  const stats = [
    {
      id: "attention",
      value: resolved.patients_needing_attention,
      label: "Need attention",
      detail: pluralize(resolved.patients_needing_attention, "patient"),
      tone: resolved.patients_needing_attention > 0 ? "alert" : "info",
    },
    {
      id: "escalations",
      value: resolved.open_escalations,
      label: "Open escalations",
      detail: pluralize(resolved.open_escalations, "escalation"),
      tone: resolved.open_escalations > 0 ? "warning" : "info",
    },
    {
      id: "in-progress",
      value: resolved.tasks_in_progress,
      label: "Tasks in progress",
      detail: pluralize(resolved.tasks_in_progress, "task"),
      tone: resolved.tasks_in_progress > 0 ? "info" : "neutral",
    },
    {
      id: "completed",
      value: resolved.completed_tasks_recently,
      label: "Completed recently",
      detail: `Last ${pluralize(recentWindowDays, "day")}`,
      tone: resolved.completed_tasks_recently > 0 ? "positive" : "neutral",
    },
  ];

  return (
    <section className="queue-impact" aria-label="Queue impact snapshot">
      <div className="queue-impact-head">
        <div>
          <p className="worklist-context-label">Impact snapshot</p>
          <p className="queue-impact-summary">{resolved.operational_summary}</p>
        </div>
      </div>
      <div className="queue-impact-grid">
        {stats.map((stat) => (
          <div
            className={`queue-impact-stat queue-impact-stat--${stat.tone}`}
            key={stat.id}
          >
            <span className="queue-impact-value">{stat.value}</span>
            <span className="queue-impact-label">{stat.label}</span>
            <span className="queue-impact-detail">{stat.detail}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
