---
description: "Task list for AS-IS Pipeline Context Budget + Dispatch Guard"
---

# Tasks: AS-IS Pipeline Context Budget + Dispatch Guard

**Input**: Design documents from `/specs/030-asis-pipeline-context-budget-dispatch-guard/`

**Prerequisites**: plan.md, spec.md, `docs/issues/ISSUE-002-agent-stuck-pipeline-performance.md`

**Tests**: não há harness automatizado neste módulo; a verificação é CLI/manual contra os dados
reais de `processaERP-008` (Fase 5).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: US1 = orçamento de contexto (RC-1) · US2 = guard de dispatch (RC-2) ·
  US3 = retomada de esteira parcial (RC-4) · US4 = documentação do padrão

---

## Phase 1: Fundação — Utilitários Determinísticos 🎯 MVP-crítico

**Purpose**: as duas medições das quais todo o resto depende. Nenhuma decisão de dispatch pode
continuar dependendo de o LLM se auto-reportar.

- [x] T001 [US1] Criar `src/modules/ava-fabric-agents/asis-diagnostic/utils/context_budget.py` — CLI `--project`/`--language`/`--agent`/`--json` + overrides de limiar, UTF-8 no Windows, docstrings/logs em pt-BR (padrão `module_partitioner.py`).
- [x] T002 [US1] Implementar `resolve_compressed_dir()` — `ast-raw/{language}/compressed` → varredura `ast-raw/*/compressed` → fallback legado `delphi-ast-raw/compressed`.
- [x] T003 [US1] Definir `AGENT_ARTIFACT_SLICE` (fonte canônica do M-1) a partir dos `## Input Contract` reais dos agentes (specs/010); aliases para os 4 solution agents não-Delphi.
- [x] T004 [US1] Implementar `build_budget()` — soma `artifacts[].tokens_out`, calcula fatia + `pct_of_total` + modo por agente; limiares lidos do `project-config.yaml` (defaults 400K/700K).
- [x] T005 [US1] Saída humana (tabela) + `--json`; exit codes `0` subagent / `1` inline / `2` bc_scoped / `3` manifest ausente.
- [x] T006 [US2] Criar `utils/artifact_gate.py` — `ARTIFACT_CONTRACTS` espelhando 1:1 `§ Artifact Output Contract per Agent`; suporte a arquivo, glob com `min_count`, diretório e `min_size`.
- [x] T007 [US2] Implementar flag `advisory` — globs de `fastqa/manual_test/` (diretório global do workspace) informam mas não decidem `complete`, para não produzir falso "presente" e pular um dispatch necessário.
- [x] T008 [US3] Implementar `--all`: filtra solution agents inativos via `legacy_technology` e acrescenta o relatório `F1_OUTPUT_CONTRACT` (12 artefatos) com `completeness_pct`.
- [x] T009 [US2] Saída humana + `--json`; exit codes `0` completo (skip) / `1` incompleto (dispatch) / `2` erro.

**Checkpoint**: ambos os utilitários rodam contra `processaERP-008` e reproduzem os números da ISSUE-002.

---

## Phase 2: Context Budget Gate no Orquestrador (US1)

- [x] T010 [US1] `orchestrator-asis.md` — bump `2.21.1` → `2.22.0`, `date` → 2026-07-29, nota `v2.22` na `description`.
- [x] T011 [US1] Nova seção `### Context Budget Gate` — `evaluate_context_budget()`, banner `🧮 CONTEXT BUDGET`, tabela de semântica dos 3 modos, tabela de fatia por agente com os números reais de `processaERP-008`.
- [x] T012 [US1] Nova **Regra Fundamental 10** — dispatch sem `ast_artifact_slice` = violação de contrato; nunca instruir agente a "ler todos os artefatos comprimidos".
- [x] T013 [US1] `dispatch_schedule.phase_a_wave2` — `context_budget: mandatory`; nota nomeando a serialização da wave como violação da Regra 3 (M-5 / RC-3).
- [x] T014 [US1] Step 3.1b reescrito — 4 pré-requisitos v2.22 (budget, guard por agente, contrato do prompt, comportamento por modo).

---

## Phase 3: Dispatch Guard no Orquestrador (US2)

- [x] T015 [US2] Nova seção `### Dispatch Guard — Artifact Existence Precheck` — `should_dispatch()` com Guard 1 (anti-storm), Guard 2 (teto de 4 tentativas), Guard 3 (artefatos presentes).
- [x] T016 [US2] Nova **Regra Fundamental 11** — guard antes de TODO dispatch; 2 dispatches do mesmo agente na mesma iteração = retry storm proibido.
- [x] T017 [US2] Streaming COLLECT Protocol — reset de `dispatched_in_current_iteration` no topo do loop; gates encadeados no dispatch da Wave 2; guard no DISPATCH AUDIT.
- [x] T018 [US2] `retry_config` — `dispatch_guard: mandatory`, `max_dispatch_per_iteration: 1`, `retry_scope: missing_artifacts_only` + nota anti retry storm.
- [x] T019 [P] [US2] `dispatch_bridge_fastqa()` — novo Step 0 com guard antes do `Read` do spec.
- [x] T020 [P] [US2] `remediate_pending_agents()` — guard antes da remediação forçada; `artifacts_present` resolve o pendente sem dispatch.
- [x] T021 [US2] `## Agent Completion Registry` — +5 campos (`dispatch_attempts`, `dispatched_in_current_iteration`, `dispatch_skipped_reason`, `ast_artifact_slice`, `execution_mode`).
- [x] T022 [US2] `§ Artifact Output Contract per Agent` — nota apontando o espelho executável em `artifact_gate.py`.

