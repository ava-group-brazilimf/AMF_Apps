# Agent Implementation Plan: Remoção de Geração de Arquivos .drawio nos Agentes TO-BE

**Spec**: `specs/014-remover-geracao-drawio-tobe/spec.md`

## Summary

| Field | Value |
|---|---|
| **Change Type** | `modify-existing` (4 agentes TO-BE + 1 orquestrador + 4 checklists/gates + 1 arquivo órfão apagado, no new agents) |
| **Primary Requirement** | 4 agentes TO-BE geravam `.drawio` "dual-output" ao lado de cada `.mmd`, mas nenhum consumidor real (Summary HTML) lê esses `.drawio` — apenas os `.mmd`. Remover a geração sem quebrar os gates downstream que hoje exigem a existência desses arquivos |
| **Technical Approach** | Remoção cirúrgica linha-a-linha (não seccional, exceto 5 blocos exclusivamente drawio) em cada agente, preservando 100% da geração Mermaid; correção em cascata dos gates que verificavam a existência desses arquivos (`orchestrator-tobe.md` Fase 4.5 HARD STOP, 2 self-validation gates, 1 checklist compartilhado, 1 step de workflow); exclusão do template órfão resultante |
| **Implementation Status** | Complete. Structural greps below. |

## Constitution Check

- [x] **Article I** — nenhuma versão de tecnologia hardcoded.
- [x] **Article II** — frontmatter inalterado exceto `version`/`date` nos 5 arquivos de agente/orquestrador tocados; `security-design-tobe.md` não tinha `version`/`date` — adicionados per Guardrail #3 do projeto.
- [x] **Article IV** — nenhuma mudança de `module.yaml` (nenhum agente novo, nenhum removido).
- [x] **Article V** — conteúdo pt-BR preservado em todos os arquivos.
- [x] **Article VI** — BDD scenarios cobrem a remoção em si, a integridade dos gates downstream, a não-regressão do Summary e o isolamento do escopo AS-IS.
- [x] **Article IX** — N/A, agentes são arquivos de instrução LLM, não código gerado.
- [x] **Article X (SemVer)** — MINOR em todos os 5 arquivos de agente/orquestrador (remoção de chave do Output Contract é mudança de contrato, não PATCH).
- [x] Nenhum marcador `[NEEDS CLARIFICATION]` — 2 rodadas de `AskUserQuestion` resolveram (1) se os gates downstream deveriam ser incluídos no escopo, e (2) o que fazer com conteúdo órfão remanescente.

## Technical Context

Edições em Markdown/prosa em arquivos de agente LLM (não código executável) mais 4 arquivos de
checklist/gate também em Markdown. "Implementação" aqui significa reescrever o contrato de saída
de cada agente para que a *próxima* execução LLM-driven pare de produzir `.drawio`, e reescrever
os gates que liam esses arquivos como pré-condição de avanço de fase, para que o pipeline TO-BE
continue avançando normalmente com o Output Contract reduzido.

## Implementation Phases

### Phase 0 — Investigação ✅ CONCLUÍDO
3 agentes Explore em paralelo, cross-verificados com leituras diretas: (1) todas as ocorrências de
`drawio`/`Draw.io` nos 4 agentes-alvo, classificadas por tipo (gate, instrução de geração,
Output Contract, checklist, template) e por "removível linha-a-linha" vs. "bloco auto-contido"; (2)
todo gate/checklist fora dos 4 agentes que dependia da existência desses `.drawio` — incluindo a
descoberta do HARD STOP literal na Fase 4.5 de `orchestrator-tobe.md`; (3) confirmação definitiva,
lendo `build_summary_comprehensive.py`/`artifact-map.yaml`/`step-03-build-html.md`, de que o
pipeline de Summary nunca consumiu os `.drawio` do TO-BE — apenas 4 arquivos AS-IS sintéticos de
um caminho totalmente diferente.

### Phase 1 — Confirmação de Escopo ✅ CONCLUÍDO
2 perguntas via `AskUserQuestion` resolvidas: (1) incluir a correção dos gates downstream no
escopo — sim, recomendado e necessário para não quebrar o pipeline; (2) remover conteúdo órfão
(`templates/migration-gantt-drawio.md`, seções de template XML dentro de
`architecture-design-tobe.md`, links para `drawio-governance.md` nos 4 agentes) — sim, remoção
completa em vez de manter como referência morta.

### Phase 2 — Edição dos 4 Agentes TO-BE ✅ CONCLUÍDO
Em ordem: `security-design-tobe.md` (mais simples — nenhum bloco auto-contido, só linhas
interleaved), `architecture-design-tobe.md` (maior — 9 chaves de Output Contract + 3 seções
inteiras removidas: `Pre-Output Checklist Draw.io`, `Canonical Draw.io XML Templates`, `Template
canônico — Value Chain Draw.io`), `migration-plan-tobe.md` (subsection `#### 6.5.5` inteira
removida, `6.5.6`→`6.5.5`; 5 pontos de contagem "14 arquivos"→"13" corrigidos), `coexistence-strategy-tobe.md`
(Step 8 item 4 + parágrafo de artefato removidos). Cada arquivo verificado com `grep -i drawio`
retornando zero matches antes de prosseguir para o próximo.

