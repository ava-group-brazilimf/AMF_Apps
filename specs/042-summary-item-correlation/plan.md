# Agent Implementation Plan: ava-summary-validate (1.5.0→1.6.0) + ava-summary-remediation (1.6.0→1.7.0)

**Spec**: `specs/042-summary-item-correlation/spec.md`
**Feature**: Summary Item Correlation — C12.6/C12.7 Concrete Identification + `parser_gap`/`render_gap`
**Created**: 2026-08-19
**Status**: Approved

---

## Summary

| Field | Value |
|---|---|
| **Agent IDs** | `ava-summary-validate` (modify-existing → 1.6.0) · `ava-summary-remediation` (modify-existing → 1.7.0) |
| **Phase** | `F8 — Summary (cross-cutting)` |
| **Module** | `summary` (`src/modules/ava-fabric-agents/summary/`) |
| **Primary Requirement** | Refatorar `_c12da_6` e `_c12da_7` para que cada elemento HTML vazio passe por uma árvore de decisão de 6 passos (resolução de id, lookup no mapa de correlação, gate de fase, verificação de artefato, presença de `D.*`, check de render) e emita um finding concreto com `html_element_id`, `d_field`, `render_function` e `finding_type` real (`missing_artifact`, `parser_gap` ou `render_gap`) em vez de `"unidentified section"` / `"ava-summary"` genéricos. |
| **Technical Approach** | (1) Extrair STEP 1–6 para helper `_classify_empty_element()` compartilhado entre as duas funções; (2) Refatorar `_c12da_6`/`_c12da_7` para loop per-element com chamada ao helper; (3) Adicionar passagem de deduplicação em `_write_deep_audit_json()` antes da serialização; (4) Bump `schema_version` `"1.0"` → `"1.1"` (3 novos campos nullable); (5) Adicionar `phase8_deep_audit_triage()` em `remediate_summary.py` com branches f (parser_gap) e g (render_gap); (6) Estender `artifact-map.yaml` v1.0.1→v1.1.0 com novo top-level `html_element_correlation`; (7) Bump frontmatter dos dois agentes e `module.yaml`. |

---

## Constitution Check

### Constitution Gates

- [x] **Article I** — Nenhuma versão tecnológica nem id HTML hardcoded em Python; `html_element_correlation` é data-driven via `artifact-map.yaml`; nenhum `PHASE_KEY_MAP` novo introduzido
- [x] **Article II** — Frontmatter atualizado contém ONLY: `name`, `version`, `description` (PT + frases de ativação), `allowed-tools`; nomes `ava-summary-validate` e `ava-summary-remediation` seguem `^ava-[a-z0-9-]+$` (ambos existentes e registrados)
- [x] **Article III** — Fase F8/cross-cutting válida; ambos os agentes já registrados em `module.yaml v1.5.0`
- [x] **Article IV** — Nenhum novo agente (Category 4 N/A); apenas `version` bump em `module.yaml` (Category 3); sem mudança nos `agents[]` registrados
- [x] **Article V** — Corpo dos agentes `.md` em Português Brasileiro; código Python em inglês técnico
- [x] **Article VI** — 6 cenários BDD no spec §5 (S1 nominal, S2 root-cause classification, S3 deduplication, S4 fallback graceful, S5 phase gate, S6 retry budget)
- [x] **Article VII** — Read-only sobre HTML existente; nenhuma modificação no sub-pipeline de segurança; `artifact_path` de artefatos de segurança pode aparecer em findings mas apenas como metadata
- [x] **Article VIII** — N/A — agentes são prompts LLM; scripts Python usam `print()`/`stderr`; sem JSON schema pipeline
- [x] **Article IX** — N/A — arquivos `.md` são prompts LLM, não código com Clean Architecture
- [x] **Article X** — MINOR bump: `ava-summary-validate` 1.5.0→1.6.0 (nova lógica de correlação + 2 novos `finding_type` em `deep-audit-report.json`); `ava-summary-remediation` 1.6.0→1.7.0 (novos branches f/g no triage de deep-audit); `artifact-map.yaml` 1.0.1→1.1.0 (nova seção top-level)
- [x] **Article XI** — `ava-summary-validate` permanece interno-only (sem SKILL.md, sem alteração de dispatch); `ava-summary-remediation` mantém SKILL.md existente inalterado (routing não muda)

### Quality Gate Check

- [x] Zero marcadores `[NEEDS CLARIFICATION]` no spec (6 clarificações fechadas em 2026-08-19: Q1, Q2, Q3 rodada 1; Q1-R2 rodada 2; Q1, Q2 rodada 3 — ver spec.md §Clarifications para o histórico completo das 3 sessões)
- [x] Outputs seguem `projects/{project_name}/outputs/summary/`
- [x] Agentes downstream (`ava-summary`, `master-orchestrator`) confirmados existentes

---

## 1. Technical Context

