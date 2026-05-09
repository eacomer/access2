import Link from "next/link";

import { requireAuth } from "../../../lib/auth/session";

export const dynamic = "force-dynamic";

const DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1";
const PRODUCTION_FRONTEND_URL = "https://access2.salvardata.com";
const PRODUCTION_E2E_BASELINE = {
  passed: 6,
  skipped: 2,
  failed: 0,
};

const EVIDENCE_CHAIN = [
  "signal",
  "escalation",
  "intervention",
  "outcome",
  "evidence",
  "case summary",
  "immutable review packet snapshot",
  "approval/rejection",
  "audit bundle",
  "manifest verification",
];

const DEMO_PATIENTS = [
  {
    name: "Demo Patient 1 - Audit Ready",
    id: "f4c31931-8fc2-41d6-9f45-9ab0bd039088",
    posture: "Audit Ready",
    message:
      "Complete proof chain with outcome evidence, approved review posture, audit bundle export coverage, and manifest verification support.",
  },
  {
    name: "Demo Patient 2 - Missing Evidence",
    id: "1c5c7db8-96f8-47af-a643-741641ecdcf3",
    posture: "Missing Evidence",
    message:
      "Demonstrates the missing outcome/evidence proof gap and why audit bundle readiness remains incomplete.",
  },
  {
    name: "Demo Patient 3 - Rejected Review",
    id: "4c1ef5ef-1216-453d-b317-b965a0dd1dea",
    posture: "Rejected Review",
    message:
      "Shows that a proof packet exists, but the review posture is rejected and export readiness is blocked.",
  },
  {
    name: "Demo Patient 4 - Override Approval",
    id: "2e9dc25c-2e56-4d6a-aea0-8706d33b0444",
    posture: "Override Approval",
    message:
      "Shows approval that depends on override/superuser review posture without exposing override mutation controls.",
  },
];

const normalizeBaseUrl = (value?: string) => {
  if (!value || value.trim().length === 0) {
    return DEFAULT_API_BASE_URL;
  }
  return value.endsWith("/") ? value.slice(0, -1) : value;
};

const patientHref = (patientId: string) => `/patients/${encodeURIComponent(patientId)}`;

export default async function DemoReleaseSummaryPage() {
  await requireAuth("/demo/release-summary");

  const apiBaseUrl = normalizeBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);

  return (
    <main className="page" data-testid="demo-release-summary-page">
      <header className="patient-workflow-header">
        <div className="patient-workflow-header-main">
          <p className="eyebrow">Release evidence</p>
          <h1>Demo Release Summary</h1>
          <p className="patient-workflow-header-subtitle">
            Read-only production/demo posture for the ACCESS2 V1 evidence path.
          </p>
        </div>
      </header>

      <section className="section-card" aria-labelledby="release-summary-purpose">
        <h2 id="release-summary-purpose">Release Posture</h2>
        <p>
          ACCESS2 V1 is validated around the evidence chain that proves interventions led to
          measurable outcomes:
        </p>
        <p>{EVIDENCE_CHAIN.join(" -> ")}</p>
      </section>

      <section className="queue-impact" aria-labelledby="release-summary-environment">
        <div className="queue-impact-head">
          <div>
            <p className="worklist-context-label" id="release-summary-environment">
              Environment
            </p>
            <p className="queue-impact-summary">
              Production/demo endpoints currently represented by the frontend release summary.
            </p>
          </div>
        </div>
        <div className="queue-impact-grid">
          <div className="queue-impact-stat queue-impact-stat--info">
            <span className="queue-impact-label">Frontend</span>
            <span className="queue-impact-detail">{PRODUCTION_FRONTEND_URL}</span>
          </div>
          <div className="queue-impact-stat queue-impact-stat--info">
            <span className="queue-impact-label">Backend API base</span>
            <span className="queue-impact-detail">{apiBaseUrl}</span>
          </div>
          <div className="queue-impact-stat queue-impact-stat--positive">
            <span className="queue-impact-label">Demo Guide</span>
            <Link className="table-link" href="/demo-guide">
              Available
            </Link>
          </div>
        </div>
      </section>

      <section className="section-card" aria-labelledby="release-summary-patients">
        <div className="section-header">
          <div>
            <h2 className="section-title" id="release-summary-patients">
              Seeded Demo Scenarios
            </h2>
            <p className="section-subtitle">Synthetic/demo data only. No real PHI.</p>
          </div>
        </div>
        <div className="audit-readiness-table-wrap">
          <table className="audit-readiness-table">
            <thead>
              <tr>
                <th>Scenario</th>
                <th>Patient ID</th>
                <th>Expected posture</th>
                <th>Operator message</th>
              </tr>
            </thead>
            <tbody>
              {DEMO_PATIENTS.map((patient) => (
                <tr key={patient.id}>
                  <td>
                    <Link className="table-link" href={patientHref(patient.id)}>
                      {patient.name}
                    </Link>
                  </td>
                  <td>{patient.id}</td>
                  <td>{patient.posture}</td>
                  <td>{patient.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="queue-impact" aria-labelledby="release-summary-e2e">
        <div className="queue-impact-head">
          <div>
            <p className="worklist-context-label" id="release-summary-e2e">
              Production E2E baseline
            </p>
            <p className="queue-impact-summary">
              Latest verified production result against the custom frontend domain.
            </p>
          </div>
        </div>
        <div className="queue-impact-grid">
          <div className="queue-impact-stat queue-impact-stat--positive">
            <span className="queue-impact-value">{PRODUCTION_E2E_BASELINE.passed}</span>
            <span className="queue-impact-label">Passed</span>
          </div>
          <div className="queue-impact-stat queue-impact-stat--warning">
            <span className="queue-impact-value">{PRODUCTION_E2E_BASELINE.skipped}</span>
            <span className="queue-impact-label">Skipped</span>
          </div>
          <div className="queue-impact-stat">
            <span className="queue-impact-value">{PRODUCTION_E2E_BASELINE.failed}</span>
            <span className="queue-impact-label">Failed</span>
          </div>
        </div>
      </section>

      <section className="section-card" aria-labelledby="release-summary-skips">
        <h2 id="release-summary-skips">Expected Skips</h2>
        <p>
          The two skipped production E2E tests are expected V1 read-only constraints, not release
          blockers.
        </p>
        <ul>
          <li>No reviewer rejection mutation control is exposed in the V1 frontend.</li>
          <li>No superuser override approval mutation control is exposed in the V1 frontend.</li>
        </ul>
        <p>
          Rejected-review and override-approval patients remain represented as read-only audit
          postures for the demo.
        </p>
      </section>
    </main>
  );
}
