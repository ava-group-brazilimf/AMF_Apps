# Agent Specification: Headroom — Atribuição de Economia em Toda a Esteira

**Feature Branch**: `031-headroom-context-compression-proxy`
**Created**: 2026-07-30
**Status**: Implemented
**Change Type**: add-new (registro canônico + validador + atribuição por janela)
+ modify-existing (6 orquestradores MINOR · 5 agentes PATCH · ~40 agentes correção de drift)
**Input**: "Todos os agentes devem ser considerados para ser interceptados pelo headroom,
não somente os agentes do AGENT_ARTIFACT_SLICE. Verifique se os agentes não devem
conter instruções para invocar o headroom."

---

## 1. Identidade

Sem agente novo. Estende `specs/031` de 5 agentes F1 para **toda** a esteira.

| Componente | Papel |
|---|---|
| `src/shared/tools/agent_registry.py` | **Novo.** Fonte canônica dos 101 agentes: varre o disco, deriva a fase pela Constituição |
| `src/shared/utils/verify_agent_observability.py` | **Novo.** Gate E1–E6 contra o drift do auto-reporte |
| `headroom_tool.py attribute` | **Novo.** Credita a economia medida pelo proxy por janela de tempo |
| `pipeline_observer.cmd_track` | Hook que alimenta o `headroom-metrics.jsonl` — cobre 98 agentes |
| `.azure-pipelines/validate-agent-observability.yml` | **Novo.** CI gate |

## 2. Problem Statement

O pedido parte de uma premissa que a apuração desmentiu.

**A compressão já cobria 100% da esteira.** O proxy Headroom intercepta o processo do
Copilot CLI inteiro, em todas as fases — nenhum texto dentro de um `.md` liga ou desliga
isso. Os 5 agentes de `specs/031` não comprimiam *mais* que os outros; eles apenas
**atribuíam** a economia ao próprio `agent_id`.

O que faltava, então, não era interceptação:

**P-1 — O proxy é cego a quem chamou.** Ele mede `tokens_before`/`tokens_after` por
requisição, mas só enxerga o processo do CLI. Sem cruzar com o tempo de execução dos
agentes, a economia é um número global sem dono.

**P-2 — 96 dos 101 agentes não apareciam nas métricas.** Só os 5 instrumentados
gravavam linha. Nenhuma visão de F2–F8.

**P-3 — Os dados existentes estavam corrompidos.** A varredura encontrou **51
violações** de consistência, todas com efeito direto sobre a atribuição:

| Defeito | Escala | Efeito |
|---|---|---|
| `--agent` de outro agente (copiar-colar) | 3 de QA reportavam `ava-asis-db-analyzer` | economia creditada ao agente errado |
| `--phase` errado | 6 agentes (`coder-react`/`coder-vue` F3, `iac-aws` F7, 3 de QA F1) | economia creditada à fase errada |
| `--version` divergente do frontmatter | 31 agentes | relatórios com versão irreal |
| Sem `version:` no frontmatter | 7 agentes | — |
| Sem bloco `track` | 3 agentes | invisíveis à observabilidade |
| Dois catálogos manuais divergentes | 52 de 101 agentes ausentes; `ava-tobe-orchestrator` 2.1.0 × 2.3.0 | baseline de relatório errada |
| `PHASE_ORDER` sem F8 | os 3 agentes de summary emitem F8 | fase fora de ordenação |

A causa-raiz é única: **o bloco de observabilidade é mantido 100% à mão** em ~100
arquivos. Uma busca por `Registro de Observabilidade` fora dos `.md` retorna zero — não
existe gerador nem validação.

## 3. Decision

### 3.1 Os agentes NÃO ganham instrução de headroom (resposta à pergunta do pedido)

Replicar um segundo bloco manual em 105 arquivos duplicaria exatamente a superfície que
produziu as 51 violações. Além disso exigiria **cinco** estratégias de inserção — o
texto-âncora só é idêntico em 81 dos 105 arquivos (8 em blockquote, 8 em variantes de
parágrafo, 2 sem fallback, 7 sem seção) — e ~101 bumps de versão.

Como **98 agentes já chamam `pipeline_observer.py track`** com modelo, tokens e duração,
a instrumentação entra ali: **1 arquivo, cobertura imediata de F1–F8, nenhuma diretiva
`Bash:` nova que o LLM possa pular.**

A exceção são os **6 orquestradores de fase**, que recebem um bloco explícito — não para
comprimir, mas porque só eles têm a visão de fase necessária para consolidar.

### 3.2 Duas camadas de métrica, complementares por necessidade

| Camada | Quando | `source` | Sabe | Não sabe |
|---|---|---|---|---|
| Hook do `track` | a cada agente | `self-report` | agent_id, phase, tokens, duração | quanto foi comprimido |
| `attribute` | ao fim da fase | `proxy` | compressão **medida** | nada além do que passou pelo proxy |

