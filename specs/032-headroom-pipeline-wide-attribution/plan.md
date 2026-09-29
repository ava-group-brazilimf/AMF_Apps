# Agent Implementation Plan: Headroom — Atribuição em Toda a Esteira

**Spec**: [spec.md](./spec.md) · **Tasks**: [tasks.md](./tasks.md) · **Quickstart**: [quickstart.md](./quickstart.md)

## Summary

Estende a instrumentação Headroom de 5 agentes F1 para os 101 agentes da esteira —
**sem** adicionar instrução a nenhum `.md` comum. A cobertura vem de plugar no
`pipeline_observer.cmd_track`, que 98 agentes já chamam; os 6 orquestradores de fase
ganham um bloco explícito para consolidar os números medidos pelo proxy.

No caminho, elimina a causa-raiz dos dados errados: dois catálogos manuais divergentes
e 51 violações de consistência que creditavam economia ao agente ou à fase errada.

## Constitution Check

### Constitution Gates

| Artigo | Gate | Status |
|---|---|---|
| **I — Configuration-Driven** | Fase e versão não hardcoded | ✅ Fase derivada da Constituição via `PHASE_BY_MODULE`; versão do frontmatter. Os catálogos deixaram de ser literais. |
| **II — Agent Contract** | Frontmatter só com os 4 campos | ✅ Só `version` mudou. 7 agentes ganharam o `version:` que faltava. |
| **III — Pipeline Execution** | Contrato de dispatch intacto | ✅ Hook é interno ao `track`; DAG e `AgentResult` inalterados. |
| **IV — Module Registration** | — | ✅ N/A (sem agente novo). `module.yaml` corrigido para a numeração v1.4.0. |
| **V — Language Convention** | pt-BR | ✅ Módulos, blocos e mensagens. |
| **VI — Test-First** | BDD antes do código | ✅ 8 cenários (CA01–CA08); 33 testes novos. |
| **VII — Security-First** | Sem segredo novo | ✅ Nenhuma credencial tocada; só leitura de JSONL local. |
| **VIII — Observability** | Rastreabilidade | ✅ `run_id` propagado; `source` distingue estimado de medido; órfãos explícitos. |
| **IX — Clean Architecture** | Dependências para dentro | ✅ `agent_registry` não conhece o headroom; `headroom_tool` não conhece o observer (lê o JSON de estado). |
| **X — Versioning** | Bump correto | ✅ MINOR nos 6 orquestradores, PATCH nos 5 com Step 1.1 alterado. |
| **XI — Skill/Agent Separation** | — | ✅ N/A. |

### Quality Gate Check

- [x] `pytest tests/ -q` → 83 passed, 6 skipped
- [x] `verify_agent_observability.py` → 0 violações em 101 agentes
- [x] Ambos os `AGENT_CATALOG` = 100 entradas idênticas
- [x] `attribute` conserva tokens (atribuído + órfão == total do proxy)
- [x] `track` funciona com o venv da tool ausente

## 1. Technical Context

| Item | Valor |
|---|---|
| Linguagem | Python 3.10+ (stdlib; nenhuma dependência nova fora do venv da tool) |
| Agentes | 105 arquivos · 101 despacháveis · 4 sub-skills |
| Cobertura antes | 5 agentes (F1) · depois: 98 via hook + 3 que ganharam `track` |
| Fusos | proxy **UTC** · observer **BRZ (-03:00)** |
| Autoridade de fase | `.specify/memory/constitution.md` v1.4.0 |

## 2. Phase Placement

Transversal (F1–F8). O hook é agnóstico de fase; `attribute --phase` recorta quando o
orquestrador de fase consolida, e o master-orchestrator roda sem filtro no fim.

## 3. Clean Architecture Alignment

```
┌─ interface ───────────────────────────────────────────────────┐
│ headroom_tool.py (attribute/stats) · verify_agent_observability │
│ .azure-pipelines/validate-agent-observability.yml              │
└───────────────────────┬───────────────────────────────────────┘
┌─ domínio ─────────────▼───────────────────────────────────────┐
│ agent_registry.py — identidade e fase canônicas               │
│ attribute_requests() — política de sobreposição               │
└───────────────────────┬───────────────────────────────────────┘
┌─ persistência ────────▼───────────────────────────────────────┐
│ pipeline-run-state.json · headroom-metrics.jsonl · proxy JSONL │
└───────────────────────────────────────────────────────────────┘
```

