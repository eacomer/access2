# ACCESS2 Selenium E2E Tests

The Selenium browser tests live in `tests/e2e`.

## Prerequisites

- Python dependencies are installed, including `pytest` and `selenium`.
- Chrome is installed locally.
- The ACCESS2 backend and frontend are already running.
- The seeded admin account is available: `admin@example.com` / `Admin123!`.

Typical local services:

- Frontend: `http://localhost:3000`
- Backend: `http://127.0.0.1:8000` or `http://127.0.0.1:8001`

Start the app the same way you normally do for local development. For example:

```powershell
docker compose up --build
```

If you run services separately, start the backend first, then start the Next.js frontend with its API base URL pointed at the running backend.

## Run

From the repo root:

```powershell
python -m pytest tests/e2e
```

To point tests at a different frontend URL:

```powershell
python -m pytest tests/e2e --e2e-base-url http://localhost:3001
```

To watch the browser:

```powershell
python -m pytest tests/e2e --e2e-headed
```

## Data-Creating Test

The workflow bootstrap submit test is scaffolded but skipped by default because it creates real application data. Enable it only against a disposable local database:

```powershell
python -m pytest tests/e2e --e2e-submit-bootstrap
```

To run only the deterministic submit-to-patient-detail workflow:

```powershell
python -m pytest tests/e2e/test_access2_smoke.py::test_admin_can_submit_workflow_bootstrap --e2e-submit-bootstrap
```

To run only the guarded patient-detail mutation workflow:

```powershell
python -m pytest tests/e2e/test_access2_smoke.py::test_admin_can_complete_patient_detail_task --e2e-submit-bootstrap
```

To run only the guarded patient-detail create-task workflow:

```powershell
python -m pytest tests/e2e/test_access2_smoke.py::test_admin_can_create_patient_detail_task --e2e-submit-bootstrap
```

To run only the guarded patient-detail escalation-action workflow:

```powershell
python -m pytest tests/e2e/test_access2_smoke.py::test_admin_can_start_patient_detail_escalation --e2e-submit-bootstrap
```

Equivalent environment variables:

- `ACCESS2_E2E_BASE_URL`
- `ACCESS2_E2E_HEADED=1`
- `ACCESS2_E2E_SUBMIT_BOOTSTRAP=1`

## Current Coverage

- Login page loads.
- Admin login succeeds and lands on `/patients`.
- Authenticated admin can load `/admin/workflow-bootstrap`.
- Optional workflow bootstrap submission verifies success feedback.
- Optional patient-detail mutation tests verify task completion, task creation, and escalation start refresh behavior.

These tests assume the frontend and backend are already running; they do not start or seed services.
