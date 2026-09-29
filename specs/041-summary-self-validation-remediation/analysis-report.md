# Cross-Artifact Consistency Analysis Report
## Feature: 041-summary-self-validation-remediation

**Generated**: 2026-08-18T17:04:05-03:00  
**Analyzer**: `/speckit.analyze`  
**Artifacts analyzed**:
- `specs/041-summary-self-validation-remediation/spec.md` — Status: Draft (6 clarificações fechadas)
- `specs/041-summary-self-validation-remediation/plan.md` — Status: Approved
- `specs/041-summary-self-validation-remediation/tasks.md` — 18 tasks (13 Cat 2 · 4 Cat 3 · 1 Cat 5)

---

## 1. Inconsistências Encontradas

> Convenção de severidade idêntica à usada em `deep-audit-report.json`:
> **CRITICAL** = bloqueia implementação / viola constituição · **HIGH** = conflito ou gap que impede implementação correta · **MEDIUM** = inconsistência documentada que causa ambiguidade para o implementador · **LOW** = discrepância de wording/detalhe sem impacto funcional

| ID | Categoria | Severidade | Localização | Resumo | Recomendação |
|----|-----------|------------|-------------|--------|--------------|
| I1 | Inconsistency | MEDIUM | spec.md §3.1 vs §4.1 | **`finding_type` enum incompleto no schema `deep-audit-report.json`**: §3.1 declara `"finding_type": "empty_by_failure\|missing_artifact\|divergent_config\|mermaid_error\|placeholder_unresolved"` (5 tipos) mas C12.6 gera `table_no_rows` e C12.7 gera `list_no_items` — ambos ausentes do enum. Task 2.4 implementa `_write_deep_audit_json()` referenciando esta spec: o implementador pode não adicionar esses dois tipos ao JSON gerado, tornando o schema inválido para um quarto dos check types. | Atualizar spec §3.1 adicionando `\|table_no_rows\|list_no_items` ao enum de `finding_type`. Atualizar task 2.4 para listar explicitamente os 7 tipos válidos. |
| I2 | Inconsistency | MEDIUM | spec §4.4 / spec Clarifications rodada 1 vs tasks 2.10 / 3.4 / plan §9 | **Categorização incorreta de `--force-promote`**: spec §4.4 diz literalmente "MUST be implemented as a new task (Category 3)"; clarificação rodada 1 confirma "Vira task explícita de Categoria 3"; plan §9 rotula `cat3-force-promote-flag`. Tasks.md, corretamente, coloca `--force-promote` na task **2.10 (Categoria 2)** porque envolve código Python (argparse + lógica), e task 3.4 é apenas uma nota de rastreamento. A categorização das tasks está certa (código = Categoria 2), mas spec e plan estão errados — risco de confusão para revisor. | Corrigir spec §4.4 (última linha) de "Category 3" → "Category 2". Corrigir plan §9 rótulo `cat3-force-promote-flag` → `cat2-force-promote-flag` ou simplesmente anotar "(implementado como Category 2, task 2.10)". |
| A1 | Ambiguity | LOW | task 2.3(e) vs plan §11 | **Comportamento de ImportError em C12.5 é ambíguo**: task 2.3(e) especifica `except ImportError: return Result(True, "Playwright unavailable, C12.5 skipped")` — `Result(True, ...)` significa check passou, **nenhum finding emitido**. Mas a mesma task diz "emitindo finding INFO em vez de crashar" e plan §11 Complexity Tracking diz "emite finding INFO 'Playwright unavailable, C12.5 skipped'". São comportamentos diferentes: finding INFO visível no relatório vs. check silenciosamente passado sem entry. Impacta auditabilidade do modo `--deep` em ambientes sem Playwright. | Decidir: `Result(True, ...)` silencioso **ou** finding INFO visível. Preferência recomendada: finding INFO (auditabilidade > silêncio). Atualizar task 2.3(e) e plan §11 para usar linguagem consistente. |
| I3 | Inconsistency | LOW | plan §12 / spec §4.3 contrato vs task 2.3(e) / spec §4.3 código | **`SKIPPED` ausente do contrato `DiagramResult.status`**: plan §12 declara `status: "PASS" \| "FIXED" \| "FAIL_UNRESOLVED" \| "EMPTY" \| "TIMEOUT"` (5 estados). Spec §4.3 repete esse contrato idêntico. Mas o código de task 2.3(e) e spec §4.3 (exemplo de código) filtram `if d.status not in ("PASS", "FIXED", "EMPTY", "SKIPPED")` — adicionando `SKIPPED` que não está no contrato declarado. Se `mermaid_playwright_gate.py` (spec 040) não emite `SKIPPED`, o filtro é inofensivo mas a declaração de contrato está incompleta. | Verificar em spec 040 / `mermaid_playwright_gate.py` se `SKIPPED` é status válido. Se sim: adicionar ao contrato em plan §12 e spec §4.3. Se não: remover dos exemplos de código para evitar dead-letter filter. |

