import Link from "next/link";

import { requireAuth } from "../../lib/auth/session";

export const dynamic = "force-dynamic";

const PROOF_CHAIN = [
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
    summary:
      "Shows a complete or audit-ready evidence chain, approved review posture, audit bundle/export posture, and manifest verification readiness where supported by existing data.",
  },
  {
    name: "Demo Patient 2 - Missing Evidence",
    id: "1c5c7db8-96f8-47af-a643-741641ecdcf3",
    summary:
      "Shows an incomplete chain where evidence is missing or insufficient, and why audit bundle/manifest verification is unavailable.",
  },
  {
    name: "Demo Patient 3 - Rejected Review",
    id: "4c1ef5ef-1216-453d-b317-b965a0dd1dea",
    summary: "Shows a rejected review posture and why export/verification should not proceed.",
  },
  {
    name: "Demo Patient 4 - Override Approval",
    id: "2e9dc25c-2e56-4d6a-aea0-8706d33b0444",
    summary:
      "Shows approved-with-override posture, export availability, and verification readiness where supported by existing data.",
  },
];

const patientHref = (patientId: string) => `/patients/${encodeURIComponent(patientId)}`;

export default async function DemoGuidePage() {
  await requireAuth("/demo-guide");

  return (
    <main className="page" data-testid="demo-guide-page">
      <header className="patient-workflow-header">
        <div className="patient-workflow-header-main">
          <p className="eyebrow">Operator guide</p>
          <h1>Demo Guide</h1>
          <p className="patient-workflow-header-subtitle">
            Read-only walkthrough for presenting ACCESS2 with seeded synthetic demo data.
          </p>
        </div>
      </header>

      <section className="section-card" aria-labelledby="demo-guide-purpose">
        <h2 id="demo-guide-purpose">Purpose</h2>
        <p>
          ACCESS2 demonstrates how chronic care workflow evidence can support CMS ACCESS-aligned
          outcome-based payment review. Use this guide to present the proof story without changing
          workflow state.
        </p>
      </section>

      <section className="section-card" aria-labelledby="demo-guide-proof-chain">
        <h2 id="demo-guide-proof-chain">Core Proof Chain</h2>
        <p>{PROOF_CHAIN.join(" -> ")}</p>
      </section>

      <section className="section-card" aria-labelledby="demo-guide-credentials">
        <h2 id="demo-guide-credentials">Demo Credentials</h2>
        <p>These are synthetic demo credentials only.</p>
        <ul>
          <li>
            <strong>admin@example.com</strong> / Admin123!
          </li>
          <li>
            <strong>demo@example.com</strong> / Secret123!
          </li>
        </ul>
      </section>

      <section className="section-card" aria-labelledby="demo-guide-patients">
        <h2 id="demo-guide-patients">Seeded Demo Patients</h2>
        <div className="audit-readiness-table-wrap">
          <table className="audit-readiness-table">
            <thead>
              <tr>
                <th>Patient</th>
                <th>ID</th>
                <th>Demo posture</th>
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
                  <td>{patient.summary}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="section-card" aria-labelledby="demo-guide-click-path">
        <h2 id="demo-guide-click-path">What To Click</h2>
        <ol>
          <li>Log in with a synthetic demo user.</li>
          <li>Open Patients.</li>
          <li>Open each seeded Demo Patient.</li>
          <li>Review the Evidence Chain panel.</li>
          <li>Review the Manifest Verification panel.</li>
          <li>For audit-ready or override-approved patients, point out audit bundle/export posture.</li>
          <li>For missing or rejected patients, point out why the chain is blocked.</li>
        </ol>
      </section>

      <section className="section-card" aria-labelledby="demo-guide-panels">
        <h2 id="demo-guide-panels">Read-Only Panels</h2>
        <h3>Evidence Chain</h3>
        <p>
          Summarizes whether the patient has the required signal-to-outcome proof chain, shows
          missing or complete chain elements, and helps explain whether interventions can be
          connected to measurable outcomes.
        </p>
        <h3>Manifest Verification</h3>
        <p>
          Summarizes persisted review packet, audit bundle, and export posture. It helps show
          whether the final audit-bundle verification story is ready without overstating dedicated
          manifest verification beyond the current audit-status data exposed by the app.
        </p>
      </section>

      <section className="section-card" aria-labelledby="demo-guide-e2e">
        <h2 id="demo-guide-e2e">Expected E2E Baseline</h2>
        <p>
          Latest production custom-domain validation result: <strong>6 passed, 2 skipped, 0 failed</strong>.
        </p>
        <p>
          The skipped tests are expected because V1 exposes reviewer rejection and override approval
          as read-only seeded demo postures, not UI mutation workflows.
        </p>
      </section>

      <section className="section-card" aria-labelledby="demo-guide-safety">
        <h2 id="demo-guide-safety">Safety And Data Framing</h2>
        <ul>
          <li>Synthetic/demo data only.</li>
          <li>No real PHI.</li>
          <li>Do not enter real patient information.</li>
          <li>No secrets should be displayed or committed.</li>
          <li>This page is read-only guidance and does not create or mutate workflow data.</li>
        </ul>
      </section>
    </main>
  );
}
