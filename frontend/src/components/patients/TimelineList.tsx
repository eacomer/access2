import Link from "next/link";

import { formatDateTime, formatEventType } from "../../lib/format";
import type { PatientTimelineItem } from "../../types/patient";

type Props = {
  events: PatientTimelineItem[];
  patientId: string;
  selectedEventId?: string;
};

export default function TimelineList({ events, patientId, selectedEventId }: Props) {
  if (events.length === 0) {
    return <p className="empty-state">No timeline events recorded for this patient.</p>;
  }

  return (
    <ul className="timeline-list">
      {events.map((event) => {
        const isSelected = event.event_id === selectedEventId;
        return (
          <li key={event.event_id}>
            <Link
              href={`/patients/${patientId}?eventId=${encodeURIComponent(event.event_id)}`}
              className={`timeline-row${isSelected ? " selected" : ""}`}
            >
              <div>
                <h4>{event.display_title}</h4>
                <p>{event.display_text ?? formatEventType(event.event_type)}</p>
              </div>
              <div className="timeline-meta">{formatDateTime(event.occurred_at)}</div>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