| Dimension | Escolha | Fonte |
|---|---|---|
| Linguagem | Python 3 | Consistente com `validate_summary.py`, `remediate_summary.py`, `build_summary_comprehensive.py` |
| Parsing HTML (extração de id) | `re.search(r'id="([^"]+)"', element_html)` | Mesmo padrão já usado em `_extract_js_function()` e outras funções de `validate_summary.py`; `BeautifulSoup` proibido (spec 041 constraint herdada) |
| Presença de D.* | `_extract_json_slice(ctx.html, d_field)` (linha 115) | Função já existente; reutilizada por C12.1 e outros; retorna `None` em miss, raw string em hit |
| Carregamento do mapa | `_load_artifact_map()` (linha 2826) + `yaml.safe_load()` | Função já existente; reutilizada por C12.3/C12.4; lê `artifact-map.yaml` |
| Gate de fase | `_is_phase_done(ctx, phase_key: str)` (linha 2836) | Função já existente; aceita lowercase key (`"f1"`–`"f8"`); verificada via `PHASE_KEY_MAP` |
| Filesystem | `pathlib.Path` + `.exists()` / `.stat().st_size` | Padrão já usado em C12.3 para verificação de artefatos |
| Invocação do builder | `run_script("build_summary_comprehensive.py", project_name)` existente em `remediate_summary.py` | Sem novo flag `--verbose` — usar stdout+stderr já capturado via `capture_output=True` (ver AD-7) |
| YAML da correlation map | PyYAML via `yaml.safe_load()` já importado | Sem nova infra de parsing |

**Restrições de arquitetura herdadas de spec 041, reafirmadas em spec 042 §8:**
- `BeautifulSoup` proibido — apenas regex já presente no arquivo
- `html_element_correlation` é YAML simples consumido por `_load_artifact_map()` já existente — nenhum novo framework de correlação
- Nenhuma reimplementação de parser Python nem função JS de renderização
- `auto_correctable=false` para `parser_gap` e `render_gap` em v1 (capability flag, não garantia de dispatch)
- Sem suíte de testes automatizados em Python — validação via protocolo manual (seção 14)

---

## 2. Phase Placement

```
/ava-summary
  → build_summary_comprehensive.py       (único produtor HTML — invariante herdada)
  → validate_summary.py --deep           (acionado por summary-agent.md)
      → _c12da_6() [REFATORADA]          → per-element STEP 1–6
      → _c12da_7() [REFATORADA]          → per-element STEP 1–6
      → _write_deep_audit_json() [ESTENDIDA]
           → deduplication pass
           → schema_version "1.1"
           → deep-audit-report.json v1.1

/ava-summary-remediation (standalone, SKILL.md inalterado)
  → phase0_audit() ... phase7_revalidate()   [existentes, inalterados]
  → phase8_deep_audit_triage() [NOVO]
       → lê deep-audit-report.json (se presente)
       → caso f: parser_gap → captura output de build_summary_comprehensive.py
       → caso g: render_gap → registra como MANUAL sem dispatch
  → write_report() [ESTENDIDO]               → inclui unresolved_triage_items
```

**Quality gate**: `deep-audit-report.json.summary.promotable` (false se CRITICAL ou HIGH não-resolvido) + exit code 0/1 integrado ao CI existente.

---

## 3. Clean Architecture Alignment

N/A — Os agentes são arquivos de prompt LLM (`.md`). O código Python adicionado (`validate_summary.py`, `remediate_summary.py`) é infraestrutura de pipeline de validação, não camada arquitetural de aplicação gerada. Princípio IX não se aplica a scripts de qualidade.

---

## 4. Architecture Decisions

### AD-1 — Mudança de finding agregado para loop per-element em _c12da_6/_c12da_7

**Estado atual**: `_c12da_6` (linha 3258) e `_c12da_7` (linha 3334) cada uma produz **um único finding dict** cobrindo todos os elementos vazios encontrados. O finding usa `"section": "Table(s): heading1, heading2..."`, `"agent_responsible": "ava-summary"`, `"phase": "MULTIPLE"` — o que foi o problema reportado no nopcommerce-02-cli-ava (45 tabelas, 3 listas, todas "unidentified section"/"ava-summary").

**Decisão**: Refatorar ambas para loop per-element que acumula **zero ou mais findings individuais** (um por elemento classificado, ou nenhum se o elemento passa pelo gate de fase ou não tem id mapeado mas usa fallback). `Result.extra` é agora uma lista de N dicts em vez de lista com 1 dict. Isso já é suportado por `_write_deep_audit_json()` que itera `res.extra` element-by-element.

**Retrocompatibilidade**: Consumidores de `deep-audit-report.json` que filtram por `finding_type: "table_no_rows"` continuam recebendo esse tipo para elementos sem id no mapa (fallback). A diferença é granularidade: um finding por tabela vazia em vez de um finding para todas.

### AD-2 — Phase key format: uppercase no YAML → lowercase em _is_phase_done()

**Problema identificado**: `html_element_correlation` usa `phase: "F1"` / `phase: "F5"` (uppercase, convenção YAML/spec). `_is_phase_done(ctx, phase_key)` recebe lowercase via `PHASE_KEY_MAP = {"f1": [...], "f5": [...], ...}` (confirmado em linha 2840).

**Decisão**: No helper `_classify_empty_element()`, aplicar `.lower()` no callsite antes de chamar `_is_phase_done()`:

```python
# STEP 3 — dentro de _classify_empty_element():
if not _is_phase_done(ctx, corr["phase"].lower()):
    return None  # legitimately empty — phase not yet executed; no finding emitted
```

**Invariante**: Nunca alterar `PHASE_KEY_MAP` nem a assinatura de `_is_phase_done()`. A normalização fica exclusivamente no callsite do helper.

### AD-3 — Shared helper _classify_empty_element()

