import { redirect } from "next/navigation";

import { getAuthTokenFromCookies } from "../../lib/auth/server-cookies";
import LoginForm from "./LoginForm";

export default function LoginPage() {
  const token = getAuthTokenFromCookies();
  if (token) {
    redirect("/patients");
  }

  return (
    <main className="page" style={{ minHeight: "100vh", display: "flex", alignItems: "center" }}>
      <section className="section-card" style={{ maxWidth: "420px", margin: "0 auto", width: "100%" }}>
        <div className="page-header">
          <p className="eyebrow">Access platform</p>
          <h1>Sign in</h1>
          <p>Authenticate to review patient worklists and timelines.</p>
        </div>
        <LoginForm />
      </section>
    </main>
  );
}
