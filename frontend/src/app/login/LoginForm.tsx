"use client";

import { useFormState, useFormStatus } from "react-dom";

import { loginAction, type LoginActionState } from "./actions";

const INITIAL_STATE: LoginActionState = {};

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button className="button button--primary" type="submit" disabled={pending}>
      {pending ? "Signing in..." : "Sign in"}
    </button>
  );
}

export default function LoginForm() {
  const [state, formAction] = useFormState(loginAction, INITIAL_STATE);

  return (
    <form className="form-stack" action={formAction}>
      <div className="form-field">
        <label htmlFor="email">Work email</label>
        <input
          id="email"
          name="email"
          type="email"
          className="form-control"
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
          placeholder="••••••••"
          required
          autoComplete="current-password"
        />
      </div>
      {state?.error ? (
        <p role="alert" className="form-feedback form-feedback--error">
          {state.error}
        </p>
      ) : null}
      <div className="form-footer">
        <SubmitButton />
      </div>
    </form>
  );
}