`attribute_requests()` é função pura sobre listas — daí ser testável sem I/O.

## 4. Agent File Structure

**Agentes comuns (95): nenhuma alteração de conteúdo.** Só correção de literais errados.

**Orquestradores (6)** ganham:

```markdown
### Consolidação da Economia Headroom (OBRIGATÓRIO)
Bash: python src/shared/tools/headroom/headroom_tool.py -p {project_name} attribute --phase FN
```

**Agentes com Step 1.1 (5)**: o `metrics` sai (duplicaria a contagem com o hook), fica a
consulta de `slice`.

## 5. module.yaml Impact

Comentários de fase da raiz alinhados à Constituição (`tech-stack` F3→F4, `prototype`
F4→F3, `devops` F7→F6, `deliverables` F6→F7) e contagens atualizadas a partir do registry.
Nenhum `module.yaml` de módulo declara fase, então não há outro ponto a tocar.

## 6. Observability & Trace Propagation

`run_id` viaja do estado para as duas origens de métrica. `source` (`self-report` ·
`proxy` · `manual`) permite reconciliar estimativa e medição. `__unattributed__` mantém a
soma auditável: **atribuído + órfão == total do proxy**.

Gap herdado e não fechado: trace_id W3C (specs/002, 006).

## 7. Schema Changes

Nenhum schema em `src/shared/schemas/`. O JSONL de métricas ganhou `source`,
`attribution`, `ambiguous_requests`, `max_overlap` e `requests`; linhas antigas
(sem `source`) são lidas como `manual`, então não há migração.

## 8. Implementation Phases

| # | Fase | Bloqueia |
|---|---|---|
| 1 | `agent_registry.py` | tudo |
| 2 | `verify_agent_observability.py` — produz a lista autoritativa de drift | 3 |
| 3 | Correção do drift (51 → 0) | 4 |
| 4 | Catálogos via registry + F8 | — |
| 5 | Hook no `cmd_track` | — |
| 6 | `attribute` + `stats` por origem | 7 |
| 7 | Blocos nos 6 orquestradores; trim dos 5 | — |
| 8 | Testes, CI gate, documentação | — |

A ordem 2→3 importa: o validador foi escrito **antes** da correção, para que a lista de
alvos viesse de uma varredura reproduzível e não de leitura manual.

## 9. Complexity Tracking

| Complexidade | Justificativa | Alternativa descartada |
|---|---|---|
| Janela reconstruída de `duration_ms` | `cmd_track` grava `start == end`; mudar isso exigiria reeditar os 98 blocos | Passar `--start-time` em todos |
| Fração `1/N` no paralelo | Sem `request_id` por agente, é a divisão defensável | Atribuir ao primeiro que casar (erro silencioso) |
| Registry varre o disco a cada import | ~105 arquivos, cache em memória, fallback estático | Manter as duas listas manuais |
| Leitor tolerante a aliases | O esquema do JSONL do proxy não é contratual | Casar campos exatos e quebrar no próximo `subtree pull` |

## 10. Test Strategy

**`tests/tools/test_agent_registry.py` (15)** — varredura, sub-skills fora do catálogo,
mapa da Constituição, frontmatter com/sem aspas, catálogo sem sintéticos e ordenado,
fallback, duplicatas, ambos os consumidores derivando do registry, F8, gate zerado,
os 6 orquestradores com `attribute`, nenhum agente com `metrics` manual.

**`tests/tools/test_headroom_attribution.py` (18)** — equivalência UTC×BRZ, naive por
contexto, lixo tolerado, exclusivo/paralelo 1/2 e 1/3, órfão, **conservação de tokens**,
bordas inclusivas, leitura e descarte no JSONL, janela por duração × explícita, estado
ausente, e um ponta-a-ponta com log UTC + estado BRZ.

**Regressão** — `tests/utils/` (28) e `tests/tools/test_headroom_context.py` (22) intactos.

**CI** — `.azure-pipelines/validate-agent-observability.yml`, CHK-01..04, disparado por
qualquer alteração em `**/agents/**` ou nas ferramentas de observabilidade.
