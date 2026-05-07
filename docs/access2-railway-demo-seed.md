# ACCESS2 Railway Demo Seed

This is a one-time synthetic-data seed path for the ACCESS2 Railway demo cases. It creates only demo patients marked with `external_patient_id` values beginning with `access2-railway-demo:` and does not use real PHI.

## Local Run

```powershell
cd C:\dev\access2\backend
py -3 scripts\seed_railway_demo_cases.py
```

The script prints copy/paste-ready patient IDs:

```text
ACCESS2_E2E_DEMO_PATIENT_1_ID=...
ACCESS2_E2E_DEMO_PATIENT_2_ID=...
ACCESS2_E2E_DEMO_PATIENT_3_ID=...
ACCESS2_E2E_DEMO_PATIENT_4_ID=...
```

## One-Time Railway Run

Run this as a one-time Railway command against the backend service environment:

```bash
python scripts/seed_railway_demo_cases.py
```

Do not change the persistent Railway backend startup command. It must remain:

```bash
bash scripts/render-start.sh
```

## Seeded Cases

- Demo Patient 1 - Audit Ready: approved snapshot, export available, JSON export event recorded, manifest verifies.
- Demo Patient 2 - Missing Evidence: signal, escalation, in-progress intervention task, missing required evidence, normal approval blocked.
- Demo Patient 3 - Rejected Review: ready snapshot rejected with the documented rejection reason and a new snapshot required.
- Demo Patient 4 - Override Approval: one persisted checklist gap, normal approval blocked, superuser override approved with the documented override reason, manifest verifies.

The script is idempotent for the intended demo path. If the latest synthetic snapshot for a demo patient does not match the required posture, the script creates a new immutable snapshot instead of mutating persisted packet content.
