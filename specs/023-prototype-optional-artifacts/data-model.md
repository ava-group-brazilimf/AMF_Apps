# Data Model: Prototype Optional Artifacts

**Feature**: 023-prototype-optional-artifacts
**Date**: 2026-07-21

---

## 1. Pre-flight Validation Table

Replaces the current prose-based `★`/`○` notation in `prototype-agent.md`.

### Input Artifact Catalogue (new classification)

| Artifact                     | Path                                           | Classification | Blocking?                              | Producing Agent                |
| ---------------------------- | ---------------------------------------------- | -------------- | -------------------------------------- | ------------------------------ |
| `business-rules.md`          | `outputs/asis/docs/business-rules.md`          | **MANDATORY**  | Yes — `DECISION: BLOCKED`              | `ava-asis-documentation`       |
| `bounded-context-map.md`     | `outputs/tobe/docs/bounded-context-map.md`     | **MANDATORY**  | Yes — `DECISION: BLOCKED`              | `ava-tobe-architecture-design` |
| `design-system.md`           | `outputs/tobe/docs/design-system.md`           | **OPTIONAL**   | No — `DECISION: AWAITING CONFIRMATION` | `ava-tobe-architecture-design` |
| `user-journeys.md`           | `outputs/tobe/docs/user-journeys.md`           | **OPTIONAL**   | No — `DECISION: AWAITING CONFIRMATION` | `ava-tobe-user-journeys`       |
| `api-map.md`                 | `outputs/tobe/docs/api-map.md`                 | **OPTIONAL**   | No — fallback to `openapi-spec.yaml`   | _(derived)_                    |
| `functional-requirements.md` | `outputs/asis/docs/functional-requirements.md` | **OPTIONAL**   | No — enrichment skipped                | `ava-asis-documentation`       |

### Pre-flight Decision Logic

```
IF business-rules.md MISSING OR bounded-context-map.md MISSING:
  DECISION: BLOCKED
  → emit canonical pre-flight table with ❌ for missing mandatory items
  → stop; write no output files
  → log {event: "end", status: "blocked"}

ELSE IF design-system.md MISSING OR user-journeys.md MISSING:
  DECISION: AWAITING CONFIRMATION
  → emit canonical pre-flight table with ⚠️ for missing optional items
  → display quality impact per R5/R6 (research.md)
  → prompt: "Continue? [yes/no]"
  → IF yes: PROCEED WITH WARNINGS
  → IF no:  log {event: "end", status: "cancelled", cancellation_reason: "user declined optional-artifact warning"}; stop

ELSE:
  DECISION: PROCEED
  → emit canonical pre-flight table with ✅ for all items
```

### Canonical Pre-flight Table Format

```
╔══════════════════════════════════════════════════════════════╗
║  PRE-FLIGHT CHECK — ava-prototype                           ║
╠══════════════════════════════════════════════════════════════╣
║  Mandatory Artifacts                                         ║
║  ─────────────────────────────────────────────────────────  ║
║  [✅|❌] business-rules.md           (ava-asis-documentation)║
║  [✅|❌] bounded-context-map.md      (ava-tobe-architecture) ║
╠══════════════════════════════════════════════════════════════╣
║  Optional Artifacts                                          ║
║  ─────────────────────────────────────────────────────────  ║
║  [✅|⚠️] design-system.md           (ava-tobe-architecture) ║
║  [✅|⚠️] user-journeys.md           (ava-tobe-user-journeys)║
║  [✅|⚠️] api-map.md                 (derived)               ║
║  [✅|⚠️] functional-requirements.md (ava-asis-documentation)║
╠══════════════════════════════════════════════════════════════╣
║  DECISION: [PROCEED | AWAITING CONFIRMATION | BLOCKED]       ║
╚══════════════════════════════════════════════════════════════╝
```

> **Nota de linguagem (Constitution Article V):** O corpo do agente é escrito em **Português Brasileiro**. Os rótulos de DECISÃO exibidos pelo agente em execução usam Português — os termos em Inglês neste documento são apenas referência de design:
>
> | Inglês (este documento) | Português (implementação do agente) |
> | ----------------------- | ----------------------------------- |
> | `PROCEED`               | `DECISÃO: PROSSEGUIR`               |
> | `PROCEED WITH WARNINGS` | `DECISÃO: PROSSEGUIR COM AVISOS`    |
> | `AWAITING CONFIRMATION` | `DECISÃO: AGUARDANDO CONFIRMAÇÃO`   |
> | `BLOCKED`               | `DECISÃO: BLOQUEADO`                |

---

## 2. Execution Log Entry Schema

**File**: `projects/{project_name}/outputs/tobe/prototype/execution-log.json`
**Format**: JSON array, append-mode.

### Start Entry

```json
{
  "agent": "ava-prototype",
  "event": "start",
  "timestamp": "<ISO8601>",
  "trace_id": "<uuid>",
  "project_name": "<string>"
}
```

### End Entry

```json
{
  "agent": "ava-prototype",
  "event": "end",
  "status": "success | blocked | warning | cancelled",
  "timestamp": "<ISO8601>",
  "trace_id": "<uuid>",
  "project_name": "<string>",
  "missing_optional": ["<artifact_relative_path>"],
  "cancellation_reason": "<string | null>"
}
```

**Status values**:

| Value       | Condition                                                                  |
| ----------- | -------------------------------------------------------------------------- |
| `success`   | All artifacts present; prototype generated without warnings                |
| `warning`   | One or more optional artifacts absent; user confirmed; prototype generated |
| `blocked`   | One or more mandatory artifacts missing; execution stopped                 |
| `cancelled` | Optional artifact warning shown; user declined confirmation                |

**`missing_optional`**: List of `outputs/…` relative paths for absent optional artifacts. Empty array `[]` when all optional artifacts are present.

**`cancellation_reason`**: String when `status == "cancelled"`, `null` otherwise. Canonical value: `"user declined optional-artifact warning"`.

---

## 3. Quality Impact Messages (per R5 and R6)

These exact strings are used in the pre-flight output and in the `screen-list.md` warnings section.

| Missing Artifact   | Quality Impact Message                                                                                                                                                            |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `design-system.md` | "Sem design-system.md, o protótipo utilizará tokens de design genéricos. Cores de marca, biblioteca de componentes e especificações de layout não serão aplicadas."               |
| `user-journeys.md` | "Sem user-journeys.md, as telas serão derivadas apenas das regras de negócio. Fluxos multi-etapa, happy/sad path e navegação entre telas não poderão ser modelados com precisão." |

---

## 4. `screen-list.md` Warnings Section

When one or more optional artifacts are absent and the user confirmed, a new `## Warnings` section is prepended to `screen-list.md`:

```markdown
## Warnings

> ⚠️ The following optional artifacts were absent at generation time.
> Prototype quality may be reduced in the areas listed below.

| Artifact                             | Impact                                                                       |
| ------------------------------------ | ---------------------------------------------------------------------------- |
| `outputs/tobe/docs/design-system.md` | Generic design tokens used. Brand colours and component library not applied. |
| `outputs/tobe/docs/user-journeys.md` | Screens derived from business rules only. Multi-step flows not modelled.     |
```

---

## 5. Version Bump

| File                             | Current Version | New Version | Bump Type               |
| -------------------------------- | --------------- | ----------- | ----------------------- |
| `prototype-agent.md` frontmatter | `1.1.0`         | `1.2.0`     | MINOR                   |
| `prototype/module.yaml`          | `1.1.0`         | `1.2.0`     | MINOR (sync with agent) |