**Decisão**: Extrair a árvore de decisão STEP 1–6 para uma função auxiliar privada inserida imediatamente antes de `_c12da_6` no arquivo:

```python
def _classify_empty_element(
    ctx: Ctx,
    element_html: str,
    corr_map: dict,          # html_element_correlation section from artifact-map.yaml
    *,
    native_finding_type: str,    # "table_no_rows" (C12.6) ou "list_no_items" (C12.7)
    native_severity: str,        # "HIGH" (C12.6) ou "MEDIUM" (C12.7)
) -> Optional[dict]:
    """Execute STEP 1-6 decision tree for one empty element.

    Returns a finding dict (ready to append to Result.extra) or None.
    None means: no finding should be emitted (phase not done, or element
    is out-of-scope for a legitimate reason — never a silent error).
    The returned dict may be of finding_type:
      native_finding_type — when element id is absent or not in corr_map (fallback)
      "missing_artifact"  — STEP 4: artifact missing/empty on disk
      "parser_gap"        — STEP 5: artifact OK but D.* field empty in HTML
      "render_gap"        — STEP 6: D.* has data but DOM element still empty
    """
```

`_c12da_6` e `_c12da_7` chamam este helper dentro de seu loop per-element e acumulam os dicts não-None em `findings: list[dict]`.

**Razão**: Evitar duplicação da árvore de 6 passos em dois lugares. Qualquer extensão futura (STEP 7, novos tipos) é feita em um único lugar.

### AD-4 — Caching de html_element_correlation (Opção A: load por função)

**Problema**: `_load_artifact_map()` abre e parseia o YAML a cada chamada. `_c12da_6` e `_c12da_7` são chamadas sequencialmente em `_run_deep_checks()`.

**Opções consideradas**:
- **Opção A** (escolhida): Cada função chama `_load_artifact_map()` internamente uma vez no início e extrai `corr_map = amap.get("html_element_correlation", {})`, passando-o ao helper. Resulta em 2 cargas do YAML (uma por função check).
- **Opção B**: Pré-carregar em `_run_deep_checks()` e injetar via módulo ou closure — mais eficiente mas exige mudança na assinatura `Check` ou uso de variável de módulo.

**Decisão**: Opção A. Mantém assinatura `_c12da_N(ctx: Ctx) -> Result` inalterada (contrato do catálogo `DEEP_CHECKS`). Overhead de 2 cargas de YAML é negligível para um arquivo de ~30KB; não é hot path. Simplicidade > micro-otimização.

### AD-5 — Campos html_element_id/d_field/render_function: exclusivos de C12.6/C12.7

**Questão**: O spec §3.1 mostra os 3 novos campos no schema mas não declara explicitamente se todos os finding_types (C12.1–C12.5) devem incluí-los.

**Decisão**: Os 3 campos são **exclusivos de findings emitidos por `_classify_empty_element()`** (C12.6/C12.7). Findings de C12.1–C12.5 NÃO incluem esses campos. Consumidores tratam ausência como `null` (contrato de backward-compatibility do schema v1.1).

**Rationale**:
1. Spec §8: "No changes to C12.1–C12.5 — existing checks are untouched by this extension."
2. Backfill para C12.1–C12.5 ampliaria escopo e exigiria auditoria de cada check — fora do escopo desta spec.
3. Schema v1.1 é retrocompatível: consumidores v1.0 tratam qualquer campo desconhecido como optional.

### AD-6 — Deduplicação: localização, algoritmo e tag interna

**Decisão**: Implementar a passagem de deduplicação **dentro de `_write_deep_audit_json()`**, após acumular `all_findings` e ANTES de serializar:

**Algoritmo**:
```python
# 1. Coletar artifact_paths de missing_artifact de C12.3
#    (C12.3 está no índice 2 de DEEP_CHECKS, antes de C12.6/C12.7 nos índices 5/6)
c12_3_paths: set[str] = {
    f["artifact_path"]
    for f in all_findings
    if f.get("_src") == "C12.3"
    and f.get("finding_type") == "missing_artifact"
    and f.get("artifact_path") is not None
}

# 2. Remover missing_artifact duplicados de C12.6/C12.7
all_findings = [
    f for f in all_findings
    if not (
        f.get("_src") in ("C12.6", "C12.7")
        and f.get("finding_type") == "missing_artifact"
        and f.get("artifact_path") in c12_3_paths
    )
]

# 3. Remover tag _src antes de serializar (nunca aparece no JSON final)
for f in all_findings:
    f.pop("_src", None)
```

**Injeção da tag `_src`**: No loop de enriquecimento em `_write_deep_audit_json()`, ao construir `enriched = dict(finding)`, adicionar `enriched["_src"] = chk.id` (onde `chk.id` é `"C12.3"`, `"C12.6"` ou `"C12.7"`). A tag é removida antes de `json.dump()`.

**Garantia de ordenação**: `DEEP_CHECKS` posiciona C12.3 no índice 2, C12.6 no índice 5, C12.7 no índice 6. `_run_deep_checks()` itera em ordem. Portanto, todos os findings de C12.3 estão em `all_findings` antes dos de C12.6/C12.7 quando a deduplication pass executa. **Nenhuma reordenação de `DEEP_CHECKS` necessária.**

### AD-7 — `--verbose` não existe em build_summary_comprehensive.py: resolução sem nova flag

