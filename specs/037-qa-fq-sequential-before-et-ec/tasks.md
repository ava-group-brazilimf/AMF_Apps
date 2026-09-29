# Tasks — Spec 037: FQ sequencial antes de ET+EC

## 1. Análise & Planejamento
- [x] Investigar dependências de dados entre FQ, ET e EC (Input Contracts).
- [x] Confirmar ausência de acoplamento programático à ordem textual do DAG.
- [x] Mapear todas as ocorrências textuais a editar em `qa-orchestrator-agent.md`.
- [x] Confirmar decisão do usuário (abrir spec formal + commit message em inglês ao final).
- [x] Criar `spec.md`, `plan.md`, `tasks.md`, `checklists/requirements.md`.

## 2. Frontmatter
- [ ] Bump `version: 2.1.0 → 2.1.1` no frontmatter.
- [ ] Atualizar `date: 2026-08-05 → 2026-08-06`.

## 3. Tabelas e notas textuais
- [ ] `## Agent Team QA`: "paralelo a ET+EC" → "sequencial, imediatamente antes de ET+EC".
- [ ] `## Triggers / Menu` (descrição `QE`): `...FT→ET→EC→FQ` → `...FT→FQ→ET→EC`.
- [ ] Nota da sequência mínima obrigatória: `...FT→ET+EC+FQ→PT→RS` → `...FT→FQ→ET+EC→PT→RS`.
- [ ] 4b TS COMPLETION GATE: "`ava-qa-evidence-capture` (passo 9)" → "(passo 9b)".
- [ ] Tabela "Resumo de cobertura por trigger": `...FT→ET→EC→FQ` → `...FT→FQ→ET→EC`.

## 4. Reestruturação do step 9
- [ ] Novo step 9: dispatch isolado de `ava-qa-bridge-fastqa-tobe` (mantém o bloco `⛔ CRITICAL`
      literal).
- [ ] Novo step 9a: FQ COMPLETION GATE (= conteúdo integral do atual 9c).
- [ ] Novo step 9b: dispatch em paralelo de `ava-qa-exploratory` + `ava-qa-evidence-capture`
      (mantém o bloco de instrução do ET literal).
- [ ] Novo step 9c: ET VERIFICATION GATE (= conteúdo integral do atual 9b).
- [ ] Confirmar que os passos 10 (PT) e 11 (RS) permanecem textualmente idênticos.

## 5. Documentação
- [ ] Entrada PATCH no `CHANGELOG.md` (`ava-qa-orchestrator` v2.1.0 → v2.1.1).

## 6. Verificação & Qualidade
- [ ] `git diff` confirma as 8 ocorrências textuais + reestruturação do bloco 9.
- [ ] Rodar `python src/shared/tools/generate_agent_wrappers.py`.
- [ ] Rodar `pytest tests/tools/test_agent_wrappers.py`.
- [ ] Rodar `pytest tests/tools/test_pipeline_plan.py`.
- [ ] Releitura manual do bloco 9/9a/9b/9c — nenhuma instrução crítica perdida.

## 7. Entrega
- [ ] Produzir mensagem de commit final em inglês, concisa e objetiva, resumindo a mudança —
      devolvida ao usuário como texto (sem executar `git commit`).