**Total de inconsistências encontradas**: 4 (0 CRITICAL · 0 HIGH · 2 MEDIUM · 2 LOW)

---

## 2. Tabela de Rastreabilidade spec → plan → tasks

| Requisito / Comportamento | ID spec | Ref plan | Task IDs | Status |
|---------------------------|---------|----------|----------|--------|
| C12.1 `empty_by_failure` — KPI vazio por falha | §4.1 | §4.1, §4.3 | 2.3(a) | ✅ Coberto |
| C12.2 `placeholder_unresolved` — token não resolvido | §4.1 | §4.1, §4.3 | 2.3(b) | ✅ Coberto |
| C12.3 `missing_artifact` — artefato ausente/zero-byte | §4.1 | §4.1, §4.5 | 2.3(c) | ✅ Coberto |
| C12.4 `divergent_config` — discrepância artifact-map vs builder | §4.1 | §4.1, §4.5 | 2.3(d) | ✅ Coberto |
| C12.5 `mermaid_error` — via mermaid_playwright_gate.py | §4.1, §4.3 | §4.1, §4.4 | 2.3(e) | ✅ Coberto |
| C12.6 `table_no_rows` — tbody presente mas vazio | §4.1 | §4.1, §4.3 | 2.3(f) | ✅ Coberto |
| C12.7 `list_no_items` — ul/ol sem li | §4.1 | §4.1, §4.3 | 2.3(g) | ✅ Coberto |
| Renumeração C12.1-3 → C11.39-41 (CHANGELOG) | §4.2 (plan) | §4.2, §8 | 2.1 | ✅ Coberto |
| `--deep` flag argparse retrocompatível | §4.5 | §4.9 | 2.2 | ✅ Coberto |
| `DEEP_CHECKS` lista + `_run_deep_checks()` | §4.1 | §4.1 | 2.3 | ✅ Coberto |
| `_write_deep_audit_json()` — schema v1.0 | §3.1 | §4.1 | 2.4 | ✅ Coberto (ver I1) |
| `run_all(deep=bool)` — integração --deep | §4.5 | §4.9 | 2.5 | ✅ Coberto |
| Loop `run_remediation_loop()` CLEAN/PARTIAL/BLOCKED | §4.4, §4.6 | §4.6 | 2.6 | ✅ Coberto |
| `_is_agent_resolvable()` — pre-check estrutural | §4.4 | §4.7 | 2.7 | ✅ Coberto |
| `_dispatch_correction()` — bifurcação transiente/estrutural | §4.4 | §4.7 | 2.8 | ✅ Coberto |
| `_resolve_max_attempts()` — cascata 3 níveis | §4.7 | §4.8 | 2.9 | ✅ Coberto |
| `--force-promote` argparse + `forced: true` schema v2.0 | §4.4, §4.6 | §4.6, §9 | 2.10 | ✅ Coberto (ver I2) |
| Bump `summary-validate-agent.md` 1.4.2→1.5.0 | §2.1 | §5 | 2.11 | ✅ Coberto |
| Bump `summary-remediation-agent.md` 1.5.0→1.6.0 | §2.2 | §5 | 2.12 | ✅ Coberto |
| Hook auto-trigger em `summary-agent.md` | §4.5 | §5 | 2.13 | ✅ Coberto |
| Bump `module.yaml` 1.4.1→1.5.0 | §1, §6 | §6, §9 | 3.1 | ✅ Coberto |
| `artifact-map.yaml`: adicionar `f3_prototype` | §9 | §4.5, §9 | 3.2 | ✅ Coberto |
| `artifact-map.yaml`: adicionar `f8_summary` | §9 | §4.5, §9 | 3.3 | ✅ Coberto |
| `cat3-force-promote-flag` (rastreabilidade plan §9) | — | §9 | 3.4 (note→2.10) | ✅ Fundida (ver I2) |
| Protocolo de validação manual | §8 excl. | §10 | 5.1 | ✅ Coberto |
| PARTIAL aplica-se em qualquer iteração | §4.6 Clarif. | §4.6 | 2.6(c) | ✅ Coberto |
| Falha estrutural NÃO consome attempt | §4.4 Clarif. | §4.7 | 2.8 | ✅ Coberto |
| Exclusão: sem test suite Python | §8 | §10 | header Cat2 | ✅ Excluído |
| Exclusão: sem HTML fora build_summary | §8 | §1 (restr.) | 2.13 inv. | ✅ Excluído |
| Exclusão: sem reimpl. Playwright/Mermaid | §8 | §1 (restr.) | 2.3(e) | ✅ Excluído |

