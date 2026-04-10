const TONE_STYLE = {
  info: {
    borderColor: "#bfdbfe",
    backgroundColor: "#eff6ff",
  },
  warning: {
    borderColor: "#fcd34d",
    backgroundColor: "#fffbeb",
  },
  danger: {
    borderColor: "#fecaca",
    backgroundColor: "#fef2f2",
  },
} as const;

type NoticeTone = keyof typeof TONE_STYLE;

type NoticeAction = {
  label: string;
  href: string;
  variant?: "primary" | "secondary";
};

type Props = {
  title: string;
  body: string;
  tone?: NoticeTone;
  actions?: NoticeAction[];
};

const BASE_STYLE: React.CSSProperties = {
  border: "1px solid #e2e8f0",
  borderRadius: "14px",
  padding: "1.25rem 1.5rem",
  display: "flex",
  flexDirection: "column",
  gap: "0.75rem",
  backgroundColor: "#fff",
  boxShadow: "0 1px 2px rgba(15, 23, 42, 0.04)",
};

const TITLE_STYLE: React.CSSProperties = {
  margin: 0,
  fontSize: "1.1rem",
  fontWeight: 600,
  color: "#0f172a",
};

const BODY_STYLE: React.CSSProperties = {
  margin: 0,
  fontSize: "0.95rem",
  color: "#475569",
};

const ACTIONS_STYLE: React.CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: "0.5rem",
};

const resolveButtonClass = (variant?: "primary" | "secondary") => {
  if (variant === "secondary") {
    return "button button--subtle";
  }
  return "button button--primary";
};

export default function StateNotice({ title, body, tone, actions = [] }: Props) {
  const toneStyle = tone ? TONE_STYLE[tone] : undefined;
  return (
    <section className="section-card" style={{ ...BASE_STYLE, ...(toneStyle ?? {}) }}>
      <h2 style={TITLE_STYLE}>{title}</h2>
      <p style={BODY_STYLE}>{body}</p>
      {actions.length ? (
        <div style={ACTIONS_STYLE}>
          {actions.map((action) => (
            <a key={`${action.label}-${action.href}`} href={action.href} className={resolveButtonClass(action.variant)}>
              {action.label}
            </a>
          ))}
        </div>
      ) : null}
    </section>
  );
}
