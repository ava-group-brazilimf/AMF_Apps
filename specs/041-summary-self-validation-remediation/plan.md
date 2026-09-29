# Agent Implementation Plan: ava-summary-validate (1.4.2→1.5.0) + ava-summary-remediation (1.5.0→1.6.0)

**Spec**: `specs/041-summary-self-validation-remediation/spec.md`
**Feature**: Summary Self-Validation & Remediation — Deep Item Audit (C12) + Remediation Loop
**Created**: 2026-08-18
**Status**: Approved

---

## Summary

| Field | Value |
|---|---|
| **Agent IDs** | `ava-summary-validate` (modify-existing → 1.5.0) · `ava-summary-remediation` (modify-existing → 1.6.0) |
| **Phase** | `F8 — Summary (cross-cutting)` |
| **Module** | `summary` (`src/modules/ava-fabric-agents/summary/`) |
| **Primary Requirement** | Após o HTML ser gerado por `build_summary_comprehensive.py`, executar auditoria item a item (C12.1–C12.7) de cada seção/card/tabela/diagrama (F1–F8), distinguir vazio-legítimo de falha-de-geração, verificar artefatos contra o manifesto, aplicar correções automáticas em loop e regenerar até zero CRITICAL/HIGH ou esgotar `MAX_REMEDIATION_ATTEMPTS`. |
| **Technical Approach** | (1) Adicionar `--deep` retrocompatível a `validate_summary.py` que ativa DEEP_CHECKS (C12.1–C12.7) e emite `deep-audit-report.json`; (2) Estender loop em `remediate_summary.py` para consumir `deep-audit-report.json`, gerir os dois caminhos de falha de dispatch e implementar `--force-promote`; (3) Completar `artifact-map.yaml` com as fases `f3_prototype` e `f8_summary`; (4) Bump `module.yaml` 1.4.1 → 1.5.0. |

---

## Constitution Check

### Constitution Gates

- [x] **Article I** — Nenhuma versão tecnológica hardcoded; `MAX_REMEDIATION_ATTEMPTS` resolvido em cascata de `project-config.yaml` → `reference-architecture.yaml` → fallback 3
- [x] **Article II** — Frontmatter atualizado contém ONLY: `name`, `version`, `description` (PT + frases de ativação), `allowed-tools`; nomes seguem `^ava-[a-z0-9-]+$`
- [x] **Article III** — Fase F8/cross-cutting válida; ambos os agentes já registrados em `module.yaml`
- [x] **Article IV** — Nenhum novo agente registrado (Category 4 N/A); apenas `version` bump em `module.yaml` (Category 3 task)
- [x] **Article V** — Corpo dos agentes em Português Brasileiro; código Python em inglês técnico
- [x] **Article VI** — 5 cenários BDD no spec (S1 nominal, S2 remediação auto, S3 legítimo-vazio, S4 BLOCKED+force-promote, S5 Mermaid)
- [x] **Article VII** — Gate é read-only sobre HTML existente; dispatch de agentes via `module.yaml` trigger codes já registrados; nenhum impacto no sub-pipeline de segurança
- [x] **Article VIII** — N/A — agentes não usam JSON schema pipeline
- [x] **Article IX** — N/A — arquivos `.md` são prompts LLM, não código com Clean Architecture
- [x] **Article X** — MINOR bump: `ava-summary-validate` 1.4.2 → 1.5.0 (nova categoria C12 + novo output `deep-audit-report.json`); `ava-summary-remediation` 1.5.0 → 1.6.0 (loop estruturado + `--force-promote`)
- [x] **Article XI** — `ava-summary-validate` permanece interno (sem SKILL.md); `ava-summary-remediation` mantém SKILL.md existente inalterado

### Quality Gate Check

- [x] Zero marcadores `[NEEDS CLARIFICATION]` no spec (5 clarificações fechadas em 2026-08-18)
- [x] Outputs seguem `projects/{project_name}/outputs/summary/`
- [x] Agente downstream (`ava-summary`, `master-orchestrator`) confirmados existentes

---

## 1. Technical Context

