import type { PatientTimelineWorklistSummaryItem } from "../../types/patient";
import STATUS_LABELS from "../../lib/statusLabels";

type Highlight = {
  id: string;
  label: string;
  value: string;
  detail?: string;
  tone?: "info" | "warning" | "alert";
};

type Props = {
  items: PatientTimelineWorklistSummaryItem[];
  title?: string;
  helper?: string;
};

const formatPlural = (count: number, singular: string, plural?: string) => {
  const normalizedPlural = plural ?? `${singular}s`;
  return `${count} ${count === 1 ? singular : normalizedPlural}`;
};

const buildHighlights = (items: PatientTimelineWorklistSummaryItem[]): Highlight[] => {
  const stats = items.reduce(
    (acc, item) => {
      const hasOpen = item.open_escalation_count > 0;
      if (hasOpen) {
        acc.openPatients += 1;
        acc.totalOpenEscalations += item.open_escalation_count;
      }
      if (item.overdue_escalation_count > 0) {
        acc.overduePatients += 1;
        acc.totalOverdueEscalations += item.overdue_escalation_count;
      }
      if (item.at_risk_escalation_count > 0) {
        acc.atRiskPatients += 1;
        acc.totalAtRiskEscalations += item.at_risk_escalation_count;
      }
      if (item.has_unread_events && item.unread_count > 0) {
        acc.unreadPatients += 1;
        acc.totalUnreadEvents += item.unread_count;
      }
      return acc;
    },
    {
      openPatients: 0,
      totalOpenEscalations: 0,
      overduePatients: 0,
      totalOverdueEscalations: 0,
      atRiskPatients: 0,
      totalAtRiskEscalations: 0,
      unreadPatients: 0,
      totalUnreadEvents: 0,
    },
  );

  const highlights: Highlight[] = [];

  if (stats.overduePatients > 0) {
    highlights.push({
      id: "overdue",
      label: STATUS_LABELS.slaOverdue,
      value: String(stats.overduePatients),
      detail: `${formatPlural(stats.totalOverdueEscalations, "escalation")}`,
      tone: "alert",
    });
  }

  if (stats.atRiskPatients > 0) {
    highlights.push({
      id: "at-risk",
      label: STATUS_LABELS.slaAtRisk,
      value: String(stats.atRiskPatients),
      detail: `${formatPlural(stats.totalAtRiskEscalations, "escalation")}`,
      tone: "warning",
    });
  }

  if (stats.openPatients > 0) {
    highlights.push({
      id: "open",
      label: STATUS_LABELS.activeEscalations,
      value: String(stats.openPatients),
      detail: `${formatPlural(stats.totalOpenEscalations, "open escalation")}`,
      tone: "info",
    });
  }

  if (stats.unreadPatients > 0) {
    highlights.push({
      id: "unread",
      label: STATUS_LABELS.unreadActivity,
      value: String(stats.unreadPatients),
      detail: `${formatPlural(stats.totalUnreadEvents, "event")}`,
      tone: "info",
    });
  }

  return highlights.slice(0, 4);
};

export default function WorklistHighlights({ items, title, helper }: Props) {
  if (!items.length) {
    return null;
  }

  const highlights = buildHighlights(items);
  if (highlights.length === 0) {
    return null;
  }

  const sectionTitle = title ?? "Escalation highlights";

  return (
    <section className="worklist-highlights" aria-label={sectionTitle}>
      <div className="worklist-context-header">
        <p className="worklist-context-label">{sectionTitle}</p>
        {helper ? <p className="worklist-context-helper">{helper}</p> : null}
      </div>
      <div className="worklist-highlights-list">
        {highlights.map((highlight) => (
          <div
            key={highlight.id}
            className={`worklist-highlight${
              highlight.tone ? ` worklist-highlight--${highlight.tone}` : ""
            }`}
          >
            <span className="worklist-highlight-value">{highlight.value}</span>
            <span className="worklist-highlight-label">{highlight.label}</span>
            {highlight.detail ? (
              <span className="worklist-highlight-detail">{highlight.detail}</span>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}
