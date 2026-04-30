# ACCESS2 V1 Demo Notes

## 1. Demo Date

April 30, 2026

## 2. Demo Environment

- Demo type: solo dry run.
- Repo: `C:\dev\access2`
- Intended frontend URL: `http://localhost:3001`
- Backend/container status: `docker compose ps` showed backend, postgres, and redis running.
- Git hygiene before demo: only expected local-only files were present:

```text
?? frontend/.env.local
?? frontend/tsconfig.tsbuildinfo
```

## 3. Demo Scope

The dry run followed `docs/access2-v1-demo-runbook.md` as far as the local environment allowed.

Intended surfaces:

- `/audit-readiness`
- `/patients?active_only=0`
- patient detail
- reviewer workload summary
- audit-readiness table
- patient audit-status panel
- patient review-packet backlog panel
- absence of mutation controls in read-only audit panels

This V1 demo scope is read-only audit visibility and evidence posture. Mutation workflows and export/verification UI are not complete in this read-only demo unless separately implemented and validated.

## 4. What Worked

- Required V1 scope and demo docs were available and consistent with the controlled local demo path.
- `docker compose ps` showed the backend, postgres, and redis containers running.
- A fresh current-workspace frontend process was started for `localhost:3001`.
- `localhost:3001` opened a listening port after the frontend start attempt.
- Generated frontend log files from the failed start attempts were removed before committing notes.

## 5. What Was Confusing

- The frontend port could be open while page requests still timed out. This makes the environment look partially ready even though the UI is not reachable.
- The existing Docker frontend service is running but exposes only container port `3000/tcp` in `docker compose ps`; the runbook's preferred current-workspace `localhost:3001` path still requires a separate local frontend process.
- Selenium timeout behavior did not produce a useful pass/fail report during this dry run.

## 6. Stakeholder Questions

- No stakeholder was present.
- No stakeholder feedback was collected.

## 7. Product Gaps Observed

- No confirmed product defects were observed because the UI surfaces could not be reached during this dry run.
- Existing documented V1 gaps remain: mutation workflows and export/verification UI are outside the current read-only demo path unless implemented and validated separately.

## 8. Environment Issues

- The Selenium bootstrap command timed out:

```powershell
py -3 -m pytest tests/e2e/test_access2_smoke.py::test_admin_can_submit_workflow_bootstrap --e2e-submit-bootstrap --e2e-base-url http://localhost:3001 -q
```

- The optional Selenium smoke command also timed out:

```powershell
py -3 -m pytest tests/e2e/test_access2_smoke.py --e2e-base-url http://localhost:3001 -q -rs
```

- Direct HTTP checks against `http://localhost:3001/login`, `http://localhost:3001/audit-readiness`, and `http://localhost:3001/patients?active_only=0` timed out.
- An existing ACCESS2 frontend process on `localhost:3100` was also checked, but page requests timed out there as well.
- The failed `localhost:3001` start attempts produced an `EADDRINUSE` log after a server process was already listening on that port.
- Pytest/cache and git status continued to show the known local `.pytest_cache` permission warning.

## 9. Decisions Made

- Do not treat this dry run as a product validation failure.
- Do not change backend code, frontend app code, tests, or seed logic.
- Record the run as blocked by local frontend reachability/page-serving behavior.
- Preserve the existing read-only V1 scope and avoid adding mutation workflow assumptions.

## 10. Recommended Next Slice

Local environment startup hardening for the demo path.

Keep the slice docs/devops-focused unless a reproducible product defect appears. The useful next step is to make the current-workspace frontend startup path deterministic enough that `/login`, `/audit-readiness`, and `/patients?active_only=0` respond before Selenium bootstrap or smoke commands run.

## 11. Follow-Up Actions

- Reproduce frontend startup from a clean terminal and confirm which command should be canonical for `localhost:3001`.
- Add or document a lightweight readiness check that requires an HTTP 200 page response, not just an open TCP port.
- Re-run the Selenium bootstrap command only after `http://localhost:3001/login` responds.
- Re-run the read-only smoke command with `-rs` after bootstrap succeeds.
- Keep `frontend/.env.local` and `frontend/tsconfig.tsbuildinfo` local and uncommitted.