**Descoberta**: Grep confirmou que `build_summary_comprehensive.py` **não possui argumento `--verbose`**. O spec §4.5 e §7 mencionam "re-executar com `--verbose`" como ação de diagnóstico para `parser_gap`/`render_gap`.

**Decisão**: **NÃO adicionar `--verbose` a `build_summary_comprehensive.py` nesta feature.** Em vez disso, usar o stdout+stderr já capturado pelo `run_script()` existente (que usa `capture_output=True, text=True`, retornando `subprocess.CompletedProcess`). O "verbose log excerpt" em `suggested_fix` é extraído de `(result.stdout + result.stderr)[-2000:]`.

**Rationale**:
1. Adicionar `--verbose` a `build_summary_comprehensive.py` está fora do escopo desta feature (não consta na lista de "arquivos modificados" de spec §8).
2. O objetivo diagnóstico — fornecer output do builder para triage — é alcançado com o stdout+stderr existente.
3. Se o output for vazio (builder silencioso), `suggested_fix` inclui `"Sem output capturado — inspecionar build_summary_comprehensive.py manualmente."`.

**Impacto na documentação**: O texto de `suggested_fix` no código não menciona `--verbose`; em vez disso, descreve "re-run de build_summary_comprehensive.py com captura de output". Adicionar `--verbose` permanece como task de Category 3 deferred (seção 13).

### AD-8 — Localização das branches f/g em remediate_summary.py: nova phase8

**Estado atual confirmado**: `remediate_summary.py` (1025 linhas) **não possui** `_dispatch_correction()` nem `_IMPLEMENTED_DISPATCH_STRATEGIES` (grep confirmou zero matches). A estrutura existente é `phase0_audit()` → `phase7_revalidate()` + `write_report()` + `main()`.

**Decisão**: Adicionar uma nova função `phase8_deep_audit_triage(project_name: str, log: list[str]) -> list[dict]` chamada em `main()` APÓS `phase7_revalidate()` e ANTES de `write_report()`:

```python
def phase8_deep_audit_triage(project_name: str, log: list[str]) -> list[dict]:
    """Triage deep-audit findings that cannot be auto-corrected.

    Cases:
      f. parser_gap: artifact present, D.* empty in HTML.
         Action: re-run build_summary_comprehensive.py, capture output,
                 attach log excerpt to suggested_fix. No upstream agent dispatched.
      g. render_gap: D.* has data, DOM element still empty.
         Action: record as MANUAL. No dispatch whatsoever.

    Returns list of unresolved_triage_items for write_report().

    NOTE: Called directly from `main()` until `run_remediation_loop` (spec 041,
    `cat3-remediation-loop-041`) is implemented. At that point, this function
    becomes the non-dispatchable branch handler inside the loop — do NOT
    delete or replace; update the call site from `main()` to
    `run_remediation_loop`.
    """
    # Provenance: Clarification Q1+Q2, spec 042 rodada 3, 2026-08-19 —
    # see spec.md §4.5 "Calling-context and annotation requirement" for
    # the full decision record. The NOTE above (inside the docstring) is
    # copied verbatim into the real implementation — do not add anything
    # to it beyond what spec.md §4.5 / tasks.md task 3.1 specify.
    deep_audit_path = (
        BASE_DIR / f"projects/{project_name}/outputs/summary/deep-audit-report.json"
    )
    if not deep_audit_path.exists():
        log.append("## Fase 8 — Deep Audit Triage\nSkipped: deep-audit-report.json not found.")
        return []
    ...
```

**Por que não implementar o framework completo de spec 041 (`run_remediation_loop` + `_dispatch_correction`)**:
- `_dispatch_correction()` completo com `_IMPLEMENTED_DISPATCH_STRATEGIES` / `_is_agent_resolvable()` é escopo de tasks Category 3 **deferred da spec 041** (ainda não implementadas).
- Spec 042 §4.5 precisa apenas de branches f/g, sem o loop de retry de `MAX_REMEDIATION_ATTEMPTS`.
- `phase8_deep_audit_triage()` lightweight atende ao requirement sem adicionar escopo de spec 041.
- A invariante "parser_gap/render_gap não consomem MAX_REMEDIATION_ATTEMPTS" aplica-se ao loop futuro — em `phase8` (sem loop de retry), a invariante é satisfeita trivialmente.

---

## 5. Component Breakdown

### 5.1 `validate_summary.py` — Modificações (3 pontos de alteração)

| Componente | Localização atual | Tipo de mudança | Detalhe |
|---|---|---|---|
| **`_classify_empty_element()`** | **NOVA** — inserir antes de `_c12da_6` (após linha 3257) | Adição | Helper STEP 1–6; ver AD-3 para assinatura completa |
| **`_c12da_6()`** | linha 3258–3327 | Refatoração in-place | (a) `corr_map = _load_artifact_map().get("html_element_correlation", {})`; (b) loop per-table com regex `<table>`; (c) chamar `_classify_empty_element(..., native_finding_type="table_no_rows", native_severity="HIGH")`; (d) acumular em `findings: list[dict]`; (e) `Result(ok=not findings, ..., extra=findings)` |
| **`_c12da_7()`** | linha 3334–3371 | Refatoração in-place | Idêntico ao acima com `native_finding_type="list_no_items"`, `native_severity="MEDIUM"` |
| **`_write_deep_audit_json()`** | linha 3420 | Extensão | (a) Injetar `_src` tag em loop de enriquecimento; (b) deduplication pass (AD-6); (c) remover `_src` tags; (d) bump `"schema_version": "1.0"` → `"1.1"`; (e) atualizar docstring com 9 finding_types válidos |

