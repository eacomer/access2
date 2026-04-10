import { signOutAction } from "../app/login/actions";

type Props = {
  variant?: "ghost" | "subtle";
  label?: string;
  className?: string;
};

export default function SignOutButton({
  variant = "ghost",
  label = "Sign out",
  className,
}: Props) {
  const baseClassName = variant === "subtle" ? "button button--subtle" : "button button--ghost";
  const resolvedClassName = className ? `${baseClassName} ${className}` : baseClassName;

  return (
    <form action={signOutAction} style={{ margin: 0 }}>
      <button type="submit" className={resolvedClassName} aria-label={label} title={label}>
        {label}
      </button>
    </form>
  );
}
