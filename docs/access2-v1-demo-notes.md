# ACCESS2 V1 Demo Notes

## 1. Demo Date

May 1, 2026

## 2. Demo Environment

- Demo type: solo dry run.
- Repo: `C:\dev\access2`
- Frontend URL: `http://localhost:3001`
- Frontend startup: `.\scripts\start-access2-demo-frontend.ps1`
- Backend/container status: `docker compose ps` showed backend, postgres, and redis running.
- Git hygiene before demo: only expected local-only files were present:

```text
?? frontend/.env.local
?? frontend/tsconfig.tsbuildinfo
```

## 3. Demo Scope

The dry run followed `docs/access2-v1-demo-runbook.md` with the deterministic startup helper.

Validated surfaces:

- `/login`
- `/audit-readiness`
- `/patients?active_only=0`
- patient detail
- reviewer workload summary
- audit-readiness table
- patient audit-status panel
- patient review-packet backlog panel
- absence of mutation controls in read-only audit panels

This V1 demo scope demonstrates read-only audit visibility and evidence posture. Mutation workflows and export/verification UI are not complete in this read-only demo unless separately implemented and validated.

## 4. What Worked

- The demo frontend helper started the current-workspace frontend on `localhost:3001`.
- `http://localhost:3001/login` returned HTTP 200.
- The Selenium bootstrap seed path passed.
- The read-only Selenium smoke path passed with expected guarded skips.
- Manual Selenium checks confirmed `/login`, `/audit-readiness`, `/patients?active_only=0`, and patient detail rendered.
- Reviewer workload summary rendered on `/audit-readiness`.
- Audit-readiness table rendered.
- Patient audit-status panel rendered.
- Patient review-packet backlog panel rendered.
- Read-only audit surfaces exposed no approve, reject, assign, export, verify, or create snapshot controls.

## 5. What Was Confusing

- The startup helper may require elevated/local execution in this sandboxed environment. Non-elevated Next startup had previously exited before readiness.
- The read-only smoke command reports 9 skipped tests by design; these are guarded data-creating or mutation-oriented checks that require `--e2e-submit-bootstrap`.
- Pytest still emits the known local `.pytest_cache` permission warning.

## 6. Stakeholder Questions

- No stakeholder was present.
- No stakeholder feedback was collected.

## 7. Product Gaps Observed

- No confirmed product defects were observed.
- Existing documented V1 gaps remain: mutation workflows and export/verification UI are outside the current read-only demo path unless implemented and validated separately.

## 8. Environment Issues

- Known `.pytest_cache` permission warning appeared during Selenium runs.
- In-app browser manual inspection was unavailable because its Node runtime was older than the browser plugin requires. A focused Selenium manual check was used instead.
- No generated frontend log files were produced or committed during this successful run.

## 9. Decisions Made

- Treat this as a successful controlled local solo dry run for the read-only V1 demo path.
- Preserve the read-only V1 framing: evidence posture is demonstrable, but mutation workflows and export/verification UI are not implied complete.
- Do not change backend code, frontend app code, Selenium tests, or seed logic.

## 10. Recommended Next Slice

Review queue visibility or controlled snapshot actions, if explicitly requested as the next V1 slice.

Keep the next slice narrow and tied to the V1 audit chain. Do not expand into broad workflow redesign, AI, integrations, billing, or general case-management features.

## 11. Follow-Up Actions

- Use `.\scripts\start-access2-demo-frontend.ps1` before future local demo runs.
- Start Selenium only after `http://localhost:3001/login` returns HTTP 200.
- Keep noting that the 9 read-only smoke skips are expected unless running guarded data-creating checks.
- Keep `frontend/.env.local` and `frontend/tsconfig.tsbuildinfo` local and uncommitted.