### 5.2 `artifact-map.yaml` — Extensão

| Campo | De | Para |
|---|---|---|
| `version` | `"1.0.1"` | `"1.1.0"` |
| `html_element_correlation` | ausente | Novo top-level section com 10 entradas conforme spec §3.3 (tb-patterns, tb-risks, tb-rules, tb-reqs, tb-schema, tb-sps, tb-tobebc, tb-endpoints, tb-scen, tb-defects) |

### 5.3 `remediate_summary.py` — Adições (3 pontos de alteração)

| Componente | Localização | Tipo de mudança | Detalhe |
|---|---|---|---|
| **`phase8_deep_audit_triage()`** | **NOVA** — inserir antes de `write_report()` (após linha ~845) | Adição | Lê `deep-audit-report.json`; branch f (parser_gap) → `run_script("build_summary_comprehensive.py", project_name)` + captura stdout+stderr[-2000:]; branch g (render_gap) → MANUAL sem dispatch; retorna `list[dict]` de unresolved_triage_items |
| **`write_report()`** | linha 847 | Extensão | Aceitar parâmetro `triage_items: Optional[list[dict]] = None`; incluir seção `## Fase 8 — Deep Audit Triage` no MD e campo `"deep_audit_triage"` no JSON (se `triage_items` não vazio) |
| **`main()`** | linha 917 | Extensão | Chamar `triage_items = phase8_deep_audit_triage(project_name, log)` após `phase7_revalidate()`; passar para `write_report()` |

### 5.4 Agent `.md` files — Version bumps (sem mudança de comportamento além do frontmatter)

| Arquivo | Caminho | Mudança |
|---|---|---|
| `summary-validate-agent.md` | `src/modules/ava-fabric-agents/summary/agents/` | `version: "1.5.0"` → `"1.6.0"` · description substituída por spec §2.1 |
| `summary-remediation-agent.md` | `src/modules/ava-fabric-agents/summary/agents/` | `version: "1.6.0"` → `"1.7.0"` · description substituída por spec §2.2 |

### 5.5 `module.yaml` — Version bump (Category 3)

| Campo | De | Para | Nota |
|---|---|---|---|
| `version` | `"1.5.0"` | `"1.6.0"` | Apenas campo `version`; `agents[]` inalterado |

---

## 6. Data Flow

```
validate_summary.py --project X --deep
│
├─ _load_artifact_map()  ← 1x por _c12da_6 + 1x por _c12da_7
│    artifact-map.yaml v1.1.0
│    corr_map = amap["html_element_correlation"]  # dict de 10 entradas
│
├─ _c12da_6(ctx)
│    for each <table[^>]*>…</table> in ctx.html:
│      if <tbody> absent → skip (C11.41 domain, not C12.6)
│      if <tbody> has <tr> → skip (not empty)
│      else → _classify_empty_element(ctx, table_html, corr_map,
│                                     native_finding_type="table_no_rows",
│                                     native_severity="HIGH")
│               STEP 1: re.search(r'id="([^"]+)"', element_html) → id_value
│                        id_value None → fallback (heading heuristic, native_finding_type)
│               STEP 2: corr_map.get(id_value) → corr
│                        corr None → fallback + note "element id not in correlation map"
│               STEP 3: _is_phase_done(ctx, corr["phase"].lower()) → False → return None
│               STEP 4: (ctx.project_dir / corr["artifact_path"]).exists()
│                        absent/empty → check dedup flag → "missing_artifact" or suppress
│               STEP 5: _extract_json_slice(ctx.html, corr["d_field"])
│                        len ≤ 4 → "parser_gap" (HIGH, auto_correctable=False)
│               STEP 6: D.* has data, element still empty
│                        → "render_gap" (MEDIUM, auto_correctable=False)
│      findings.append(result)  # result is dict or None (skipped)
│    Result(ok=not findings, extra=findings)
│
├─ _c12da_7(ctx)  [same pattern; native_finding_type="list_no_items", "MEDIUM"]
│
└─ _write_deep_audit_json(ctx, deep_results)
      for (chk, res) in deep_results:
        for finding in res.extra:
          enriched = dict(finding)
          enriched["id"] = f"DA-{seq:03d}"
          enriched["_src"] = chk.id    ← tag interna (C12.3/C12.6/C12.7)
          all_findings.append(enriched)

      # Deduplication pass (AD-6)
      c12_3_paths = {f["artifact_path"] for f in all_findings
                     if f.get("_src")=="C12.3" and f.get("finding_type")=="missing_artifact"}
      all_findings = [f for f in all_findings
                      if not (f.get("_src") in ("C12.6","C12.7")
                              and f.get("finding_type")=="missing_artifact"
                              and f.get("artifact_path") in c12_3_paths)]

      for f in all_findings: f.pop("_src", None)   ← limpar antes de serializar

      report = {
        "schema_version": "1.1",   ← bumped de "1.0"
        ...
        "findings": all_findings   ← inclui html_element_id/d_field/render_function
      }                            #   em findings de C12.6/C12.7; ausentes em C12.1-C12.5
      json.dump(report, ...)
```

