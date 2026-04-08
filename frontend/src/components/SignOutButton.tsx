import { signOutAction } from "../app/login/actions";

type Props = {
  variant?: "ghost" | "subtle";
  label?: string;
};

export default function SignOutButton({ variant = "ghost", label = "Sign out" }: Props) {
  const className = variant === "subtle" ? "button button--subtle" : "button button--ghost";
  return (
    <form action={signOutAction} style={{ margin: 0 }}>
      <button type="submit" className={className}>
        {label}
      </button>
    </form>
  );
}
