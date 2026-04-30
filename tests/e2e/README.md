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

## Seeded Read-Only Audit Validation

To seed one local patient through the existing admin workflow bootstrap UI:

```powershell
py -3 -m pytest tests/e2e/test_access2_smoke.py::test_admin_can_submit_workflow_bootstrap --e2e-submit-bootstrap -q
```

Then run the smoke suite:

```powershell
py -3 -m pytest tests/e2e/test_access2_smoke.py -q
```

If an already-running frontend on `localhost:3000` is stale, read-only audit panel checks can fail even though the committed code is correct. Restart `localhost:3000`, or start a fresh current-workspace frontend on another port and pass that URL:

```powershell
py -3 -m pytest tests/e2e/test_access2_smoke.py --e2e-base-url http://localhost:3001 -q
```

Latest known seeded result against a fresh `localhost:3001` frontend: `5 passed, 9 skipped`.

The 9 skipped tests are expected in the read-only smoke command above. They are data-creating bootstrap, patient-detail mutation, workflow alignment, and escalation mutation checks that require `--e2e-submit-bootstrap` and a disposable local database. If the first 5 tests fail with `net::ERR_CONNECTION_REFUSED`, the selected frontend URL is not running or is not reachable; start or restart the frontend before interpreting the smoke result.

The read-only patient audit-status and review-packet backlog sections should render without mutation controls such as approve, reject, assign, export, verify, or create snapshot.

To run only the guarded patient-detail mutation workflow:

```powershell
python -m pytest tests/e2e/test_access2_smoke.py::test_admin_can_complete_patient_detail_task --e2e-submit-bootstrap
```

To run only the guarded patient-detail create-task workflow:

```powershell
python -m pytest tests/e2e/test_access2_smoke.py::test_admin_can_create_patient_detail_task --e2e-submit-bootstrap
```

To run only the guarded patient-detail create-task validation prevention workflow:

```powershell
python -m pytest tests/e2e/test_access2_smoke.py::test_admin_create_task_requires_title_before_submit --e2e-submit-bootstrap
```

To run only the guarded workflow summary alignment check across `/patients` and patient detail:

```powershell
python -m pytest tests/e2e/test_access2_smoke.py::test_admin_workflow_summary_alignment_between_worklist_and_detail --e2e-submit-bootstrap
```

To run only the guarded patient-detail escalation-action workflow:

```powershell
python -m pytest tests/e2e/test_access2_smoke.py::test_admin_can_start_patient_detail_escalation --e2e-submit-bootstrap
```

To run only the guarded worklist refresh after patient-detail task creation workflow:

```powershell
python -m pytest tests/e2e/test_access2_smoke.py::test_admin_worklist_refreshes_after_patient_detail_task_creation --e2e-submit-bootstrap
```

To run only the guarded escalation-resolution plus worklist refresh workflow:

```powershell
python -m pytest tests/e2e/test_access2_smoke.py::test_admin_can_resolve_escalation_and_worklist_refreshes --e2e-submit-bootstrap
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
- Optional workflow summary alignment checks verify the queue and patient detail reflect matching operational meaning for deterministic bootstrap scenarios.
- Optional patient-detail mutation tests verify task completion, task creation, create-task validation prevention, escalation start refresh behavior, worklist refresh after detail-page task creation, and escalation resolution across detail/worklist.

These tests assume the frontend and backend are already running; they do not start or seed services.
