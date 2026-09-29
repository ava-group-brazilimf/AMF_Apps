# Tasks: Summary Item Correlation — C12.6/C12.7 Concrete Identification

**Spec**: `specs/042-summary-item-correlation/spec.md`
**Plan**: `specs/042-summary-item-correlation/plan.md`
**Feature Branch**: `042-summary-item-correlation`
**Change Type**: modify-existing · `ava-summary-validate` 1.5.0→1.6.0 · `ava-summary-remediation` 1.6.0→1.7.0 · `artifact-map.yaml` 1.0.1→1.1.0

> **Categorias ativas**: **2** (Implementação), **3** (Config/Metadata), **5** (Validação Manual).
> Categorias 1, 4, 6, 7 são **N/A**: nenhum novo agente criado (spec §1: `modify-existing`);
> SKILL.md de `ava-summary-remediation` inalterado; `ava-summary-validate` permanece interno (sem
> SKILL.md); Category 4 registra apenas _novos_ agentes — o bump de `version` em `module.yaml` é
> task de Categoria 3 (plan.md §7, spec §1).
>
> **Organização**: 5 Task Groups seguindo exatamente plan.md §11 — Groups 1 e 4 mapeiam para
> Categoria 3; Groups 2 e 3 mapeiam para Categoria 2; Group 5 mapeia para Categoria 5. Backlog
> (não implementar nesta feature) na seção 6.
>
> **Suíte automatizada de testes Python**: **Excluída** — spec §8 (restrição herdada de spec 041,
> decisão SpecKit 039-prototype-design-input). Validação é o protocolo manual único da Categoria 5
> (plan.md §14), documentado como comentário/anexo da PR, não como arquivo no repositório.

---

## Categoria 3 — Config/Metadata (Task Group 1: artifact-map.yaml)

> **Pré-requisito para Categoria 2.** Pode iniciar imediatamente — sem dependências externas.
> Tasks 1.1 e 1.2 tocam o mesmo arquivo; executar sequencialmente nessa ordem.
> **Esforço estimado (Task Group 1):** P×1 · M×1 — 2 tasks

- [X] **1.1** Bump `version: "1.0.1"` → `"1.1.0"` no cabeçalho de `artifact-map.yaml`. Campo único — preservar indentação YAML e todos os demais campos inalterados (nenhuma outra linha alterada). **Arquivo**: `src/modules/ava-fabric-agents/summary/data/artifact-map.yaml`. **Esforço**: P. **Categoria**: 3. **Depende de**: —

- [X] **1.2** Adicionar top-level section `html_element_correlation` ao final de `artifact-map.yaml` com EXATAMENTE as 10 entradas de spec §3.3: `tb-patterns`, `tb-risks`, `tb-rules`, `tb-reqs`, `tb-schema`, `tb-sps`, `tb-tobebc`, `tb-endpoints`, `tb-scen`, `tb-defects`. Incluir: (a) bloco de cabeçalho de seção com comentários de proveniência das Clarificações Q2+Q3 rodada 1 (texto "Audited & corrected: Clarification Q2+Q3 (2026-08-19)…" conforme spec §3.3); (b) comentário `# REMOVED: tb-cc` documentando elemento ausente do template (C11.10 / renderComplexityTable() removido); (c) comentário `# REMOVED: tb-tobebc-detail` documentando elemento ausente do template (C11.15 / renderTOBEBCDetail() removido); (d) comentários inline nas entradas `tb-rules` ("was: tb-bizrules"), `tb-schema` ("was: schema-tbody"), `tb-sps` ("was: sp-tbody + wrong function"), `tb-tobebc` ("was: tobebc-tbody"), `tb-endpoints` ("was: endpoints-tbody + wrong function") documentando correções de ids auditadas. Valores exatos de `render_function` fixados pelas Clarificações Q2/Q3: `tb-sps.render_function: "renderDBSchema()"` (não `renderSPs()`); `tb-endpoints.render_function: "renderAPISurface()"` (não `renderEndpoints()`) — copiar de spec §3.3, não inventar. **Arquivo**: `src/modules/ava-fabric-agents/summary/data/artifact-map.yaml`. **Esforço**: M. **Categoria**: 3. **Depende de**: 1.1

