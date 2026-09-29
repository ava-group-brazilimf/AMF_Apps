# Agent Specification: Remoção de Geração de Arquivos .drawio nos Agentes TO-BE

**Feature Branch**: `014-remover-geracao-drawio-tobe`
**Created**: 2026-07-09
**Status**: Implemented
**Change Type**: modify-existing (4 agentes TO-BE + orquestrador + 4 checklists de gate, MINOR — remoção de saída do Output Contract, nenhum campo de entrada afetado)
**Input**: "Remover a Geração de Arquivos .drawio nos Agentes: security-design-tobe.md, architecture-design-tobe.md, migration-plan-tobe.md, coexistence-strategy-tobe.md. Objetivo: Não fazer a geração de arquivos .drawio que não estão sendo usados."

---

## 1. Agent Identity

| Field | File | Version |
|---|---|---|
| `ava-tobe-security-design` | `tobe-architecture/agents/security-design-tobe.md` | *(sem version/date no frontmatter)* → `1.1.0` (MINOR — campo `version`/`date` adicionado per Guardrail #3; `security_diagram_drawio` removido do Output Contract) |
| `ava-tobe-architecture-design` | `tobe-architecture/agents/architecture-design-tobe.md` | `1.0.0` → `1.1.0` (MINOR — 9 chaves `*_drawio` removidas do Output Contract; 3 seções drawio-only removidas) |
| `ava-tobe-migration-plan` | `tobe-architecture/agents/migration-plan-tobe.md` | `1.2.1` → `1.3.0` (MINOR — `gantt_chart_drawio` removido; Output Contract 14→13 arquivos; Step 6.5.5 removido) |
| `ava-tobe-coexistence-strategy` | `tobe-architecture/agents/coexistence-strategy-tobe.md` | `1.0.0` → `1.1.0` (MINOR — `coexistence_drawio` removido; Output Contract 4→3 artefatos) |
| `ava-tobe-orchestrator` | `tobe-architecture/agents/orchestrator-tobe.md` | `2.3.0` → `2.4.0` (MINOR — gates das Fases 1, 1.6, 4, 4.3 e 4.5 atualizados para não mais exigir os `.drawio` removidos) |

**Phase**: F2 (TO-BE Architecture) — cross-cutting dentro da fase, afeta 4 agentes + o orquestrador + 4 arquivos de checklist/gate.
**Module**: `tobe-architecture` (primário — 4 agentes + orquestrador + 2 checklists internos), `shared` (checklist compartilhado `migration-design-checklist.md`), mais um step de workflow (`workflows/design-dotnet/steps/step-01c-security-design.md`).

## 2. Problem Statement

Quatro agentes TO-BE geram, para cada diagrama Mermaid (`.mmd`), um arquivo `.drawio` nativo
equivalente ("dual-output", regido por `shared/drawio-governance.md`): `context-map.drawio` e os
5 `.drawio` do trigger `TD` (`architecture-design-tobe.md`), `security-architecture.drawio`
(`security-design-tobe.md`), `migration-gantt.drawio` (`migration-plan-tobe.md`) e
`coexistence-architecture.drawio` (`coexistence-strategy-tobe.md`).

Investigação (não inferência — leitura direta do pipeline de Summary) confirmou que **nenhum
consumidor real usa esses `.drawio` do TO-BE**:

1. O builder do Summary (`build_summary_comprehensive.py`) renderiza diagramas exclusivamente a
   partir dos `.mmd` — seu único carregador de `.drawio` (`load_drawio_files()`) lê apenas 4
   arquivos AS-IS sintéticos de `outputs/asis/drawio/`, produzidos por
   `generate_drawio_from_mermaid.py` a partir dos próprios `.mmd`, não pelos 4 agentes TO-BE
   listados acima.
2. `summary/data/artifact-map.yaml` não contém nenhuma referência a `.drawio`.
3. `step-03-build-html.md` confirma explicitamente: "`{{CONTEXT_MAP_DIAGRAM}}` vem de
   `tobe/diagrams/context-map.mmd` — NÃO do arquivo `.drawio`."
4. O único script que referencia os `.drawio` do TO-BE (`validate_drawio_integration.py`) é
   órfão — não é invocado por nenhum workflow, step ou orquestrador do pipeline.

Gerar esses arquivos custa tempo de execução (protocolo de sanitização Draw.io, gate
`validate_diagram.py`, templates XML extensos — até 137 linhas de templates canônicos só em
`architecture-design-tobe.md`) sem entregar valor observável ao usuário final.

Um efeito colateral crítico da remoção, descoberto durante a investigação: `orchestrator-tobe.md`
possui um **HARD STOP** literal na Fase 4.5 que falha se `migration-gantt.drawio` ou
`coexistence-architecture.drawio` estiverem ausentes (itens 11/14 e 4/4 de duas tabelas de gate
bloqueante), e os próprios self-validation gates de `migration-plan-tobe.md` e
`coexistence-strategy-tobe.md` (`migration-validation-gate.md`, `coexistence-validation-gate.md`)
travariam esses agentes em loop de regeneração de um artefato que nunca mais seria produzido. Sem
corrigir esses gates, a remoção quebraria permanentemente a esteira TO-BE.

## 3. Decision

### 3.1 Remover toda instrução de geração `.drawio` dos 4 agentes, preservando 100% da geração `.mmd`

Em cada um dos 4 arquivos, removidos: blocos `PRE-WRITE VALIDATION GATE` (mantendo apenas a
ramificação `.mmd`), bullets "gerar simultaneamente o `.drawio`", linhas de sanitização Draw.io,
chaves `*_drawio` do Output Contract (YAML e tabelas), itens de checklist `- [ ] ....drawio criado`,
e referências a `shared/drawio-governance.md`. Nenhuma instrução de geração de `.mmd`/Mermaid foi
tocada.

### 3.2 Remover 5 blocos de conteúdo exclusivamente drawio, auto-contidos, em `architecture-design-tobe.md` e `migration-plan-tobe.md`

- `architecture-design-tobe.md`: `### Pre-Output Checklist Draw.io`, `## Canonical Draw.io XML
  Templates` (mapeamento de shapes + 4 templates XML + placeholder), `### Template canônico —
  Value Chain Draw.io` — mantendo os templates Mermaid/Value Chain Mapping irmãos intactos.
- `migration-plan-tobe.md`: `#### 6.5.5 — Gerar migration-gantt.drawio` inteira (7 sub-passos) —
  mantendo `#### 6.5.4 — Gerar migration-gantt.mmd` intacta; `6.5.6` renumerada para `6.5.5`.

### 3.3 Corrigir os gates downstream que exigiam os `.drawio` removidos (não opcional)

Sem esta correção o pipeline TO-BE trava permanentemente (ver §2). Atualizados:

- `orchestrator-tobe.md`: tabelas de output e checklists das Fases 1, 1.6, 4 e 4.3; e — o ponto
  crítico — a tabela de gate bloqueante da Fase 4.5 (14→13 arquivos do migration-plan, 4→3 da
  coexistence-strategy, total 18→16).
- `migration-validation-gate.md` (self-gate de `migration-plan-tobe.md`): removidos os checks
  3.12/3.13/3.16 (comparação `.mmd`×`.drawio` e detecção de stub), a linha 11/14 do Output
  Contract, e a referência ao `.drawio` na Etapa 7.1 (Wave Model Cross-Validation). Total
  14→13 arquivos em todo o documento (Etapa 4, Relatório de Completude, Output Invariant).
- `coexistence-validation-gate.md` (self-gate de `coexistence-strategy-tobe.md`): removido o
  check 3.2 (`.drawio` é XML válido) e a linha 4/4 do Output Contract. Total 4→3 artefatos.
- `shared/checklists/migration-design-checklist.md`: removidas as linhas `B5` (Context Map
  Draw.io) e `D3` (Security Diagram Draw.io) das Seções B e D. A fórmula de score
  (`Σ pass×peso / Σ total×peso`) é dinâmica — a remoção das linhas ajusta o denominador
  automaticamente, sem exigir recálculo manual em nenhuma outra parte do documento.
- `workflows/design-dotnet/steps/step-01c-security-design.md`: removida a linha de
  `security-architecture.drawio` da tabela de Output Files e o critério `AC-3`; "3 arquivos" →
  "2 arquivos" no Critério de Conclusão.

### 3.4 Remover conteúdo órfão

`tobe-architecture/templates/migration-gantt-drawio.md` (template XML consumido apenas pela seção
6.5.5 removida) foi apagado — confirmado via grep que nenhum outro arquivo do repositório o
referenciava antes da remoção.

### 3.5 O que NÃO foi tocado

`shared/drawio-governance.md` permanece intacto — ainda é consumido pelos agentes AS-IS
`solution-vb.md`, `solution-cobol.md`, `solution-vbnet.md` e `solution-powerbuilder.md`, que
continuam produzindo `.drawio` legado (fora do escopo desta mudança). Nenhuma instrução de geração
`.mmd`/Mermaid foi alterada em nenhum dos 4 agentes.

## 4. Functional Changes by Component

| Component | Change |
|---|---|
| `tobe-architecture/agents/security-design-tobe.md` | Gate `.drawio` removido do bloco PRE-WRITE; linha de sanitização Draw.io removida; `security_diagram_drawio` removido do Output Contract; checklist item removido; `version`/`date` adicionados (1.1.0/2026-07-09) |
| `tobe-architecture/agents/architecture-design-tobe.md` | Gate `.drawio` removido do bloco PRE-WRITE; 9 chaves `*_drawio` removidas do Output Contract; 3 seções drawio-only removidas (~150 linhas); tabela AS-IS Parity Check e bullets "Diagrams Creation Mandate" simplificados para `.mmd`-only; 2 guardrails reescritos |
| `tobe-architecture/agents/migration-plan-tobe.md` | Gate `.drawio` removido do bloco PRE-WRITE; subsection `#### 6.5.5` removida inteira; `gantt_chart_drawio` removido do Output Contract; Output Contract 14→13 arquivos em 5 pontos do documento (tabela de triggers, YAML, nota, G-6, G-10, G-21, Validation Gate) |
| `tobe-architecture/agents/coexistence-strategy-tobe.md` | Gate `.drawio` removido do bloco PRE-WRITE; Step 8 item 4 (geração drawio) removido; `coexistence_drawio` removido do Output Contract; Output Contract 4→3 artefatos |
| `tobe-architecture/agents/orchestrator-tobe.md` | Fases 1/1.6/4/4.3: linhas de output e checklist `.drawio` removidas; **Fase 4.5 (gate bloqueante)**: tabelas 14→13 e 4→3 arquivos, contagem total 18→16 |
| `tobe-architecture/checklists/migration-validation-gate.md` | Checks 3.12/3.13/3.16 removidos; Etapa 4 e Relatório de Completude 14→13 arquivos; Etapa 7.1 sem referência a `.drawio` |
| `tobe-architecture/checklists/coexistence-validation-gate.md` | Check 3.2 removido; Etapa 4 e Relatório de Completude 4→3 arquivos |
| `shared/checklists/migration-design-checklist.md` | Linhas `B5`/`D3` removidas; Seção B 5→4 artefatos, Seção D 3→2 artefatos |
| `tobe-architecture/workflows/design-dotnet/steps/step-01c-security-design.md` | Linha de output e `AC-3` removidos; "3 arquivos" → "2 arquivos" |
| `tobe-architecture/templates/migration-gantt-drawio.md` | **Apagado** (órfão — só era referenciado pela seção 6.5.5 removida) |

## 5. User Scenarios (Given-When-Then)

### Scenario 1 — Agentes TO-BE não geram mais `.drawio` (Priority: P1)

**Story**: Como orquestrador TO-BE, quero que os 4 agentes gerem apenas `.mmd` para que o tempo de
execução não seja gasto em artefatos `.drawio` que nenhum consumidor downstream utiliza.

**Why this priority**: objetivo central do PBI.

**Acceptance Scenarios**:

1. **Given** um projeto TO-BE válido, **When** `architecture-design-tobe.md` executa os triggers
   `CB`/`BC`/`TD`, **Then** produz `architecture-blueprint.mmd`, `context-map.mmd` e os 5 `.mmd`
   de `TD` — nenhum arquivo `.drawio` é criado em `outputs/tobe/diagrams/`.
2. **Given** o mesmo projeto, **When** `security-design-tobe.md`, `migration-plan-tobe.md` e
   `coexistence-strategy-tobe.md` executam, **Then** cada um produz apenas seu `.mmd`
   correspondente (`security-architecture.mmd`, `migration-gantt.mmd`,
   `coexistence-architecture.mmd`) — nenhum `.drawio` é criado.

### Scenario 2 — Gates downstream não bloqueiam mais o pipeline (Priority: P1)

**Why this priority**: sem este comportamento a mudança quebra a esteira TO-BE inteira — é o
requisito que torna a Scenario 1 segura de aplicar.

**Acceptance Scenarios**:

1. **Given** os 13 arquivos do Output Contract de `migration-plan-tobe.md` presentes em disco
   (sem `migration-gantt.drawio`), **When** `orchestrator-tobe.md` avalia o gate de entrada da
   Fase 4.5, **Then** o gate passa (`13/13 OK`) sem exigir `migration-gantt.drawio`.
2. **Given** os 3 arquivos do Output Contract de `coexistence-strategy-tobe.md` presentes em disco
   (sem `coexistence-architecture.drawio`), **When** o gate adicional da Fase 4.5 é avaliado,
   **Then** o gate passa (`3/3 OK`).
3. **Given** `migration-plan-tobe.md` concluiu sua execução, **When** sua própria
   `migration-validation-gate.md` é executada (Step 8), **Then** o Relatório de Completude reporta
   `13/13` sem tentar validar um `migration-gantt.drawio` inexistente.

### Scenario 3 — Diagramas Mermaid permanecem 100% funcionais (Priority: P1)

**Why this priority**: garante que a remoção não teve efeito colateral sobre o que É consumido
(Summary HTML).

**Acceptance Scenarios**:

1. **Given** os `.mmd` gerados pelos 4 agentes, **When** o Summary é construído
   (`build_summary_comprehensive.py`), **Then** todos os diagramas renderizam normalmente a
   partir dos `.mmd` — comportamento idêntico ao anterior, já que o Summary nunca consumiu os
   `.drawio` do TO-BE.

### Scenario 4 — Agentes AS-IS que ainda usam Draw.io permanecem intocados (Priority: P2)

**Why this priority**: garante escopo mínimo — a mudança não deveria afetar `solution-vb.md` e
irmãos, que estão fora do pedido do usuário.

**Acceptance Scenarios**:

1. **Given** `shared/drawio-governance.md`, **When** inspecionado após esta mudança, **Then**
   permanece idêntico ao original, e `solution-vb.md`/`solution-cobol.md`/`solution-vbnet.md`/
   `solution-powerbuilder.md` continuam referenciando-o normalmente.

## 6. Quality Gate Requirements

- [x] Agent IDs inalterados; frontmatter alterado apenas em `version`/`date` (Article II)
- [x] Version bumps: MINOR em todos os 5 agentes/orquestrador tocados — remoção de saída do
      Output Contract é mudança de contrato, não PATCH (Article X)
- [x] BDD scenarios cobrem a remoção em si (CA01), a integridade dos gates downstream (CA02), a
      não-regressão do Summary (CA03) e o isolamento do escopo AS-IS (CA04) (Article VI)
- [x] Nenhuma versão de tecnologia hardcoded (Article I)
- [x] Nenhum marcador `[NEEDS CLARIFICATION]` — escopo confirmado com o usuário via
      `AskUserQuestion` antes da implementação (incluir correção de gates: sim; remover conteúdo
      órfão: sim)

## 7. Dependencies

- `docs/asis-diagnostic-io-map.md`, `docs/tobe-architecture-io-map.md`,
  `docs/tech-stack-io-map.md` — mapas de I/O produzidos em sessão anterior que documentaram os
  Output Contracts originais (incluindo os 9 arquivos `.drawio`) usados como baseline desta
  remoção.
- `shared/drawio-governance.md` — permanece como dependência ativa dos 4 agentes AS-IS de solução
  legada não-Delphi; não foi modificado.
- `summary/utils/build_summary_comprehensive.py`, `summary/data/artifact-map.yaml`,
  `summary/workflows/generate-summary/steps/step-03-build-html.md` — inspecionados para confirmar
  que nenhum deles consome os `.drawio` removidos.

## 8. Exclusions

- Não alterou a geração `.mmd`/Mermaid de nenhum dos 4 agentes.
- Não removeu `shared/drawio-governance.md` nem qualquer referência a ele nos agentes AS-IS de
  solução legada (`solution-vb.md`, `solution-cobol.md`, `solution-vbnet.md`,
  `solution-powerbuilder.md`) — fora do escopo pedido pelo usuário.
- Não investigou nem corrigiu `summary/utils/validate_drawio_integration.py` (script órfão,
  não invocado por nenhum workflow) — identificado como pré-existente e não relacionado.
- Não tentou reconciliar a fórmula de peso/score de `migration-design-checklist.md` além de
  remover as duas linhas — a fórmula já era dinâmica e não precisou de ajuste adicional.

## 9. Assumptions

- A conclusão de que "nenhum consumidor real usa os `.drawio` do TO-BE" se baseia em inspeção
  direta do pipeline de Summary (o único consumidor plausível de diagramas neste repositório) — não
  foi feita uma varredura de sistemas externos ao repositório que porventura leiam esses arquivos
  diretamente do `outputs/tobe/diagrams/`.
- `templates/migration-gantt-drawio.md` foi considerado seguro para exclusão definitiva (não
  arquivamento) por não haver nenhuma referência restante no repositório após a remoção da seção
  6.5.5 — confirmado via grep antes da exclusão.

## Success Criteria

| Criterion | Measure |
|---|---|
| Nenhuma instrução de geração `.drawio` restante nos 4 agentes | `grep -ri drawio` nos 4 arquivos → 0 matches |
| Gates downstream consistentes | `grep -c "14 arquivos\|18 arquivos"` em `orchestrator-tobe.md`/`migration-validation-gate.md` → 0; contagens `13`/`3`/`16` presentes nos pontos corretos |
| Nenhuma regressão na geração `.mmd` | Diff de cada um dos 4 agentes mostra apenas remoções de linhas `.drawio` — nenhuma linha de instrução Mermaid alterada |
| Órfãos removidos | `migration-gantt-drawio.md` ausente do repositório; `grep -r migration-gantt-drawio` → 0 matches |
| Escopo AS-IS preservado | `shared/drawio-governance.md` sem diff; `solution-{vb,cobol,vbnet,powerbuilder}.md` sem diff |
