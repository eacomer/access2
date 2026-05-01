"use client";

import { FormEvent, useState } from "react";

type VerificationMismatch = {
  field: string;
  expected: string | number | boolean;
  actual: string | number | boolean;
};

type VerificationResponse = {
  snapshot_id: string;
  verified: boolean;
  mismatches: VerificationMismatch[];
  expected_manifest?: Record<string, unknown>;
  error?: string;
};

type VerificationState =
  | { status: "idle" }
  | { status: "submitting" }
  | { status: "invalid"; message: string }
  | { status: "success"; result: VerificationResponse }
  | { status: "error"; message: string };

const SAMPLE_MANIFEST = `{
  "snapshot_id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "review_status": "approved",
  "generated_from": "persisted_snapshot",
  "packet_json_sha256": "...",
  "packet_markdown_sha256": "...",
  "decision_event_count": 1,
  "approval_event_id": "00000000-0000-0000-0000-000000000000",
  "approval_override_used": false
}`;

const stringifyValue = (value: string | number | boolean) => String(value);

export default function AuditBundleVerifyForm() {
  const [snapshotId, setSnapshotId] = useState("");
  const [manifestText, setManifestText] = useState("");
  const [state, setState] = useState<VerificationState>({ status: "idle" });

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmedSnapshotId = snapshotId.trim();
    if (!trimmedSnapshotId) {
      setState({ status: "invalid", message: "Enter a snapshot ID." });
      return;
    }

    let auditManifest: unknown;
    try {
      auditManifest = JSON.parse(manifestText);
    } catch {
      setState({
        status: "invalid",
        message: "Invalid manifest JSON. Paste the audit_manifest object from an exported audit bundle.",
      });
      return;
    }

    if (!auditManifest || typeof auditManifest !== "object" || Array.isArray(auditManifest)) {
      setState({
        status: "invalid",
        message: "Invalid manifest JSON. The pasted value must be a JSON object.",
      });
      return;
    }

    setState({ status: "submitting" });

    try {
      const response = await fetch("/audit-bundle-verify/verify", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          snapshotId: trimmedSnapshotId,
          auditManifest,
        }),
      });

      const payload = (await response.json().catch(() => ({}))) as VerificationResponse;
      if (!response.ok) {
        setState({
          status: "error",
          message: payload.error || "Audit bundle verification request failed.",
        });
        return;
      }

      setState({ status: "success", result: payload });
    } catch {
      setState({
        status: "error",
        message: "Audit bundle verification request failed. Check the frontend and backend services.",
      });
    }
  };

  const result = state.status === "success" ? state.result : null;
  const hasMismatch = Boolean(result && !result.verified);

  return (
    <section className="section-card" data-testid="audit-bundle-verify-form">
      <div className="section-header">
        <div>
          <p className="eyebrow">Audit bundle verification</p>
          <h2 className="section-title">Verify manifest</h2>
          <p className="section-subtitle">
            Compare an exported audit_manifest against the persisted snapshot manifest.
          </p>
        </div>
      </div>

      <form className="form-stack" onSubmit={handleSubmit}>
        <div className="form-field">
          <label htmlFor="snapshot-id">Snapshot ID</label>
          <input
            className="form-control"
            id="snapshot-id"
            name="snapshotId"
            onChange={(event) => setSnapshotId(event.target.value)}
            placeholder="Paste snapshot ID"
            type="text"
            value={snapshotId}
          />
        </div>
        <div className="form-field">
          <label htmlFor="audit-manifest">Audit manifest JSON</label>
          <textarea
            className="form-control manifest-textarea"
            id="audit-manifest"
            name="auditManifest"
            onChange={(event) => setManifestText(event.target.value)}
            placeholder={SAMPLE_MANIFEST}
            rows={14}
            value={manifestText}
          />
        </div>
        <div className="form-footer">
          <button className="button button--primary" disabled={state.status === "submitting"} type="submit">
            {state.status === "submitting" ? "Verifying..." : "Verify Manifest"}
          </button>
          <p className="inline-helper">Verification is read-only and does not export or update snapshots.</p>
        </div>
      </form>

      {state.status === "invalid" ? (
        <div className="action-feedback action-feedback--error" role="alert">
          <p className="form-feedback form-feedback--error">Invalid manifest: {state.message}</p>
        </div>
      ) : null}

      {state.status === "error" ? (
        <div className="action-feedback action-feedback--error" role="alert">
          <p className="form-feedback form-feedback--error">Request error: {state.message}</p>
        </div>
      ) : null}

      {result ? (
        <div
          className={
            result.verified
              ? "action-feedback action-feedback--success"
              : "action-feedback action-feedback--error"
          }
          role="status"
        >
          <div>
            <p className={result.verified ? "form-feedback form-feedback--success" : "form-feedback form-feedback--error"}>
              {result.verified ? "Verified" : "Mismatch"}
            </p>
            <p className="inline-helper">
              Snapshot {result.snapshot_id} {result.verified ? "matches" : "does not match"} the submitted manifest.
            </p>
          </div>
        </div>
      ) : null}

      {hasMismatch && result ? (
        <div className="audit-readiness-table-wrap">
          <table className="audit-readiness-table">
            <thead>
              <tr>
                <th>Field</th>
                <th>Expected</th>
                <th>Actual</th>
              </tr>
            </thead>
            <tbody>
              {result.mismatches.map((mismatch) => (
                <tr key={mismatch.field}>
                  <td>{mismatch.field}</td>
                  <td>{stringifyValue(mismatch.expected)}</td>
                  <td>{stringifyValue(mismatch.actual)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