---

## Categoria 2 — Corpo dos Agentes / Implementação

> Implementação em Python (inglês técnico). Tasks marcadas com `[P]` podem ser executadas em
> paralelo com outras tasks dentro do mesmo Task Group, desde que dependências explícitas estejam
> satisfeitas. **Esforço estimado (Categoria 2):** G×1 · M×3 · P×3 — 7 tasks

### Task Group 2 — validate_summary.py [Depende de Task Group 1 completo]

- [X] **2.1** Inserir função privada `_classify_empty_element(ctx, element_html, corr_map, *, native_finding_type, native_severity) -> Optional[dict]` imediatamente antes de `_c12da_6` (após linha ~3257) em `validate_summary.py`. Implementar STEP 1–6 completos conforme spec §4.1 e plan.md AD-3: **STEP 1** — `re.search(r'id="([^"]+)"', element_html)` — id ausente cai no fallback de heading-heuristic existente emitindo `native_finding_type` (unchanged behaviour); **STEP 2** — `corr_map.get(id_value)` — miss cai no mesmo fallback com nota `"element id not in correlation map — update artifact-map.yaml html_element_correlation"`; **STEP 3** (Clarificação Q1 rodada 1 + Q1-R2 rodada 2, plan.md AD-2) — `_is_phase_done(ctx, corr["phase"].lower())` com `.lower()` OBRIGATÓRIO (phase key vem uppercase do YAML, e.g. `"F5"`, `_is_phase_done` exige lowercase `"f5"`) — se `False` → retornar `None` SEM emitir finding; emitir debug para `sys.stderr` apenas: `f"[C12.6/DEBUG] Skipping element id='{id_value}' — phase '{corr['phase']}' not yet executed."`; **STEP 4** — verificar `ctx.project_dir / corr["artifact_path"]` via `.exists()` e `.stat().st_size == 0` — ausente ou vazio → classificar como `missing_artifact` com `auto_correctable=True`; **STEP 5** — `_extract_json_slice(ctx.html, corr["d_field"])` — slice `None` ou `len(raw_slice.strip()) <= 4` (exclui `[]`, `{}`, `""`, `null`) → classificar como `parser_gap` (`severity: "HIGH"`, `auto_correctable=False`, `suggested_fix` menciona `D.{d_field}` e instrui re-run de `build_summary_comprehensive.py`); **STEP 6** — D.* tem dado mas elemento ainda vazio → classificar como `render_gap` (`severity: "MEDIUM"`, `auto_correctable=False`, `suggested_fix` menciona `corr["render_function"]` e `id` DOM). Docstring completa conforme plan.md AD-3: lista os 4 tipos de retorno possíveis (native_finding_type via fallback, missing_artifact, parser_gap, render_gap); semântica de `None` (não é erro silencioso — fase não executada ou out-of-scope legítimo). Assinatura exata: `def _classify_empty_element(ctx: Ctx, element_html: str, corr_map: dict, *, native_finding_type: str, native_severity: str) -> Optional[dict]:`. **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/validate_summary.py`. **Esforço**: G. **Categoria**: 2. **Depende de**: 1.2

- [X] **2.2** [P] Refatorar `_c12da_6()` in-place (linhas 3258–3327): (a) `corr_map = _load_artifact_map().get("html_element_correlation", {})` no início da função (carga isolada por função, per plan.md AD-4 Opção A — assinatura `_c12da_6(ctx: Ctx) -> Result` permanece inalterada); (b) loop per-table sobre o regex `<table>` já existente; (c) chamar `_classify_empty_element(ctx, table_html, corr_map, native_finding_type="table_no_rows", native_severity="HIGH")` para cada elemento com `<tbody>` vazio detectado; (d) acumular resultados não-`None` em `findings: list[dict]`; (e) retornar `Result(ok=not findings, detail=..., extra=findings)`. Preservar TODA a lógica de detecção já existente (condição tbody-presente/empty, mutually exclusive com C11.41 que cobre `<tbody>` totalmente ausente): somente o que ocorre APÓS a detecção muda. `Result.extra` passa a ser lista de N dicts em vez de 1 dict. **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/validate_summary.py`. **Esforço**: M. **Categoria**: 2. **Depende de**: 2.1

