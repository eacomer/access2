type DateLike = string | number | Date | undefined | null;

const toDate = (value: DateLike): Date | null => {
  if (!value) {
    return null;
  }
  const parsed = value instanceof Date ? value : new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};

export const formatDateTime = (value: DateLike): string => {
  const date = toDate(value);
  if (!date) {
    return "—";
  }
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
};

const relativeTimeFormatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

const getRelativeLabel = (target: Date): string => {
  const diffMs = target.getTime() - Date.now();
  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;
  if (Math.abs(diffMs) < hour) {
    const minutes = Math.round(diffMs / minute);
    return relativeTimeFormatter.format(minutes, "minute");
  }
  if (Math.abs(diffMs) < day) {
    const hours = Math.round(diffMs / hour);
    return relativeTimeFormatter.format(hours, "hour");
  }
  const days = Math.round(diffMs / day);
  return relativeTimeFormatter.format(days, "day");
};

export const formatDueDate = (value: DateLike): string => {
  const date = toDate(value);
  if (!date) {
    return "No SLA scheduled";
  }
  return `${formatDateTime(date)} (${getRelativeLabel(date)})`;
};

export const formatPriority = (priority?: string | null): string => {
  if (!priority) {
    return "Not set";
  }
  return priority
    .split("_")
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1).toLowerCase())
    .join(" ");
};

export const formatEventType = (eventType?: string | null): string => {
  if (!eventType) {
    return "Unknown event";
  }
  return eventType
    .split(/[:_]/)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1).toLowerCase())
    .join(" ");
};

export const pluralize = (count: number, noun: string): string => {
  const normalized = noun.endsWith("s") ? noun : `${noun}s`;
  return count === 1 ? `${count} ${noun}` : `${count} ${normalized}`;
};
