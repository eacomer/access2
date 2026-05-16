# ACCESS2 V2 Local Demo Handoff Index

## Purpose

This is the entry point for the localhost-only ACCESS2 V2 correction-loop demo package.

Use it when handing the local demo to an operator or reviewer. It is not a new product spec, does not authorize staging or production mutation, and should not replace the detailed runbooks linked below.

## Safety Scope

- Localhost-only.
- Frontend target must be `http://localhost:3000` or a verified current-workspace `http://localhost:3001`.
- API target must be `http://localhost:8000/api/v1`.
- Do not use Railway, staging, `salvardata.com`, `api.salvardata.com`, `railway.app`, `up.railway.app`, `https://`, or non-loopback targets.
- Do not use real PHI.
- V1 production remains read-only.

## Recommended Reading Order

Start with [access2-product-release-positioning.md](C:/dev/access2/docs/access2-product-release-positioning.md) if the operator needs the cross-version product and release framing before the V2 localhost demo package.

1. [access2-v2-checkpoint-and-roadmap.md](C:/dev/access2/docs/access2-v2-checkpoint-and-roadmap.md) - use to understand current V2 local readiness status and next options.
2. [access2-v2-demo-readiness-handoff.md](C:/dev/access2/docs/access2-v2-demo-readiness-handoff.md) - use for prerequisites, validation summary, limitations, and troubleshooting.
3. [access2-v2-correction-loop-demo.md](C:/dev/access2/docs/access2-v2-correction-loop-demo.md) - use for detailed correction-loop mechanics and local E2E/seed guidance.
4. [access2-v2-local-demo-operator-script.md](C:/dev/access2/docs/access2-v2-local-demo-operator-script.md) - use during the actual live/manual presenter walkthrough.

## What The Demo Proves

- Reviewer assignment for the latest `pending_review` snapshot.
- Rejection of the latest pending snapshot with a reason.
- The rejected terminal snapshot remains read-only.
- Corrected/new snapshot creation from current corrected evidence.
- Approval of the corrected latest snapshot.
- `audit_bundle.available=true` after approval.
- Prior rejected snapshots remain in backlog/history and are not overwritten.
- Immutable review packet history is preserved.

## What It Does Not Prove

- No staging mutation approval.
- No production mutation approval.
- No Railway mutation approval.
- No override approval UI.
- No EHR/FHIR integration.
- No billing integration.
- No real PHI workflow.

## Local Demo Path Summary

1. Confirm local backend and frontend health.
2. Confirm frontend and API targets are loopback-only.
3. Confirm the disposable patient starts at latest `pending_review`.
4. Run the documented local seed/reset only if the disposable patient is terminal.
5. Follow the operator script for the live walkthrough.
6. Use fallback language if local browser tooling or local Next.js timing is unavailable.
7. Record whether the manual rehearsal completed or where it stopped.

## Troubleshooting Pointers

Use [access2-v2-demo-readiness-handoff.md](C:/dev/access2/docs/access2-v2-demo-readiness-handoff.md) for the concise readiness checklist and [access2-v2-correction-loop-demo.md](C:/dev/access2/docs/access2-v2-correction-loop-demo.md) for detailed commands.

Common local issues:

- Stale `.next` output.
- Port `3000` versus `3001` mismatch.
- Cold Next.js route compilation delays.
- Playwright `EPERM` or generated artifacts.
- Terminal-approved disposable patient requiring local seed/reset.

## Recommended Next Step

Recommended next step: use this handoff index for one clean manual local presenter rehearsal. If the talk track is stable, defer staging until an isolated staging environment is explicitly approved.

## Latest Clean Readiness Rehearsal - May 16, 2026

- Scope: localhost-only; no staging, Railway, production, `https://`, or non-loopback mutation target was used.
- Targets checked: frontend `http://localhost:3000`; API `http://localhost:8000/api/v1`.
- Local stack health: backend live/ready returned 200; frontend `/login` returned 200.
- Seed/reset: needed because the disposable patient was terminal-approved from the prior rehearsal; the documented local seed/reset restored latest `pending_review`.
- Rehearsal path: local API-backed presenter sequence completed; automated local mutation E2E was not run.
- Result: reviewer assignment persisted, rejection persisted, corrected/new snapshot creation worked, approval persisted, `audit_bundle.available=true`, and prior rejected snapshot history remained preserved/read-only.
- Latest approved snapshot after this run: `1a2929c5-fabd-43d2-a53a-8c9020e7ffe1`.

## Confirmation

This handoff package is documentation-only and does not approve staging, Railway, or production mutation.
