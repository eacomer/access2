"""
Dry-run ACCESS2 V2 staging seed/reset contract check.

This script validates only non-secret environment inputs for a future isolated
staging seed/reset flow. It performs no database writes, no database reads, and
no network calls.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from urllib.parse import urlparse


DRY_RUN_ENV_VAR = "ACCESS2_STAGING_SEED_RESET_DRY_RUN"
STAGING_GATE_ENV_VAR = "ACCESS2_ENABLE_STAGING_MUTATION_DRY_RUN"
FRONTEND_URL_ENV_VAR = "ACCESS2_STAGING_FRONTEND_URL"
API_BASE_URL_ENV_VAR = "ACCESS2_STAGING_API_BASE_URL"
ENV_LABEL_ENV_VAR = "ACCESS2_STAGING_ENV_LABEL"
DATA_CLASSIFICATION_ENV_VAR = "ACCESS2_STAGING_DATA_CLASSIFICATION"
ALLOW_LOCAL_VALIDATION_ENV_VAR = "ACCESS2_ALLOW_LOCAL_STAGING_DRY_RUN"

REQUIRED_ENV_VARS = (
    DRY_RUN_ENV_VAR,
    STAGING_GATE_ENV_VAR,
    FRONTEND_URL_ENV_VAR,
    API_BASE_URL_ENV_VAR,
    ENV_LABEL_ENV_VAR,
    DATA_CLASSIFICATION_ENV_VAR,
)

PRODUCTION_HOST_MARKERS = (
    "access2.salvardata.com",
    "api.salvardata.com",
    "railway.app",
    "up.railway.app",
)

LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
STAGING_LABEL_MARKERS = ("staging", "stage", "preview", "sandbox")
PRODUCTION_LABEL_MARKERS = ("prod", "production", "live", "main")


class StagingSeedResetContractError(RuntimeError):
    """Raised when future staging seed/reset inputs are unsafe or incomplete."""


@dataclass(frozen=True, slots=True)
class ContractCheckResult:
    environment_label: str
    frontend_target: str
    api_target: str
    data_classification: str
    local_validation_mode: bool


def main() -> int:
    try:
        result = validate_staging_seed_reset_contract(os.environ)
    except StagingSeedResetContractError as exc:
        print(f"ACCESS2 staging seed/reset dry-run contract check failed: {exc}", file=sys.stderr)
        return 1

    print("ACCESS2 staging seed/reset dry-run contract check passed.")
    print(f"- environment label: {result.environment_label}")
    print(f"- frontend target: {result.frontend_target}")
    print(f"- API target: {result.api_target}")
    print(f"- data classification: {result.data_classification}")
    print(f"- local validation mode: {'yes' if result.local_validation_mode else 'no'}")
    print("- dry-run only: no database or network operations were performed")
    return 0


def validate_staging_seed_reset_contract(env: dict[str, str]) -> ContractCheckResult:
    missing = [name for name in REQUIRED_ENV_VARS if not env.get(name, "").strip()]
    if missing:
        raise StagingSeedResetContractError(
            f"missing required environment variable(s): {', '.join(missing)}"
        )

    if not _is_true(env[DRY_RUN_ENV_VAR]):
        raise StagingSeedResetContractError(f"{DRY_RUN_ENV_VAR}=true is required.")
    if not _is_true(env[STAGING_GATE_ENV_VAR]):
        raise StagingSeedResetContractError(f"{STAGING_GATE_ENV_VAR}=true is required.")

    data_classification = env[DATA_CLASSIFICATION_ENV_VAR].strip().lower()
    if data_classification != "synthetic":
        raise StagingSeedResetContractError(
            f"{DATA_CLASSIFICATION_ENV_VAR}=synthetic is required."
        )

    environment_label = _validate_environment_label(env[ENV_LABEL_ENV_VAR])
    allow_local_validation = _is_true(env.get(ALLOW_LOCAL_VALIDATION_ENV_VAR, ""))
    frontend_target = _validate_url(
        env[FRONTEND_URL_ENV_VAR],
        label=FRONTEND_URL_ENV_VAR,
        allow_local_validation=allow_local_validation,
    )
    api_target = _validate_url(
        env[API_BASE_URL_ENV_VAR],
        label=API_BASE_URL_ENV_VAR,
        allow_local_validation=allow_local_validation,
    )

    return ContractCheckResult(
        environment_label=environment_label,
        frontend_target=frontend_target,
        api_target=api_target,
        data_classification=data_classification,
        local_validation_mode=allow_local_validation,
    )


def _validate_environment_label(raw_label: str) -> str:
    label = raw_label.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,62}", label):
        raise StagingSeedResetContractError(
            f"{ENV_LABEL_ENV_VAR} must be a staging/preview-like label using only letters, numbers, hyphens, or underscores."
        )
    if any(marker in label for marker in PRODUCTION_LABEL_MARKERS):
        raise StagingSeedResetContractError(
            f"{ENV_LABEL_ENV_VAR} must not be production-like."
        )
    if not any(marker in label for marker in STAGING_LABEL_MARKERS):
        raise StagingSeedResetContractError(
            f"{ENV_LABEL_ENV_VAR} must look staging/preview-like."
        )
    return label


def _validate_url(raw_url: str, *, label: str, allow_local_validation: bool) -> str:
    value = raw_url.strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise StagingSeedResetContractError(f"{label} must be a valid http(s) URL.")

    host = parsed.hostname.lower()
    if parsed.username or parsed.password:
        raise StagingSeedResetContractError(
            f"{label} must not include URL credentials for host {host}."
        )
    if parsed.query:
        raise StagingSeedResetContractError(
            f"{label} must not include query strings for host {host}."
        )
    if parsed.fragment:
        raise StagingSeedResetContractError(
            f"{label} must not include URL fragments for host {host}."
        )

    blocked_marker = _production_like_host_marker(host)
    if blocked_marker:
        raise StagingSeedResetContractError(
            f"{label} points to blocked production-like host {host}."
        )
    if host in LOOPBACK_HOSTS and not allow_local_validation:
        raise StagingSeedResetContractError(
            f"{label} points to local host {host}; set {ALLOW_LOCAL_VALIDATION_ENV_VAR}=true only for local validation mode."
        )

    return _sanitized_url(parsed)


def _production_like_host_marker(host: str) -> str | None:
    for marker in PRODUCTION_HOST_MARKERS:
        if marker in host:
            return marker
    return None


def _sanitized_url(parsed) -> str:
    host = parsed.hostname or "[missing-host]"
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{host.lower()}{port}"


def _is_true(value: str) -> bool:
    return value.strip().lower() == "true"


if __name__ == "__main__":
    raise SystemExit(main())
