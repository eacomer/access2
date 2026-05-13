const PRODUCTION_HOST_MARKERS = [
  "access2.salvardata.com",
  "api.salvardata.com",
  "railway.app",
  "up.railway.app",
] as const;

const LOOPBACK_HOSTS = new Set(["localhost", "127.0.0.1", "::1", "[::1]"]);

export type MutationE2ETarget = {
  label: string;
  url: string | undefined;
};

export type MutationE2EHostGuardOptions = {
  allowedNonLocalHosts?: string[];
};

export function assertSafeMutationE2ETargets(
  targets: MutationE2ETarget[],
  options: MutationE2EHostGuardOptions = {},
) {
  const allowedNonLocalHosts = new Set(
    (options.allowedNonLocalHosts ?? []).map((host) => normalizeHost(host)).filter(Boolean),
  );

  for (const target of targets) {
    const parsed = parseTarget(target);
    const host = normalizeHost(parsed.hostname);

    if (!host) {
      throw blockedMutationTarget(target.label, "missing host");
    }
    if (isProductionLikeHost(host)) {
      throw blockedMutationTarget(target.label, `production-like host ${host}`);
    }
    if (isLoopbackHost(host)) {
      continue;
    }
    if (allowedNonLocalHosts.has(host)) {
      continue;
    }

    throw blockedMutationTarget(target.label, `non-local host ${host} is not explicitly allowlisted`);
  }
}

export function sanitizeMutationTargetForError(target: MutationE2ETarget): string {
  const value = target.url?.trim();
  if (!value) {
    return `${target.label}: [missing]`;
  }

  try {
    const parsed = new URL(value);
    return `${target.label}: ${parsed.hostname || "[missing-host]"}`;
  } catch {
    return `${target.label}: [malformed-url]`;
  }
}

function parseTarget(target: MutationE2ETarget): URL {
  const value = target.url?.trim();
  if (!value) {
    throw blockedMutationTarget(target.label, "missing URL");
  }

  try {
    return new URL(value);
  } catch {
    throw blockedMutationTarget(target.label, "malformed URL");
  }
}

function normalizeHost(host: string): string {
  return host.trim().toLowerCase();
}

function isLoopbackHost(host: string): boolean {
  return LOOPBACK_HOSTS.has(host);
}

function isProductionLikeHost(host: string): boolean {
  return PRODUCTION_HOST_MARKERS.some((marker) => host.includes(marker));
}

function blockedMutationTarget(label: string, reason: string): Error {
  return new Error(`Mutation E2E is blocked for ${label}: ${reason}.`);
}