```
remediate_summary.py --project X
│
├─ phase0_audit() ... phase7_revalidate()   [inalterados]
│
├─ phase8_deep_audit_triage(project_name, log)   [NOVO]
│    deep_audit = json.load("deep-audit-report.json")
│    for finding in deep_audit["findings"]:
│      if finding["auto_correctable"]: continue  # tratado pelas fases anteriores
│      if finding["finding_type"] == "parser_gap":   ← branch f
│           result = run_script("build_summary_comprehensive.py", project_name)
│           excerpt = (result.stdout + result.stderr)[-2000:] or "Sem output capturado."
│           finding["suggested_fix"] += f"\n[Build output excerpt]:\n{excerpt}"
│           unresolved_triage_items.append(finding)
│      elif finding["finding_type"] == "render_gap":   ← branch g
│           # No dispatch, no rebuild — purely MANUAL
│           unresolved_triage_items.append(finding)
│    return unresolved_triage_items
│
└─ write_report(..., triage_items=triage_items)   [estendido]
     remediation-report.json schema v2.0 (inalterado)
     + campo "deep_audit_triage": [{...}, ...] se triage_items não vazio
```

---

## 7. module.yaml Impact

**Mudança**: Somente bump de `version` — nenhum novo agente registrado (Category 4 N/A).

```yaml
# src/modules/ava-fabric-agents/summary/module.yaml
name: summary
display_name: "AVA Fabric Summary"
version: "1.6.0"    # era "1.5.0" — Category 3 bump (spec 042)
```

Nenhum item em `agents[]`, `workflows[]`, `templates{}` ou `outputs{}` é alterado.

---

## 8. Observability & Trace Propagation

N/A — agentes são prompts LLM. Os scripts Python usam `print()`/`sys.stderr` para logging.

**Observabilidade de STEP 3 (phase gate silencioso)**: Quando `_is_phase_done()` retorna `False` e `_classify_empty_element()` retorna `None`, a função pode emitir para `sys.stderr`:

```python
print(
    f"[C12.6/DEBUG] Skipping element id='{id_value}' — "
    f"phase '{corr['phase']}' not yet executed.",
    file=sys.stderr,
)
```

Nunca para `deep-audit-report.json`. Consistente com o padrão de C12.1 (spec 041 §4.3: "phase.done==False → skip (legitimate)").

---

## 9. Schema Changes

| Artefato | Mudança | Descrição |
|---|---|---|
| `deep-audit-report.json` | schema `"1.0"` → **`"1.1"`** | Adiciona 3 campos opcionais (nullable) **exclusivos de findings C12.6/C12.7**: `html_element_id` (str\|null), `d_field` (str\|null), `render_function` (str\|null). Backward-compatible: consumidores v1.0 tratam ausência como null. |
| `artifact-map.yaml` | `"1.0.1"` → **`"1.1.0"`** | Novo top-level section `html_element_correlation` com 10 entradas auditadas (spec §3.3 + Clarificações Q2/Q3). MINOR bump pois é adição de nova seção. |
| `remediation-report.json` | **NO CHANGE** (schema v2.0 preservado) | `parser_gap`/`render_gap` aparecem em campo `deep_audit_triage[]` (novo campo additive no JSON); o schema v2.0 não define campos proibidos — extensão segura sem bump de versão. |
| `validation-report.json` | NO CHANGE | C1–C11 e C12.1–C12.5 inalterados; nenhum ID de check renumerado nesta feature |
| `agent-task.schema.json` | NO | Sem mudança |
| `agent-result.schema.json` | NO | Sem mudança |

**Finding_type enum atualizado** (9 valores válidos — docstring de `_write_deep_audit_json()` deve refletir):

```
empty_by_failure | missing_artifact | divergent_config | mermaid_error |
placeholder_unresolved | table_no_rows | list_no_items | parser_gap | render_gap
```

---

## 10. Risks and Mitigations

| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| Loop per-element aumenta número de findings vs. finding agregado anterior — CI que filtra por severidade pode receber mais achados HIGH após upgrade | ALTA | MÉDIO | CHANGELOG documenta "mais granular, não mais severo"; `schema_version` "1.1" sinaliza mudança de comportamento; consumers devem filtrar por `html_element_id` se precisam de granularidade |
| Phase key mismatch uppercase/lowercase entre YAML ("F5") e `_is_phase_done("f5")` — sem `.lower()`, STEP 3 nunca dispara, gerando falso-positivos | ALTA (bug latente, certo sem a correção) | ALTO | AD-2 resolve com `.lower()` no callsite; coberto por Scenario 5 de aceite |
| `_classify_empty_element()` acessa `ctx.project_dir` para verificar artefato — mesma acesso já usado em C12.3 sem falha | BAIXA | BAIXO | Nenhuma mitigação adicional necessária; C12.3 já valida esse caminho em produção |
| Deduplication pass remove finding de C12.6/7 indevidamente porque C12.3 emitiu para um `artifact_path` diferente mas mesmo nome de arquivo em path diferente | BAIXA | MÉDIO | Comparação usa `artifact_path` completo (string exata) — não basename; dois paths diferentes são dois registros distintos no set |
| `_classify_empty_element()` retorna `None` para elementos com id em corr_map mas fase não executada — comportamento silencioso pode confundir debugging | BAIXA | BAIXO | stderr observability (seção 8) emite debug line; nunca supressão silenciosa sem evidência |
| `build_summary_comprehensive.py` não possui `--verbose`; output capturado pode ser vazio para erros silenciosos | MÉDIA | BAIXO | AD-7: `suggested_fix` inclui "Sem output capturado — inspecionar manualmente" quando ambos stdout+stderr estão vazios |
| `phase8_deep_audit_triage()` executada quando `deep-audit-report.json` não existe (usuário rodou `remediate_summary.py` sem `--deep` prévio) | BAIXA | NENHUM | Guard explícito: `if not deep_audit_path.exists(): log.append("Fase 8 — skipped: sem deep-audit-report.json"); return []` |
| `remediation-report.json` schema v2.0 não define campos proibidos — campo `deep_audit_triage` adicionado sem bump de versão pode surpreender consumidores estáticos | MUITO BAIXA | BAIXO | Schema v2.0 é produzido pela equipe e consumido pela mesma equipe; nenhum consumer externo documentado |

