"use client";

import { useFormStatus } from "react-dom";

import { loginAction } from "./actions";

type Props = {
  nextPath?: string;
  errorMessage?: string;
};

function SubmitButton() {
  const { pending } = useFormStatus();

  return (
    <button
      className="button button--primary"
      type="submit"
      disabled={pending}
      data-testid="login-submit"
    >
      {pending ? "Signing in..." : "Sign in"}
    </button>
  );
}

export default function LoginForm({ nextPath, errorMessage }: Props) {
  return (
    <form className="form-stack" action={loginAction} data-testid="login-form">
      {nextPath ? <input type="hidden" name="next" value={nextPath} /> : null}

      <div className="form-field">
        <label htmlFor="email">Work email</label>
        <input
          id="email"
          name="email"
          type="email"
          className="form-control"
          data-testid="login-email"
          placeholder="care@access.example"
          required
          autoComplete="email"
        />
      </div>

      <div className="form-field">
        <label htmlFor="password">Password</label>
        <input
          id="password"
          name="password"
          type="password"
          className="form-control"
          data-testid="login-password"
          placeholder="••••••••"
          required
          autoComplete="current-password"
        />
      </div>

      {errorMessage ? (
        <p role="alert" className="form-feedback form-feedback--error">
          {errorMessage}
        </p>
      ) : null}

      <div className="form-footer">
        <SubmitButton />
      </div>
    </form>
  );
}