---

## 3. Verificações Detalhadas por Seção

### 3.1 Rastreabilidade spec → plan → tasks

**Resultado**: ✅ PASS — todos os 19 requisitos funcionais identificados no spec.md têm pelo menos uma task correspondente em tasks.md, com referência explícita ao plan.md. Nenhum gap de cobertura funcional encontrado.

- **C12.1–C12.7** (7 sub-rules): todos mapeados para subtarefas explícitas dentro de task 2.3 (a)–(g). ✅
- **Loop CLEAN/PARTIAL/BLOCKED**: task 2.6 descreve fidedignamente o pseudocódigo de plan §4.6. ✅
- **`--force-promote`**: task 2.10 cobre 100% do comportamento descrito em spec §4.4 e plan §4.6. ✅
- **MAX_REMEDIATION_ATTEMPTS** cascata 3 níveis: task 2.9 espelha exatamente plan §4.8. ✅
- **Todas as decisões arquiteturais §4.1–§4.9**: cada decisão tem task(s) correspondentes. ✅

### 3.2 Consistência das 6 Clarificações

**Rodada 1 (5 clarificações)**:

| Decisão | spec.md | plan.md | tasks.md | Status |
|---------|---------|---------|----------|--------|
| `module.yaml` bump → Categoria 3 (não 4) | §1 ✅ | §6 ✅ | 3.1 ✅ | ✅ Consistente |
| Falha transiente/estrutural (Opção C) | §4.4 ✅ | §4.7 ✅ | 2.8 ✅ | ✅ Consistente |
| `--force-promote` implementar nesta feature | §4.4 ✅ | §4.6 ✅ | 2.10 ✅ | ✅ Consistente (ver I2 sobre categoria) |
| PARTIAL em qualquer iteração (não só no esgotamento) | §4.6 ✅ | §4.6 ✅ | 2.6(c) ✅ | ✅ Consistente |
| `artifact-map.yaml` scope obrigatório | §9 ✅ | §9 ✅ | 3.2/3.3 ✅ | ✅ Consistente |

