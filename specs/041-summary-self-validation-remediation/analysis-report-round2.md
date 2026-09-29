# Analysis Report — Round 2 (Code vs. Spec)
## Feature: 041-summary-self-validation-remediation

**Rodada**: 2 — Pós `/speckit.implement`  
**Foco**: Código real vs. artefatos aprovados (spec.md, plan.md, tasks.md)  
**Data**: 2026-08-18  
**Analista**: `/speckit.analyze` — modo code-vs-spec  
**Arquivos auditados**:
- `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py` (1.149 linhas)
- `src/modules/ava-fabric-agents/summary/utils/validate_summary.py` (3.275 linhas)
- `specs/041-summary-self-validation-remediation/{spec.md, plan.md, tasks.md}`

---

## Tabela de Findings Consolidada

| ID | Categoria | Severidade | Localização no Código | Localização no Spec/Plan/Tasks | Resumo | Veredito |
|----|-----------|------------|-----------------------|-------------------------------|--------|----------|
| F1 | Wiring | CRITICAL | `remediate_summary.py:1166–1295` (main) | task 2.6; spec §4.4; SC "Auto-correction efficacy" | `run_remediation_loop()` definida (L975) mas NUNCA invocada de `main()` | ✅ CONFIRMADO |
| F2 | Schema Contract | CRITICAL | `remediate_summary.py:1146–1163` (write_report) | spec §3.2; tasks 2.6, 2.10 | `remediation-report.json` faltam 7 campos obrigatórios do schema v2.0 | ✅ CONFIRMADO |
| F3 | Auto-Correction | CRITICAL | `validate_summary.py:2916,2994,3081,3152` | spec §4.4, SC "Auto-correction efficacy"; task 2.3 | `auto_correctable` hardcoded `False` em `_c12da_2`, `_c12da_3`, `_c12da_4` (3/4 tipos exigidos) | ✅ CONFIRMADO |
| F4 | Dispatch Impl. | HIGH | `remediate_summary.py:965–972` | plan.md §4.7; task 2.8 | `_invoke_agent()` não implementada; dispatch para tipos ≠ `mermaid_error` é stub otimista | ✅ CONFIRMADO |
| F5 | Deduplication | HIGH | `validate_summary.py:1045–1052` (_c12_3) | plan.md §4.2; task 2.3 comentário inline para C12.6; spec §4.1 Opção C | C11.41 (`_c12_3`) NÃO foi restrito a `<tbody>` ausente — ainda dispara para tabelas com `<tbody>` vazio, sobrepondo C12.6 | ✅ CONFIRMADO |
| F6 | Output Contract | MEDIUM | `validate_summary.py:3661–3700` (run_all) | spec §3.1; plan.md §4.9; task 2.5 | `run_all()` nunca escreve `validation-report.md` / `validation-report.json` em disco | ✅ CONFIRMADO |
| A7.1 | Reachability | CRITICAL (derivado F1) | `remediate_summary.py:1005` | task 2.9 | `_resolve_max_attempts()` é código morto — só seria alcançada dentro de `run_remediation_loop()` | ✅ CONFIRMADO |
| A7.2 | Force-Promote | MEDIUM | `remediate_summary.py:1264,1283` | task 2.10; spec §4.6; Scenario 4 | `--force-promote` aplica-se ao resultado do pipeline legado (`errors_after > 0`), não ao `final_status == "BLOCKED"` do state machine | ✅ CONFIRMADO |
| A7.3 | Retrocompat | OK | `validate_summary.py:3682–3700` | spec §4.5; SC "Backward compatibility"; task 2.2 | Modo sem `--deep` 100% retrocompatível — DEEP_CHECKS completamente ignorados | ✅ OK |
| A7.4 | Test Suites | OK | `tests/summary/*.py` (datas 2026-08-10) | spec §8 | Nenhuma nova suíte de teste Python criada por esta feature (arquivos preexistem à branch 041) | ✅ OK |

---

## Análise Detalhada por Finding

---

### F1 — CRITICAL: `run_remediation_loop()` definida mas nunca chamada de `main()`

**Evidência no código** (`remediate_summary.py:1166–1295`):

