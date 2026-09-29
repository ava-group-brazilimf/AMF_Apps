# Agent Implementation Plan: ava-summary / ava-summary-remediation (feature 040)

**Spec**: `specs/040-mermaid-playwright-autofix/spec.md`
**Feature**: Mermaid Playwright Auto-Fix Quality Gate
**Created**: 2026-08-17
**Status**: Implementado

---

## Summary

| Field                   | Value                                                                                                                                                                                                                                 |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Agent ID**            | `ava-summary` / `ava-summary-remediation` (modify-existing)                                                                                                                                                                           |
| **Phase**               | `F8 — Summary (cross-cutting)`                                                                                                                                                                                                        |
| **Module**              | `summary` (`src/modules/ava-fabric-agents/summary/`)                                                                                                                                                                                  |
| **Primary Requirement** | Carregar o Summary HTML gerado em Chromium headless, capturar falhas de renderização Mermaid, aplicar correções automáticas guiadas por guardrails (GR-001..GR-012) e emitir relatório estruturado antes de finalizar o arquivo       |
| **Technical Approach**  | Novo módulo Python `mermaid_playwright_gate.py` + probe JS `gate_mermaid_probe.js`; integrado como Phase G em `build_summary_comprehensive.py` e Phase 3.5 em `remediate_summary.py`; check C13.2 adicionado em `validate_summary.py` |

---

## Constitution Check

### Constitution Gates

- [x] **Article I** — Versão Mermaid não hardcoded no corpo do agente; resolvida do `mermaid.min.js` embutido no template
- [x] **Article II** — Frontmatter contém ONLY: `name`, `version`, `description` (PT + frases de ativação), `allowed-tools`
- [x] **Article II** — `name` segue `^ava-[a-z0-9-]+$` (`ava-summary`, `ava-summary-remediation`)
- [x] **Article III** — Fase F8/cross-cutting válida; ambos os agentes já registrados
- [x] **Article IV** — `module.yaml` recebe apenas bump de versão (sem novo `id` de agente)
- [x] **Article V** — Corpo dos agentes em Português Brasileiro; código Python em inglês técnico
- [x] **Article VI** — 6 BDD scenarios no spec (S1 nominal, S2 auto-fix, S3 exhaustion, S4 edge/SKIPPED, S5 isolation, S6 opt-out/RF9)
- [x] **Article VII** — Gate é read-only sobre HTML existente; nenhum impacto no sub-pipeline de segurança
- [x] **Article VIII** — N/A — agentes não usam JSON schema pipeline (`agent-task.schema.json`)
- [x] **Article IX** — N/A — arquivos `.md` são prompts LLM, não código com Clean Architecture
- [x] **Article X** — MINOR bump: `ava-summary` 2.1.0 → 2.2.0; `ava-summary-remediation` 1.4.2 → 1.5.0
- [x] **Article XI** — SKILL.md já existem para ambos; gate é interno, sem novo SKILL.md

### Quality Gate Check

- [x] Zero marcadores `[NEEDS CLARIFICATION]` no spec (resolvidos em 2026-08-17)
- [x] Outputs seguem `projects/{project_name}/outputs/summary/`
- [x] Agentes downstream (`validate_summary.py`, master-orchestrator) confirmados existentes

---

## 1. Technical Context

| Dimension     | Escolha                                                               | Fonte                                                                                     |
| ------------- | --------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Linguagem     | Python 3                                                              | Consistente com `build_summary_comprehensive.py` e `remediate_summary.py`                 |
| Motor browser | Playwright (Chromium headless) via Node.js                            | `probe_browser.js` já existente; `execute_probe()` em `render_blueprint_compatibility.py` |
| Probe JS      | `gate_mermaid_probe.js` (novo) + reuso de infra de `probe_browser.js` | Spec seção 12 — avaliar reaproveitamento                                                  |
| Mermaid       | v11.14.0 (pinned)                                                     | `mermaid.min.js` embutido no template                                                     |
| Guardrails    | `src/modules/ava-fabric-agents/shared/mermaid-guardrails.md` v1.6.0   | Confirmado existente                                                                      |
| Relatórios    | `mermaid-validation-report.json` + `.md`                              | Spec seção 3 e 5                                                                          |

---

## 2. Phase Placement

```
build_summary_comprehensive.py:
  Phase 1-6: coleta de dados + montagem HTML
  Phase G:   [NOVO] Playwright Mermaid Validation & Auto-Fix Gate
  Phase 7:   validate_summary.py / run_checks

remediate_summary.py:
  Phase 0-3: auditoria + síntese + sanitização
  Phase 3.5: [NOVO] Playwright Mermaid Validation & Auto-Fix Gate
  Phase 4-7: security + UI guard + rebuild + revalidação
```

---

## 3. Clean Architecture Alignment

N/A — Os agentes são arquivos de prompt LLM (`.md`). O código Python adicionado é infraestrutura de pipeline, não camada arquitetural de aplicação gerada.

---

## 4. Novos Artefatos

| Artefato                                                                 | Tipo   | Propósito                           |
| ------------------------------------------------------------------------ | ------ | ----------------------------------- |
| `src/modules/ava-fabric-agents/summary/utils/mermaid_playwright_gate.py` | NOVO   | Módulo principal do gate            |
| `src/modules/ava-fabric-agents/summary/utils/gate_mermaid_probe.js`      | NOVO   | Probe Node.js para o HTML completo  |
| `projects/{project_name}/outputs/summary/mermaid-validation-report.json` | OUTPUT | Relatório estruturado (schema v1.0) |
| `projects/{project_name}/outputs/summary/mermaid-validation-report.md`   | OUTPUT | Versão legível em Markdown          |

