from __future__ import annotations

import ast
from pathlib import Path

import pytest

from scripts.check_staging_v2_seed_reset_contract import (
    API_BASE_URL_ENV_VAR,
    DATA_CLASSIFICATION_ENV_VAR,
    DRY_RUN_ENV_VAR,
    ENV_LABEL_ENV_VAR,
    FRONTEND_URL_ENV_VAR,
    STAGING_GATE_ENV_VAR,
    StagingSeedResetContractError,
    main,
    validate_staging_seed_reset_contract,
)


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_staging_v2_seed_reset_contract.py"


def safe_env(**overrides: str) -> dict[str, str]:
    env = {
        DRY_RUN_ENV_VAR: "true",
        STAGING_GATE_ENV_VAR: "true",
        FRONTEND_URL_ENV_VAR: "https://staging.access2.example.test",
        API_BASE_URL_ENV_VAR: "https://api-staging.access2.example.test/api/v1",
        ENV_LABEL_ENV_VAR: "staging-preview",
        DATA_CLASSIFICATION_ENV_VAR: "synthetic",
    }
    env.update(overrides)
    return env


def assert_contract_fails(env: dict[str, str], expected: str) -> None:
    with pytest.raises(StagingSeedResetContractError) as exc:
        validate_staging_seed_reset_contract(env)
    assert expected in str(exc.value)


def test_contract_check_fails_without_dry_run_flag() -> None:
    env = safe_env()
    env.pop(DRY_RUN_ENV_VAR)

    assert_contract_fails(env, DRY_RUN_ENV_VAR)


def test_contract_check_fails_without_staging_mutation_dry_run_gate() -> None:
    env = safe_env()
    env.pop(STAGING_GATE_ENV_VAR)

    assert_contract_fails(env, STAGING_GATE_ENV_VAR)


def test_contract_check_fails_on_production_frontend_url() -> None:
    assert_contract_fails(
        safe_env(**{FRONTEND_URL_ENV_VAR: "https://access2.salvardata.com"}),
        "blocked production-like host access2.salvardata.com",
    )


def test_contract_check_fails_on_production_api_url() -> None:
    assert_contract_fails(
        safe_env(**{API_BASE_URL_ENV_VAR: "https://api.salvardata.com/api/v1"}),
        "blocked production-like host api.salvardata.com",
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://access2-production.railway.app",
        "https://access2-production.up.railway.app",
    ],
)
def test_contract_check_fails_on_railway_like_targets(url: str) -> None:
    assert_contract_fails(
        safe_env(**{FRONTEND_URL_ENV_VAR: url}),
        "blocked production-like host",
    )


def test_contract_check_fails_on_malformed_urls() -> None:
    assert_contract_fails(
        safe_env(**{FRONTEND_URL_ENV_VAR: "not a url"}),
        f"{FRONTEND_URL_ENV_VAR} must be a valid http(s) URL",
    )


def test_contract_check_fails_on_url_credentials_and_sanitizes_output(capsys, monkeypatch) -> None:
    monkeypatch.setenv(DRY_RUN_ENV_VAR, "true")
    monkeypatch.setenv(STAGING_GATE_ENV_VAR, "true")
    monkeypatch.setenv(
        FRONTEND_URL_ENV_VAR,
        "https://admin:secret@staging.access2.example.test/path?token=hidden",
    )
    monkeypatch.setenv(API_BASE_URL_ENV_VAR, "https://api-staging.access2.example.test/api/v1")
    monkeypatch.setenv(ENV_LABEL_ENV_VAR, "staging-preview")
    monkeypatch.setenv(DATA_CLASSIFICATION_ENV_VAR, "synthetic")

    assert main() == 1
    output = capsys.readouterr()
    combined = output.out + output.err
    assert "staging.access2.example.test" in combined
    assert "secret" not in combined
    assert "token" not in combined
    assert "hidden" not in combined
    assert "admin" not in combined
    assert "path" not in combined


def test_contract_check_fails_on_url_query_and_sanitizes_output(capsys, monkeypatch) -> None:
    monkeypatch.setenv(DRY_RUN_ENV_VAR, "true")
    monkeypatch.setenv(STAGING_GATE_ENV_VAR, "true")
    monkeypatch.setenv(FRONTEND_URL_ENV_VAR, "https://staging.access2.example.test?token=hidden")
    monkeypatch.setenv(API_BASE_URL_ENV_VAR, "https://api-staging.access2.example.test/api/v1")
    monkeypatch.setenv(ENV_LABEL_ENV_VAR, "staging-preview")
    monkeypatch.setenv(DATA_CLASSIFICATION_ENV_VAR, "synthetic")

    assert main() == 1
    output = capsys.readouterr()
    combined = output.out + output.err
    assert "staging.access2.example.test" in combined
    assert "token" not in combined
    assert "hidden" not in combined


def test_contract_check_fails_on_non_synthetic_data_classification() -> None:
    assert_contract_fails(
        safe_env(**{DATA_CLASSIFICATION_ENV_VAR: "deidentified"}),
        f"{DATA_CLASSIFICATION_ENV_VAR}=synthetic is required",
    )


def test_contract_check_fails_on_production_like_env_label() -> None:
    assert_contract_fails(
        safe_env(**{ENV_LABEL_ENV_VAR: "production"}),
        f"{ENV_LABEL_ENV_VAR} must not be production-like",
    )


def test_contract_check_fails_on_missing_env_label() -> None:
    env = safe_env()
    env[ENV_LABEL_ENV_VAR] = ""

    assert_contract_fails(env, ENV_LABEL_ENV_VAR)


def test_contract_check_fails_on_localhost_without_explicit_local_validation_mode() -> None:
    assert_contract_fails(
        safe_env(**{FRONTEND_URL_ENV_VAR: "http://localhost:3000"}),
        "ACCESS2_ALLOW_LOCAL_STAGING_DRY_RUN=true",
    )


def test_contract_check_passes_with_safe_staging_placeholder_values() -> None:
    result = validate_staging_seed_reset_contract(safe_env())

    assert result.environment_label == "staging-preview"
    assert result.frontend_target == "https://staging.access2.example.test"
    assert result.api_target == "https://api-staging.access2.example.test"
    assert result.data_classification == "synthetic"
    assert result.local_validation_mode is False


def test_contract_check_does_not_require_secrets() -> None:
    env = safe_env(
        ACCESS2_STAGING_ADMIN_PASSWORD="",
        ACCESS2_STAGING_TOKEN="",
        DATABASE_URL="",
    )

    result = validate_staging_seed_reset_contract(env)

    assert result.data_classification == "synthetic"


def test_contract_check_script_imports_no_db_or_network_modules() -> None:
    tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module.split(".")[0])

    assert "sqlalchemy" not in imported_modules
    assert "requests" not in imported_modules
    assert "httpx" not in imported_modules
    assert "socket" not in imported_modules
    assert "app" not in imported_modules
