# Research: tobe-master-report-optional

**Phase**: 0 — Outline & Research  
**Spec**: [spec.md](spec.md)  
**Date**: 2026-07-21

No NEEDS CLARIFICATION markers remain in the spec. This phase documents the exact
edit targets found by inspecting the agent file, and confirms no residual unknowns.

---

## Decision 1 — Exact strings for the 3 edit sites

**File**: `src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md`

### Edit Site A — Fase 0-Pre pre-condition (line 145)

Current text (verbatim):
```
- **Pré-condição**: outputs AS-IS concluídos (`master-report.md`, `bounded-context-map.md`, `gaps-risks-report.md`)
```

Target text:
```
- **Pré-condição**: outputs AS-IS essenciais presentes — `bounded-context-map.md`, `architecture-blueprint.md`, `db-analysis-report.md` (ver Gate SD); `master-report.md` é opcional — se ausente, emitir `[AVISO]` e prosseguir
```

**Rationale**: The pre-condition accurately lists what is truly required. `master-report.md` is omitted from the mandatory list; the essential artifacts are named explicitly.

---

### Edit Site B — Trigger table SD gate (lines 1495–1498)

Current text (verbatim):
```
> ⛔ **[SD] Gate Obrigatório — AS-IS Master Report**: Antes de qualquer execução do trigger `SD`, verificar se `projects/{project_name}/outputs/asis/master-report.md` existe. Se não existir → **PARAR IMEDIATAMENTE** com a mensagem:
> `[GATE FAILED] AS-IS Master Report não encontrado. Execute o diagnóstico AS-IS (F1) antes de iniciar o design TO-BE`
```

Target text:
```
> ⚠️ **[SD] Verificação Opcional — AS-IS Master Report**: Antes de executar o trigger `SD`, verificar se `projects/{project_name}/outputs/asis/master-report.md` existe. Se não existir → emitir **aviso não-bloqueante**:
> `[AVISO] master-report.md não encontrado. O pipeline TO-BE prosseguirá com os artefatos AS-IS disponíveis. Para gerar o relatório consolidado execute: @ava-asis-orchestrator trigger: SR`
```

**Rationale**: `⛔` (hard block) replaced by `⚠️` (advisory). PARAR IMEDIATAMENTE removed. Escalation note in the following line (§2.2 artifact-only-consumption-protocol) is preserved unchanged.

---

### Edit Site C — Reasoning Approach step 1 (line 1810)

Current text (verbatim, up to the `; ler timing_benchmark_enabled` continuation):
```
1. **Validate** — **[GATE OBRIGATÓRIO — apenas trigger `SD`]** verificar se `projects/{project_name}/outputs/asis/master-report.md` existe; SE não existir → **PARAR IMEDIATAMENTE** com a mensagem: `[GATE FAILED] AS-IS Master Report não encontrado. Execute o diagnóstico AS-IS (F1) antes de iniciar o design TO-BE`;
```

Target text:
```
1. **Validate** — **[VERIFICAÇÃO OPCIONAL — apenas trigger `SD`]** verificar se `projects/{project_name}/outputs/asis/master-report.md` existe; SE não existir → emitir `[AVISO] master-report.md ausente — pipeline prosseguirá com artefatos AS-IS disponíveis` (**não interromper**); verificar artefatos essenciais (`bounded-context-map.md`, `architecture-blueprint.md`, `db-analysis-report.md`) — SE todos ausentes → **PARAR IMEDIATAMENTE** com `[GATE FAILED] Artefatos essenciais do AS-IS não encontrados. Execute @ava-asis-orchestrator antes de iniciar o design TO-BE`;
```

**Rationale**: The hard-stop on `master-report.md` alone is removed. A fallback hard-stop on all essential artifacts being absent is introduced to preserve the safety intent.

---

## Decision 2 — Version bump

- Current version: `2.4.1`
- Change type: PATCH (behavioral bug fix, no Output Contract change)
- Target version: `2.4.2`

**Rationale**: Constitution Article X — bug fixes in agent instructions = PATCH bump.

---

## Decision 3 — Escalation note preservation

The `[@artifact-only-consumption-protocol](../../shared/artifact-only-consumption-protocol.md) §2.2` note that follows Edit Site B is **retained unchanged**. It describes the general principle of waiting for user decisions, which remains valid for the advisory warning.

---

## Decision 4 — CHANGELOG entry

A `### Fixed` entry must be added to `CHANGELOG.md` documenting the removal of the hard gate. This is required by Constitution Article X for breaking behavioral changes.

```markdown
### Fixed
- `ava-tobe-orchestrator` v2.4.2: Removida obrigatoriedade bloqueante de `master-report.md`
  no trigger SD. O arquivo passa a ser verificado com aviso não-bloqueante; o pipeline
  prossegue com os demais artefatos AS-IS presentes. Gate de artefatos essenciais
  (`bounded-context-map.md`, `architecture-blueprint.md`, `db-analysis-report.md`)
  permanece bloqueante.
```

---

## Summary

| Unknown | Status |
|---|---|
| Exact edit strings | ✅ Confirmed from file inspection |
| Version bump type | ✅ PATCH (`2.4.1` → `2.4.2`) |
| CHANGELOG required | ✅ Yes, `### Fixed` entry |
| Module registration | ✅ Not required (agent already registered) |
| SKILL.md change | ✅ Not required (routing unchanged) |
| data-model.md | ✅ N/A (no data structures) |
| contracts/ | ✅ N/A (Output Contract unchanged) |
