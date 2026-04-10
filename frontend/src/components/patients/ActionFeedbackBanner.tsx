"use client";

import { useMemo } from "react";

export type ActionResult = {
  success: boolean;
  message?: string;
};

type Props = {
  feedback: ActionResult | null;
  onDismiss?: () => void;
};

const defaultMessage = (success: boolean) =>
  success ? "Action completed." : "Action could not be completed.";

export default function ActionFeedbackBanner({ feedback, onDismiss }: Props) {
  const resolvedFeedback = useMemo(() => {
    if (!feedback) {
      return null;
    }
    const message = feedback.message && feedback.message.trim().length > 0
      ? feedback.message
      : defaultMessage(feedback.success);
    return { ...feedback, message };
  }, [feedback]);

  if (!resolvedFeedback) {
    return null;
  }

  const toneClass = resolvedFeedback.success ? "action-feedback--success" : "action-feedback--error";
  const feedbackClass = resolvedFeedback.success ? "form-feedback--success" : "form-feedback--error";

  return (
    <div className={`action-feedback ${toneClass}`} role="status">
      <p className={`form-feedback ${feedbackClass}`}>{resolvedFeedback.message}</p>
      {onDismiss ? (
        <button
          type="button"
          className="button button--ghost action-feedback__dismiss"
          onClick={onDismiss}
        >
          Clear
        </button>
      ) : null}
    </div>
  );
}
