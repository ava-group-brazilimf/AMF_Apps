# Plan — Spec 035: QA Orchestrator em dois momentos

## Constitution Check

- **Altera o contrato de triggers e a semântica do `QS`** (caller-visible: o `QS` passa a ter um
  gate que pode bloquear) → **MAJOR bump 1.3.0 → 2.0.0** (Article X,
  `.specify/memory/constitution.md:177`).
- **`## Output Contract` não muda** — os 12 artefatos declarados permanecem idênticos. Nenhum
  parser downstream (`build_summary_comprehensive.py`, `artifact-map.yaml`) é afetado.
- **`module.yaml` não muda** — nenhum agente é adicionado ou removido; o arquivo lista apenas
  `id` + `file` por agente, sem triggers. Category 4 = N/A.
- **`SKILL.md` não muda** — `.github/skills/ava-qa-orchestrator/SKILL.md` é genérico e apenas
  aponta para o arquivo do agente. Category 1.5 = N/A.
- **MAJOR bump → entrada em `CHANGELOG.md` obrigatória** (Article X).
- **Corpo do agente em português brasileiro** (Article V) — mantido; esta spec é o documento de
  planejamento.
- **Nenhuma versão de tecnologia hardcoded** (Article I) — os paths verificados no gate são
  artefatos de projeto, não versões de stack.

## Technical Context

O `ava-qa-orchestrator` reside em
`src/modules/ava-fabric-agents/qa-agents/agents/qa-orchestrator-agent.md` (v1.3.0, 754 linhas) e
é despachado pelo `ava-master-orchestrator` na Fase F5 com trigger `QS`.

A esteira principal executa `F1 AS-IS → F2 TO-BE → F2.5 DevOps DP → F3 Prototype → F4 Stack →
F5 QA → F6 DevOps DE → F7 Deliverables`. O trigger `TPT` do QA já é, na prática, um ponto de
transferência acionado a partir do `ava-tobe-orchestrator` (Fase 6 do F2) e interrompe o fluxo do
orquestrador QA logo após o dispatch.

Os artefatos que o `QE` passa a exigir e seus produtores reais:

| Artefato | Produtor | Referência |
|---|---|---|
| `outputs/tobe/docs/bounded-context-map.md` | `ava-tobe-architecture-design` (trigger `BC`) | F2 |
| `outputs/tobe/qa/test-plan.md`, `test-cases.md` | `ava-test-plan-tobe` (trigger `TP`, via `TPT`) | spec 029 |
| `outputs/tobe/source-code/README.md` | `ava-stack-orchestrator` (trigger `SG`) | `master-orchestrator.md:600` |
| `outputs/tobe/infra/` | `ava-devops-iac` | `iac-agent.md:271-274` |
| `outputs/tobe/iac/ci/`, `iac/cd/azure-pipelines-cd.yml` | `ava-devops-ci`, `ava-devops-cd` | `cd-agent.md:47,59-61` |
| `outputs/tobe/parity-test-report.md` | `ava-devops-compare-version` | `compare-version-agent.md:216` |

O corpo do `## Routing — Trigger QS` atual (linhas 331-427) já é maduro e contém blocos que não
devem ser reescritos: instruções literais de dispatch para `ava-qa-exploratory` e
`ava-qa-bridge-fastqa-tobe`, o ET VERIFICATION GATE (9b), o FQ COMPLETION GATE (9c), a execução
do `qa_test_runner.py` (11b) e a geração do `qa-master-report.md` (12). O refactor **move** esse
corpo para `## Routing — Trigger QE` preservando-o, em vez de reescrevê-lo.

## Implementation Phases

### Phase 1 — Spec Artifacts
- Criar `spec.md`, `plan.md`, `tasks.md`, `checklists/requirements.md`.

### Phase 2 — Frontmatter, cabeçalho e menu
- Bump `version: 1.3.0 → 2.0.0` e `date`; ampliar `description` com os gatilhos de ativação do
  Momento 2.
- Ajustar a linha `Step` do cabeçalho para refletir os dois momentos.
- `## Agent Team QA`: acrescentar coluna **Momento** (1 — Planejamento / 2 — Execução).
- `## Triggers / Menu`: adicionar `QE`; marcar `TPT` como Momento 1; marcar `QS` como deprecado;
  adicionar `PT` e `RS`; atualizar a nota do invariante PT→RS.

### Phase 3 — Pre-condition Gate (QE)
- Inserir `## Pre-condition Gate (QE)` após o gate `(QS)`, com 4 passos bloqueantes + Passo 4b
  (WARN) e o bloco `### Resultado PASS`.
- Inserir `### Mensagem de Bloqueio QE`, incluindo a emissão do sinal `QE DEFERRED`.

### Phase 4 — Routings
- Criar `## Routing — Trigger QE` movendo o corpo do Routing `QS` e inserindo o passo `FTM` após
  o `BM`.
- Reduzir `## Routing — Trigger QS` a um stub de depreciação que delega ao `QE`.
- Criar `## Routing — Trigger PT` (verificação de disponibilidade, não dispatch).
- Criar `## Routing — Trigger RS` (dispatch de `ava-qa-script-generator` em `mode: regression`).

### Phase 5 — Seções terminais e tabelas
- `## Terminal Mandatory Steps (PT → RS)`: atualizar a lista do invariante para incluir `QE` e
  `FQ`; exceções `TPT`, `FTM`, `PT`, `RS`.
- `### Resumo de cobertura por trigger`: adicionar `QE`; marcar `QS` como deprecado.
- Bloco de observabilidade: `--version 1.3.0 → 2.0.0` (manter `--phase F5`).

### Phase 6 — CHANGELOG
- Entrada MAJOR no topo do `CHANGELOG.md`, no formato da entrada 034.

### Phase 7 — Verify
- Grep de consistência interna (referências `§Routing`, cobertura de triggers, versão).
- Conferência dos paths do gate contra os agentes produtores.
- Revisão manual de coerência.

## Complexity

Média. Concentra-se em um único arquivo de agente, mas envolve um refactor estrutural (mover o
corpo do Routing `QS` sem perder blocos maduros) e a criação de quatro seções novas, duas delas
resolvendo referências pendentes preexistentes.