| Dimension | Escolha | Fonte |
|---|---|---|
| Linguagem | Python 3 | Consistente com `validate_summary.py`, `remediate_summary.py`, `build_summary_comprehensive.py` |
| Parsing HTML | `re` + `_extract_json_slice()` já existente em `validate_summary.py` | Padrão já usado para extrair `D.*` do bloco `const D = {…}` |
| Parsing YAML | `yaml.safe_load()` (PyYAML, já usado em `_load_ctx()`) | `artifact-map.yaml` e `project-config.yaml` |
| Playwright gate | `mermaid_playwright_gate.py` (spec 040) — importado in-process | `run_playwright_mermaid_gate(html_path) -> MermaidGateResult` |
| Filesystem | `pathlib.Path` + `.glob()` | Checagem de existência/tamanho de artefatos |
| Config cascade | `yaml.safe_load` de `project-config.yaml` → `reference-architecture.yaml` → fallback `3` | Resolução de `MAX_REMEDIATION_ATTEMPTS` |
| Relatórios novos | `deep-audit-report.json` (schema v1.0); `remediation-report.json` schema v2.0 | spec §3.1 e §3.2 |

**Restrições de arquitetura herdadas**:
- Nenhuma síntese de HTML fora de `build_summary_comprehensive.py`
- Nenhuma reimplementação de lógica Playwright/Mermaid (consumir `mermaid_playwright_gate.py` as-is)
- `--deep` 100% retrocompatível (sem a flag: apenas C1–C11, mesmo exit-code semântico)

---

## 2. Phase Placement

```
/ava-summary
  → build_summary_comprehensive.py     (único produtor HTML)
  → validate_summary.py --deep         [NOVO HOOK em summary-agent.md]
      → se findings → remediate_summary.py   (loop)
          → deep audit iteration N
          → build_summary_comprehensive.py (rebuild)
          → validate_summary.py --deep (re-check)
          → BREAK se CLEAN ou PARTIAL
          → BLOCKED após MAX_REMEDIATION_ATTEMPTS

/ava-summary-remediation (standalone)
  → loop principal já é o fluxo de remediação
```

**Quality gate**: `deep-audit-report.json.summary.promotable` + exit code 0/1 integrado ao CI existente.

---

## 3. Clean Architecture Alignment

N/A — Os agentes são arquivos de prompt LLM (`.md`). O código Python adicionado é infraestrutura de pipeline, não camada arquitetural de aplicação gerada.

---

## 4. Decisões de Arquitetura

### 4.1 — Localização do Código C12 (Deep Auditor)

**Decisão**: Funções inline `_c12da_1()` a `_c12da_7()` em `validate_summary.py`, registradas em lista separada `DEEP_CHECKS: list[Check]`.

**Rationale**: O arquivo inteiro segue o padrão flat-function sem sub-módulos. Não existe diretório `checks/suites/` no projeto — criar um violaria o padrão existente e introduziria complexidade de import desnecessária. A separação em `DEEP_CHECKS` é suficiente para retrocompatibilidade sem alterar a estrutura física do arquivo.

**Convenção de nomes**: Os IDs de check usados no catálogo são `"C12.1"` a `"C12.7"` (com categoria `"Deep Item Audit"`), mas as funções internas usam sufixo `_da_` para não colidir com as existentes `_c12_1()`, `_c12_2()`, `_c12_3()` (ver §4.2).

**Assinatura de entrada**: `_c12da_N(ctx: Ctx) -> Result` — idêntico a todos os outros checks.

**Registro no reporter**: `DEEP_CHECKS` é uma lista `list[Check]` que usa a mesma dataclass `Check`. Quando `--deep` está ativo, `_run_checks_deep(ctx)` chama `CHECKS + DEEP_CHECKS` e retorna os resultados; o `_format_json()` e `_format_md()` existentes operam sobre a lista resultante sem alteração.

**Emissão de `deep-audit-report.json`**: Uma nova função `_format_deep_audit_json()` produz o schema estendido (com `phase`, `section`, `agent_responsible`, `finding_type`, `auto_correctable`, `suggested_fix`) a partir dos resultados dos DEEP_CHECKS. O arquivo é escrito em paralelo ao `validation-report.json` standard.

### 4.2 — Resolução da Colisão de Namespace C12

**Problema**: `validate_summary.py` já possui `_c12_1()`, `_c12_2()`, `_c12_3()` registrados como `Check("C12.1", "Artifact Integrity", …)` no catálogo CHECKS (linhas 2770-2782). Esses checks verificam `[INCOMPLETE]`, `[ARTIFACT-MISSING]` e `<table>` vazia. A nova spec usa C12.1–C12.7 para o Deep Item Audit, criando colisão de ID.