### Artefatos Modificados

| Artefato                            | Modificação                                                                                      |
| ----------------------------------- | ------------------------------------------------------------------------------------------------ |
| `build_summary_comprehensive.py`    | Flags `--skip-mermaid-gate`, `--mermaid-guardrails-path`, `--mermaid-gate-max-attempts`; Phase G |
| `remediate_summary.py`              | Mesmas flags; Phase 3.5; seção `mermaid_gate` em `remediation-report.json`                       |
| `validate_summary.py`               | Check C13.2 — lê `mermaid-validation-report.json`                                                |
| `render_blueprint_compatibility.py` | Nova função `discover_browser_executable()` exportada                                            |
| `summary-agent.md`                  | version 2.1.0 → 2.2.0 + description                                                              |
| `summary-remediation-agent.md`      | version 1.4.2 → 1.5.0 + description                                                              |
| `module.yaml`                       | version 1.4.0 (reflete CHANGELOG [2026-08-17])                                                   |

---

## 5. module.yaml Impact

Apenas bump de versão do módulo — nenhum agente novo registrado:

```yaml
# antes:  version: "1.2.0"
# depois: version: "1.3.0"
```

---

## 6. Observability & Trace Propagation

N/A — Gate é infraestrutura interna de build. Trilha de auditoria exposta via `mermaid-validation-report.json` com campos `before`, `after`, `timestamp` (ISO 8601) por cada `fix_applied`.

---

## 7. Schema Changes

| Schema                           | Mudança                | Descrição                            |
| -------------------------------- | ---------------------- | ------------------------------------ |
| `mermaid-validation-report.json` | NOVO                   | Schema v1.0 definido na Spec seção 5 |
| `remediation-report.json`        | EXTENSÃO (append-only) | Nova seção `mermaid_gate` adicionada |
| `agent-task.schema.json`         | NÃO                    | Não usado por estes agentes          |
| `agent-result.schema.json`       | NÃO                    | Não usado por estes agentes          |

---

## 8. Regras de Correção (GR-001 a GR-012)

Implementadas como tabela de regras priorizadas em `mermaid_playwright_gate.py`:

| ID     | Trigger                                                         | Correção                                                       |
| ------ | --------------------------------------------------------------- | -------------------------------------------------------------- |
| GR-001 | `graph` sem direção (`TD`/`LR`/etc.)                            | → `flowchart`                                                  |
| GR-002 | `graph TD` / `graph LR` etc.                                    | → `flowchart TD` / `flowchart LR`                              |
| GR-003 | Label multi-linha sem `<br/>` em quotes                         | Join + `<br/>` + wrap em `"..."`                               |
| GR-004 | `subgraph` sem `end` de fechamento                              | Insere `end` antes do próximo `subgraph` ou EoD                |
| GR-005 | Node ID com chars proibidos (`~→—` NBSP ZWS backtick `;` emoji) | Strip/replace por `_`                                          |
| GR-006 | Curly quotes em node ID                                         | → aspas retas                                                  |
| GR-007 | Node referenciado em aresta antes de declarado                  | Insere linha de declaração antes                               |
| GR-008 | Mais de 2 níveis de `subgraph` aninhado                         | Flatten 3rd level → 2nd level                                  |
| GR-009 | Diagrama C4 com `graph`/`flowchart` em vez de macros C4         | Reclassifica + flag `%% [NEEDS REVIEW]`                        |
| GR-010 | `sequenceDiagram` participant com chars proibidos               | Sanitiza + atualiza referências                                |
| GR-011 | `-->` em `stateDiagram-v2`                                      | Replace/valida sintaxe correta                                 |
| GR-012 | Fonte vazia ou só whitespace                                    | Substitui por placeholder `flowchart LR\n  A[No diagram data]` |

---

## 9. Complexity Tracking

| Gate   | Failure Reason                                    | Justification                                                   | Mitigating Controls                                           |
| ------ | ------------------------------------------------- | --------------------------------------------------------------- | ------------------------------------------------------------- |
| GR-003 | Label multi-linha requer entendimento de contexto | Regra é melhor-esforço; casos ambíguos → FAIL_UNRESOLVED        | max_attempts limita retries; placeholder garante visibilidade |
| GR-007 | Inserção de declaração pode quebrar fluxo         | Detecta por aresta; posição determinística (antes da 1ª aresta) | Re-probe valida resultado                                     |
| GR-008 | Flatten subgraph pode alterar semântica           | Regra sintática; tag `%% [NEEDS REVIEW]` adicionada             | max_attempts + FAIL_UNRESOLVED como fallback                  |

---

## 10. Test Strategy

| Tipo             | Ferramenta      | Alvo                                                      |
| ---------------- | --------------- | --------------------------------------------------------- |
| BDD Nominal      | Manual / FastQA | Scenario 1 — todos PASS sem intervenção                   |
| BDD Auto-Fix     | Manual / FastQA | Scenario 2 — GR-001/GR-002 corrigidos automaticamente     |
| BDD Exhaustion   | Manual / FastQA | Scenario 3 — placeholder `[INCOMPLETE]` após max_attempts |
| BDD Edge/SKIPPED | Manual / FastQA | Scenario 4 — Chromium ausente → graceful degrade          |
| BDD Isolation    | Manual / FastQA | Scenario 5 — zero writes fora de `outputs/summary/`       |
| BDD Opt-Out      | Manual / FastQA | Scenario 6 — `--skip-mermaid-gate` → DISABLED sem WARNING |
| Regressão        | Existing suite  | Builds sem `--skip-mermaid-gate` continuam funcionando    |