**Rodada 2 (1 clarificação — deduplicação C11.x/C12.x, Opção C)**:

| Elemento | spec.md | plan.md | tasks.md | Status |
|----------|---------|---------|----------|--------|
| C12.2 regex restrito: `{{X}}`, `[NEEDS CLARIFICATION]`, `AG-NN` apenas | §4.1 ✅ | §4.3 ✅ | 2.3(b) regex ✅ | ✅ Consistente |
| Comment inline C12.2: `# DEDUPLICATION DECISION (2026-08-18, Opção C)` | §4.1 invariant ✅ | §4.3 nota ✅ | 2.3(b) comment ✅ | ✅ Consistente |
| C12.6 restrição: `<tbody>` existe E zerows — C11.41 cobre ausência total de `<tbody>` | §4.1 ✅ | §4.2/4.3 ✅ | 2.3(f) comment ✅ | ✅ Consistente |
| Comment inline C12.6: `# DEDUPLICATION (Opção C 2026-08-18)` | §4.1 invariant ✅ | §4.3 nota ✅ | 2.3(f) comment ✅ | ✅ Consistente |
| Invariante: zero duplicatas funcionais C11.x ↔ C12.x em modo `--deep` | §4.1 ✅ | §11 ✅ | design tasks ✅ | ✅ Consistente |

### 3.3 Consistência de Dependências e Ordenação

**Cadeia principal de Categoria 2** (verificada contra plan §4.6 pseudocódigo):

```
2.1 → 2.2 → 2.3 → 2.4 → {2.5, 2.7, 2.9, 2.10}  [paralelo]
      2.5 → 2.11 [P]
      2.7 → 2.8
      {2.8 + 2.9 + 2.10} → 2.6           ← CORRETO: orquestrador depende dos helpers
      {2.5 + 2.6} → 2.13
```

- **2.6 ← {2.7, 2.8, 2.9, 2.10}**: ✅ CORRETO — `run_remediation_loop` chama `_is_agent_resolvable` (2.7), `_dispatch_correction` (2.8), `_resolve_max_attempts` (2.9) e argparse `--force-promote` (2.10). Direção confirmada correta.
- **2.3 ← {2.1, 2.2}**: ✅ CORRETO — `DEEP_CHECKS` só faz sentido após renumeração (2.1) e flag argparse (2.2) existirem.
- **Nenhum ciclo detectado**: grafo é DAG puro. ✅
- **Dependências 2.7 e 2.9 ← 2.4**: moderadamente conservadoras (2.7 e 2.9 não usam diretamente `_run_deep_checks`/`_write_deep_audit_json`), mas correctas como ordenação de "estrutura definida antes dos helpers". ✅
- **3.3 ← 3.2**: ✅ CORRETO — mesmo arquivo `artifact-map.yaml`, edições sequenciais obrigatórias.
- **5.1 ← todas**: ✅ CORRETO — validação manual executa apenas após implementação completa.

### 3.4 Consistência de Schema e Contratos

**`deep-audit-report.json` (schema v1.0)**:

| Campo spec §3.1 | Prometido por task 2.4 | Consistente? |
|-----------------|------------------------|--------------|
| `schema_version: "1.0"` | ✅ | ✅ |
| `generated_at` (ISO-8601) | ✅ | ✅ |
| `project`, `html_path` | ✅ | ✅ |
| `summary.{critical,high,medium,low}` | ✅ | ✅ |
| `summary.promotable` = `critical==0 and high==0` | ✅ | ✅ |
| `findings[].{id, severity, phase, section, agent_responsible}` | ✅ | ✅ |
| `findings[].{artifact_path, finding_type, detail, root_cause}` | ✅ | ✅ |
| `findings[].{auto_correctable, suggested_fix}` | ✅ | ✅ |
| `finding_type` enum inclui `table_no_rows`, `list_no_items` | ❌ ausente em §3.1 | ⚠️ I1 (MEDIUM) |