O auto-reporte grava `original_tokens: null` — o agente **não** conhece o tamanho
pré-compressão, e inventar um número seria pior que admitir a lacuna. `stats` separa as
duas origens, permitindo comparar estimado × medido.

### 3.3 Atribuição por janela de tempo

`headroom_tool.py attribute` cruza o JSONL do proxy com o `pipeline-run-state.json`:

> ⚠️ **A janela não está pronta no estado.** `cmd_track` grava `start_time == end_time`,
> porque os agentes só informam `--duration-ms`. A janela é reconstruída como
> `[end_time − duration_ms, end_time]`.

> ⚠️ **Fusos diferentes.** O proxy grava em **UTC** (`…Z`), o observer em **BRZ**
> (`-03:00`). Tratar os dois como locais deslocaria tudo em 3 h e zeraria a atribuição.

Política de sobreposição — dispatch paralelo produz janelas concorrentes:

- 1 agente → atribuição integral, `attribution: "exclusive"`
- N agentes → fração `1/N`, `attribution: "ambiguous"`, `overlap_count: N`
- nenhum → bucket `__unattributed__` (orquestrador entre dispatches, ou agente sem `track`)

Um número honesto e rotulado vale mais que creditar tudo ao primeiro que casar.

### 3.4 Registro canônico substitui os dois catálogos manuais

`agent_registry.py` varre `**/agents/**/*.md`, lê o frontmatter e deriva a fase pelo
módulo, usando o mapa da **Constituição v1.4.0**:

```
F1 asis-diagnostic · F2 tobe-architecture · F3 prototype   · F4 tech-stack
F5 qa-agents       · F6 devops-agents     · F7 deliverables · F8 summary
```

O `module.yaml` da raiz carregava a numeração pré-1.4.0 nos comentários e foi alinhado.

`AGENT_CATALOG` dos dois consumidores passa a vir do registry, com a lista estática como
fallback fora da árvore do repo. Resultado: **56 → 100 entradas**, idênticas nos dois, sem
as 7 linhas sintéticas `ava-summary (F1..F7)`.

Não é cosmético: `cmd_track` já usava o catálogo como fallback de `phase`/`version` quando
o agente omite.

### 3.5 Correção do drift e gate permanente

As 51 violações foram corrigidas com o **frontmatter como fonte de verdade**, e
`verify_agent_observability.py` reprova E1–E6 no CI. Corrigir sem o gate só adiaria a
próxima divergência.

## 4. User Scenarios (Given-When-Then)

### Scenario 1 — Agente de qualquer fase entra nas métricas sem edição (CA01)

**Given** `ava-qa-exploratory` (F5), que **não** tem instrução de headroom no `.md`,
**When** ele executa seu `track` do Step 1, **Then** uma linha `source: "self-report"` é
acrescentada a `outputs/observability/headroom-metrics.jsonl` com `agent_id`, `phase`,
tokens e duração — sem nenhuma alteração no agente.

### Scenario 2 — Economia medida ganha dono (CA02)

**Given** um projeto onde `ava-asis-inventory` rodou sozinho entre t=0 e t=60,
**When** o orquestrador executa `attribute --phase F1`, **Then** as requisições do proxy
naquela janela são creditadas integralmente a ele com `attribution: "exclusive"` e os
`tokens_before/after` reais.

### Scenario 3 — Dispatch paralelo é dividido e rotulado (CA03)

**Given** `db-analyzer` e `events-pubsub` despachados em paralelo com janelas
sobrepostas, **When** `attribute` roda, **Then** cada requisição da sobreposição é
dividida em 1/2, e ambos recebem `attribution: "ambiguous"` com `max_overlap: 2` — a
soma continua igual ao total do proxy.

### Scenario 4 — Requisição órfã não é inventada (CA04)

**Given** uma requisição fora de qualquer janela de agente, **When** `attribute` roda,
**Then** ela vai para `__unattributed__` e aparece no resumo, em vez de ser atribuída ao
agente mais próximo.

### Scenario 5 — Fuso não desloca a atribuição (CA05)

**Given** o proxy gravando `2026-07-30T13:00:00Z` e o observer `2026-07-30T10:00:00-03:00`,
**When** as janelas são construídas, **Then** os dois resolvem para o **mesmo** epoch e a
requisição casa com a janela.

### Scenario 6 — Drift é barrado no CI (CA06)

**Given** um agente editado com `--phase` do módulo errado, **When**
`verify_agent_observability.py` roda, **Then** ele reporta `E2` com o valor esperado e
sai com código 1, reprovando o pipeline.

### Scenario 7 — Esteira roda sem a tool (CA07)

