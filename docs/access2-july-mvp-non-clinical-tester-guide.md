# ACCESS2 July MVP Tester Guide for Non-Clinical Testers

Date/checkpoint: May 22, 2026

## Purpose

Use this guide if you have been asked to test the ACCESS2 July MVP and you do not have a clinical or healthcare operations background.

You do not need to judge medical accuracy. Your job is to check whether a normal user can follow the screens, understand the story, and see that the product keeps its safety boundaries.

This guide is for testing with synthetic/demo data only.

## What ACCESS2 Is

ACCESS2 is a chronic-care workflow and audit-readiness application.

In plain English, it helps show what happened in a care workflow:

- Why a patient needed attention.
- What action the care team took.
- What result happened after that action.
- What evidence supports the result.
- What packet was reviewed.
- Whether the packet was approved or rejected.
- Whether approved evidence is ready for audit review.

The July MVP is trying to prove the accountability chain from patient signal to audit-ready evidence.

## What ACCESS2 Is Not

ACCESS2 July MVP is not:

- A live medical record system.
- A billing system.
- A claims submission system.
- A CMS production submission system.
- A place for real PHI in this MVP.
- A system that makes clinical decisions by itself.
- A replacement for clinical review, compliance review, security review, or production launch approval.

Do not enter real patient data, real names, real medical details, secrets, tokens, passwords, claims, billing information, or CMS submission information.

## Simple Concept Glossary

**Chronic care**  
Care for a health condition that lasts a long time, such as diabetes, high blood pressure, or heart disease.

**Patient signal**  
The first sign that a patient may need attention. It could be a care gap, missed follow-up, or a result that needs review.

**Escalation**  
A signal that has been flagged for action. It means someone needs to look at the issue and follow up.

**Intervention**  
The action taken to help with the issue. For example, a care team might schedule follow-up, update a care plan, or contact a patient.

**Outcome**  
What happened after the intervention.

**Measurable outcome**  
An outcome that can be compared or checked. It should have a clear result, such as a follow-up value, completed care step, or documented improvement.

**Care update**  
A note or event that shows the patient's care plan or follow-up status changed.

**Evidence**  
Information that supports the story. Evidence helps answer, "How do we know this happened?"

**Review packet**  
A saved package of information that a reviewer can inspect. It should summarize the care story and the evidence.

**Immutable**  
Cannot be changed after it is saved. In ACCESS2, an immutable review packet must not be edited or rebuilt when someone reads it later.

**Approval**  
A reviewer accepts the packet as ready for the next evidence step.

**Rejection**  
A reviewer does not accept the packet. The rejected packet should remain preserved, and the issue should be corrected in a new packet or later workflow step.

**Correction loop**  
The process of rejecting a packet, fixing the issue, saving a corrected packet, and reviewing it again. In this MVP, mutation for this proof is localhost-only.

**Audit-ready evidence**  
Evidence that is organized enough to support a later audit review. It does not mean CMS has approved it.

**CSV dry-run**  
A local file check that validates a CSV file format without writing anything to the database.

**Synthetic data**  
Fake demo data made for testing. It is not real patient information.

**PHI**  
Protected Health Information. This means real patient-identifying health information. Do not use real PHI in this MVP.

**CMS**  
Centers for Medicare & Medicaid Services. ACCESS2 is aligned to a CMS ACCESS-style accountability model, but this MVP does not submit data to CMS.

**ACCESS track**  
The evidence category or path used to describe the chronic-care outcome story for ACCESS-style review.

**Outcome Evidence Readiness**  
A read-only section that helps show whether the outcome evidence is complete enough for review.

## The Big Workflow

The main ACCESS2 workflow is:

```text
signal -> escalation -> intervention -> measurable outcome -> care update -> immutable review packet -> approval/rejection -> audit-ready evidence
```

The tester should check whether this order is visible and understandable.

### 1. Signal

What it means:  
A signal is the first sign that a patient needs attention.

What to look for:  
Look for the patient reason, care gap, risk flag, or event that started the workflow.

What is a problem:  
Report a problem if the patient appears in the workflow but there is no clear reason why the case started.

### 2. Escalation

What it means:  
An escalation means the signal needs follow-up.

What to look for:  
Look for a status, label, timeline item, or summary that shows the issue was flagged for action.

What is a problem:  
Report a problem if the escalation is missing, unclear, out of order, or does not match the patient story.

### 3. Intervention

What it means:  
An intervention is the action taken by the care team.

What to look for:  
Look for what action happened, when it happened, and how it connects to the escalation.

What is a problem:  
Report a problem if an outcome appears before any action, or if the action is too vague to understand.

### 4. Measurable Outcome

What it means:  
A measurable outcome is the result that can be checked.