---

## 11. Implementation Phases (groups para /speckit.tasks)

### Task Group 1 — artifact-map.yaml v1.1.0 [Pré-requisito para Group 2]

| Task | Arquivo | Detalhe |
|---|---|---|
| 1.1 | `summary/data/artifact-map.yaml` | Bump `version: "1.0.1"` → `"1.1.0"` |
| 1.2 | `summary/data/artifact-map.yaml` | Adicionar top-level section `html_element_correlation` com exatamente as 10 entradas de spec §3.3 (incluindo comentários de proveniência Q2/Q3) |

### Task Group 2 — validate_summary.py: core refactor [Depende de Group 1]

| Task | Arquivo | Detalhe |
|---|---|---|
| 2.1 | `validate_summary.py` | Inserir `_classify_empty_element()` antes de `_c12da_6` (após linha ~3257); implementar STEP 1–6 per AD-3; assinatura e docstring completas |
| 2.2 | `validate_summary.py` | Refatorar `_c12da_6()` in-place: loop per-table, chamada ao helper, acumular `findings`, retornar `Result(ok=not findings, extra=findings)` |
| 2.3 | `validate_summary.py` | Refatorar `_c12da_7()` in-place: idêntico ao 2.2 com `native_finding_type="list_no_items"`, `native_severity="MEDIUM"` |
| 2.4 | `validate_summary.py` | Estender `_write_deep_audit_json()`: (a) tag `_src` no loop de enriquecimento; (b) deduplication pass per AD-6; (c) cleanup de `_src` antes de dump; (d) bump `schema_version` `"1.0"` → `"1.1"`; (e) atualizar docstring com 9 finding_types |

### Task Group 3 — remediate_summary.py: phase8 triage [Depende de Group 2]

| Task | Arquivo | Detalhe |
|---|---|---|
| 3.1 | `remediate_summary.py` | Implementar `phase8_deep_audit_triage(project_name, log) -> list[dict]` per AD-8; guard de `deep-audit-report.json` ausente; branch f (parser_gap + captura output); branch g (render_gap + MANUAL); **(d) docstring DEVE incluir o parágrafo NOTE especificado em spec.md §4.5 "Required docstring annotation" — obrigatório, não opcional (Clarification Q2, rodada 3). Ver AD-8 acima para o texto exato já incorporado ao exemplo de código.** |
| 3.2 | `remediate_summary.py` | Estender `write_report()` com parâmetro `triage_items: Optional[list[dict]] = None`; seção `## Fase 8` no MD; campo `"deep_audit_triage"` no JSON |
| 3.3 | `remediate_summary.py` | Integrar chamada de `phase8` em `main()` após `phase7_revalidate()` |

### Task Group 4 — Version bumps e frontmatter [Paralelo, sem dependência]

| Task | Arquivo | Detalhe |
|---|---|---|
| 4.1 | `agents/summary-validate-agent.md` | `version: "1.5.0"` → `"1.6.0"` · description atualizada conforme spec §2.1 |
| 4.2 | `agents/summary-remediation-agent.md` | `version: "1.6.0"` → `"1.7.0"` · description atualizada conforme spec §2.2 |
| 4.3 | `module.yaml` | `version: "1.5.0"` → `"1.6.0"` |

### Task Group 5 — Validação Manual [Depende de Groups 1–4]

| Task | Detalhe |
|---|---|
| 5.1 | Protocolo de validação manual (seção 14 abaixo) sobre `nopcommerce-02-cli-ava` ou projeto equivalente |

---

## 12. Complexity Tracking