```python
def main() -> int:
    # ...
    ok, failures_before = phase0_audit(project_name, log, args.language_target)
    synthesized.extend(phase1_artifact_resolution(project_name, log))
    synthesized.extend(phase2_diagram_synthesis(project_name, log))
    phase3_mermaid_sanitization(project_name, log)
    mermaid_gate_result = phase35_playwright_gate(...)      # L1223
    phase4_security_reconciliation(project_name, log)       # L1231
    ui_guard_findings = phase5_content_ui_guard_check(...)  # L1233
    rebuilt = phase6_rebuild(...)                           # L1235
    validation = phase7_revalidate(...)                     # L1260
    # ← NUNCA CHAMA run_remediation_loop() ←
    forced = args.force_promote and validation["errors_after"] > 0
    write_report(project_name, log, synthesized, ui_guard_findings, validation, ...)
    return 0 if validation["errors_after"] == 0 else 1
```

`run_remediation_loop()` existe em L975–1077 com sua assinatura completa e estado machine CLEAN/PARTIAL/BLOCKED, mas não há nenhuma chamada a ela em todo o corpo de `main()`.

**Impacto real**: executar `python remediate_summary.py --project X` percorre o pipeline legado de 7 fases (pré-041), reporta resultados da validação C1–C11, e encerra — **sem nunca ativar o state machine C12**, que é a proposta de valor central desta feature.

**Assinatura real vs. esperada**:

| Campo | plan.md §4.6 (spec) | Código (L975) |
|---|---|---|
| Retorno | `dict` | `str` ("CLEAN"\|"PARTIAL"\|"BLOCKED") |
| Parâmetro `force_promote` | `force_promote: bool = False` | `forced: bool = False` (renomeado) |
| Parâmetro extra | — | `log: list[str]` (adicionado) |
| Parâmetro extra | — | `max_attempts: int \| None = None` (adicionado) |

A mudança de `dict` para `str` como retorno implica que mesmo se `run_remediation_loop()` fosse chamada, `write_report()` não teria acesso ao report dict interno da função (corrections_applied, unresolved_findings etc.), porque a função não os retorna.

**Tasks de tasks.md que deveriam ter coberto isto**:
- Task **2.6** `[X]` (marcada done): "Implementar `run_remediation_loop()` em `remediate_summary.py`" — A função foi implementada, mas **não foi conectada ao `main()`**. A DoD de 2.6 exige que o loop seja funcional end-to-end; o wiring em main() é pré-requisito implícito e não foi executado.
- Task **5.1** `[X]` passo **(c)** "Teste do loop completo — `python remediate_summary.py --project {NOME}`; confirmar que `remediation-report.json` contém `final_status: CLEAN|PARTIAL|BLOCKED`" — Se este passo tivesse sido executado, a ausência de `final_status` no output seria detectada imediatamente.

**Conclusão**: DoD de task 2.6 violada nominalmente (marcada [X] sem verificação de integração). Task 5.1 não exercitada de forma que detectaria o bug.

---

### F2 — CRITICAL: `remediation-report.json` não cumpre schema v2.0

**Evidência no código** (`remediate_summary.py:1146–1163`):

```python
json_payload: dict = {
    "schema_version": "2.0",        # ✅ PRESENTE
    "project_name": project_name,   # ❌ spec exige "project" (nome diferente)
    "timestamp": ...,               # ⚠️ não listado no schema v2.0 (campo extra)
    "forced": forced,               # ✅ PRESENTE
    "synthesized_artifacts": ...,   # ⚠️ campo extra, não no schema v2.0
    "ui_guard_findings": ...,       # ⚠️ campo extra, não no schema v2.0
    **validation,                   # ⚠️ espalha: errors_before, errors_after, improvement_pct, fixed, remaining
}
# Condicionalmente adicionados:
if mermaid_gate_section is not None:
    json_payload["mermaid_gate"] = ...  # ✅ CONDICIONAL
if deep_audit_summary is not None:
    json_payload["deep_audit_summary"] = ...  # ✅ CONDICIONAL
```

**Gap campo a campo contra spec §3.2**:

| Campo (spec §3.2) | Status no Código | Evidência |
|---|---|---|
| `"schema_version": "2.0"` | ✅ PRESENTE | L1147 |
| `"project": "<project_name>"` | ❌ AUSENTE — código usa `"project_name"` | L1148 |
| `"attempts": 1` | ❌ AUSENTE — vem do state machine (nunca chamado) | — |
| `"max_attempts": 3` | ❌ AUSENTE — idem | — |
| `"final_status": "CLEAN\|PARTIAL\|BLOCKED"` | ❌ AUSENTE — idem | — |
| `"exit_code": 0` | ❌ AUSENTE | — |
| `"forced": false` | ✅ PRESENTE | L1150 |
| `"deep_audit_summary": {...}` | ⚠️ CONDICIONAL (só se arquivo existe) | L1157–1158 |
| `"corrections_applied": []` | ❌ AUSENTE | — |
| `"unresolved_findings": []` | ❌ AUSENTE | — |
| `"mermaid_gate": {...}` | ⚠️ CONDICIONAL (só se gate rodou) | L1155–1156 |

Resumo: 7 campos obrigatórios ausentes. 1 campo com nome errado (`"project_name"` vs `"project"`). 2 campos obrigatórios presentes apenas condicionalmente em vez de sempre.

**Causa raiz**: Consequência direta de F1. Sem `run_remediation_loop()` sendo chamada, não há de onde extrair `attempts`, `max_attempts`, `final_status`, `exit_code`, `corrections_applied`, `unresolved_findings`.

**Tasks**: 2.6 (schema fields do loop), 2.10 (forced, schema_version), tasks 5.1(c) e 5.1(d) (validação do schema no report).

---

### F3 — CRITICAL: `auto_correctable` hardcoded `False` em 3 dos 4 tipos exigidos

**Evidência no código**:

| Função | Tipo de Finding | `auto_correctable` | Linha | Spec exige |
|---|---|---|---|---|
| `_c12da_1` | `empty_by_failure` | `False` (hardcoded) | L2916 | auto-corrigível via rebuild |
| `_c12da_2` | `placeholder_unresolved` | `False` (hardcoded) | L2994 | **✅ exigido no SC** |
| `_c12da_3` | `missing_artifact` | `False` (hardcoded) | L3081 | **✅ exigido no SC** |
| `_c12da_4` | `divergent_config` | `False` (hardcoded) | L3152 | **✅ exigido no SC** |
| `_c12da_5` | `mermaid_error` | `status == "FAIL_UNRESOLVED"` (condicional) | L3233 | ✅ correto |
| `_c12da_6` | `table_no_rows` | `False` (hardcoded) | L3312 | não listado no SC |
| `_c12da_7` | `list_no_items` | `False` (hardcoded) | L3356 | não listado no SC |

**Success Criteria violado** (spec §, "Auto-correction efficacy"):
> "At least `missing_artifact`, `divergent_config`, `mermaid_error`, and `placeholder_unresolved` finding types are auto-corrected in the remediation loop without manual intervention"

Três dos quatro tipos listados explicitamente têm `auto_correctable: False` hardcoded. Isso significa que mesmo se `run_remediation_loop()` fosse corretamente invocada (F1 corrigido), o dispatch loop:
```python
for finding in [f for f in critical_high if f["auto_correctable"]]:
    _dispatch_correction(finding, project_name, report)
```
…nunca processaria `missing_artifact`, `divergent_config` ou `placeholder_unresolved`. A remediação automática ficaria limitada apenas a `mermaid_error`.

**Conflito adicional com Scenario 2.1** (spec §5):
> "Given a Summary HTML with one KPI tile showing 0 where risk-register.md exists and has 15 entries, When ava-summary-remediation runs, Then the deep audit produces a finding C12.1 with severity HIGH, `auto_correctable: true`"

O código produz `auto_correctable: False` para C12.1 — contradição direta com o cenário de aceite aprovado.

**Tasks**: 2.3 (implementar `_c12da_1` a `_c12da_7`), 2.8 (dispatch depende de auto_correctable correto), task 5.1(c) e 5.1(d).

---

### F4 — HIGH: `_dispatch_correction()` não implementa `_invoke_agent()`

**Evidência no código** (`remediate_summary.py:955–972`):

```python
# Para finding_type == "mermaid_error":
if finding_type == "mermaid_error":
    gate_result = phase35_playwright_gate(project_name, log)
    return True  # ✅ Implementado via delegação ao gate existente

# Para QUALQUER outro finding_type (missing_artifact, divergent_config, etc.):
log.append(
    f"    Auto-dispatch for '{finding_type}' not yet implemented for {agent_id}; "
    "recorded for tracking — manual re-run of the agent is required."  # ← stub explícito
)
return True  # Otimista: registrado, sem ação real
```

