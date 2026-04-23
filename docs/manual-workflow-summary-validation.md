# Manual workflow summary validation

Use the existing admin workflow bootstrap endpoint to create a compact validation set for queue/detail alignment. This is a developer reference only; it does not add end-user workflow controls.

## Local PowerShell setup

1. Start the local backend and frontend.
2. Use a superuser account for the API login.
3. Create one patient for each scenario with `POST /api/v1/admin/workflow/bootstrap`.

```powershell
$ApiBase = "http://localhost:8000/api/v1"

$Login = Invoke-RestMethod `
  -Method Post `
  -Uri "$ApiBase/auth/login" `
  -ContentType "application/json" `
  -Body (@{
    email = "admin@example.com"
    password = "Admin123!"
  } | ConvertTo-Json)

$Headers = @{
  Authorization = "Bearer $($Login.access_token)"
}
```

If your local superuser uses different credentials, change only `email` and `password`.

## Create validation scenarios

Each command returns IDs for the created records. The stored patient marker uses `validation-scenario:<scenario>:<unique-suffix>` so the same scenario can be created more than once. Patient detail displays only `Validation scenario: <scenario>`.

### Overdue task

```powershell
$OverdueTask = Invoke-RestMethod `
  -Method Post `
  -Uri "$ApiBase/admin/workflow/bootstrap" `
  -Headers $Headers `
  -ContentType "application/json" `
  -Body (@{
    scenario = "overdue_task"
    first_name = "Overdue"
    last_name = "Validation"
    date_of_birth = "1975-01-01"
  } | ConvertTo-Json)

$OverdueTask
```

Expected result: creates a patient with an open task due in the past. Use it to check task-driven urgency, stale/due posture, and queue/detail alignment.

### In-progress task

```powershell
$InProgressTask = Invoke-RestMethod `
  -Method Post `
  -Uri "$ApiBase/admin/workflow/bootstrap" `
  -Headers $Headers `
  -ContentType "application/json" `
  -Body (@{
    scenario = "in_progress_task"
    first_name = "InProgress"
    last_name = "Validation"
    date_of_birth = "1975-01-01"
  } | ConvertTo-Json)

$InProgressTask
```

Expected result: creates a patient with an active task already marked `in_progress`. Use it to check active work posture in queue and detail.

### Open escalation without active task

```powershell
$OpenEscalationNoTask = Invoke-RestMethod `
  -Method Post `
  -Uri "$ApiBase/admin/workflow/bootstrap" `
  -Headers $Headers `
  -ContentType "application/json" `
  -Body (@{
    scenario = "open_escalation_no_task"
    first_name = "EscalationOnly"
    last_name = "Validation"
    date_of_birth = "1975-01-01"
  } | ConvertTo-Json)

$OpenEscalationNoTask
```

Expected result: creates a patient with an open escalation and no task. Use it to check escalation driver and missing-task next-step posture.

### Recent completion

```powershell
$RecentCompletion = Invoke-RestMethod `
  -Method Post `
  -Uri "$ApiBase/admin/workflow/bootstrap" `
  -Headers $Headers `
  -ContentType "application/json" `
  -Body (@{
    scenario = "recent_completion"
    first_name = "Recent"
    last_name = "Completion"
    date_of_birth = "1975-01-01"
  } | ConvertTo-Json)

$RecentCompletion
```

Expected result: creates a patient with a recently completed task and resolved escalation. Use it to check recent completion and resolution posture.

### Routine

```powershell
$Routine = Invoke-RestMethod `
  -Method Post `
  -Uri "$ApiBase/admin/workflow/bootstrap" `
  -Headers $Headers `
  -ContentType "application/json" `
  -Body (@{
    scenario = "routine"
    first_name = "Routine"
    last_name = "Validation"
    date_of_birth = "1975-01-01"
  } | ConvertTo-Json)