| Gate | Situação | Justificativa | Controles |
|---|---|---|---|
| Mudança de finding agregado para per-element (AD-1) | Breaking change comportamental em `deep-audit-report.json`: número de findings por run pode aumentar | Comportamento anterior era impreciso (agrupamento arbitrário); mudança é melhoria documentada | CHANGELOG entry + `schema_version` bump "1.1" sinaliza mudança; spec §10 Success Criteria cobrem |
| Phase key uppercase/lowercase mismatch (AD-2) | Bug latente no STEP 3 sem `.lower()` — corrigido no callsite | Invariante documentada como AD-2; coberta por Scenario 5 | Code review confirma conversão present em `_classify_empty_element()` |
| `--verbose` ausente em `build_summary_comprehensive.py` (AD-7) | Spec descreve `--verbose` mas flag não existe no código | AD-7 resolve usando stdout+stderr capturado; sem nova dependência de argparse | Deferred como Category 3 task; comportamento documentado no CHANGELOG |
| `_dispatch_correction()` / loop de spec 041 não implementado (AD-8) | 042 adiciona branches f/g sem o framework completo de loop de retentativa | `phase8_deep_audit_triage()` lightweight é suficiente para os dois novos casos; framework completo permanece como Category 3 deferred de spec 041 | Scope-limiting decision documentada no CHANGELOG |
| Deduplicação por `artifact_path` pode suprimir finding de C12.6/7 quando C12.3 não o cobriu | Improvável por design (C12.3 cobre todos os artefatos registrados no manifesto) | Algoritmo usa `_src` tag para garantir que apenas C12.3 findings bloqueiam duplicatas; se C12.3 não emitiu, nada é suprimido | Unit test manual: verificar com artefato ausente não coberto por C12.3 |

---

## 13. Category 3 Tasks (para /speckit.tasks)

| Task ID sugerido | Descrição | Artefato |
|---|---|---|
| `cat3-module-version-bump-042` | Bump `module.yaml` version `"1.5.0"` → `"1.6.0"` | `summary/module.yaml` |
| `cat3-changelog-entry-042` | Adicionar entrada de CHANGELOG para 042: novos finding_types, schema v1.1, mudança de agregado → per-element em C12.6/C12.7, resolução de `--verbose` sem nova flag, deduplication pass | `CHANGELOG.md` |
| `cat3-verbose-flag-bsc` | (Deferred, fora do escopo de 042) Adicionar `--verbose` a `build_summary_comprehensive.py` para output por função de parser — habilita diagnóstico mais preciso de `parser_gap` | `utils/build_summary_comprehensive.py` |
| `cat3-remediation-loop-041` | (Deferred, spec 041 Category 3 pendente) Implementar `run_remediation_loop()` + `_dispatch_correction()` com `_IMPLEMENTED_DISPATCH_STRATEGIES` / `_is_agent_resolvable()` + `--force-promote` para integrar `phase8_deep_audit_triage()` ao loop de retentativa com `MAX_REMEDIATION_ATTEMPTS` | `utils/remediate_summary.py` |

---

## 14. Validation Protocol (Manual — sem suíte automatizada, per spec §8)

Protocolo idêntico ao da spec 041 task 5.1, estendido para os novos casos:

### Pré-requisito
Projeto com pelo menos F1 executado e `AVA-FABRIC-SUMMARY-*.html` gerado em `outputs/summary/`.

### Protocolo

**P1 — Nominal (Scenario 1)**: Projeto com tabelas/listas com ids mapeados em `html_element_correlation`:
1. `python validate_summary.py --project {NOME} --deep`
2. Verificar `deep-audit-report.json`:
   - `"schema_version": "1.1"` ✓
   - Findings com `html_element_id` ≠ null para elementos com id no mapa ✓
   - Zero findings com `"section": "unidentified section"` para elementos mapeados ✓
   - Zero findings com `"agent_responsible": "ava-summary"` para elementos mapeados ✓

**P2 — Deduplicação (Scenario 3)**: Remover um artefato (ex.: `scenario-register.json`) e regenerar HTML:
1. Confirmar que `deep-audit-report.json` contém exatamente UM finding com `artifact_path` do artefato removido
2. Confirmar que nenhum dois findings têm `artifact_path` idêntico E `finding_type: "missing_artifact"` ✓

**P3 — Phase gate (Scenario 5)**: Projeto onde F5 não foi executado:
1. `python validate_summary.py --project {NOME} --deep`
2. Confirmar que `deep-audit-report.json.findings` contém zero entradas com `"html_element_id": "tb-scen"` ou `"html_element_id": "tb-defects"` ✓
3. Confirmar que `summary.promotable` não está afetado por esses elementos ✓

**P4 — parser_gap (Scenario 2a)**: Injetar `D.scenarios: []` manualmente no HTML (mock):
1. `python validate_summary.py --project {NOME} --deep`
2. Confirmar finding `"finding_type": "parser_gap"`, `"severity": "HIGH"`, `suggested_fix` menciona `D.scenarios` ✓

**P5 — render_gap (Scenario 2b)**: `D.scenarios` com dados mas `<tbody id="tb-scen">` vazio no HTML:
1. `python validate_summary.py --project {NOME} --deep`
2. Confirmar finding `"finding_type": "render_gap"`, `"severity": "MEDIUM"`, `suggested_fix` menciona `renderScenarios()` ✓

**P6 — Fallback gracioso (Scenario 4)**: Elemento com `id="tb-nonexistent"` não presente no mapa:
1. Confirmar finding `"finding_type": "table_no_rows"`, `"html_element_id": "tb-nonexistent"`, `"d_field": null`, nota "element id not in correlation map" ✓

**P7 — Remediation triage (Scenario 6)**: `deep-audit-report.json` com `parser_gap`:
1. `python remediate_summary.py --project {NOME}`
2. Confirmar que `phase8_deep_audit_triage` processa sem dispatch de agente upstream ✓
3. Confirmar `remediation-report.json` contém `"deep_audit_triage": [...]` com os itens não resolvidos ✓
4. Confirmar que `final_status: BLOCKED` (≥1 HIGH não resolvido) se `parser_gap` é o único finding ✓
