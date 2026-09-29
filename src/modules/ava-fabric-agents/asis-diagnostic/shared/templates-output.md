# Output Templates — AVA AS-IS Orchestrator

Templates de saída referenciados pelo `orchestrator-asis.md`.

---

## Wave 1 Dispatch Checklist

```
[DISPATCH:W1] agents={N} | start={start_time_brz}
  solution-{tech} → running
  test-qa → running
  security-orchestrator → running
  inventory → running
  db-analyzer → running
```

---

## Error Evidence Template

Exibir para cada agente com `status: failed`:

```
[FAILED] {agent_id} | retries={retries}/4 | start={start_time_brz} | failed_at={end_time_brz}
  artifacts_ok: {artifacts_confirmed} | error: {error_detail}
```

---

## Completion Banner — Success

```
[COMPLETED] AS-IS — {project_name} | 7/7 agents OK | next: {next_phase}
```

---

## Completion Banner — With Errors

```
[COMPLETED_WITH_ERRORS] AS-IS — {project_name} | {N}/7 OK | failed: {lista}
  Action: human review required (HG)
```

---

## Workspace Reset Confirmation

```
[RESET:OK] {project_name} | 0A=outputs_deleted | 0B=shared_context_removed | 0C=template_copied
```

---

## Execution Timing Block

```
## ⏱ Execução Concluída
| Agent | Start (BRZ) | End (BRZ) | Duration |
|-------|-------------|-----------|----------|
| {agent_id} | {start_time_brz} | {end_time_brz} | {duration_seconds}s |
| ... | ... | ... | ... |
| **TOTAL** | {start_time_brz} | {end_time_brz} | {total_seconds}s |
```