What to look for:  
Look for a baseline, follow-up value, completion status, or other evidence that shows the result.

What is a problem:  
Report a problem if the result is missing, impossible to compare, or not connected to the intervention.

### 5. Care Update

What it means:  
A care update shows that the care plan or follow-up status changed.

What to look for:  
Look for a completed follow-up, care-plan note, or milestone that shows the case moved forward.

What is a problem:  
Report a problem if the care update is missing or contradicts the outcome.

### 6. Immutable Review Packet

What it means:  
A review packet is a saved snapshot of the evidence. Immutable means the saved packet should not change later.

What to look for:  
Look for packet content, packet status, created date, reviewer information, and evidence summary.

What is a problem:  
Report a problem if the packet seems to change when you only view it, or if rejected history appears overwritten.

### 7. Approval Or Rejection

What it means:  
A reviewer can approve the packet or reject it.

What to look for:  
Look for clear status such as approved, rejected, pending review, or needs correction.

What is a problem:  
Report a problem if the status is unclear, if a rejected packet looks approved, or if production allows edits.

### 8. Audit-Ready Evidence

What it means:  
Approved evidence can be organized for audit review.

What to look for:  
Look for audit bundle availability, manifest verification, or audit-ready status tied to an approved packet.

What is a problem:  
Report a problem if audit evidence appears available for a rejected packet, or if the page implies claims, billing, or CMS production submission.

## Testing Mindset

You are not judging whether the care was medically correct.

You are checking:

- Can I find the screen?
- Does the screen explain itself?
- Is the data consistent?
- Does the workflow order make sense?
- Are read-only areas actually read-only?
- Are warning and scope messages clear?
- Are there broken links, confusing labels, missing data, or unexpected errors?
- Does the app avoid claims that it is billing-ready, claims-ready, CMS-approved, or production PHI-ready?

If something is confusing to you, it may also confuse a real stakeholder. Report it as a question or minor defect.

## Test Environments And Safety Boundaries

### Tester Access Options

Use this section before testing. It explains what you can test from outside the project owner's desktop.

#### 1. External Hands-On Testing

Use production read-only only:

- URL: `https://access2.salvardata.com`
- Test login, navigation, patient detail, Outcome Evidence Readiness, review packet visibility, audit-ready evidence visibility, guide clarity, confusing labels, and read-only behavior.
- Do not test approval, rejection, correction-loop mutation, production writes, staging writes, or any other data-changing action.
- Do not report "cannot access V2 localhost" as a defect. That is expected because V2 runs only on the project owner's local desktop unless you have your own local setup.
- Do report confusion if this guide, the user guide, or the app makes the localhost-only limit unclear.

#### 2. Supervised V2 Walkthrough

Use this when the tester needs to see the V2 correction loop but does not have a local ACCESS2 setup.

- The project owner runs localhost V2 on their desktop.
- The tester observes by screen share or approved remote-control session.
- Mutation remains localhost-only.
- Data must remain disposable synthetic/demo data only.
- The tester may comment on screen clarity, wording, workflow order, and whether the correction-loop story is understandable.

#### 3. Independent Local V2 Testing

Use this only if the tester has their own local ACCESS2 setup.

- The tester needs Docker/local setup and approved synthetic data.
- The tester must use loopback targets only, such as `localhost` or `127.0.0.1`.
- The tester must not point V2 mutation testing at production, staging, Railway, `https://`, or any non-loopback target.
- A separate local tester setup guide should cover this if independent local V2 testing is needed.

#### 4. Future Shared Synthetic V2 Sandbox

A shared synthetic V2 demo sandbox could be created later. It is not part of the current July MVP guardrails.

- Do not assume a shared V2 environment exists.
- Do not create or use staging/production mutation tests for this guide.
- Treat shared sandbox work as a future planning item only.

### Production Read-Only V1 Demo

Use this for external hands-on testing.

- Production is look-only.
- Do not change anything.
- Do not approve, reject, assign, create, edit, import, or submit anything.
- Use synthetic/demo data only.
- Report any production edit control as a serious issue.

### Localhost-Only V2 Correction-Loop Proof

Use this only if your test plan specifically asks you to test the correction loop locally or observe it through a supervised walkthrough.

- Localhost means a loopback address such as `http://localhost:3000`, `http://localhost:3001`, or `http://127.0.0.1`.
- This is the safe place for approved demo mutation tests with synthetic data.
- Do not run this against production, staging, Railway, `https://`, or any non-loopback target.
- External testers cannot open the project owner's localhost directly from their own browser. They can observe the owner's desktop by screen share or remote-control session if approved.
- Independent V2 mutation testing requires the tester's own local ACCESS2 setup and approved synthetic data.

### Local CSV Dry-Run / No-Write Validator

