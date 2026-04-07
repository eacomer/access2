const STATUS_LABELS = {
  unreadActivity: "Unread activity",
  activeEscalation: "Active escalation",
  activeEscalations: "Active escalations",
  slaAtRisk: "SLA at risk",
  slaOverdue: "SLA overdue",
  nextSlaDue: "Next SLA due",
  latestEvent: "Latest event",
  openWork: "Open work",
  linkedEscalation: "Escalation link",
  linkedTask: "Task link",
  linkedOutcome: "Outcome evidence",
  careUpdate: "Care update",
  taskActivity: "Task activity",
  taskDueSoon: "Task due soon",
  taskOverdue: "Task overdue",
  taskOutcome: "Task outcome",
  escalationUpdate: "Escalation update",
};

export const FILTER_LABELS = {
  unreadOnly: `${STATUS_LABELS.unreadActivity} only`,
  openWorkOnly: `${STATUS_LABELS.openWork} only`,
  activeEscalationOnly: `${STATUS_LABELS.activeEscalation} only`,
};

export default STATUS_LABELS;
