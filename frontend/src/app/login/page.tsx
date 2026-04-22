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
    <main
      className="page"
      style={{ minHeight: "100vh", display: "flex", alignItems: "center" }}
      data-testid="login-page"
    >
      <section className="section-card" style={{ maxWidth: "420px", margin: "0 auto", width: "100%" }}>
        <div className="page-header">
          <p className="eyebrow">Access platform</p>
          <h1>Sign in</h1>
          <p>Authenticate to review patient worklists and timelines.</p>
        </div>
        <LoginForm nextPath={sanitizedNext ?? undefined} errorMessage={errorMessage ?? undefined} />
      </section>
    </main>
  );
}