**`remediation-report.json` (schema v2.0)**:

| Campo spec §3.2 | plan §4.6 pseudo | task 2.6 | task 2.10 | Consistente? |
|-----------------|------------------|----------|-----------|--------------|
| `schema_version: "2.0"` | implícito | ✅ explícito | — | ✅ |
| `project`, `attempts`, `max_attempts` | ✅ | ✅ | — | ✅ |
| `final_status` CLEAN/PARTIAL/BLOCKED | ✅ | ✅ | — | ✅ |
| `exit_code` 0/1 | ✅ | ✅ | — | ✅ |
| `forced: false` (default, sempre presente) | ✅ inicializado | ✅ invariante | ✅ explícito | ✅ |
| `forced: true` somente com --force-promote | ✅ | ✅ | ✅ | ✅ |
| `deep_audit_summary` | ✅ | ✅ | — | ✅ |
| `corrections_applied`, `unresolved_findings` | ✅ | ✅ | — | ✅ |
| `mermaid_gate` | ✅ | ✅ | — | ✅ |

**`finding_type` enumerados → tasks de implementação**:

| finding_type | C12 rule | Implementado em | Status |
|-------------|----------|-----------------|--------|
| `empty_by_failure` | C12.1 | task 2.3(a) | ✅ |
| `placeholder_unresolved` | C12.2 | task 2.3(b) | ✅ |
| `missing_artifact` | C12.3 | task 2.3(c) | ✅ |
| `divergent_config` | C12.4 | task 2.3(d) | ✅ |
| `mermaid_error` | C12.5 | task 2.3(e) | ✅ |
| `table_no_rows` | C12.6 | task 2.3(f) | ✅ implementado — ⚠️ ausente do enum §3.1 (I1) |
| `list_no_items` | C12.7 | task 2.3(g) | ✅ implementado — ⚠️ ausente do enum §3.1 (I1) |

### 3.5 Verificação de Esforço e Categorização

**Contagem Categoria 2** — verificação linha a linha:

| Task | Esforço declarado | Tipo de trabalho | Cat. correta? |
|------|-------------------|------------------|--------------|
| 2.1 | P | Rename strings em catálogo + CHANGELOG | ✅ |
| 2.2 | P | Argparse `--deep` (1 linha) | ✅ |
| 2.3 | G | 7 funções `_c12da_N` (maior task) | ✅ |
| 2.4 | M | `_run_deep_checks` + `_write_deep_audit_json` | ✅ |
| 2.5 | P | Parâmetro `deep=bool` em `run_all()` | ✅ |
| 2.6 | G | `run_remediation_loop()` completo | ✅ |
| 2.7 | P | `_is_agent_resolvable()` helper | ✅ |
| 2.8 | M | `_dispatch_correction()` bifurcação | ✅ |
| 2.9 | P | `_resolve_max_attempts()` cascata | ✅ |
| 2.10 | M | `--force-promote` argparse + lógica | ✅ |
| 2.11 | P | Bump frontmatter agent.md | ✅ |
| 2.12 | P | Bump frontmatter agent.md | ✅ |
| 2.13 | M | Hook auto-trigger em summary-agent.md | ✅ |

**P count**: 2.1, 2.2, 2.5, 2.7, 2.9, 2.11, 2.12 = **7** ✅  
**M count**: 2.4, 2.8, 2.10, 2.13 = **4** ✅  
**G count**: 2.3, 2.6 = **2** ✅  
**Total**: P×7 + M×4 + G×2 = **13 tasks** ✅ — bate com o sumário declarado.

**Categoria 3 — nenhuma contém código**:
- 3.1: bump de string em YAML → ✅ Config/Metadata
- 3.2: adicionar bloco YAML → ✅ Config/Metadata
- 3.3: adicionar bloco YAML → ✅ Config/Metadata
- 3.4: nota de rastreamento, esforço `—` → ✅ Não conta para esforço