- [X] **2.3** [P] Refatorar `_c12da_7()` in-place (linhas 3334–3371) de forma idêntica a 2.2 com `native_finding_type="list_no_items"` e `native_severity="MEDIUM"`; loop per-list sobre `<ul>`/`<ol>` com zero `<li>` em seção de fase done. Task trivial após 2.2 servir de modelo exato — mesma estrutura, parâmetros diferentes. **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/validate_summary.py`. **Esforço**: P. **Categoria**: 2. **Depende de**: 2.1

- [X] **2.4** Estender `_write_deep_audit_json()` (linha ~3420) com passagem de deduplicação (plan.md AD-6) e bump de schema: (a) no loop de enriquecimento de findings, ao construir `enriched = dict(finding)`, adicionar `enriched["_src"] = chk.id` (valores: `"C12.3"` para o check de artefatos, `"C12.6"` para tables, `"C12.7"` para lists — conforme índices em `DEEP_CHECKS`); (b) após acumular `all_findings`, implementar deduplication pass: `c12_3_paths = {f["artifact_path"] for f in all_findings if f.get("_src") == "C12.3" and f.get("finding_type") == "missing_artifact" and f.get("artifact_path") is not None}` → filtrar: `all_findings = [f for f in all_findings if not (f.get("_src") in ("C12.6", "C12.7") and f.get("finding_type") == "missing_artifact" and f.get("artifact_path") in c12_3_paths)]`; (c) remover tag antes de serializar: `for f in all_findings: f.pop("_src", None)`; (d) bump `"schema_version": "1.0"` → `"1.1"` na dict do report; (e) atualizar docstring listando os 9 `finding_type` válidos: `empty_by_failure | missing_artifact | divergent_config | mermaid_error | placeholder_unresolved | table_no_rows | list_no_items | parser_gap | render_gap`. Garantia de ordenação: `DEEP_CHECKS` posiciona C12.3 no índice 2, C12.6 no índice 5, C12.7 no índice 6 — todos os findings de C12.3 precedem os de C12.6/C12.7 quando a dedup pass executa; nenhuma reordenação necessária. **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/validate_summary.py`. **Esforço**: M. **Categoria**: 2. **Depende de**: 2.2, 2.3

---

### Task Group 3 — remediate_summary.py [Depende de Task Group 2 completo]

- [X] **3.1** [P] Implementar `phase8_deep_audit_triage(project_name: str, log: list[str]) -> list[dict]` em `remediate_summary.py`, inserida imediatamente antes de `write_report()` (após linha ~845). Guard explícito: `deep_audit_path = BASE_DIR / f"projects/{project_name}/outputs/summary/deep-audit-report.json"` — se `not deep_audit_path.exists()`: `log.append("## Fase 8 — Deep Audit Triage\nSkipped: deep-audit-report.json not found.")` + `return []`. Para cada finding em `deep_audit["findings"]`: se `finding.get("auto_correctable"): continue` (tratado pelas fases anteriores); **branch f** (`finding_type == "parser_gap"`): executar `run_script("build_summary_comprehensive.py", project_name)` (função `run_script` já existente em `remediate_summary.py`), capturar `excerpt = (result.stdout + result.stderr)[-2000:] or "Sem output capturado — inspecionar build_summary_comprehensive.py manualmente."`, anexar `"\n[Build output excerpt]:\n" + excerpt` a `finding["suggested_fix"]`, appender finding a `unresolved_triage_items`; **branch g** (`finding_type == "render_gap"`): appender finding a `unresolved_triage_items` diretamente, sem dispatch nem rebuild (MANUAL). Retornar `unresolved_triage_items`. **OBRIGATÓRIO**: docstring DEVE incluir EXATAMENTE o parágrafo NOTE de spec §4.5 / plan.md AD-8 (patch P1, Clarification Q2 rodada 3): _"NOTE: Called directly from `main()` until `run_remediation_loop` (spec 041, `cat3-remediation-loop-041`) is implemented. At that point, this function becomes the non-dispatchable branch handler inside the loop — do NOT delete or replace; update the call site from `main()` to `run_remediation_loop`."_ — não opcional. **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py`. **Esforço**: M. **Categoria**: 2. **Depende de**: 2.4

- [X] **3.2** [P] Estender assinatura de `write_report()` (linha ~847): adicionar parâmetro `triage_items: Optional[list[dict]] = None` (backward-compatible — callers existentes sem o argumento não se alteram); quando `triage_items` não vazio, acrescentar seção `## Fase 8 — Deep Audit Triage\n\n{len(triage_items)} item(s) requerem intervenção manual.` no relatório `.md` e campo `"deep_audit_triage": triage_items` no relatório `.json`. Schema `remediation-report.json` permanece `schema_version: "2.0"` sem bump (extensão additive segura, spec §3.2). **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py`. **Esforço**: P. **Categoria**: 2. **Depende de**: 2.4