### Phase 3 — Correção dos Gates Downstream ✅ CONCLUÍDO
`orchestrator-tobe.md`: tabelas de output/checklist das Fases 1, 1.6, 4, 4.3 limpas; a tabela de
gate bloqueante da Fase 4.5 (o ponto crítico) corrigida de 14→13 (migration-plan) e 4→3
(coexistence-strategy), total 18→16. `migration-validation-gate.md`: checks 3.12/3.13/3.16
removidos, Etapa 4/Relatório de Completude/Output Invariant 14→13 arquivos em todos os pontos.
`coexistence-validation-gate.md`: check 3.2 removido, 4→3 arquivos. `shared/checklists/migration-design-checklist.md`:
linhas `B5`/`D3` removidas das Seções B/D (fórmula de score dinâmica, sem recálculo necessário).
`step-01c-security-design.md`: linha de output + `AC-3` removidos, "3 arquivos"→"2 arquivos".

### Phase 4 — Remoção de Conteúdo Órfão ✅ CONCLUÍDO
`grep -r migration-gantt-drawio` confirmou que, após a remoção da seção 6.5.5, nenhum arquivo do
repositório ainda referenciava `templates/migration-gantt-drawio.md` — apagado. Links para
`shared/drawio-governance.md` removidos dos 4 agentes (o arquivo compartilhado em si não foi
tocado — permanece em uso pelos 4 agentes AS-IS de solução legada não-Delphi).

### Phase 5 — Verificação (esta sessão)
Greps estruturais confirmando zero ocorrências de `drawio` (case-insensitive) em cada um dos 9
arquivos editados, e presença das contagens corrigidas (`13`, `3`, `16`) nos pontos certos — ver
`## Test Strategy` abaixo. Nenhuma execução de pipeline ao vivo possível nesta sessão (arquivos de
instrução em prosa, não código executável) — consistente com o precedente de verificação
estrutural-apenas de outras specs deste repositório (ex. `specs/013`).

## Complexity Tracking

| Item | Status |
|---|---|
| Risco de remover uma instrução `.mmd` por engano ao editar linhas interleaved com `.drawio` | Cada edição usou `old_string`/`new_string` cirúrgicos que preservam a linha `.mmd` irmã explicitamente; verificado via leitura pós-edição de cada arquivo antes de prosseguir |
| Descoberta do HARD STOP na Fase 4.5 de `orchestrator-tobe.md` (risco de escopo maior que o pedido original) | Investigado e confirmado via Phase 0 antes de perguntar ao usuário — não assumido; correção incluída no escopo por decisão explícita do usuário, não por iniciativa unilateral |
| Contagens numéricas espalhadas (14→13, 4→3, 18→16) em múltiplos arquivos e múltiplos pontos dentro do mesmo arquivo | Cada arquivo teve um grep de verificação dedicado (`14 arquivos`, `18 arquivos`) após as edições, não apenas confiança na primeira substituição |
| `migration-design-checklist.md` usa um sistema de pesos — risco de a fórmula de score quebrar com menos critérios | Fórmula (`Σ pass×peso / Σ total×peso`) é dinâmica sobre os critérios presentes na tabela — confirmado por leitura da seção "Fórmula de Score" antes de remover as linhas; nenhum ajuste de fórmula foi necessário |
| Decidir se `drawio-governance.md` deveria ser apagado junto | Não apagado — confirmado via grep que ainda é referenciado pelos 4 agentes AS-IS de solução legada (`solution-vb.md` e irmãos), fora do escopo desta mudança |

## Test Strategy

| Test | Command | Expected |
|---|---|---|
| Nenhuma referência `.drawio` restante nos 4 agentes | `grep -ri drawio` em cada um dos 4 arquivos de agente | 0 matches em cada |
| Nenhuma referência `.drawio` restante nos gates | `grep -ri drawio` em `orchestrator-tobe.md`, `migration-validation-gate.md`, `coexistence-validation-gate.md`, `migration-design-checklist.md`, `step-01c-security-design.md` | 0 matches em cada |
| Contagens corrigidas presentes | `grep -c "13 arquivos\|13/13"` em `migration-plan-tobe.md`/`migration-validation-gate.md`/`orchestrator-tobe.md` | ≥ 1 em cada |
| Nenhuma contagem antiga remanescente | `grep -c "14 arquivos\|14/14\|18 arquivos"` nos mesmos arquivos | 0 em cada |
| Órfão removido | `Test-Path templates/migration-gantt-drawio.md` | False; `grep -r migration-gantt-drawio` → 0 matches |
| Escopo AS-IS preservado | `git diff shared/drawio-governance.md solution-vb.md solution-cobol.md solution-vbnet.md solution-powerbuilder.md` | vazio (nenhum diff) |
| Geração Mermaid intacta | Diff de cada um dos 4 agentes mostra apenas remoções de linha — nenhuma linha `flowchart`/`erDiagram`/`gantt`/instrução Mermaid alterada | Confirmado por revisão manual do diff |
| Frontmatter version consistency | `security-design-tobe.md` `version: "1.1.0"`, `architecture-design-tobe.md` `1.1.0`, `migration-plan-tobe.md` `1.3.0`, `coexistence-strategy-tobe.md` `1.1.0`, `orchestrator-tobe.md` `2.4.0` | Todos correspondem |
