import { formatDateTime, formatEventType } from "../../lib/format";
import STATUS_LABELS from "../../lib/statusLabels";
import type {
  PatientEscalationEvidence,
  PatientTimelineWorklistSummaryItem,
} from "../../types/patient";

type HeaderChip = {
  id: string;
  label: string;
  value: string;
  tone?: "info" | "warning" | "alert";
};

type MetadataItem = {
  id: string;
  label: string;
  value: string;
};

type Props = {
  patientName: string;
  patientId: string;
  summary: PatientTimelineWorklistSummaryItem | null;
  evidence: PatientEscalationEvidence | null;
};

const pluralize = (count: number, singular: string, plural?: string) => {
  if (!Number.isFinite(count)) {
    return singular;
  }
  const resolvedPlural = plural ?? `${singular}s`;
  return `${count} ${count === 1 ? singular : resolvedPlural}`;
};

const humanizeStatus = (value?: string | null) => {
  if (!value) {
    return null;
  }
  return value
    .split("_")
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1).toLowerCase())
    .join(" ");
};

const buildSubtitle = (
  summary: PatientTimelineWorklistSummaryItem | null,
  evidence: PatientEscalationEvidence | null,
): string => {
  const parts: string[] = [];
  if (summary?.total_events) {
    parts.push(pluralize(summary.total_events, "recorded event"));
  }
  if (summary?.has_unread_events && summary.unread_count > 0) {
    parts.push(pluralize(summary.unread_count, "unread event"));
  }
  if (summary?.open_escalation_count) {
    parts.push(pluralize(summary.open_escalation_count, "open escalation"));
  }
  const status = humanizeStatus(evidence?.latest_open_escalation_status);
  if (status) {
    parts.push(`Escalation ${status.toLowerCase()}`);
  }
  if (parts.length === 0) {
    return "Escalation-aware detail for the selected patient.";
  }
  return parts.join(" • ");
};

const buildMetadata = (
  patientId: string,
  summary: PatientTimelineWorklistSummaryItem | null,
): MetadataItem[] => {
  const items: MetadataItem[] = [
    {
      id: "patient-id",
      label: "Patient ID",
      value: patientId,
    },
  ];

  if (summary?.latest_event_type) {
    items.push({
      id: "latest-type",
      label: "Latest event type",
      value: formatEventType(summary.latest_event_type),
    });
  }

  if (summary?.latest_event_occurred_at) {
    items.push({
      id: "latest-event",
      label: "Latest event at",
      value: formatDateTime(summary.latest_event_occurred_at),
    });
  }

  return items;
};

const buildChips = (
  summary: PatientTimelineWorklistSummaryItem | null,
  evidence: PatientEscalationEvidence | null,
): HeaderChip[] => {
  const chips: HeaderChip[] = [];

  if (summary?.has_unread_events && summary.unread_count > 0) {
    chips.push({
      id: "unread",
      label: STATUS_LABELS.unreadActivity,
      value: String(summary.unread_count),
      tone: "info",
    });
  }

  if (summary?.open_escalation_count && summary.open_escalation_count > 0) {
    chips.push({
      id: "open-escalations",
      label: STATUS_LABELS.activeEscalations,
      value: String(summary.open_escalation_count),
    });
  }

  if (summary?.at_risk_escalation_count && summary.at_risk_escalation_count > 0) {
    chips.push({
      id: "at-risk",
      label: STATUS_LABELS.slaAtRisk,
      value: String(summary.at_risk_escalation_count),
      tone: "warning",
    });
  }

  if (summary?.overdue_escalation_count && summary.overdue_escalation_count > 0) {
    chips.push({
      id: "overdue",
      label: STATUS_LABELS.slaOverdue,
      value: String(summary.overdue_escalation_count),
      tone: "alert",
    });
  }

  const status = humanizeStatus(evidence?.latest_open_escalation_status);
  if (status) {
    chips.push({
      id: "status",
      label: STATUS_LABELS.activeEscalation,
      value: status,
      tone: evidence?.latest_open_escalation_status === "overdue" ? "alert" : undefined,
    });
  }

  const prioritized = chips.filter((chip) => chip.value.trim().length > 0);
  return prioritized.slice(0, 4);
};

export default function PatientWorkflowHeader({ patientName, patientId, summary, evidence }: Props) {
  const subtitle = buildSubtitle(summary, evidence);
  const metadata = buildMetadata(patientId, summary);
  const chips = buildChips(summary, evidence);

  return (
    <section className="page-header patient-workflow-header">
      <div className="patient-workflow-header-main">
        <p className="eyebrow">Patient timeline</p>
        <h1>{patientName}</h1>
        <p className="patient-workflow-header-subtitle">{subtitle}</p>
      </div>
      {metadata.length ? (
        <dl className="patient-workflow-meta">
          {metadata.map((item) => (
            <div className="patient-workflow-meta-item" key={item.id}>
              <dt>{item.label}</dt>
              <dd>{item.value}</dd>
            </div>
          ))}
        </dl>
      ) : null}
      {chips.length ? (
        <div className="patient-workflow-cues">
          {chips.map((chip) => (
            <div
              key={chip.id}
              className={`patient-workflow-chip${
                chip.tone ? ` patient-workflow-chip--${chip.tone}` : ""
              }`}
            >
              <span className="patient-workflow-chip-label">{chip.label}</span>
              <span className="patient-workflow-chip-value">{chip.value}</span>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}