`_invoke_agent(agent_id, project_name, timeout=300)` — especificada em plan.md §4.7, task 2.8 — **não existe em nenhuma linha do arquivo**.

**Divergência de assinatura de `_dispatch_correction`**:

| Campo | plan.md §4.7 | Código (L923) |
|---|---|---|
| Parâmetro 3 | `report: dict` | `log: list[str]` |
| Retorno | `None` | `bool` |
| Efeito em `report["corrections_applied"]` | Atualiza | Nunca acontece |
| Efeito em `report["unresolved_findings"]` | Atualiza | Nunca acontece |
| Falha estrutural → `finding["auto_correctable"] = False` | Sim | Não — apenas loga |

**Bifurcação transiente/estrutural**: O pré-check `_is_agent_resolvable()` existe (L944) e funciona corretamente. Porém, na path "estrutural" (agente não resolvível), o código apenas loga uma string — não registra em `unresolved_findings` nem modifica `finding["auto_correctable"]` como exige a invariante do plan.md §4.4:
> "Structural failure MUST NOT silently consume retry attempts. It is recorded immediately as a non-auto-correctable finding."

**Task 2.8** (marcada [X]): DoD exige bifurcação transiente/estrutural completa com registro no report dict e chamada real a `_invoke_agent()`. O código entrega apenas o pré-check estrutural via `_is_agent_resolvable()` — a tentativa real não existe.

---

### F5 — HIGH: C11.41 (`_c12_3`) não foi restrito a `<tbody>` ausente — assimetria com C12.6

**Evidência no código** (`validate_summary.py:1045–1052`):

```python
def _c12_3(ctx: Ctx) -> Result:
    """C12.3 — No <table> with thead but zero tbody rows (warn)."""
    tables = re.findall(r'<table[^>]*>.*?</table>', ctx.html, re.DOTALL | re.IGNORECASE)
    empty = [t for t in tables if re.search(r'<thead', t, re.IGNORECASE)
             and not re.search(r'<tbody[^>]*>\s*<tr', t, re.IGNORECASE)]
    #                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # PROBLEMA: esta regex retorna True em DOIS cenários:
    # 1. <tbody> completamente ausente (→ domínio de C11.41 ✅)
    # 2. <tbody> presente mas sem <tr> imediatamente após (→ domínio de C12.6 ❌)
```

**Decisão Opção C** aplicada ASSIMETRICAMENTE:

| Regra | Escopo definido (plan.md §4.2) | Implementação real |
|---|---|---|
| C11.41 (`_c12_3`) | Tabelas **SEM `<tbody>` algum** | Tabelas sem `<tbody>` **OU** com `<tbody>` vazio ← **ERRADO** |
| C12.6 (`_c12da_6`) | Tabelas com `<tbody>` presente mas zero `<tr>` | Implementação **CORRETA** (L3275–3277: `if tbody_match is None: continue`) |

**Consequência**: Quando `--deep` está ativo, uma tabela com `<tbody>` presente mas vazia dispara **dois findings**: C11.41 (warn) + C12.6 (HIGH). Isso é exatamente a duplicação de reporte que a Opção C pretendia eliminar.

**Fix cirúrgico necessário** (não realizado pela task 2.1):
```python
# Linha 1048–1049 atual:
empty = [t for t in tables if re.search(r'<thead', t, re.IGNORECASE)
         and not re.search(r'<tbody[^>]*>\s*<tr', t, re.IGNORECASE)]

# Fix necessário — C11.41 deve ser exclusivo de tbody AUSENTE:
empty = [t for t in tables if re.search(r'<thead', t, re.IGNORECASE)
         and '<tbody' not in t.lower()  # tbody completamente ausente
         and not re.search(r'<tbody[^>]*>\s*<tr', t, re.IGNORECASE)]
```

**Task 2.1** (marcada [X]): renumerou os IDs do catálogo mas não aplicou a restrição de escopo no código da função `_c12_3` conforme exigido pela Opção C. Task 2.3 inclui comentário inline para C12.6 explicando a exclusão, mas não atualiza a função legada C11.41.

---

### F6 — MEDIUM: `run_all()` nunca escreve `validation-report.md` / `validation-report.json`

**Evidência no código** (`validate_summary.py:3661–3700`):

