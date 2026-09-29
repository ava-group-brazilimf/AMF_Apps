# Quickstart Validation Guide: tobe-master-report-optional

**Purpose**: Verify that the three edits to `orchestrator-tobe.md` produce the correct behavior.  
**Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md)

---

## Prerequisites

- A project directory exists at `projects/{project_name}/` with:
  - `context/project-config.yaml` — valid project config
  - `context/shared-context.md` — present (can be minimal)
- AS-IS artifacts present: `outputs/asis/bounded-context-map.md`, `outputs/asis/architecture-blueprint.md`, `outputs/asis/db-analysis-report.md`
- `master-report.md` intentionally **absent** from `outputs/asis/`

---

## Validation Scenario 1 — SD trigger without master-report.md

**Goal**: Confirm the pipeline emits a `[AVISO]` and does NOT stop.

**Steps**:
1. Confirm `projects/{project_name}/outputs/asis/master-report.md` does NOT exist.
2. Invoke `@ava-tobe-orchestrator` with `trigger: SD`.

**Expected outcome**:
- Output contains `[AVISO] master-report.md` (non-blocking message).
- Output does **not** contain `[GATE FAILED]` or `PARAR IMEDIATAMENTE`.
- Pipeline proceeds to Fase 0-Pre (Architecture Decision Matrix).

---

## Validation Scenario 2 — SD trigger with master-report.md present

**Goal**: Confirm backward compatibility — no regression.

**Steps**:
1. Create `projects/{project_name}/outputs/asis/master-report.md` with any content.
2. Invoke `@ava-tobe-orchestrator` with `trigger: SD`.

**Expected outcome**:
- No `[AVISO]` about `master-report.md`.
- Pipeline proceeds normally to Fase 0-Pre.

---

## Validation Scenario 3 — SD trigger with NO AS-IS artifacts

**Goal**: Confirm essential gate still blocks when all AS-IS artifacts are missing.

**Steps**:
1. Remove (or do not create) all files under `outputs/asis/`.
2. Invoke `@ava-tobe-orchestrator` with `trigger: SD`.

**Expected outcome**:
- Output contains `[GATE FAILED] Artefatos essenciais do AS-IS não encontrados`.
- Pipeline stops immediately.
- No Fase 0-Pre is reached.

---

## Verification Checklist

- [ ] Scenario 1 passes — `[AVISO]` present, no `[GATE FAILED]`, pipeline continues
- [ ] Scenario 2 passes — no behavioral change when `master-report.md` is present
- [ ] Scenario 3 passes — `[GATE FAILED]` emitted when all essential artifacts are absent
- [ ] Version in frontmatter is `2.4.2`
- [ ] `CHANGELOG.md` contains `### Fixed` entry for `ava-tobe-orchestrator` v2.4.2