- [X] **3.3** Integrar `phase8_deep_audit_triage()` em `main()` (linha ~917): adicionar `triage_items = phase8_deep_audit_triage(project_name, log)` após `phase7_revalidate()` e ANTES de `write_report()`; passar `triage_items=triage_items` para `write_report()`. Confirmar que o guard da função (`deep-audit-report.json` não encontrado) protege execuções onde `--deep` não foi rodado previamente — sem crash, `triage_items` retorna `[]`, `write_report()` não inclui seção Fase 8. **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py`. **Esforço**: P. **Categoria**: 2. **Depende de**: 3.1, 3.2

---

## Categoria 3 — Config/Metadata (Task Group 4: Version Bumps e Frontmatter)

> **Totalmente paralelo** — sem dependências entre si nem com os Task Groups 1, 2 ou 3. Podem
> iniciar imediatamente junto com as tasks 1.1/1.2 e correr em paralelo a toda a Categoria 2.
> **Esforço estimado (Task Group 4):** P×3 — 3 tasks

- [X] **4.1** [P] Bump `version: "1.5.0"` → `"1.6.0"` no frontmatter YAML de `summary-validate-agent.md`; substituir campo `description` pelo bloco PT-BR de spec §2.1 (texto completo: inicia em "Non-regression quality gate do Summary HTML…", termina com frases de ativação "validate summary", "audit summary", "check summary integrity", "summary validator", "summary-validate", "validar summary"). Não adicionar campos além dos permitidos por Art. II (`name`, `version`, `description`, `allowed-tools`). `allowed-tools` permanece `Read, Bash, Glob, Grep, Write` (inalterado). **Arquivo**: `src/modules/ava-fabric-agents/summary/agents/summary-validate-agent.md`. **Esforço**: P. **Categoria**: 3. **Depende de**: —

- [X] **4.2** [P] Bump `version: "1.6.0"` → `"1.7.0"` no frontmatter YAML de `summary-remediation-agent.md`; substituir campo `description` pelo bloco PT-BR de spec §2.2 (texto completo: inicia em "Agente de reparo pós-pipeline do Summary executivo…", termina com frases de ativação "corrigir o summary", "remediar o summary", "@ava-summary-remediation", "consertar visualização do summary"). Não adicionar campos além dos permitidos por Art. II. `allowed-tools` permanece `Read, Write, Edit, Glob, Grep, Bash` (inalterado). **Arquivo**: `src/modules/ava-fabric-agents/summary/agents/summary-remediation-agent.md`. **Esforço**: P. **Categoria**: 3. **Depende de**: —

- [X] **4.3** [P] Bump `version: "1.5.0"` → `"1.6.0"` em `module.yaml`; preservar TODOS os demais campos (`name`, `display_name`, `agents[]`, `bmad_version: ">=6.0.0"`) INALTERADOS. Nenhum novo agente em `agents[]` — Category 4 N/A per spec §1 e plan.md §7. **Arquivo**: `src/modules/ava-fabric-agents/summary/module.yaml`. **Esforço**: P. **Categoria**: 3. **Depende de**: —

---

## Categoria 5 — Validação Manual (Task Group 5)

> **Task única desta categoria.** Sem suíte automatizada em Python — spec §8, restrição herdada
> de spec 041. Resultado documentado como comentário/anexo da PR, não como arquivo no repositório.
> Esta task é **sempre a última** — executar somente após todas as tasks 1.1–4.3 estarem completas.
> **Esforço estimado (Task Group 5):** M×1 — 1 task

- [X] **5.1** Executar protocolo de validação manual P1–P7 do plan.md §14 cobrindo EXATAMENTE os 6 cenários de spec §5. **P1 — Nominal (S1)**: `python validate_summary.py --project {NOME} --deep` em projeto com tabelas/listas com ids mapeados; verificar `deep-audit-report.json`: `"schema_version": "1.1"` ✓; findings com `html_element_id` ≠ null para elementos com id no mapa ✓; zero findings com `"section": "unidentified section"` para elementos mapeados ✓; zero findings com `"agent_responsible": "ava-summary"` para elementos mapeados ✓. **P2 — Deduplicação (S3)**: remover artefato (ex.: `scenario-register.json`), regenerar HTML; confirmar exatamente UM finding com `artifact_path` do artefato removido; confirmar nenhum par de findings com `artifact_path` idêntico e `finding_type: "missing_artifact"` ✓. **P3 — Phase gate (S5)**: projeto onde F5 não foi executado; confirmar zero entradas com `"html_element_id": "tb-scen"` ou `"html_element_id": "tb-defects"` em `findings[]`; confirmar `summary.promotable` não afetado por esses elementos ✓. **P4 — parser_gap (S2a)**: injetar `D.scenarios: []` manualmente no HTML (mock); confirmar `"finding_type": "parser_gap"`, `"severity": "HIGH"`, `suggested_fix` menciona `D.scenarios` ✓. **P5 — render_gap (S2b)**: `D.scenarios` com dados mas `<tbody id="tb-scen">` vazio; confirmar `"finding_type": "render_gap"`, `"severity": "MEDIUM"`, `suggested_fix` menciona `renderScenarios()` ✓. **P6 — Fallback gracioso (S4)**: elemento com `id="tb-nonexistent"` não presente no mapa; confirmar `"finding_type": "table_no_rows"`, `"html_element_id": "tb-nonexistent"`, `"d_field": null`, nota `"element id not in correlation map"` ✓; confirmar nenhuma exceção levantada, auditoria continua, JSON gerado ✓. **P7 — Remediation triage (S6)**: `deep-audit-report.json` com `parser_gap`; `python remediate_summary.py --project {NOME}`; confirmar `phase8_deep_audit_triage` processa sem dispatch de agente upstream ✓; confirmar `remediation-report.json` contém `"deep_audit_triage": [...]` ✓; confirmar `final_status: BLOCKED` e exit code `1` se `parser_gap` é o único finding HIGH ✓. Documentar resultado (aprovado/reprovado + observações) como **comentário ou anexo da PR** — sem arquivo de resultado no repositório, sem suíte Python. **Arquivo**: _comentário/anexo da PR_. **Esforço**: M. **Categoria**: 5. **Depende de**: 1.1, 1.2, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3

---

## Categoria 3 — Backlog (Rastreabilidade — NÃO implementar nesta feature)

> Tasks de backlog para rastreabilidade. **Não implementar nesta feature** — escopo fechado.
> Task 6.1 é implementável e idealmente entregue junto com 1.1–4.3, mas independente.
> Tasks 6.2 e 6.3 são DEFERRED e registradas apenas para não perder o contexto decisório.

- [ ] **6.1** [P] Adicionar entrada de CHANGELOG para spec 042: documentar novos `finding_type` (`parser_gap` severity HIGH, `render_gap` severity MEDIUM); bump `schema_version: "1.1"` em `deep-audit-report.json` (3 novos campos opcionais nullable exclusivos de findings C12.6/C12.7: `html_element_id`, `d_field`, `render_function`); mudança de finding agregado → granularidade per-element em C12.6/C12.7 (behavioral change, não breaking: consumidores que filtram por `finding_type: "table_no_rows"` continuam recebendo esse tipo para elementos não mapeados); passagem de deduplicação (AD-6) — mesmo `artifact_path` nunca aparece duas vezes como `missing_artifact`; `--verbose` em `build_summary_comprehensive.py` não adicionado nesta versão (AD-7 — stdout+stderr capturado via `run_script` existente); `phase8_deep_audit_triage()` adicionado a `remediate_summary.py`; `artifact-map.yaml` v1.1.0 com seção `html_element_correlation` (10 entradas). **Arquivo**: `CHANGELOG.md`. **Esforço**: P. **Categoria**: 3. **Depende de**: — _(idealmente após 1.1–4.3, mas independente)_

- [ ] **6.2** _(Nota de rastreamento — DEFERRED, fora do escopo de 042)_ `cat3-verbose-flag-bsc`: Adicionar argumento `--verbose` a `build_summary_comprehensive.py` para output granular por função de parser — habilitaria diagnóstico mais preciso de `parser_gap` sem depender de stdout+stderr agregado. Não implementar nesta feature (AD-7: objetivo diagnóstico já atendido com stdout+stderr de `run_script` existente). **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py`. **Esforço estimado**: M. **Categoria**: 3. **Depende de**: _N/A (DEFERRED)_

