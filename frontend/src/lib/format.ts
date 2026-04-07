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

type RelativeUnit = "minute" | "hour" | "day";

const getRelativeParts = (target: Date): { value: number; unit: RelativeUnit } => {
  const diffMs = target.getTime() - Date.now();
  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;
  if (Math.abs(diffMs) < hour) {
    return { value: Math.round(diffMs / minute), unit: "minute" };
  }
  if (Math.abs(diffMs) < day) {
    return { value: Math.round(diffMs / hour), unit: "hour" };
  }
  return { value: Math.round(diffMs / day), unit: "day" };
};

const getRelativeLabel = (target: Date): string => {
  const { value, unit } = getRelativeParts(target);
  return relativeTimeFormatter.format(value, unit);
};

export const formatDueDate = (value: DateLike): string => {
  const date = toDate(value);
  if (!date) {
    return "No SLA scheduled";
  }
  return `${formatDateTime(date)} (${getRelativeLabel(date)})`;
};

export const formatRelativeTime = (value: DateLike): string => {
  const date = toDate(value);
  if (!date) {
    return "—";
  }
  return getRelativeLabel(date);
};

const RELATIVE_UNIT_SYMBOL: Record<RelativeUnit, string> = {
  minute: "m",
  hour: "h",
  day: "d",
};

export const formatRelativeTimeCompact = (value: DateLike): string => {
  const date = toDate(value);
  if (!date) {
    return "—";
  }
  const { value: rawValue, unit } = getRelativeParts(date);
  const magnitude = Math.abs(rawValue);
  if (magnitude === 0) {
    return "now";
  }
  const suffix = rawValue <= 0 ? "ago" : "";
  const prefix = rawValue > 0 ? "in " : "";
  const unitSymbol = RELATIVE_UNIT_SYMBOL[unit];
  return rawValue <= 0 ? `${magnitude}${unitSymbol} ${suffix}`.trim() : `${prefix}${magnitude}${unitSymbol}`;
};

export const formatDayGrouping = (value: DateLike): string => {
  const date = toDate(value);
  if (!date) {
    return "Unknown date";
  }
  const today = new Date();
  const startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
  const startOfTarget = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
  const diffDays = Math.round((startOfToday - startOfTarget) / (24 * 60 * 60 * 1000));
  if (diffDays === 0) {
    return "Today";
  }
  if (diffDays === 1) {
    return "Yesterday";
  }
  return new Intl.DateTimeFormat("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
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
