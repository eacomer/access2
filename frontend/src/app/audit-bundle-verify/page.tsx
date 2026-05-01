import AuditBundleVerifyForm from "./AuditBundleVerifyForm";
import { requireAuth } from "../../lib/auth/session";

export const dynamic = "force-dynamic";

export default async function AuditBundleVerifyPage() {
  await requireAuth("/audit-bundle-verify");

  return (
    <main className="page" data-testid="audit-bundle-verify-page">
      <header className="patient-workflow-header">
        <div className="patient-workflow-header-main">
          <p className="eyebrow">ACCESS audit bundle</p>
          <h1>Audit bundle verification</h1>
          <p className="patient-workflow-header-subtitle">
            Read-only support screen for checking an exported audit manifest against persisted snapshot data.
          </p>
        </div>
      </header>
      <AuditBundleVerifyForm />
    </main>
  );
}