**Decisão**: Renumerar os checks existentes:

| ID atual | Novo ID | Função | Descrição |
|---|---|---|---|
| `C12.1` | `C11.39` | `_c12_1` → `_c11_39` (rename apenas no catálogo) | No [INCOMPLETE] placeholder |
| `C12.2` | `C11.40` | `_c12_2` → `_c11_40` | No [ARTIFACT-MISSING] marker |
| `C12.3` | `C11.41` | `_c12_3` → `_c11_41` | No empty thead-only <table> |

A renumeração é feita apenas no string ID da instância `Check(…)` no catálogo CHECKS — as funções Python subjacentes não precisam ser renomeadas (são privadas). O bloco C13.x (Blueprint Compatibility + Mermaid Gate) permanece inalterado.

**Retrocompatibilidade de relatórios**: Qualquer CI consumindo `validation-report.json` que filtre por `id: "C12.1"`, `"C12.2"`, `"C12.3"` precisará ser atualizado para os novos IDs. Esse efeito é documentado no CHANGELOG. O `deep-audit-report.json` é um artefato novo sem clientes pré-existentes.

**Deduplicação de escopo (Opção C — decidido 2026-08-18)**: A renumeração expôs sobreposição funcional entre C11.39/C11.40/C11.41 (legados) e os novos C12.2/C12.6. A resolução adotada é **restrição de escopo** (Opção C), sem supressão condicional e sem campo `duplicate_of`:

| Regra legada | Escopo exclusivo (após restrição) | Regra nova | Escopo exclusivo (após restrição) |
|---|---|---|---|
| C11.39 | Token `[INCOMPLETE]` — único responsável; C12.2 nunca cobre esse token | C12.2 | Tokens `{{X}}`, `[NEEDS CLARIFICATION]`, `AG-NN` apenas |
| C11.40 | Token `[ARTIFACT-MISSING]` — único responsável; C12.2 nunca cobre esse token | C12.2 | (idem acima) |
| C11.41 | Tabelas **sem elemento `<tbody>`** (template estruturalmente incompleto) | C12.6 | Tabelas **com `<tbody>` mas zero `<tr>`** E fase `done == true` (falha de conteúdo) |

Resultado: CI sem `--deep` → comportamento de C11.39-41 inalterado. Modo `--deep` → zero duplicatas funcionais entre os dois conjuntos de regras. Loop de remediação → não afetado (lê somente `deep-audit-report.json` que contém apenas C12.x).

### 4.3 — Parsing HTML para C12.1/C12.2/C12.6/C12.7

**Localização por fase/seção**: O template HTML usa `data-phase-id="f1"` a `data-phase-id="f7"` nas divs de grupo de navegação e IDs de seção como `id="s-f1-arch"`, `id="s-f2-tobe"`, etc. O deep auditor extrai fatias do HTML por seção usando `re.search(r'id="s-f{N}-[a-z]+"[\s\S]*?(?=id="s-f|</main>)', html)` para restringir checks a uma seção antes de varrer cards/tabelas/listas.

**Leitura de `D.agentStatus[phase].done`**: Já disponível em `ctx.D_agentStatus` (extraído por `_load_js_data()` via `_extract_json_slice(h, 'agentStatus')`). Para C12.1/C12.6/C12.7, o auditor lê `ctx.D_agentStatus.get(phase_key, {}).get("done", False)` antes de classificar um item vazio como falha ou legítimo.

**Mapeamento phase_key → prefixo HTML**: Usar mapeamento interno consistente com o template:

```python
PHASE_KEY_MAP = {
    "f1": ["ava-asis"],
    "f2": ["ava-tobe"],
    "f3": ["ava-prototype"],
    "f4": ["ava-stack"],
    "f5": ["ava-qa"],
    "f6": ["ava-devops"],
    "f7": ["ava-deliverable"],
    "f8": ["ava-summary"],
}
```

**KPI tile vazio (C12.1)**: Varrer o bloco `D.kpis` via `_extract_json_slice(ctx.html, 'kpis')`, iterar itens, para cada item com `v == "0"` ou `v == "N/E"` ou `v == ""` verificar se o artefato fonte existe e tem > 100 bytes. Se sim e a fase está `done`: C12.1 HIGH.