**Task 3.4 — duplicação de esforço na contagem total**: ❌ Não duplica. Esforço declarado como `—`, implementação absorvida por task 2.10 (Categoria 2). Nenhuma dupla-contagem. ✅

### 3.6 Verificação de Exclusões e Restrições Arquiteturais

| Restrição | Evidência em tasks.md | Status |
|-----------|----------------------|--------|
| Nenhuma reimplementação Playwright/Mermaid | Task 2.3(e): delega exclusivamente a `mermaid_playwright_gate.py` via import | ✅ |
| Nenhuma síntese HTML fora de `build_summary_comprehensive.py` | Task 2.13: invariante explícito; task 2.6(e): invoca builder para rebuild | ✅ |
| Sem suíte de testes Python automatizada | Header Cat2: "Suíte automatizada de testes Python: Excluída" | ✅ |
| Sem checklist de verificação manual formal (arquivo no repo) | Header Cat2 + task 5.1: "não criar arquivo no repositório" | ✅ |
| `--deep` retrocompatível em todos os toques a `validate_summary.py` | Tasks 2.2, 2.3, 2.4, 2.5: cada uma confirma retrocompatibilidade | ✅ |

### 3.7 Verificação de Gaps Remanescentes

**`[NEEDS CLARIFICATION]` não resolvidos**: ✅ Zero marcadores encontrados nos três documentos.

**4 tasks de Categoria 3 do plan §9**:

| ID plan §9 | Presente em tasks.md | Observação |
|-----------|---------------------|------------|
| `cat3-module-version-bump` | ✅ task 3.1 | |
| `cat3-artifact-map-f3-prototype` | ✅ task 3.2 | |
| `cat3-artifact-map-f8-summary` | ✅ task 3.3 | |
| `cat3-force-promote-flag` | ✅ task 3.4 (nota→2.10) | Reclassificada Cat 2 (ver I2) |

**Quality Gate §6 — item não marcado** (`[ ] module.yaml version field updated`):
Task 3.1 cobre exatamente este gate: "Bump `version` em `module.yaml`". Uma vez executada, o gate §6 pode ser marcado `[x]`. ✅

---

## 4. Gaps de Cobertura (requisito sem task)

**Nenhum gap encontrado.** Todos os requisitos funcionais e comportamentos definidos em spec.md têm cobertura explícita em tasks.md.

---

## 5. Tasks Órfãs (task sem requisito rastreável)

**Nenhuma task órfã encontrada.** Cada uma das 18 tasks é rastreável a pelo menos uma seção do spec.md ou uma decisão arquitetural do plan.md.

---

## 6. Verificação da Constituição

| Artigo | Status | Evidência |
|--------|--------|-----------|
| I — Configuration-Driven | ✅ | `MAX_REMEDIATION_ATTEMPTS` via cascata yaml; sem hardcodes |
| II — Agent Contract Standard | ✅ | Frontmatter apenas `name/version/description/allowed-tools` |
| III — Pipeline Execution Contract | ✅ | F8/cross-cutting; Summary Validator gate já existente |
| IV — Module Registration | ✅ | Nenhum novo agente; apenas version bump (task 3.1) |
| V — Language Convention | ✅ | Agente bodies PT-BR; código Python inglês técnico |
| VI — Test-First | ✅ | 5 cenários BDD cobrindo S1-S5 (nominal, remediação, legítimo-vazio, BLOCKED+force, Mermaid) |
| VII — Security-First | ✅ | Gate é read-only; sem impacto no sub-pipeline de segurança |
| VIII — Observability | N/A | Agentes são prompts LLM; scripts usam print/stderr |
| IX — Clean Architecture | N/A | Arquivos .md + Python de infraestrutura de pipeline |
| X — Versioning | ✅ | MINOR bump (novos outputs; sem breaking change na API pública) |
| XI — Skill/Agent Separation | ✅ | `ava-summary-validate` permanece interno; SKILL.md de `ava-summary-remediation` inalterado |

