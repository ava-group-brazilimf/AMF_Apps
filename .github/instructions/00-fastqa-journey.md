---
description: "FastQA — Sistema de Jornadas de Trabalho. Regras de comportamento proativo, definição de jornadas e detecção automática."
applyTo: '**'
tools: ['memory', 'sequential-thinking']
---

# FastQA — Jornadas de Trabalho do QA

> **📌 REGRA CRÍTICA:** Ao receber o comando `@fastqa:journey`, carregar o agent `fastqa/agents/core/fastqa_0.2_journey_selector.md`.
> Para todos os demais comandos, o footer proativo de cada agent lê `journey_state.json` e sugere o próximo step.

---

## 🗺️ Jornadas Disponíveis

| ID | Nome | Persona | Steps | Duração |
|----|------|---------|-------|---------|
| `full_automation_cycle` | 🚀 Full Automation Cycle | Automation Engineer | 25 | 2-4 dias |
| `sprint_qa` | 🏃 Sprint QA (Manual) | Manual Tester | 8 | 4-8 horas |
| `automate_existing` | 🔧 Automate Existing TCs | QA com TCs prontos | 8 | 1-3 dias |
| `false_negative` | 🐛 False Negative Fix | QA debugando | 4 | 30 min - 2h |
| `api_quality` | 🌐 API Quality Assurance | API/Security Tester | 8 | 1-2 dias |
| `regression` | 📊 Regression Execution | QA Lead | 8 | 30 min - 1h |
| `test_plan_management` | 📋 Test Plan Management | QA organizando | 7 | 2-4 horas |
| `quick_exploratory` | ⚡ Quick Exploratory | QA smoke test | 3 | 15-30 min |

---

## 📂 Estado Persistente

**Arquivo:** `fastqa/scripts/journey_state.json`

O estado contém:
- `active_journey` — ID da jornada ativa (null = nenhuma)
- `current_step_index` — Próximo step a executar (0-based)
- `steps[]` — Array com comando, agent, status de cada step
- `context` — Dados compartilhados: pbi_id, test_plan_id, pipeline_id, build_id, repo_name
- `history[]` — Jornadas anteriores concluídas

---

## 🔄 Regras de Comportamento Proativo

### Após cada comando (footer proativo em todos os agents core):

1. **Ler** `fastqa/scripts/journey_state.json`
2. **Se jornada ativa:**
   - Marcar step como `"completed"`
   - Adicionar artefatos ao `artifacts_produced`
   - Atualizar `context` com IDs relevantes
   - Incrementar `current_step_index`
   - Exibir: `{ícone} {nome} — Step {N}/{total} ✅ Próximo: @fastqa:{comando}`
3. **Se sem jornada:**
   - Usar tabela de detecção abaixo para sugerir jornadas compatíveis
   - Exibir: `💡 Este comando faz parte da jornada **{nome}**. Ativar? @fastqa /journey`

### Steps condicionais:
- Avaliar condição (ex: "step_4_has_failures")
- Se não atendida → marcar como `"skipped"` → avançar

### Conclusão de jornada:
- Quando todos os steps são `completed` ou `skipped`
- Exibir resumo: duração, artefatos, IDs
- Mover para `history[]` e limpar `active_journey`

---

## 🔍 Detecção Automática de Jornada

| Comando | Jornadas (● principal) |
|---------|----------------------|
| `load_pbi` | ● J1, ● J2, ○ J5 |
| `identify_gaps` | ● J1 |
| `azdo_add_comment` | ● J1 |
| `estimate_effort` | ● J1 |
| `analyze_requirements` | ● J1 |
| `map_behaviors` | ● J1 |
| `ac_scope_analysis` | ○ J1, ● J2 |
| `test_case_with_fastqa` | ● J1, ● J2, ● J5, ○ J7 |
| `validate_scenarios` | ● J1 |
| `automate_test` | ● J1, ● J3 |
| `verify_and_fix` | ● J1, ● J3, ● J4, ○ J6 |
| `run_manual_test` | ● J2, ● J8 |
| `run_manual_api_test_swagger` | ● J5 |
| `exploratory_api_test` | ● J5 |
| `destructive_api_test` | ● J5 |
| `azdo_list_test_plans` | ● J3, ● J6 |
| `azdo_create_test_plan` | ● J7 |
| `azdo_run_pipeline` | ● J1, ● J3, ● J4, ● J6 |
| `azdo_generate_report` | ● J1, ● J2, ● J5, ● J6, ● J7 |

**Regras:** Match único ● → sugerir diretamente. Múltiplos ● → listar. Sem match → não sugerir.

---

## 📖 Referência Completa

Para detalhes completos de cada jornada (step tables, condições, artefatos), consultar: `JOURNEYS.md` na raiz do projeto.