**Placeholder não resolvido (C12.2)**: Regex `r'\{\{[A-Z0-9_]+\}\}|\[NEEDS CLARIFICATION\]|AG-\d+'` sobre o HTML fora de blocos `<script>`. **Nota**: `[INCOMPLETE]` e `[ARTIFACT-MISSING]` foram removidos deste regex — são responsabilidade exclusiva de C11.39 e C11.40 respectivamente (deduplicação Opção C, 2026-08-18). Severidade CRITICAL se o token aparece no título, nome-do-projeto ou bloco KPI; HIGH em qualquer outro local.

**Tabela vazia (C12.6)**: Para cada `<table id="tb-…">` no HTML onde a fase correspondente está `done` (`D.agentStatus[phase].done == true`): verificar se o elemento `<tbody>` **existe** e tem zero `<tr>` elementos internos → HIGH. **Distinção estrutural de C11.41**: C11.41 verifica tabelas sem `<tbody>` algum (falha estrutural do template); C12.6 verifica tabelas com `<tbody>` presente mas sem linhas de dados (falha de conteúdo em fase concluída). Um `<table>` sem `<tbody>` não dispara C12.6; um `<table>` com `<tbody>` vazio não dispara C11.41 — escopos mutuamente exclusivos.

**Lista vazia (C12.7)**: Para cada `<ul>/<ol>` dentro de seções de fases `done`, verificar se há zero `<li>`: MEDIUM (não HIGH, pois listas podem ser intencionalmente curtas).

### 4.4 — Integração com `mermaid_playwright_gate.py` (C12.5)

**Contrato exato de chamada**:

```python
# Em validate_summary.py, função _c12da_5(ctx: Ctx) -> Result
from mermaid_playwright_gate import run_playwright_mermaid_gate, MermaidGateResult

def _c12da_5(ctx: Ctx) -> Result:
    try:
        gate_result: MermaidGateResult = run_playwright_mermaid_gate(
            html_path=ctx.html_path,
            # guardrails_path usa o default (_DEFAULT_GUARDRAILS_PATH no módulo)
            # max_attempts usa default (3)
            # timeout_ms usa default (15_000)
        )
    except Exception as e:
        return Result(False, f"Playwright gate crash: {e!r}")
    failed = [d for d in gate_result.diagrams if d.status not in ("PASS", "FIXED", "EMPTY", "SKIPPED")]
    ok = not failed
    return Result(ok, f"all {gate_result.total_diagrams} diagrams pass" if ok
                  else f"{len(failed)} diagram(s) failed: {[d.diagram_id for d in failed[:3]]}")
```

**Mapeamento `DiagramResult` → finding C12.5**:

| `DiagramResult.status` | Severidade C12.5 | `finding_type` |
|---|---|---|
| `FAIL_UNRESOLVED` | CRITICAL (se seção F1-F2) / HIGH (demais) | `mermaid_error` |
| `TIMEOUT` | MEDIUM | `mermaid_error` |
| `PASS` / `FIXED` / `EMPTY` | — (não é finding) | — |

**`_format_deep_audit_json()`**: Para cada `DiagramResult` com status `FAIL_UNRESOLVED`/`TIMEOUT`, emite finding com:

```json
{
  "id": "DA-NNN",
  "severity": "HIGH",
  "phase": "F1",
  "section": "s-f1-arch",
  "agent_responsible": "mermaid_playwright_gate",
  "artifact_path": null,
  "finding_type": "mermaid_error",
  "detail": "<DiagramResult.error_message>",
  "root_cause": "Playwright rendering failure — diagram_id: <DiagramResult.diagram_id>",
  "auto_correctable": true,
  "suggested_fix": "Invoke mermaid_playwright_gate.py auto-fix (GR-001..GR-012)"
}
```

**Nota**: C12.5 SOMENTE quando `--deep` está ativo. C13.2 (existente) continua lendo `mermaid-validation-report.json` estático para o modo C1–C11 sem `--deep`.

### 4.5 — Cross-Reference com `artifact-map.yaml` (C12.3 / C12.4)

**Carregamento**:

