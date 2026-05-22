# ACCESS2 July MVP User Guide Screenshots

Use this folder for screenshots referenced by `docs/access2-july-mvp-user-guide.md`.

Guardrails:

- Production screenshots must be read-only.
- Localhost screenshots may show V2 correction-loop proof only on loopback targets.
- Do not capture staging or production mutation workflows.
- Do not include real PHI, secrets, passwords, tokens, cookies, or session values.

## Captured Or Placed Files

- `01-login.png` - captured from the production login screen; no visible secrets.
- `02-dashboard-or-landing.png` - captured from the production read-only patient queue.
- `03-patient-detail.png` - captured from the production read-only Demo Patient 1 detail page.
- `04-outcome-evidence-readiness.png` - captured from the production read-only Outcome Evidence Readiness section. Current persisted production packet data shows no ACCESS clinical track outcome fields in this section.
- `05-immutable-review-packet.png` - captured from the production read-only review packet backlog.
- `06-audit-ready-evidence.png` - captured from the production read-only audit bundle verification posture.
- `07-localhost-correction-loop.png` - placed from the existing safe localhost login screenshot. This is a localhost-only V2 entrypoint image, not a live mutation-loop capture.
- `08-csv-dry-run-output.png` - generated from the documented local dry-run/no-write CSV validator output after the validator was run against the synthetic sample.

## Pending Manual Capture

- Full V2 correction-loop proof screenshot after reviewer rejection/correction/approval remains pending. Capture it only on verified loopback targets with disposable synthetic local data. Do not capture staging or production mutation workflows.