---

## Phase 4: Retomada + Agente de Solução (US3)

- [x] T023 [US3] `orchestrator-asis.md` — novo **Step 0.3 (Resume Detection)** no `## Reasoning Approach`: `artifact_gate.py --all --json`, pré-registro dos completos, banner `📦 Contrato F1`, exceção explícita para `SA|FULL`.
- [x] T024 [US1/US3] `solution-delphi.md` — bump `2.6.0` → `2.7.0` + nota `v2.7.0` na `description`.
- [x] T025 [US1/US3] `solution-delphi.md` — novo **Step 0.6 (Context Budget & Resume Check)**: tabela de estratégia por `execution_mode`, resume idempotente por artefato, consumo de `artifacts_missing[]`, banner ao usuário, degradação em caso de falha.
- [x] T026 [P] [US4] Sincronizar literais de versão — `--version` da FASE OBRIGATÓRIA nos 2 agentes + catálogos de `pipeline_observer.py` e `generate_observability_report.py` (estavam defasados: orquestrador 2.18.0 vs. frontmatter 2.21.1).

---

## Phase 5: Verificação (dados reais de processaERP-008)

- [x] T027 [US1] `context_budget.py --project processaERP-008` → `total_tokens: 761376`, `execution_mode: bc_scoped`, exit 2 — bate com a ISSUE-002 §3 (761.376 tokens).
- [x] T028 [US1] Fatias conferem com a ISSUE-002 §5 M-1: `db-analyzer` 559.144 (73,4%) · `doc:VC/RF/RN/BRF` 135.259 (17,8%) · `inventory` 72.434 (9,5%) · `events-pubsub` 417 (0,1%) — nenhum agente da Wave 2 recebe 100%.
- [x] T029 [US2] `artifact_gate.py --project processaERP-008 --agent ava-asis-inventory` → SKIP, exit 0 (4 artefatos presentes).
- [x] T030 [US3] `artifact_gate.py --project processaERP-008 --all` → `📦 Contrato F1: 3/12 (25.0%)`, exit 1; `db-analyzer`, `doc:*`, `gaps-risks`, `gap-migration` e `master-report.md` listados como DISPATCH — reproduz o RC-4 da ISSUE-002.
- [x] T031 [US2] Caminho de erro: projeto inexistente → exit 2; `manifest.json` ausente → `status: manifest_missing` + `execution_mode: subagent` (degrada, não bloqueia).

---

## Phase 6: Documentação (US4)

- [x] T032 [US4] `docs/guia-repositorios-legados-grandes.md` — padrão conhecido para repos > 200 units / > 100K LOC: sintoma, 4 causas, tabela de mitigações, checklist de pré-execução (3 comandos), tuning por `project-config.yaml`, procedimento de retomada, sinais de regressão.
- [x] T033 [US4] SpecKit — `spec.md` (7 cenários BDD + exclusões honestas), `plan.md` (design + Constitution Check), `tasks.md` (este arquivo).

---

## Dependencies & Execution Order

- Fase 1 (utilitários) bloqueia tudo — os gates dos agentes apenas consomem suas saídas.
- Fases 2 e 3 tocam o mesmo arquivo (`orchestrator-asis.md`) → **sequenciais entre si**.
- Fase 4 depende do contrato de saída definido na Fase 1 (`artifacts_missing[]`, `F1_OUTPUT_CONTRACT`).
- T019, T020 e T026 são `[P]` (seções/arquivos independentes).
- Fase 5 verifica ponta a ponta contra dados reais; Fase 6 fecha a documentação.

## Notes

- A decisão de dispatch é **determinística** — não depende de o agente se auto-reportar. Esse é o núcleo da correção, mesmo princípio de specs/028.
- Ambos os utilitários são **read-only** e falham para o lado seguro: em erro, sempre "despache" / "modo subagent". Um guard que impede uma entrega seria pior que o problema que resolve.
- `module.yaml` inalterado — utilitários não são registrados (consistente com `module_partitioner.py` / `sql_ir_generator.py` / `business_rules_catalog_generator.py`).
- **Em aberto (não é tarefa desta entrega)**: reexecutar `processaERP-008` para os 8 artefatos F1 ausentes (ISSUE-002 §6 ação 1). É ação operacional — o Step 0.3 e o Dispatch Guard a habilitam, mas ela exige uma execução real da esteira.
- **Em aberto**: decompor o modo `bc_scoped` em sub-steps numerados dentro dos Steps 3-13 do `solution-delphi.md`. Hoje o agente recebe a instrução e o `module-partition.json`; a decomposição fina espera uma execução `bc_scoped` real para calibrar.