```python
_ARTIFACT_MAP_PATH = Path(__file__).resolve().parent.parent / "data" / "artifact-map.yaml"

def _load_artifact_map() -> dict:
    if yaml is None:
        return {}
    try:
        return yaml.safe_load(_ARTIFACT_MAP_PATH.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}
```

**C12.3 — `missing_artifact`**: Para cada fase `fN_*` no manifesto, para cada agente, para cada artefato em `outputs_map` ou `primary_output`: construir path `outputs_dir / relative_path.replace("project/outputs/", "")`, verificar `.exists()` e `.stat().st_size > 0`. Se `D.agentStatus[phase_key]["done"] == True` e arquivo ausente/zero: finding CRITICAL (se fase bloqueante) ou HIGH.

**C12.4 — `divergent_config`**: Comparar `artifact-path` declarado no manifesto com o path que `build_summary_comprehensive.py` realmente lê (verificado via análise estática do builder source — `_read_builder_source()` já disponível). Discrepâncias → MEDIUM finding.

**Adições obrigatórias ao `artifact-map.yaml`** (Category 3 tasks — não implementar agora):
- `f3_prototype`: agente `ava-prototype`, primary_output: `project/outputs/tobe/prototype/index.html`, seção HTML: `s-f3-proto`
- `f8_summary`: agente `ava-summary`, outputs: `AVA-FABRIC-SUMMARY-*.html`, `validation-report.md`, `validation-report.json`, `deep-audit-report.json`, `remediation-report.json`

### 4.6 — Loop de Remediação em `remediate_summary.py`

**Assinatura do loop** (pseudo-código implementável):

```python
def run_remediation_loop(project_name: str, force_promote: bool = False) -> dict:
    max_attempts = _resolve_max_attempts(project_name)   # cascade config
    report = {"attempts": 0, "corrections_applied": [], "unresolved_findings": [],
              "forced": False, "mermaid_gate": {...}}
    
    for attempt in range(1, max_attempts + 1):
        report["attempts"] = attempt
        deep_audit = _run_deep_audit(project_name)       # validate_summary.py --deep
        write_deep_audit_json(project_name, deep_audit)
        
        critical_high = [f for f in deep_audit["findings"]
                         if f["severity"] in ("CRITICAL", "HIGH")]
        if not critical_high:
            report["final_status"] = "CLEAN" if not deep_audit["findings"] else "PARTIAL"
            report["exit_code"] = 0
            break
        
        for finding in [f for f in critical_high if f["auto_correctable"]]:
            _dispatch_correction(finding, project_name, report)  # ver §4.7
        
        _rebuild_html(project_name)   # build_summary_comprehensive.py
    else:
        # Loop exauriu tentativas
        report["final_status"] = "BLOCKED"
        report["exit_code"] = 1
        report["unresolved_findings"] = [f for f in deep_audit["findings"]
                                          if f["severity"] in ("CRITICAL", "HIGH")]
    
    if force_promote and report["final_status"] == "BLOCKED":
        report["forced"] = True
        # exit_code permanece 1
        print("[WARN] FORCED PROMOTION — unresolved CRITICAL/HIGH findings remain")
        for f in report["unresolved_findings"]:
            print(f"  [{f['severity']}] {f['id']}: {f['detail']}")
    
    _write_remediation_report(project_name, report)
    return report
```

**`--force-promote` no argparse**:

```python
parser.add_argument("--force-promote", action="store_true",
    help="Deliver HTML even when final_status is BLOCKED. "
         "Sets 'forced': true in remediation-report.json. Exit code stays 1.")
```

### 4.7 — Detecção de Falha de Dispatch (Transiente vs. Estrutural)

**Pre-check estrutural** (ANTES de tentar invocar):

```python
def _is_agent_resolvable(agent_id: str) -> bool:
    """Check if agent_id is registered in its module.yaml."""
    # Procura em todos os module.yaml de ava-fabric-agents/
    for module_yaml in Path("src/modules/ava-fabric-agents").glob("*/module.yaml"):
        try:
            data = yaml.safe_load(module_yaml.read_text(encoding="utf-8")) or {}
            if any(a.get("id") == agent_id for a in data.get("agents", [])):
                return True
        except Exception:
            continue
    return False
```

**Lógica de dispatch com bifurcação**:

```python
def _dispatch_correction(finding: dict, project_name: str, report: dict):
    agent_id = finding["agent_responsible"]
    
    # — Falha estrutural —
    if not _is_agent_resolvable(agent_id):
        finding["auto_correctable"] = False
        report["unresolved_findings"].append({
            **finding,
            "dispatch_error": {
                "type": "structural",
                "reason": f"agent_id '{agent_id}' not found in any module.yaml",
                "suggested_fix": f"Register '{agent_id}' in the appropriate module.yaml"
            }
        })
        return  # NÃO consome attempt para este finding
    
    # — Tentativa de dispatch real —
    try:
        result = _invoke_agent(agent_id, project_name, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"exit code {result.returncode}: {result.stderr[:200]}")
        report["corrections_applied"].append({"finding_id": finding["id"], "agent": agent_id})
    except (TimeoutError, RuntimeError) as e:
        # — Falha transiente — consome attempt, continua loop
        report["unresolved_findings"].append({
            **finding,
            "dispatch_error": {"type": "transient", "reason": str(e)}
        })
```

### 4.8 — Resolução de `MAX_REMEDIATION_ATTEMPTS`

```python
def _resolve_max_attempts(project_name: str) -> int:
    # 1. project-config.yaml
    cfg_path = Path(f"projects/{project_name}/context/project-config.yaml")
    if cfg_path.exists() and yaml is not None:
        try:
            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            v = (cfg.get("summary") or {}).get("max_remediation_attempts")
            if isinstance(v, int) and v > 0:
                return v
        except Exception:
            pass
    # 2. reference-architecture.yaml
    ref_path = Path("src/shared/data/reference-architecture.yaml")
    if ref_path.exists() and yaml is not None:
        try:
            ref = yaml.safe_load(ref_path.read_text(encoding="utf-8")) or {}
            v = (ref.get("summary") or {}).get("max_remediation_attempts")
            if isinstance(v, int) and v > 0:
                return v
        except Exception:
            pass
    # 3. Hard fallback
    return 3
```

### 4.9 — Modificações ao `validate_summary.py`

**Argparse** (retrocompatível — `--deep` é opcional):

```python
parser.add_argument("--deep", action="store_true",
    help="Activate C12 Deep Item Audit rules. Without this flag, "
         "only C1–C11 rules run (backward-compatible).")
```

**Fluxo `run_all()`** atualizado:

```python
def run_all(project: str, auto_fix: bool = False, deep: bool = False, …) -> int:
    ctx = _load_ctx(project)
    results = _run_checks(ctx)          # CHECKS (C1-C11 + renumerado C11.39-C11.41 + C13.x)
    
    if deep:
        deep_results = _run_deep_checks(ctx)    # DEEP_CHECKS (C12.1-C12.7)
        _write_deep_audit_json(ctx, deep_results)
        results = results + deep_results        # anexar para o relatório unificado
    
    _write_validation_reports(ctx, results)
    errors = [r for c, r in results if not r.ok and c.level == "error"]
    return 1 if errors else 0
```

**`_run_deep_checks(ctx)`**: Chama cada check em `DEEP_CHECKS`; para C12.5 faz o import/call do Playwright gate com tratamento de falha de import (`try/except ImportError`).

---

## 5. Estrutura de Arquivos Modificados

```
src/modules/ava-fabric-agents/summary/
├── module.yaml                          ← version "1.4.1" → "1.5.0"  [Category 3]
├── data/
│   └── artifact-map.yaml               ← adicionar f3_prototype + f8_summary  [Category 3]
├── agents/
│   ├── summary-validate-agent.md       ← bump version 1.4.2 → 1.5.0  [Category 2]
│   └── summary-remediation-agent.md    ← bump version 1.5.0 → 1.6.0  [Category 2]
└── utils/
    ├── validate_summary.py             ← (1) renumerar C12.x→C11.39-41
    │                                      (2) adicionar argparse --deep
    │                                      (3) adicionar DEEP_CHECKS (C12.1-C12.7)
    │                                      (4) adicionar _run_deep_checks(), _write_deep_audit_json()
    │                                      (5) run_all() aceita deep=True  [Category 2]
    └── remediate_summary.py            ← (1) loop estruturado consumindo deep-audit-report.json
                                           (2) _dispatch_correction() com bifurcação transiente/estrutural
                                           (3) argparse --force-promote
                                           (4) _resolve_max_attempts() com cascata de config  [Category 2]
```