```python
def run_all(...) -> int:
    ctx = _load_ctx(project_name)
    results = _run_checks(ctx)
    # ...auto-fix loop...
    if deep:
        deep_results = _run_deep_checks(ctx)
        _write_deep_audit_json(ctx, deep_results)  # ✅ deep-audit-report.json escrito
        results = results + deep_results
    jb = _format_json(results, ctx, applied_fixes=applied_fixes)  # ← apenas constrói o dict
    # ... prints to stdout apenas ...
    return 1 if errors else 0
    # ← NENHUMA CHAMADA A _write_validation_reports() ou equivalente ←
```

**Docstring do módulo** (L10–11):
```
Output:
  - projects/{project}/outputs/summary/validation-report.md
  - projects/{project}/outputs/summary/validation-report.json
```

**Output Contract spec §3.1**:
```yaml
outputs:
  validation_report_md:    "projects/{project_name}/outputs/summary/validation-report.md"
  validation_report_json:  "projects/{project_name}/outputs/summary/validation-report.json"
```

**Pseudo-código plan.md §4.9** (aprovado):
```python
def run_all(...) -> int:
    # ...
    _write_validation_reports(ctx, results)  # ← AUSENTE no código real
    errors = [r for c, r in results if not r.ok and c.level == "error"]
    return 1 if errors else 0
```

`_write_validation_reports()` aparece explicitamente no pseudo-código aprovado do plan.md §4.9 como parte do fluxo de `run_all()`, mas não foi implementada.

**Contexto histórico vs. nova omissão**: O comentário interno de `_run_validator()` em `remediate_summary.py` (L138–139) diz: *"run_all() itself only prints to stdout/returns an exit code and never persists validation-report.*"* — evidência de que isso é comportamento **pré-existente** à feature 041. Contudo, o plan.md desta feature mostra `_write_validation_reports()` como parte da atualização esperada de `run_all()`, tornando a omissão em uma regressão de scope desta entrega.

**Task 2.5** (marcada [X]): "Atualizar `run_all()` para aceitar parâmetro `deep: bool`" — o parâmetro foi adicionado, mas o pseudo-código do plan.md inclui `_write_validation_reports()` que não foi implementado.

**Nota de escopo**: Isso pode ser classificado como "dívida técnica pré-existente" se o time decidir que spec §7 ("does not replace existing validation-report.*") implica que os arquivos existentes não precisam ser reescritos. Porém, o docstring e o plan.md são inequívocos: os arquivos devem ser escritos.

---

## Verificações da Seção 7

### A7.1 — `_resolve_max_attempts()` é código morto (consequência de F1)

`_resolve_max_attempts()` está implementada corretamente (L65–101) e é chamada dentro de `run_remediation_loop()` (L1005–1006). Porém, como `run_remediation_loop()` nunca é invocada de `main()`, essa função também é inacessível em qualquer caminho de execução real. Severidade derivada de F1 (CRITICAL).

### A7.2 — `--force-promote` aplica-se ao contexto errado

**Evidência** (`remediate_summary.py:1264, 1283`):

```python
# Código real (L1264):
forced = args.force_promote and validation["errors_after"] > 0
# "validation" vem de phase7_revalidate() — pipeline legado C1–C11

# Spec task 2.10 exige:
# "quando force_promote=True and report["final_status"] == "BLOCKED"
#   → report["forced"] = True"
```

O comportamento real:
- **`forced=True`** quando há erros do pipeline legado (`errors_after > 0`) — sem relação com o state machine BLOCKED
- **Header**: `"⚠️ [ava-summary-remediation] FORCE-PROMOTE ativo — N erro(s)"` (L1283) vs. spec: `"[WARN] FORCED PROMOTION — unresolved CRITICAL/HIGH findings remain"` (spec §4.4 e task 2.10)
- A flag funciona parcialmente (forced=true escrito no JSON, exit code 1 preservado), mas semântica é diferente da spec: aplica-se a erros legados, não ao BLOCKED do deep audit

**Severidade**: MEDIUM (flag existe e o campo `forced` é escrito; o desvio é semântico, não estrutural).

### A7.3 — Retrocompatibilidade: OK ✅

`run_all()` com `deep=False` (default): o bloco DEEP_CHECKS é completamente ignorado (L3682: `if deep:`). Exit code semântico idêntico ao pré-041. CHECKS (C1–C11 + C13.x) são os únicos executados. Nenhuma regressão.

Verificação adicional: `_run_checks()` não foi alterada; C11.39/C11.40/C11.41 foram apenas renumerados no catálogo, não removidos. Comportamento retrocompatível preservado.

