import Image from "next/image";

import { sanitizeReturnPath } from "../../lib/auth/session";
import LoginForm from "./LoginForm";

type PageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

export default async function LoginPage({ searchParams }: PageProps) {
  const resolvedSearchParams =
    (searchParams ? await searchParams : {}) as Record<string, string | string[] | undefined>;

  const nextParam = resolvedSearchParams.next;
  const requestedNext =
    typeof nextParam === "string" ? nextParam : Array.isArray(nextParam) ? nextParam[0] : null;

  const errorParam = resolvedSearchParams.error;
  const errorMessage =
    typeof errorParam === "string" ? errorParam : Array.isArray(errorParam) ? errorParam[0] : null;

  const sanitizedNext = sanitizeReturnPath(requestedNext ?? undefined);

  return (
    <main className="page login-page" data-testid="login-page">
      <section className="login-shell" aria-labelledby="login-title">
        <div className="login-story">
          <div className="login-brand">
            <Image
              src="/salvardata-wordmark.svg"
              alt="SalvarData"
              width={184}
              height={40}
              className="login-brand-logo"
              priority
            />
            <span>Powered by SalvarData</span>
          </div>

          <div className="login-copy">
            <p className="eyebrow">CMS ACCESS-aligned workflow</p>
            <h1 id="login-title">ACCESS2</h1>
            <h2>Chronic-Care Workflow and Audit-Readiness</h2>
            <p>
              ACCESS2 helps care teams track the accountability chain from signal to escalation,
              intervention, measurable outcome, care update, immutable review packet, and
              audit-ready evidence.
            </p>
          </div>

          <ul className="login-feature-list" aria-label="ACCESS2 capabilities">
            <li>Track chronic-care workflow activity</li>
            <li>Monitor outcome evidence readiness</li>
            <li>Preserve immutable review packets</li>
            <li>Support audit-ready review</li>
          </ul>

          <p className="login-boundary-note">
            Demo environment using synthetic data. This application demonstrates workflow and
            audit-readiness capabilities and is not a live claims, billing, or CMS submission
            system.
          </p>
        </div>

        <div className="section-card login-card" aria-labelledby="login-form-title">
          <div className="page-header">
            <p className="eyebrow">Secure access</p>
            <h2 id="login-form-title">Sign in</h2>
            <p>Authenticate to review patient worklists and timelines.</p>
          </div>
          <LoginForm nextPath={sanitizedNext ?? undefined} errorMessage={errorMessage ?? undefined} />
        </div>
      </section>
    </main>
  );
}