**Outputs novos** (por projeto):
```
projects/{project_name}/outputs/summary/
├── deep-audit-report.json              ← novo (schema v1.0, emitido por validate_summary.py --deep)
└── remediation-report.json            ← schema v2.0 (campo forced adicionado)
```

---

## 6. module.yaml Impact

**Mudança**: Somente bump de `version` — nenhum novo agente registrado (Category 4 N/A).

```yaml
# src/modules/ava-fabric-agents/summary/module.yaml
name: summary
display_name: "AVA Fabric Summary"
version: "1.5.0"    # era "1.4.1"
```

---

## 7. Observability & Trace Propagation

N/A — agentes são prompts LLM. Os scripts Python usam print/stderr para logging de progresso; nenhum trace_id é propagado explicitamente.

---

## 8. Schema Changes

| Artefato | Mudança | Descrição |
|---|---|---|
| `deep-audit-report.json` | **NOVO** (schema v1.0) | Emitido por `validate_summary.py --deep`; consumido por `remediate_summary.py` |
| `remediation-report.json` | **schema v2.0** | Adiciona campo `forced` (bool, sempre presente), `deep_audit_summary`, `mermaid_gate` |
| `validation-report.json` | ID rename: C12.x → C11.39-41 | Breaking change documentada no CHANGELOG |
| `agent-task.schema.json` | NO | Sem mudança |
| `agent-result.schema.json` | NO | Sem mudança |

---

## 9. Tasks de Categoria 3 (para `/speckit.tasks`)

As seguintes tasks são **fora do escopo de implementação** deste plan (sem código agora), mas DEVEM ser registradas como tasks explícitas de Categoria 3 no `/speckit.tasks` subsequente:

| Task ID sugerido | Descrição | Artefato |
|---|---|---|
| `cat3-module-version-bump` | Bump `module.yaml` version `1.4.1` → `1.5.0` | `summary/module.yaml` |
| `cat3-artifact-map-f3-prototype` | Adicionar fase `f3_prototype` ao `artifact-map.yaml` com agent `ava-prototype` e seus Output Contracts contratuais | `summary/data/artifact-map.yaml` |
| `cat3-artifact-map-f8-summary` | Adicionar fase `f8_summary` ao `artifact-map.yaml` com agent `ava-summary` e outputs (HTML + reports) | `summary/data/artifact-map.yaml` |
| `cat3-force-promote-flag` | Implementar `--force-promote` em `remediate_summary.py` (argparse + campo `forced` + header `[WARN]`) | `utils/remediate_summary.py` |

---

## 10. Estratégia de Validação Manual

Per spec §8: sem suíte automatizada. Validação via inspeção manual de `deep-audit-report.json`.

**Projeto de referência**: Usar qualquer projeto já existente em `projects/` com pipeline F1 completo (deve ter `ava-asis/` outputs e um `AVA-FABRIC-SUMMARY-*.html` já gerado).

**Protocolo**:

1. Executar: `python validate_summary.py --project {NOME} --deep`
2. Inspecionar `projects/{NOME}/outputs/summary/deep-audit-report.json`:
   - Verificar que `summary.promotable` é `true` para projeto saudável
   - Verificar que fases não-executadas aparecem como INFO (não CRITICAL/HIGH)
   - Verificar que C12.5 aparece como finding quando há diagrama sabidamente inválido
3. Para testar C12.1: temporariamente remover um artefato fonte (ex.: renomear `risk-register.md`), reger summary, rodar `--deep`, confirmar finding HIGH com `empty_by_failure`
4. Para testar loop: executar `python remediate_summary.py --project {NOME}`, confirmar que `remediation-report.json` emite `final_status: CLEAN|PARTIAL|BLOCKED` com contagem de tentativas correta
5. Para testar `--force-promote`: com projeto BLOCKED, executar `python remediate_summary.py --project {NOME} --force-promote`, confirmar `"forced": true` no report e header `[WARN]` no console

---

## 11. Complexity Tracking

