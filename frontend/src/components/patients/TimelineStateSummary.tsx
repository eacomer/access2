type Props = {
  primary: string;
  detail?: string | null;
};

export default function TimelineStateSummary({ primary, detail }: Props) {
  if (!primary && !detail) {
    return null;
  }

  return (
    <div className="timeline-state">
      {primary ? <p className="timeline-state-primary">{primary}</p> : null}
      {detail ? <p className="timeline-state-detail">{detail}</p> : null}
    </div>
  );
}