- [ ] **6.3** _(Nota de rastreamento — DEFERRED, spec 041 Category 3 pendente)_ `cat3-remediation-loop-041`: Implementar `run_remediation_loop()` + `_dispatch_correction()` com `_IMPLEMENTED_DISPATCH_STRATEGIES` / `_is_agent_resolvable()` + `MAX_REMEDIATION_ATTEMPTS` — framework completo de loop de retentativa de spec 041. Quando implementado, **migrar call site** de `phase8_deep_audit_triage()` de `main()` para o loop SEM deletar a função (ela se torna o branch handler não-dispatchável das branches f/g per spec §4.5). **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py`. **Esforço estimado**: G. **Categoria**: 3. **Depende de**: _N/A (DEFERRED)_

---

## Dependências entre Tasks

```
INÍCIO IMEDIATO (sem dependências):
  1.1  (artifact-map.yaml: version bump 1.0.1→1.1.0)
    └─→ 1.2  (artifact-map.yaml: html_element_correlation — 10 entradas, comentários Q2/Q3)
                                             │
                                             ▼
  2.1  (_classify_empty_element — STEP 1–6, helper compartilhado)
         ├─→ 2.2 [P]  (_c12da_6 refactor: loop per-table + helper call)   ──┐
         └─→ 2.3 [P]  (_c12da_7 refactor: loop per-list  + helper call)   ──┤
                                                                              │
                                                              [2.2 + 2.3] ───┘
                                                                └─→ 2.4  (_write_deep_audit_json:
                                                                             _src tag + dedup pass +
                                                                             schema "1.1" + 9 types)
                                                                           │
                                                                           ▼
  3.1 [P]  (phase8_deep_audit_triage: guard + branches f/g + NOTE docstring) ──┐
  3.2 [P]  (write_report: parâmetro triage_items + seção Fase 8)           ────┤
                                                               [3.1 + 3.2] ────┘
                                                                └─→ 3.3  (main: integrar phase8
                                                                           após phase7_revalidate)
                                                                           │
                                                                           ▼
                                                                          5.1  (protocolo P1–P7
                                                                                6 cenários S1–S6
                                                                                comentário/PR)