Use this only if your test plan asks you to review the CSV dry-run output.

- The CSV dry-run checks file format only.
- It should not write to the database.
- It should not read from the database.
- It should not make network calls.
- It should use synthetic/demo CSV data only.

Example PowerShell command shape:

```powershell
cd C:\dev\access2
py -3 backend\scripts\validate_external_csv_intake.py docs\examples\access2_external_csv_intake_valid_sample.csv
```

## Step-By-Step Tester Walkthrough

Use these checkboxes as a simple testing path.

### Before You Start

- [ ] Confirm which environment you are testing: production read-only, localhost V2, or CSV dry-run.
- [ ] Confirm you are using synthetic/demo data only.
- [ ] Confirm you are not using real PHI, claims data, billing data, CMS submission data, secrets, or tokens.
- [ ] Open this guide and the July MVP user guide.
- [ ] Prepare a place to save screenshots or notes.

### Log In

- [ ] Open the provided ACCESS2 URL.
- [ ] Confirm the login page loads.
- [ ] Confirm the page explains what ACCESS2 does in plain language.
- [ ] Confirm the page includes the demo/scope boundary if visible.
- [ ] Log in with approved demo credentials only.

Report a defect if the page is blank, crashes, has broken layout, or asks for real patient information.

### View The Dashboard Or Landing Page

- [ ] Confirm the first screen after login loads.
- [ ] Look for patient worklist, audit-readiness, or demo navigation.
- [ ] Confirm labels are understandable.
- [ ] Confirm production screens are read-only.

Report a defect if you cannot tell where to go next.

### Open A Patient Record

- [ ] Open a synthetic/demo patient.
- [ ] Confirm the patient page loads.
- [ ] Confirm the patient data looks synthetic or demo-safe.
- [ ] Confirm the page does not show real PHI.

Report a defect if patient details are inconsistent across sections.

### Find The Signal, Escalation, Intervention, And Outcome Story

- [ ] Find why the patient needed attention.
- [ ] Find the escalation or care gap.
- [ ] Find what intervention happened.
- [ ] Find the measurable outcome.
- [ ] Confirm the order makes sense.

Report a defect if the story is missing, out of order, or too unclear to explain.

### Find Outcome Evidence Readiness

- [ ] Find the Outcome Evidence Readiness section if it is present.
- [ ] Confirm it is read-only.
- [ ] Look for ACCESS track, qualifying condition, metric, baseline, follow-up, readiness status, evidence completeness, or care update milestone.
- [ ] Confirm it does not say evidence is being submitted to CMS.

Report a defect if the section implies claims submission, billing, or CMS production submission.

### Review The Immutable Review Packet

- [ ] Find the review packet or review summary.
- [ ] Confirm packet content is readable.
- [ ] Confirm packet status is clear.
- [ ] Confirm the page treats the packet as saved evidence.
- [ ] Confirm read-only views do not rebuild or edit packet content.

Report a defect if a saved packet appears to change during view-only use.

### Review Audit-Ready Evidence

- [ ] Find audit bundle or audit-ready evidence visibility if available.
- [ ] Confirm audit evidence is tied to an approved packet.
- [ ] Confirm rejected packet history remains visible when expected.
- [ ] Confirm wording does not claim actual CMS production submission.

Report a defect if audit evidence appears available for a rejected packet.

### Confirm Scope And Boundary Notes Are Visible

- [ ] Confirm the app or guide makes clear that demo data is synthetic.
- [ ] Confirm production is described as read-only.
- [ ] Confirm V2 correction-loop mutation is localhost-only.
- [ ] Confirm CSV validation is dry-run/no-write.
- [ ] Confirm there are no unsupported claims about HIPAA certification, CMS approval, billing readiness, claims readiness, or production PHI readiness.

### Optional Localhost-Only Correction-Loop Test

Only do this if your test plan explicitly asks for it.

- [ ] Confirm the URL is loopback only: `localhost`, `127.0.0.1`, or another approved local target.
- [ ] Confirm you are either on your own local ACCESS2 setup or observing the project owner's localhost V2 session by approved screen share or remote control.
- [ ] Confirm you are using disposable synthetic data.
- [ ] Confirm the rejected packet remains preserved.
- [ ] Confirm correction creates a new/corrected packet instead of editing old history.
- [ ] Confirm approved corrected evidence can become audit-bundle-ready.

Stop and report immediately if the target is production, staging, Railway, `https://`, or any non-loopback URL.

External testers should not report "cannot access V2 localhost" as a defect. That limitation is expected. Report it only if the docs or test plan failed to explain it clearly.

### Optional CSV Dry-Run Validation Review

Only do this if your test plan explicitly asks for it.