$Routine
```

Expected result: creates a patient with no signal, escalation, or task. Use it to check the routine/no urgent workflow driver state.

Minimal request body pattern:

```json
{
  "scenario": "overdue_task",
  "first_name": "Overdue",
  "last_name": "Validation",
  "date_of_birth": "1975-01-01"
}
```

Supported `scenario` values:

| Scenario | Purpose |
| --- | --- |
| `overdue_task` | Open task with a past due date |
| `in_progress_task` | Active task already started |
| `open_escalation_no_task` | Open escalation with no active task |
| `recent_completion` | Recently completed task with resolved escalation |
| `routine` | Patient with no signal, escalation, or task |

## UI checks

For each scenario:

1. Open `/patients`.
2. Find the validation patient in the queue.
3. Record the visible summary state on the queue card, including attention reason, next step, owner, waiting-on, priority, staleness, recent change, and closure/readiness labels when present.
4. Open the patient detail page from the queue card.
5. Confirm the detail page shows `Validation scenario: <scenario>`.
6. Confirm the detail summary uses the same backend-derived state as the queue card.
7. Confirm there is no queue sorting change beyond the existing application behavior.

Expected coverage:

| Scenario | Queue/detail alignment to verify |
| --- | --- |
| `overdue_task` | The task-driven urgency and stale/due posture are consistent in both places |
| `in_progress_task` | The active work posture is consistent in both places |
| `open_escalation_no_task` | The escalation driver and missing task/next-step posture are consistent in both places |
| `recent_completion` | The recent completion/resolution posture is consistent in both places |
| `routine` | Both views show no urgent workflow driver without inventing task or escalation urgency |

### Patient-detail outcome banner

When validating patient-detail workflow actions, confirm the compact success banner appears near the workflow action area after the action completes.

Expected messages:

| Action | Expected banner |
| --- | --- |
| Start task | Task started successfully |
| Complete task | Task completed successfully |
| Create task | Task created successfully |
| Start escalation | Escalation started successfully |
| Resolve escalation | Escalation resolved successfully |

After selecting `Clear`, the banner should disappear, `workflow_outcome` should no longer be present in the URL, and the dismissed banner should not reappear after refreshing or revisiting the patient detail page.

## Operational summary checklist

Use this table to validate the backend-derived operational summary fields on the queue card and patient detail summary. The wording should match across surfaces when the same field is visible in both places.

| Scenario | Queue `attention_reason` | Detail `attention_reason` or why-now wording | Queue `next_step` | Detail next action | Queue/detail match? |
| --- | --- | --- | --- | --- | --- |
| `overdue_task` |  |  |  |  |  |
| `in_progress_task` |  |  |  |  |  |
| `open_escalation_no_task` |  |  |  |  |  |
| `recent_completion` |  |  |  |  |  |
| `routine` |  |  |  |  |  |

| Scenario | Queue `next_step_reason` | Detail supporting wording | Queue `recommended_timeframe` | Detail urgency/timeframe wording | Queue/detail match? |
| --- | --- | --- | --- | --- | --- |
| `overdue_task` |  |  |  |  |  |
| `in_progress_task` |  |  |  |  |  |
| `open_escalation_no_task` |  |  |  |  |  |
| `recent_completion` |  |  |  |  |  |
| `routine` |  |  |  |  |  |

| Scenario | Queue `active_owner_label` | Detail owner | Queue `waiting_on_label` | Detail waiting on | Queue/detail match? |
| --- | --- | --- | --- | --- | --- |
| `overdue_task` | Care team queue |  | Task start |  |  |
| `in_progress_task` | Assigned care team |  | Task completion |  |  |
| `open_escalation_no_task` | Clinical review |  | Task creation |  |  |
| `recent_completion` | Monitoring |  | Next signal or follow-up |  |  |
| `routine` | Routine monitoring |  | No immediate action |  |  |

## Reviewer notes

For each scenario, note any of the following:

| Scenario | Contradictory wording | Redundant wording | Overly crowded presentation | Queue/detail mismatch | Scenario-specific confusion |
| --- | --- | --- | --- | --- | --- |
| `overdue_task` |  |  |  |  |  |
| `in_progress_task` |  |  |  |  |  |
| `open_escalation_no_task` |  |  |  |  |  |
| `recent_completion` |  |  |  |  |  |
| `routine` |  |  |  |  |  |

Use this checklist only to confirm that existing backend-derived summary fields render consistently across queue and patient detail. Do not expand it into new workflow behavior or product scope.