**Given** um clone sem `src/shared/tools/headroom/.venv`, **When** qualquer agente chama
`track`, **Then** o evento é registrado normalmente e a linha do headroom é apenas
omitida — o hook é silencioso por design.

### Scenario 8 — Catálogo sobrevive fora do repo (CA08)

**Given** `pipeline_observer.py` executado de um diretório sem a árvore de agentes,
**When** o módulo carrega, **Then** `AGENT_CATALOG` cai para a lista estática de 56
entradas em vez de ficar vazio.

## 5. Quality Gate Requirements

- [x] Nenhum agente ganhou dependência nova; o hook é import defensivo (Art. I, IX)
- [x] Version bump MINOR nos 6 orquestradores e PATCH nos 5 com Step 1.1 alterado (Art. X)
- [x] Consistência tripla em **101** agentes — `verify_agent_observability.py` = 0 violações
- [x] Docstrings, blocos de agente e mensagens em pt-BR (Art. V)
- [x] Fase derivada da Constituição, nunca do `module.yaml` obsoleto (Art. I)
- [x] Métricas em `outputs/observability/`, timestamps BRZ (Art. VIII)
- [x] 8 cenários BDD; 33 testes novos (15 registry + 18 atribuição)
- [x] CI gate criado e apontando para os 4 checks
- [x] Nenhum marcador `[NEEDS CLARIFICATION]` remanescente

## 6. Dependencies

- `.specify/memory/constitution.md` § Project Reference — **autoridade** do mapa de fases.
  Criar módulo novo exige acrescentá-lo a `PHASE_BY_MODULE`; o teste
  `test_nenhuma_fase_indefinida` reprova se esquecerem.
- `pipeline_observer.py` — o hook depende de `cmd_track` continuar sendo o ponto único de
  auto-reporte.
- `headroom_config.py` (specs/031) — resolve o caminho do JSONL e do log do proxy.
- Log do proxy: exige `HEADROOM_LOG_FILE` ativo, já default em `headroom.yaml`.

## 7. Exclusions

- **Gerador do bloco de observabilidade** — o validador detecta o drift; derivar o bloco
  do frontmatter é o passo seguinte natural, não feito aqui.
- **Os 4 `db-analyzer/skills/*.md`** — sub-skills lidas por um agente pai, sem identidade
  de execução. Excluídas do registry por `_is_dispatchable`.
- **Os 76 `.github/skills/*/SKILL.md`** — são ponteiros para o `.md` do agente; com o hook
  em `track` a cobertura independe deles.
- **Remoção do `agents/security-review-asis.md` (`1.4.0-DEPRECATED`)** — declara o mesmo
  `name` do arquivo vivo em `agents/security/`. `duplicates()` ignora depreciados; apagar
  o arquivo é limpeza separada.
- **Reconciliar `--version` "para baixo"** — em `adr-tobe` o bloco reportava `2.2.0` e o
  frontmatter `1.2.0`. Aplicamos a regra (frontmatter vence) uniformemente; se o
  frontmatter é que estava desatualizado, corrigi-lo é uma mudança de conteúdo do agente.
- **O 404 `Model not found` do Copilot CLI** — investigação separada, Anexo A de
  `src/shared/tools/headroom/docs/02-esteira-github-cli.md`.

## 8. Assumptions

- O JSONL do proxy tem `timestamp`, `tokens_before`, `tokens_after` e `latency_ms`. O
  leitor aceita aliases e descarta linhas inutilizáveis — o esquema do headroom **não** é
  contratual e pode mudar num `git subtree pull`.
- `duration_ms` reportado pelo agente aproxima bem a janela real. Se o agente subestimar,
  requisições caem em `__unattributed__` em vez de serem mal atribuídas — a falha é para
  o lado seguro.
- Fração `1/N` é a divisão mais defensável sem rastrear `request_id` por agente, o que
  exigiria o host propagar um header que o Copilot CLI não permite customizar.
- Frontmatter é a fonte de verdade da versão (Artigo II).

## Success Criteria

| Criterion | Measure |
|---|---|
| Cobertura da esteira | 98 dos 101 agentes gravam métrica sem nenhuma edição de `.md`; os 3 restantes ganharam bloco `track` |
| Consistência | `verify_agent_observability.py` → **51 → 0** violações |
| Catálogo único | Ambos os `AGENT_CATALOG` = 100 entradas idênticas, derivadas do disco (antes 56, divergentes) |
| Atribuição correta | Exclusivo integral · sobreposto 1/N rotulado · órfão isolado · conservação de tokens verificada |
| Fuso | `10:00Z` e `07:00-03:00` resolvem para o mesmo epoch |
| Degradação | `track` funciona sem a tool; catálogo cai para o fallback fora do repo |
| Testes | `pytest tests/ -q` → **83 passed** (era 50) |
| Gate permanente | `.azure-pipelines/validate-agent-observability.yml` com CHK-01..04 |