- [ ] Run the approved local PowerShell command.
- [ ] Confirm the output says dry-run only.
- [ ] Confirm accepted and rejected row counts are clear.
- [ ] Confirm no database, network, or file write operation is reported.
- [ ] Confirm the CSV uses synthetic/demo data only.

Report a defect if the validator appears to write to the database.

## Expected Observations

You should expect to see:

- Synthetic/demo patient data.
- Patient workflow information.
- A signal, escalation, intervention, outcome, and care update story.
- Outcome Evidence Readiness when evidence fields are available.
- Review packet content or review summary.
- Audit evidence availability only when a packet is approved.
- Clear language saying this is not claims submission, billing, or CMS production submission.
- Read-only behavior in production.
- Localhost-only mutation for the V2 correction-loop proof.
- Local dry-run/no-write behavior for CSV validation.

## What To Report As A Defect

Report these as defects:

- Login page does not load.
- App crashes or shows a blank page.
- Labels are confusing or missing.
- Links are broken.
- Screenshots or docs do not match the app.
- Patient data is inconsistent across sections.
- Real PHI, secrets, tokens, or private credentials appear.
- A production read-only page allows edits.
- Scope warnings are missing.
- Audit bundle appears available for a rejected packet.
- Rejected packet history appears overwritten.
- Immutable packet content appears rebuilt or changed during read-only viewing.
- CSV dry-run appears to write to the database.
- The app claims to submit claims, submit to CMS production, handle billing, or make clinical decisions by itself.

## What Not To Report As A Defect

These are expected MVP limitations:

- No real PHI.
- No EHR integration.
- No FHIR integration.
- No claims submission.
- No billing workflow.
- No CMS production submission.
- No live medical record workflow.
- No clinical decision-making by the app.
- Production V1 is intentionally read-only.
- V2 correction-loop mutation is intentionally localhost-only.
- External testers cannot directly open localhost V2 running on the project owner's desktop.
- V2 correction-loop screenshots or walkthroughs may be observed by screen share or approved remote control, but they are not independently testable unless the tester has a local ACCESS2 setup.
- CSV validation is intentionally dry-run/no-write.

## Simple Test Notes Template

Copy and paste this block for each issue or question.

```text
Tester name:
Date:
Environment:
Browser:
Test area:

What I expected:

What happened:

Screenshot/file name:

Severity: blocker / major / minor / question

Notes:
```

Severity guide:

- Blocker: You cannot continue testing, or a guardrail appears broken.
- Major: A core workflow is wrong, missing, confusing, or unsafe.
- Minor: The app works, but wording, layout, or labels are confusing.
- Question: You are not sure whether the behavior is expected.

## Beginner-Friendly FAQ

**Am I testing medical accuracy?**  
No. You are testing whether the workflow and evidence story are understandable and consistent.

**Should I use real patient data?**  
No. Use synthetic/demo data only. Do not enter real PHI.

**Why is production read-only?**  
Because the current V1 production demo is meant to show the evidence workflow safely without changing production data.

**What does immutable mean?**  
It means a saved packet should not change later. If a correction is needed, the system should preserve the old packet and create a corrected/new packet.

**What is the difference between a rejected packet and a corrected packet?**  
A rejected packet is the saved packet that a reviewer did not accept. A corrected packet is a new or later packet created after the issue was fixed. The rejected packet should not be overwritten.

**What is a CSV dry-run?**  
It is a local file check. It validates whether a CSV file has the expected format, but it should not write anything to the database.

**What does audit-ready mean?**  
It means the evidence is organized enough for audit review. It does not mean CMS has accepted it.

**Is this sending data to CMS?**  
No. The July MVP does not submit data to CMS production systems.

**Does ACCESS2 make clinical decisions by itself?**  
No. The MVP organizes workflow and evidence. It does not replace human clinical judgment.

**Should I test mutation in production?**  
No. Production V1 is read-only.

**Where can V2 correction-loop mutation be tested?**  
Only on approved localhost targets with synthetic data.

**Can I open the project owner's localhost V2 from my own computer?**
No. `localhost` means the computer running ACCESS2. If V2 is running on the project owner's desktop, an external tester can only observe it by approved screen share or remote control.

## Related Docs

- [ACCESS2 July MVP User Guide](C:/dev/access2/docs/access2-july-mvp-user-guide.md)
- [ACCESS2 July MVP Final Rehearsal And Go/No-Go](C:/dev/access2/docs/access2-july-mvp-final-rehearsal-and-go-no-go.md)
- [ACCESS2 Stakeholder Walkthrough Feedback And Go/No-Go](C:/dev/access2/docs/access2-stakeholder-walkthrough-feedback-and-go-no-go.md)
- [ACCESS2 Stakeholder Demo Package Index](C:/dev/access2/docs/access2-stakeholder-demo-package-index.md)