PARALELO A TUDO (sem dependências, iniciar imediatamente):
  4.1 [P]  (summary-validate-agent.md: 1.5.0→1.6.0 + description spec §2.1)
  4.2 [P]  (summary-remediation-agent.md: 1.6.0→1.7.0 + description spec §2.2)
  4.3 [P]  (module.yaml: version 1.5.0→1.6.0)

BACKLOG (independente, não implementar nesta feature):
  6.1 [P]  (CHANGELOG.md: entry 042 — idealmente após 1.1–4.3)
  6.2      (DEFERRED: --verbose em build_summary_comprehensive.py)
  6.3      (DEFERRED: run_remediation_loop + _dispatch_correction de spec 041)
```

**Janelas de paralelismo recomendadas**:
- Iniciar `1.1` + `4.1` + `4.2` + `4.3` imediatamente (e `6.1` se possível).
- Após `1.1` concluir, iniciar `1.2`.
- Após `1.2` concluir, iniciar `2.1` (unblocked).
- Após `2.1` concluir, iniciar `2.2` e `2.3` **em paralelo**.
- Após `2.2` + `2.3` concluírem, iniciar `2.4`.
- Após `2.4` concluir, iniciar `3.1` e `3.2` **em paralelo**.
- Após `3.1` + `3.2` concluírem, iniciar `3.3`.
- Após `1.1–4.3` **todos** completos (incluindo `3.3`), iniciar `5.1`.

---

## Definition of Done

- [X] `artifact-map.yaml`: `version: "1.1.0"` confirmado; top-level section `html_element_correlation` presente com exatamente 10 entradas (tb-patterns, tb-risks, tb-rules, tb-reqs, tb-schema, tb-sps, tb-tobebc, tb-endpoints, tb-scen, tb-defects); comentários `# REMOVED: tb-cc` e `# REMOVED: tb-tobebc-detail` presentes; valores de `render_function` auditados per Q2/Q3 (`renderDBSchema()` para tb-sps, `renderAPISurface()` para tb-endpoints).
- [X] `validate_summary.py`: `_classify_empty_element()` inserida antes de `_c12da_6`; STEP 1–6 implementados com `.lower()` obrigatório no callsite de `_is_phase_done()` (AD-2); assinatura keyword-only para `native_finding_type`/`native_severity`; docstring completa per AD-3. `_c12da_6()` refatorada: loop per-table, chamada ao helper, `Result.extra` como lista de N dicts. `_c12da_7()` refatorada: idêntica com `list_no_items`/`MEDIUM`. `_write_deep_audit_json()` estendida: tag `_src` injetada e removida, deduplication pass per AD-6, `schema_version: "1.1"`, docstring com 9 finding_types.
- [X] `remediate_summary.py`: `phase8_deep_audit_triage()` implementada com guard de arquivo ausente, branch f (parser_gap + captura stdout+stderr[-2000:]), branch g (render_gap + MANUAL); docstring inclui EXATAMENTE o parágrafo NOTE de spec §4.5 (não opcional). `write_report()` aceita `triage_items: Optional[list[dict]] = None`; seção `## Fase 8` no MD e campo `deep_audit_triage` no JSON quando não vazio. `main()` chama `phase8_deep_audit_triage()` após `phase7_revalidate()`.
- [X] `summary-validate-agent.md`: frontmatter `version: "1.6.0"`, description spec §2.1 completo (PT-BR), frases de ativação presentes; nenhum campo além dos 4 permitidos por Art. II.
- [X] `summary-remediation-agent.md`: frontmatter `version: "1.7.0"`, description spec §2.2 completo (PT-BR), frases de ativação presentes; nenhum campo além dos 4 permitidos por Art. II.
- [X] `module.yaml`: `version: "1.6.0"` confirmado; `bmad_version: ">=6.0.0"` preservado; `agents[]` INALTERADO (nenhum novo agente).
- [X] `deep-audit-report.json` produzido com `schema_version: "1.1"`; findings de C12.6/C12.7 contêm `html_element_id`, `d_field`, `render_function` (nullable para fallback); zero findings com `section: "unidentified section"` / `agent_responsible: "ava-summary"` para elementos com id no mapeados.
- [X] `remediation-report.json` schema `v2.0` preservado (sem bump); campo `deep_audit_triage` presente quando triage_items não vazio (validado via P7 inline + guard test).
- [X] Protocolo de validação manual 5.1 (P1–P7, 6 cenários S1–S6) executado; resultado (aprovado/reprovado + observações) documentado como comentário/anexo da PR — zero arquivo de suíte Python gerado.
- [ ] `CHANGELOG.md` atualizado (task 6.1) com entry de spec 042 documentando novos finding_types, schema v1.1, mudança per-element, deduplication pass, phase8_deep_audit_triage.