**Nenhuma violação de Constituição encontrada.** ✅

---

## 7. Métricas

| Métrica | Valor |
|---------|-------|
| Total de requisitos funcionais mapeados | 27 |
| Total de tasks | 18 (13 Cat2 + 4 Cat3 + 1 Cat5) |
| Cobertura de requisitos (≥1 task) | **27/27 = 100%** |
| Tasks com requisito rastreável | **18/18 = 100%** |
| Issues CRITICAL | 0 |
| Issues HIGH | 0 |
| Issues MEDIUM | 2 (I1, I2) |
| Issues LOW | 2 (A1, I3) |
| Gaps de cobertura | 0 |
| Tasks órfãs | 0 |
| `[NEEDS CLARIFICATION]` remanescentes | 0 |
| Clarificações verificadas e consistentes | 6/6 |

---

## 8. Veredito Final

```
╔══════════════════════════════════════════════════════════════════════════╗
║         ✅  READY FOR IMPLEMENTATION                                      ║
║                                                                          ║
║  Nenhum issue CRITICAL ou HIGH encontrado.                               ║
║  Cobertura 100%: todos os requisitos têm task; todas as tasks têm        ║
║  rastreabilidade. Cadeia de dependências sem ciclos e logicamente         ║
║  executável. Contagem de esforço P×7·M×4·G×2=13 verificada. As 6        ║
║  clarificações estão refletidas de forma idêntica nos três documentos.   ║
║                                                                          ║
║  2 issues MEDIUM e 2 issues LOW documentados — recomenda-se corrigi-los  ║
║  antes ou durante a implementação para evitar ambiguidade para o          ║
║  implementador (especialmente I1 e A1, que afetam task 2.4 e 2.3(e)).   ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## 9. Próximos Passos

### Antes de `/speckit.implement`:

1. **Corrigir I1 (MEDIUM — recomendado antes)**: Adicionar `table_no_rows` e `list_no_items` ao enum de `finding_type` na spec §3.1 (esquema do `deep-audit-report.json`) e em task 2.4. Risco: sem correção, o implementador de 2.4 pode não incluir esses tipos no JSON gerado.
   - → Executar `/speckit.specify` com refinamento pontual em spec §3.1

2. **Corrigir I2 (MEDIUM — pode ser feito pós-implementação, impacto baixo)**: Corrigir a classificação de `--force-promote` em spec §4.4 ("Category 3" → "Category 2") e atualizar o rótulo em plan §9 de `cat3-force-promote-flag` → deixar anotação "(implementado como Cat 2, task 2.10)".
   - → Edição direta em spec §4.4 e plan §9

3. **Resolver A1 (LOW — antes de implementar task 2.3(e))**: Decidir se ImportError em C12.5 produz finding INFO visível ou silenciosamente passa. Atualizar task 2.3(e) e plan §11 para linguagem consistente.

4. **Verificar I3 (LOW — depende de spec 040)**: Confirmar com spec 040 / `mermaid_playwright_gate.py` se `SKIPPED` é status válido; atualizar contrato se necessário.

### Sequência de implementação recomendada:

```
Iniciar imediatamente em paralelo:
  3.1 (module.yaml bump) + 3.2 (artifact-map f3_prototype)
  ↕ simultâneo com:
  2.1 → 2.2 → 2.3 (sequencial, maior task)

Após 2.4 concluir → 2.5, 2.7, 2.9, 2.10 em paralelo
Após 3.2 → 3.3

Após {2.8 + 2.9 + 2.10} → 2.6 (orquestrador)
Após {2.5 + 2.6} → 2.13

Por último: 5.1 (validação manual, após tudo completo)
```

---

*Relatório gerado por `/speckit.analyze` em 2026-08-18. Read-only — nenhum arquivo de artefato foi modificado.*
