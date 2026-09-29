# Plan — Spec 037: FQ sequencial antes de ET+EC

## Constitution Check

- **Não altera `## Output Contract`** — os artefatos declarados permanecem idênticos; nenhum
  parser downstream (`build_summary_comprehensive.py`, `artifact-map.yaml`) é afetado.
- **Não altera nomes/semântica de triggers** — `QE`, `ET`, `EC`, `FQ` continuam existindo e
  significando o mesmo; muda apenas a ordem de disparo interna ao trigger `QE`.
- **Classificação do bump**: reordenação de execução sem mudança de contrato = correção de
  comportamento → **PATCH bump 2.1.0 → 2.1.1** (Article X, "Bug fixes in agent instructions =
  PATCH bump").
- **PATCH bump → entrada em `CHANGELOG.md` recomendada** por consistência com o histórico do
  próprio agente (todos os bumps anteriores têm entrada, incluindo PATCH-like changes).
- **`module.yaml` não muda** — nenhum agente adicionado/removido.
- **`SKILL.md` não muda** — `.github/skills/ava-qa-orchestrator/SKILL.md` é genérico.
- **Corpo do agente em português brasileiro** (Article V) — mantido.
- **Wrapper `.github/agents/ava-qa-orchestrator.agent.md`** — gerado por
  `generate_agent_wrappers.py`; deve ser regenerado após o bump de `version` no frontmatter para
  que `metadata.version` não fique desatualizado (testado por `test_agent_wrappers.py`).

## Technical Context

Arquivo alvo: `src/modules/ava-fabric-agents/qa-agents/agents/qa-orchestrator-agent.md` (v2.1.0).

Investigação de dependências (concluída antes deste plano, sem uso de subagentes):
- `evidence-capture-agent.md` (EC) — Input Contract não lista nenhum artefato de
  `outputs/qa/fastqa/` (automation-summary.md, exploratory-api-report.md, gherkin-scenarios.md)
  como obrigatório ou opcional.
- `exploratory-agent.md` (ET) — 100% AS-IS, sem qualquer menção a FastQA.
- `src/shared/**` / `tests/**` — nenhum código faz parsing programático da ordem textual do DAG.
- `tests/tools/test_pipeline_plan.py` — valida apenas mapeamento fase→agente→trigger (`TPT`,
  `QE`), não a ordem interna — não quebra com esta mudança.
- `.github/agents/ava-qa-orchestrator.agent.md` — wrapper fino gerado por
  `src/shared/tools/generate_agent_wrappers.py`; não contém a lógica de routing (cap de 30.000
  caracteres do `.agent.md`, 37/107 specs do repo excedem), mas herda `version` do frontmatter da
  spec para `metadata.version`.
- `specs/035-qa-orchestrator-two-moments/*` — specs fechadas (checkboxes marcados) que documentam
  o estado passado do refactor QS→QE; não travam mudanças futuras de ordenação interna.

Todas as ocorrências textuais a editar (grep confirmado, único arquivo):
1. Frontmatter: `version: 2.1.0` → `2.1.1`, `date: 2026-08-05` → `2026-08-06`.
2. Linha ~42 (tabela `## Agent Team QA`): "paralelo a ET+EC" → "sequencial, imediatamente antes
   de ET+EC".
3. Linha ~57 (tabela `## Triggers / Menu`, descrição `QE`): `...FT→ET→EC→FQ` → `...FT→FQ→ET→EC`.
4. Linha ~61 (nota da sequência mínima): `...FT→ET+EC+FQ→PT→RS` → `...FT→FQ→ET+EC→PT→RS`.
5. Linha ~527 (dentro do 4b TS COMPLETION GATE): "`ava-qa-evidence-capture` (passo 9)" →
   "(passo 9b)".
6. Bloco principal (linhas ~535-605): step 9 dividido em 9/9a/9b/9c — ver §Implementation Phases.
7. Linha ~760 (tabela "Resumo de cobertura por trigger"): `...FT→ET→EC→FQ` → `...FT→FQ→ET→EC`.
8. `CHANGELOG.md`: nova entrada PATCH 2.1.0 → 2.1.1.

## Implementation Phases

### Phase 1 — Spec Artifacts
- Criar `spec.md`, `plan.md` (este arquivo), `tasks.md`, `checklists/requirements.md`.

### Phase 2 — Frontmatter
- Bump `version: 2.1.0 → 2.1.1` e `date: 2026-08-05 → 2026-08-06`.

### Phase 3 — Tabelas e notas textuais (ocorrências 2, 3, 4, 5, 7 acima)
- Atualizar as 5 ocorrências textuais fora do bloco principal do step 9.

### Phase 4 — Reestruturação do bloco step 9 (núcleo da mudança)
Substituir o bloco atual:
```
9. **ET + EC + FQ** — invocar ... em paralelo
   - [instrução ET]
   - [instrução FQ]
9b. **ET VERIFICATION GATE** — ...
9c. **FQ COMPLETION GATE** — ...
```
Pelo novo bloco:
```
9. **FQ** — invocar ava-qa-bridge-fastqa-tobe sozinho, sequencial
   - [instrução FQ — texto idêntico ao atual]
9a. **FQ COMPLETION GATE** — [texto idêntico ao atual 9c]
9b. **ET + EC** — invocar ava-qa-exploratory + ava-qa-evidence-capture em paralelo
   - [instrução ET — texto idêntico ao atual]
9c. **ET VERIFICATION GATE** — [texto idêntico ao atual 9b]
```
Passos 10 (PT) e 11 (RS) permanecem sem alteração.

### Phase 5 — Documentação
- Adicionar entrada PATCH no `CHANGELOG.md` seguindo o padrão
  `### 🔧 Changed — ava-qa-orchestrator (v2.1.0 → v2.1.1)`.

### Phase 6 — Verificação
- `git diff` conferindo as 8 ocorrências.
- Rodar `python src/shared/tools/generate_agent_wrappers.py`.
- Rodar `pytest tests/tools/test_agent_wrappers.py` (detecta drift do wrapper).
- Rodar `pytest tests/tools/test_pipeline_plan.py` (não deve quebrar).
- Releitura manual do bloco 9/9a/9b/9c confirmando que nenhuma instrução crítica foi perdida.

### Phase 7 — Entrega
- Produzir mensagem de commit final em inglês, concisa e objetiva, resumindo a mudança —
  devolvida ao usuário, sem `git commit` automático.