### A7.4 — Nenhuma suíte de teste Python criada por esta feature: OK ✅

Arquivos existentes em `tests/summary/`:
- `test_summary_pt_remediation.py`: modificado 2026-08-10 (preexiste à branch 041, criada 2026-08-18)
- `test_summary_pt_validation.py`: modificado 2026-08-10 (idem)

Confirmado via `git log --since="2026-08-17" --diff-filter=A`: nenhum arquivo `tests/` foi adicionado por commits desta feature. spec §8 ("No new Python test suites") — compliance ✅.

---

## Coverage Summary: Tasks.md DoD vs. Entrega Real

| Task | Status Declarado | DoD Cumprida? | Observação |
|------|-----------------|---------------|-----------|
| 2.1 — Renumeração C12→C11.39-41 | [X] | ⚠️ PARCIAL | IDs renumerados ✅; `_c12_3` não restrito ao escopo exclusivo (F5) |
| 2.2 — argparse `--deep` | [X] | ✅ | Implementado corretamente |
| 2.3 — DEEP_CHECKS (`_c12da_1` a `_c12da_7`) | [X] | ⚠️ PARCIAL | Funções existem; `auto_correctable` hardcoded False em 3/4 tipos exigidos (F3) |
| 2.4 — `_run_deep_checks` + `_write_deep_audit_json` | [X] | ✅ | Implementados corretamente |
| 2.5 — `run_all()` aceita `deep: bool` | [X] | ⚠️ PARCIAL | deep=bool funciona; `_write_validation_reports()` ausente (F6) |
| 2.6 — `run_remediation_loop()` | [X] | ❌ NÃO | Função implementada mas nunca chamada de main() (F1) |
| 2.7 — `_is_agent_resolvable()` | [X] | ✅ | Implementada e funcional |
| 2.8 — `_dispatch_correction()` | [X] | ⚠️ PARCIAL | Pré-check estrutural ok; `_invoke_agent()` ausente; report dict não atualizado (F4) |
| 2.9 — `_resolve_max_attempts()` | [X] | ✅ (inacessível) | Lógica correta; código morto por F1 |
| 2.10 — argparse `--force-promote` | [X] | ⚠️ PARCIAL | Flag existe; semântica desviada (A7.2); schema v2.0 incompleto (F2) |
| 2.11 — bump `summary-validate-agent.md` | [X] | Não auditado | Fora do escopo desta análise |
| 2.12 — bump `summary-remediation-agent.md` | [X] | Não auditado | Fora do escopo desta análise |
| 2.13 — hook em `summary-agent.md` | [X] | Não auditado | Depende de F1 para ser efetivo |
| 3.1 — bump `module.yaml` | [X] | Não auditado | |
| 3.2 — `f3_prototype` em `artifact-map.yaml` | [X] | Não auditado | |
| 3.3 — `f8_summary` em `artifact-map.yaml` | [X] | Não auditado | |
| 5.1 — Validação manual | [X] | ❌ NÃO EFETIVO | Passos (c) e (d) teriam detectado F1 e F2 se executados |

---

## Métricas da Análise

| Métrica | Valor |
|---------|-------|
| Findings CRITICAL | 3 primários + 1 derivado = **4** |
| Findings HIGH | **2** |
| Findings MEDIUM | **2** |
| Findings OK | **2** |
| Tasks com DoD violada (total ou parcial) | **7 de 13 auditadas** |
| Campos de schema v2.0 ausentes | **7 de 11** |
| Tipos `auto_correctable` incorretos | **3 de 4** exigidos pelo Success Criteria |
| Linhas de código morto (inacessível) | `run_remediation_loop` (L975–1077) + `_resolve_max_attempts` (L65–101) = **~140 linhas** nunca executadas |

---

## Veredito

### 🔴 BLOCKED — Não está pronto para merge

A feature não cumpre seu Success Criterion central ("Auto-correction efficacy") por três razões independentes e simultâneas:
1. O state machine de remediação não é executado (F1)
2. O schema do report de saída não está em conformidade com o contrato (F2)
3. Os findings que deveriam ser auto-corrigíveis não são sinalizados como tal (F3)