| Gate | Situação | Justificativa | Controles |
|---|---|---|---|
| C12 namespace collision (existentes C12.1-C12.3) | Renumeração para C11.39-C11.41 é breaking change no `validation-report.json` | Necessário para liberar namespace C12 exigido pela spec | Documentar no CHANGELOG; bump é MINOR pois `deep-audit-report.json` é novo arquivo sem clientes existentes |
| Sobreposição C11.39-41 vs C12.2/C12.6 em modo `--deep` | Após renumeração, C12.2 (regex antigo) e C12.6 cobriam os mesmos tokens/condições que C11.39-41, inflando `validation-report.json` no modo `--deep` | Resolvido por restrição de escopo (Opção C, 2026-08-18): regex C12.2 restringe a `{{X}}`, `[NEEDS CLARIFICATION]`, `AG-NN`; C12.6 verifica apenas `<tbody>` presente com zero `<tr>` (C11.41 verifica ausência de `<tbody>`) | Escopos são mutuamente exclusivos; loop de remediação (lê `deep-audit-report.json` com só C12.x) não afetado; zero mudança de schema |
| Dispatch real de agentes no loop | `_invoke_agent()` usa subprocess em `remediate_summary.py` | Pattern já existente (`run_script()` em `phase1_artifact_resolution`) | Timeout de 300s; bifurcação transiente/estrutural previne loop infinito |
| Playwright gate em-process (C12.5) | `ImportError` se Playwright não disponível | Ambientes sem Playwright devem degradar graciosamente | `try/except ImportError` → emite finding INFO "Playwright unavailable, C12.5 skipped" |
| `artifact-map.yaml` incompleto (f3+f8 ausentes) | C12.3 pode produzir falso-negativo até tasks de Categoria 3 serem executadas | Tasks explícitas documentadas em §9 | C12.3 usa `D.agentStatus[phase].done` para suprimir findings de fases não declaradas no manifesto |

---

## 12. Dados dos Agentes Existentes (referência de implementação)

### `validate_summary.py` — estrutura chave para extensão

| Elemento | Localização no arquivo | Uso na feature |
|---|---|---|
| `Check` dataclass | linha ~44 | Reutilizado para DEEP_CHECKS sem alteração |
| `Ctx` dataclass | linha ~80 | `ctx.D_agentStatus` já disponível para decisão legítimo-vazio |
| `_load_js_data()` | linha ~244 | Já extrai `agentStatus`; chamado uma vez em `_load_ctx()` |
| `_extract_json_slice()` | linha ~114 | Reutilizado para parsing de `D.*` em C12.1 |
| `CHECKS` | linha ~2386 | Lista existente; DEEP_CHECKS é lista adicional separada |
| `_c12_1/2/3` existentes | linha ~2770 | Renumerar IDs para C11.39-C11.41 no catálogo |
| `_run_checks()` | linha ~2896 | Nova variante `_run_deep_checks()` segue o mesmo padrão |
| `C13.1/C13.2` | linha ~2907 | Permanecem inalterados |

### `mermaid_playwright_gate.py` — contrato de consumo

```python
# Import em validate_summary.py para C12.5:
from mermaid_playwright_gate import run_playwright_mermaid_gate, MermaidGateResult, DiagramResult

# Assinatura:
# run_playwright_mermaid_gate(html_path, guardrails_path=None, max_attempts=3, timeout_ms=15_000)
#   → MermaidGateResult
#
# MermaidGateResult.diagrams: list[DiagramResult]
# DiagramResult.diagram_id, .status, .error_message, .fixes_applied
# status: "PASS" | "FIXED" | "FAIL_UNRESOLVED" | "EMPTY" | "TIMEOUT" | "SKIPPED"
# NOTE (I3, 2026-08-18): "SKIPPED" was already used in the filter logic at §4.4
# (not in ("PASS","FIXED","EMPTY","SKIPPED")) but was absent from this contract
# documentation. Added here for completeness — no code change required.
```

### `remediate_summary.py` — extensões sobre base existente

| Função existente | Papel na extensão |
|---|---|
| `run_script()` | Base para `_invoke_agent()` no loop de remediação |
| `_run_validator()` | Reutilizada internamente; `run_remediation_loop()` chama `_run_deep_audit()` que usa o mesmo padrão mas com `--deep` |
| `phase0_audit()` a `phase7_*` | Permanecem; o novo loop de remediação é executado DEPOIS da cadeia de fases existente ou como caminho alternativo quando `--deep` é a entrada |
| `write_if_absent()` | Reutilizada nas correções de artefatos ausentes |
