# Implementation Plan: AS-IS Pipeline Context Budget + Dispatch Guard

**Branch**: `030-asis-pipeline-context-budget-dispatch-guard` | **Date**: 2026-07-29 | **Spec**: [spec.md](./spec.md)

## Summary

Tirar do LLM duas decisões que ele vinha tomando às cegas — *"quanto contexto este agente
precisa?"* e *"vale a pena despachar este agente?"* — e passá-las para **dois utilitários
determinísticos** que o orquestrador consulta com um `Bash` cada, sem custo de inferência.

`context_budget.py` lê o `manifest.json` da compressão e devolve, por agente, a fatia de
artefatos AST que ele realmente consome e o `execution_mode` (`subagent`/`inline`/`bc_scoped`).
`artifact_gate.py` lê o contrato de artefatos e devolve se aquele agente já entregou.
O `orchestrator-asis.md` ganha dois gates que consomem essas saídas, e o `solution-delphi.md`
ganha escrita incremental + resume idempotente por artefato.

O princípio de projeto é o mesmo de `business_rules_catalog_generator.py` (specs/028): quando
uma decisão pode ser calculada a partir de arquivos em disco, ela não deve depender de o LLM
se auto-reportar corretamente.

## Technical Context

**Language/Version**: Python 3.13 (stdlib `argparse`, `json`, `pathlib`; `pyyaml` já no módulo)
**Primary Dependencies**: nenhuma nova — reutiliza a convenção `utils/` de `module_partitioner.py`
**Storage**: arquivos — lê `outputs/asis/ast-raw/{language}/compressed/manifest.json` (fallback
legado `delphi-ast-raw/`) e `outputs/asis/**`; não escreve nada (utilitários são read-only)
**Testing**: verificação manual/CLI contra os dados reais de `processaERP-008` — sem harness
automatizado neste módulo (Fase 5)
**Project Type**: 2 utilitários CLI + edições de contrato em markdown de agente
**Scale/Scope**: até ~1,2M tokens brutos / 761K comprimidos por projeto (`processaERP-008`)
**Constraints**: determinístico (sem `random`/relógio na lógica de decisão); UTF-8 no Windows;
os utilitários **nunca** podem bloquear uma entrega — em erro, o default é sempre "despache"

## Constitution Check

- **Art. I (nada hardcoded)**: PASS — limiares `context_budget_inline_threshold` /
  `context_budget_bc_scoped_threshold` resolvidos do `project-config.yaml` com defaults
  400K/700K; `legacy_technology` resolve o path do `compressed/`.
- **Art. II (frontmatter / Output Contract)**: PASS — apenas `version` e `description` mudam nos
  dois agentes; nenhum campo de Output Contract adicionado ou removido.
- **Art. V (corpo em pt-BR)**: PASS — seções novas dos agentes, docstrings e logs em pt-BR.
- **Art. VI (BDD)**: PASS — 7 cenários Given-When-Then na spec.
- **Art. X (SemVer)**: PASS — MINOR nos dois agentes (adições retrocompatíveis).
- **Art. IV (`module.yaml`)**: N/A — utilitários não são registrados, consistente com
  `module_partitioner.py` / `sql_ir_generator.py` / `business_rules_catalog_generator.py`.

## Project Structure

```text
src/modules/ava-fabric-agents/asis-diagnostic/
├── utils/
│   ├── context_budget.py          # NOVO — budget por agente + execution_mode (M-1/M-2/M-3)
│   └── artifact_gate.py           # NOVO — guard pré-dispatch + contrato F1 (M-4 / RC-4)
└── agents/
    ├── orchestrator-asis.md       # MODIFICADO — v2.22.0
    └── solution-delphi.md         # MODIFICADO — v2.7.0

src/shared/tools/
├── pipeline_observer.py           # MODIFICADO — catálogo de versões
└── generate_observability_report.py  # MODIFICADO — catálogo de versões

docs/
└── guia-repositorios-legados-grandes.md  # NOVO — padrão conhecido (ISSUE-002 §6.4)

specs/030-asis-pipeline-context-budget-dispatch-guard/
└── spec.md · plan.md · tasks.md
```

**Structure Decision**: dois utilitários + edições de contrato dentro do módulo
`asis-diagnostic` existente. Nenhum módulo ou pacote novo.

## Design

### Utilitário — `context_budget.py`

- Resolve o `compressed/` por `legacy_technology`, com varredura de `ast-raw/*/` e fallback ao
  path legado `delphi-ast-raw/` (projetos antigos como `processaERP-008` ainda usam esse layout).