Mesmo que F1 fosse corrigido isoladamente, F3 garantiria que o loop de remediação seria um no-op para 3 dos 4 tipos exigidos. A feature entrega corretamente: (a) os checks C12.x de validação profunda, (b) a flag `--deep`, (c) a escrita de `deep-audit-report.json`, e (d) a retrocompatibilidade. Esses são avanços reais e estão corretos. O problema é que a camada de orquestração (wiring + schema + auto_correctable) está incompleta.

---

## Correções Necessárias Antes de Reabrir Task 5.1

Ordem de prioridade para desbloqueio:

### P0 — Bloqueadores Críticos (devem ser corrigidos antes de qualquer reteste)

**C1. Wiring de `run_remediation_loop()` em `main()`** (F1):
- Após `validation = phase7_revalidate(...)`, adicionar chamada a `run_remediation_loop(project_name, log, forced=args.force_promote)`
- Capturar `final_status` retornado
- Integrar `final_status` e campos do loop (`attempts`, `max_attempts`, `corrections_applied`, `unresolved_findings`) em `write_report()`
- Alterar retorno de `run_remediation_loop()` para `dict` (como especificado) OU atualizar `write_report()` para receber os campos como parâmetros separados

**C2. Schema v2.0 de `write_report()`** (F2):
- Renomear `"project_name"` → `"project"` no payload JSON (L1148)
- Adicionar `"attempts"`, `"max_attempts"`, `"final_status"`, `"exit_code"` (vindos do loop — dependente de C1)
- Garantir `"corrections_applied": []` e `"unresolved_findings": []` sempre presentes (default vazio)
- `"deep_audit_summary"` e `"mermaid_gate"` devem ser sempre presentes (não condicionais)

**C3. `auto_correctable` em `_c12da_2`, `_c12da_3`, `_c12da_4`** (F3):

```python
# _c12da_2 (placeholder_unresolved) — L2994:
"auto_correctable": True,  # re-run build_summary_comprehensive.py resolve placeholders

# _c12da_3 (missing_artifact) — L3081:
"auto_correctable": _is_agent_resolvable_static(agent_id),  # True se agente disponível

# _c12da_4 (divergent_config) — L3152:
"auto_correctable": True,  # patch artifact-map.yaml é determinístico
```

### P1 — Correções Altas (necessárias para comportamento correto do dispatch)

**H1. Implementar `_invoke_agent()` ou documentar como scoped-out** (F4):
- Implementar `_invoke_agent(agent_id, project_name, timeout=300)` conforme plan.md §4.7
- OU: registrar explicitamente em spec §8/tasks.md que `_invoke_agent()` é deferido para uma feature posterior e documentar que `--force-promote` é o workaround recomendado enquanto isso
- Atualizar assinatura de `_dispatch_correction()` para receber `report: dict` e popular `report["corrections_applied"]` e `report["unresolved_findings"]`

**H2. Restringir C11.41 (`_c12_3`) a `<tbody>` ausente** (F5):

```python
# validate_summary.py L1048-1049:
# ANTES:
empty = [t for t in tables if re.search(r'<thead', t, re.IGNORECASE)
         and not re.search(r'<tbody[^>]*>\s*<tr', t, re.IGNORECASE)]

# DEPOIS (fix cirúrgico — adicionar exclusão explícita de tbody-presente):
empty = [t for t in tables if re.search(r'<thead', t, re.IGNORECASE)
         and not re.search(r'<tbody', t, re.IGNORECASE)  # tbody AUSENTE = C11.41's domain
         and not re.search(r'<tbody[^>]*>\s*<tr', t, re.IGNORECASE)]
```

### P2 — Correções Médias (recomendadas antes do merge; não bloqueiam o comportamento crítico)

**M1. Implementar `_write_validation_reports()` em `run_all()`** (F6):
- Escrever `validation-report.md` e `validation-report.json` usando `_format_md()` e `_format_json()` existentes
- Seguir pseudo-código plan.md §4.9

**M2. Alinhar `--force-promote` ao state machine** (A7.2):
- A condição `forced` deve verificar `final_status == "BLOCKED"` (do loop) e não `errors_after > 0` (do pipeline legado)
- O header de warning deve ser `"[WARN] FORCED PROMOTION — unresolved CRITICAL/HIGH findings remain"` (spec literal)

---

## Gostaria de sugestões de edições concretas para os top N achados?

Os achados P0 (C1, C2, C3) são os que bloqueiam o merge e têm correções de alta precisão. Posso gerar as edições específicas para esses três se confirmado.