- Soma `artifacts[].tokens_out` do `manifest.json` — a mesma métrica que o motor `headroom`
  grava em `metrics.jsonl`.
- `AGENT_ARTIFACT_SLICE` é a **fonte canônica** do mapa agente → artefatos, derivada dos
  `## Input Contract` reais (specs/010). A tabela no `orchestrator-asis.md` é o espelho documental.
- Classificação por fatia, não só global: `db-analyzer` cai em `inline` (559K) enquanto
  `inventory` fica em `subagent` (72K) no mesmo projeto.
- Exit codes carregam a decisão: `0` subagent · `1` inline · `2` bc_scoped · `3` manifest ausente.

### Utilitário — `artifact_gate.py`

- `ARTIFACT_CONTRACTS` espelha 1:1 a tabela `§ Artifact Output Contract per Agent`. Suporta
  arquivo simples, glob com `min_count`, diretório com `min_count`, e `min_size` (rejeita
  placeholder — `qa/test-plan.md` ≥ 3.000 bytes).
- Itens `advisory` (globs de `fastqa/manual_test/`, que é global do workspace) aparecem no
  relatório mas **não decidem** `complete` — um falso "presente" ali faria o guard pular um
  dispatch necessário.
- `--all` filtra os agentes de solução inativos via `legacy_technology`, e acrescenta o
  relatório `F1_OUTPUT_CONTRACT` usado pelo Step 0.3 (Resume Detection).
- Exit codes: `0` completo (skip) · `1` incompleto (dispatch) · `2` erro.

### Agente — `orchestrator-asis.md` (v2.22.0)

| Seção | Mudança |
|---|---|
| `### Regras Fundamentais` | +Regra 10 (Context Budget antes de despachar) · +Regra 11 (Dispatch Guard obrigatório / anti retry storm) |
| `### Context Budget Gate` | **NOVA** — `evaluate_context_budget()`, semântica dos 3 modos, tabela de fatia por agente com os números reais de `processaERP-008` |
| `### Dispatch Guard` | **NOVA** — `should_dispatch()` com 3 guards (anti-storm, teto de tentativas, artefatos presentes) |
| `dispatch_schedule.phase_a_wave2` | `context_budget: mandatory` · `dispatch_guard: mandatory` · nota nomeando a serialização da wave como violação da Regra 3 (RC-3) |
| `### Streaming COLLECT Protocol` | Reset de `dispatched_in_current_iteration` no topo do loop · gates encadeados no dispatch da Wave 2 · guard no DISPATCH AUDIT |
| `### Retry Protocol` | `dispatch_guard: mandatory` · `max_dispatch_per_iteration: 1` · `retry_scope: missing_artifacts_only` |
| `dispatch_bridge_fastqa()` | Novo Step 0 — guard antes do `Read` do spec |
| `remediate_pending_agents()` | Guard antes da remediação forçada |
| `## Reasoning Approach` | **Novo Step 0.3** — Resume Detection (exceto em `SA|FULL`) · Step 3.1b reescrito com os 4 pré-requisitos v2.22 |
| `## Agent Completion Registry` | +5 campos: `dispatch_attempts`, `dispatched_in_current_iteration`, `dispatch_skipped_reason`, `ast_artifact_slice`, `execution_mode` |
| FASE OBRIGATÓRIA | `--version` 2.18.1 → 2.22.0 (estava defasado do frontmatter) |

### Agente — `solution-delphi.md` (v2.7.0)

Novo **Step 0.6 — Context Budget & Resume Check**, entre o Step 0.5 (partição) e o Step 1: mede
a própria fatia, escolhe a estratégia (fluxo normal / escrita incremental / por bounded
context) e aplica resume idempotente por artefato. Não substitui o LARGE ARTIFACT PROTOCOL do
Step 0 — soma-se a ele.

### Filosofia de falha (invariante transversal)

Ambos os gates **degradam e continuam**, alinhados a specs/011 e specs/012:

| Situação | Comportamento |
|---|---|
| `manifest.json` ausente / Step 0 não rodou | `execution_mode: subagent`, flag `CONTEXT_BUDGET_UNAVAILABLE`, esteira segue |
| `artifact_gate.py` falha | `{dispatch: true}` — o guard evita trabalho redundante, nunca impede entrega |
| `module-partition.json` ausente em `bc_scoped` | Aviso + degradação para `inline` |

`HALT` continua reservado exclusivamente a `STUB` e retries esgotados do agente de solução.

## Complexity Tracking

Nenhuma violação da constituição — sem entradas.
