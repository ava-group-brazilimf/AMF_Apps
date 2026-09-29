# Tasks: Summary Self-Validation & Remediation — Deep Audit C12 + Remediation Loop

**Spec**: `specs/041-summary-self-validation-remediation/spec.md`
**Plan**: `specs/041-summary-self-validation-remediation/plan.md`
**Feature Branch**: `041-summary-self-validation-remediation`
**Change Type**: modify-existing · `ava-summary-validate` 1.4.2 → 1.5.0 · `ava-summary-remediation` 1.5.0 → 1.6.0

> **Categorias ativas**: **2** (Implementação), **3** (Config/Metadata), **5** (Validação Manual).
> Categorias 1, 4, 6, 7 são **N/A**: nenhum novo agente criado; SKILL.md de `ava-summary-remediation`
> inalterado; `ava-summary-validate` permanece interno (sem SKILL.md). Category 4 registra apenas
> *novos* agentes — o bump de `version` em `module.yaml` é task de Categoria 3 (spec §1).
>
> **Suíte automatizada de testes Python**: **Excluída** — spec §8, decisão SpecKit 039-prototype-design-input.
> **Checklist de verificação manual formal**: **Excluída** — a validação é o protocolo único da
> Categoria 5 (plan.md §10), documentado como comentário/anexo da PR, não como arquivo no repositório.

---

## Categoria 2 — Corpo dos Agentes / Implementação

> Implementação em Python (inglês técnico) e Markdown (PT-BR para corpo dos agentes, Art. V da Constituição).
> Tasks marcadas com `[P]` podem ser executadas em paralelo com outras tasks dentro desta categoria,
> desde que suas dependências explícitas estejam satisfeitas.
> **Esforço estimado (Categoria 2):** P×7 · M×4 · G×2 — 13 tasks

- [X] **2.1** Renumerar catálogo `CHECKS` em `validate_summary.py`: alterar **apenas o ID string** nas três instâncias `Check(...)` — `"C12.1"` → `"C11.39"`, `"C12.2"` → `"C11.40"`, `"C12.3"` → `"C11.41"` (funções Python subjacentes `_c12_1`, `_c12_2`, `_c12_3` são privadas e **não precisam ser renomeadas**); adicionar entrada em `CHANGELOG.md` documentando a breaking change: consumidores de `validation-report.json` que filtrem por `id: "C12.1"`, `"C12.2"` ou `"C12.3"` devem atualizar para `"C11.39"`, `"C11.40"`, `"C11.41"` respectivamente; bump é MINOR pois `deep-audit-report.json` é arquivo novo sem clientes pré-existentes (plan.md §8, §11). **Arquivos**: `src/modules/ava-fabric-agents/summary/utils/validate_summary.py`, `CHANGELOG.md`. **Esforço**: P. **Categoria**: 2. **Depende de**: —

- [X] **2.2** Adicionar argparse `--deep` retrocompatível em `validate_summary.py`: `parser.add_argument("--deep", action="store_true", help="Activate C12 Deep Item Audit rules. Without this flag, only C1–C11 rules run (backward-compatible).")`; confirmar que sem a flag o comportamento, a sequência de checks (C1–C11 + C13.x) e o exit code semântico permanecem **absolutamente inalterados** (plan.md §4.9). **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/validate_summary.py`. **Esforço**: P. **Categoria**: 2. **Depende de**: 2.1

- [X] **2.3** Implementar `DEEP_CHECKS: list[Check]` com as 7 funções `_c12da_N(ctx: Ctx) -> Result` (assinatura idêntica às funções existentes); registrar todas em `DEEP_CHECKS` usando a mesma dataclass `Check` do catálogo principal. Implementar cada função conforme plan.md §4.1–§4.5 e spec §4.1: **(a)** `_c12da_1` (C12.1, `empty_by_failure`): árvore de decisão via `ctx.D_agentStatus.get(phase_key, {}).get("done", False)` + threshold definido como constante local `_EMPTY_THRESHOLD_BYTES = 100` (sem exigir nova config); fluxo: fase `done==false` → INFO legítimo; artefato ausente → delegar a C12.3 (não levantar C12.1 simultaneamente); artefato existe com tamanho ≤ threshold → INFO legítimo; artefato existe com tamanho > threshold e KPI renderiza `0`/`"N/E"`/`""`/`"—"` → HIGH (plan.md §4.3 — leitura de `D.kpis` via `_extract_json_slice`). **(b)** `_c12da_2` (C12.2, `placeholder_unresolved`): regex restrito a `r'\{\{[A-Z0-9_]+\}\}|\[NEEDS CLARIFICATION\]|AG-\d+'` sobre HTML fora de blocos `<script>`; adicionar comentário inline no código: `# DEDUPLICATION DECISION (2026-08-18, Opção C): [INCOMPLETE] → exclusivo C11.39; [ARTIFACT-MISSING] → exclusivo C11.40. NÃO adicionar aqui para evitar duplo-report.`; severidade: CRITICAL se token em título/nome-do-projeto/bloco KPI, HIGH em qualquer outro local. **(c)** `_c12da_3` (C12.3, `missing_artifact`): carregar `artifact-map.yaml` via `_load_artifact_map()` (`_ARTIFACT_MAP_PATH = Path(__file__).resolve().parent.parent / "data" / "artifact-map.yaml"`); para cada fase `fN_*` no manifesto onde `D.agentStatus[phase_key]["done"] == True`, verificar existência e `st_size > 0` de cada artefato declarado; ausente/zero → CRITICAL (fase bloqueante) ou HIGH (não-bloqueante). _Nota: testável end-to-end somente após tasks 3.2 e 3.3 (f3_prototype e f8_summary no manifesto)._ **(d)** `_c12da_4` (C12.4, `divergent_config`): comparar path declarado em `artifact-map.yaml` com o path que `build_summary_comprehensive.py` efetivamente lê (via `_read_builder_source()` já disponível); discrepâncias → MEDIUM. **(e)** `_c12da_5` (C12.5, `mermaid_error`): `try: from mermaid_playwright_gate import run_playwright_mermaid_gate, MermaidGateResult` / `except ImportError: return Result(True, "Playwright unavailable, C12.5 skipped")` emitindo finding INFO em vez de crashar; chamar `run_playwright_mermaid_gate(html_path=ctx.html_path)` com defaults do módulo; mapear `DiagramResult.status` → severidade C12.5 (plan.md §4.4: `FAIL_UNRESOLVED` → CRITICAL se seção F1-F2, HIGH demais; `TIMEOUT` → MEDIUM; `PASS`/`FIXED`/`EMPTY`/`SKIPPED` → não é finding). **(f)** `_c12da_6` (C12.6, `table_no_rows`): para cada `<table>` em seção de fase com `D.agentStatus[phase].done == true`, verificar se `<tbody>` **existe** e tem zero `<tr>` internos → HIGH; adicionar comentário inline: `# DEDUPLICATION (Opção C 2026-08-18): <table> SEM <tbody> algum → exclusivo C11.41. C12.6 só dispara quando <tbody> EXISTE e está vazio.` **(g)** `_c12da_7` (C12.7, `list_no_items`): `<ul>/<ol>` com zero `<li>` em seção de fase `done == true` → MEDIUM. **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/validate_summary.py`. **Esforço**: G. **Categoria**: 2. **Depende de**: 2.2

- [X] **2.4** Implementar `_run_deep_checks(ctx: Ctx) -> list[tuple[Check, Result]]` seguindo o mesmo padrão de `_run_checks()` existente — iterar sobre `DEEP_CHECKS`, chamar cada função com `ctx`, coletar resultados; implementar `_write_deep_audit_json(ctx: Ctx, deep_results: list[tuple[Check, Result]]) -> None` que grava `projects/{project_name}/outputs/summary/deep-audit-report.json` com schema v1.0 completo (spec §3.1): campos `schema_version: "1.0"`, `generated_at` (ISO-8601), `project`, `html_path`, `summary.{critical,high,medium,low,promotable}` (promotable = `True` quando `critical == 0 and high == 0`), e lista `findings` com campos `id` (DA-001, DA-002…), `severity`, `phase`, `section`, `agent_responsible`, `artifact_path`, `finding_type`, `detail`, `root_cause`, `auto_correctable`, `suggested_fix`; garantir que o arquivo é escrito **em paralelo** ao `validation-report.json` standard, não em substituição. **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/validate_summary.py`. **Esforço**: M. **Categoria**: 2. **Depende de**: 2.3

- [X] **2.5** Atualizar `run_all(project, auto_fix=False, deep=False, …) -> int` para aceitar parâmetro `deep: bool`: quando `deep=True`, após `_run_checks(ctx)`, chamar `_run_deep_checks(ctx)` → `_write_deep_audit_json(ctx, deep_results)` → `results = results + deep_results`; quando `deep=False`, omitir completamente e preservar exit code semantics idêntico ao existente; o argparse mapeia `args.deep` para o parâmetro `deep` de `run_all` (plan.md §4.9). **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/validate_summary.py`. **Esforço**: P. **Categoria**: 2. **Depende de**: 2.4

- [X] **2.6** Implementar `run_remediation_loop(project_name: str, force_promote: bool = False) -> dict` em `remediate_summary.py` com loop `for attempt in range(1, max_attempts + 1)`: **(a)** executar deep audit via subprocess `validate_summary.py --deep --project {project_name}` e consumir `deep-audit-report.json`; **(b)** extrair `critical_high = [f for f in findings if severity in ("CRITICAL","HIGH")]`; **(c)** se `not critical_high` → BREAK com `final_status = "CLEAN"` (nenhum finding) ou `"PARTIAL"` (MEDIUM/LOW restantes) — **PARTIAL aplica-se em qualquer iteração**, não apenas ao esgotar tentativas; **(d)** para cada finding `auto_correctable`, chamar `_dispatch_correction(finding, project_name, report)`; **(e)** rebuild via `build_summary_comprehensive.py`; após loop esgotar sem BREAK → `final_status = "BLOCKED"`, `exit_code = 1`, `unresolved_findings` populado; chamar `_write_remediation_report(project_name, report)` incondicionalmente ao final; inicializar `report["forced"] = False` (campo sempre presente no schema v2.0, spec §3.2); incluir campos `mermaid_gate`, `deep_audit_summary`, `schema_version: "2.0"`. **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py`. **Esforço**: G. **Categoria**: 2. **Depende de**: 2.7, 2.8, 2.9, 2.10

- [X] **2.7** [P] Implementar `_is_agent_resolvable(agent_id: str) -> bool` em `remediate_summary.py`: varrer `Path("src/modules/ava-fabric-agents").glob("*/module.yaml")`; para cada arquivo, `yaml.safe_load()` e checar `any(a.get("id") == agent_id for a in data.get("agents", []))`; tratar `OSError`/`yaml.YAMLError` com `continue` silencioso; retornar `True` se encontrado, `False` caso contrário (plan.md §4.7). **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py`. **Esforço**: P. **Categoria**: 2. **Depende de**: 2.4

- [X] **2.8** Implementar `_dispatch_correction(finding: dict, project_name: str, report: dict) -> None` em `remediate_summary.py` com bifurcação dupla: **(1) Falha estrutural** — se `not _is_agent_resolvable(finding["agent_responsible"])`: `finding["auto_correctable"] = False`; registrar em `report["unresolved_findings"]` com `dispatch_error = {"type": "structural", "reason": f"agent_id '{agent_id}' not found in any module.yaml", "suggested_fix": f"Register '{agent_id}' in the appropriate module.yaml"}`; **retornar sem consumir attempt** (invariante do plan.md §4.4). **(2) Tentativa real** — `_invoke_agent(agent_id, project_name, timeout=300)`; em sucesso: registrar em `report["corrections_applied"]`; em `TimeoutError`/`RuntimeError` (exit ≠ 0): registrar em `report["unresolved_findings"]` com `dispatch_error = {"type": "transient", "reason": str(e)}` — esta falha **consome a tentativa** normalmente. **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py`. **Esforço**: M. **Categoria**: 2. **Depende de**: 2.7

- [X] **2.9** [P] Implementar `_resolve_max_attempts(project_name: str) -> int` em `remediate_summary.py` com cascata de 3 níveis: **(1)** `projects/{project_name}/context/project-config.yaml` → `cfg.get("summary", {}).get("max_remediation_attempts")`; **(2)** `src/shared/data/reference-architecture.yaml` → mesma chave; **(3)** fallback hard `return 3`; cada nível usa `yaml.safe_load` com `try/except (OSError, yaml.YAMLError, AttributeError)` e avança ao próximo em caso de falha; validar que o valor lido é `isinstance(v, int) and v > 0` antes de retornar (plan.md §4.8). **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py`. **Esforço**: P. **Categoria**: 2. **Depende de**: 2.4

- [X] **2.10** [P] Implementar argparse `--force-promote` em `remediate_summary.py`: `parser.add_argument("--force-promote", action="store_true", help="Deliver HTML even when final_status is BLOCKED. Sets 'forced': true in remediation-report.json. Exit code stays 1.")`; na lógica pós-loop de `run_remediation_loop`: quando `force_promote=True and report["final_status"] == "BLOCKED"` → `report["forced"] = True` (campo **sempre presente** no schema v2.0, default `False`), `exit_code` permanece `1`, emitir header `[WARN] FORCED PROMOTION — unresolved CRITICAL/HIGH findings remain` seguido da lista de findings não resolvidos com `[{severity}] {id}: {detail}`. _Esta task cobre integralmente o `cat3-force-promote-flag` do plan.md §9 — ver task 3.4 (nota de rastreamento)._ **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py`. **Esforço**: M. **Categoria**: 2. **Depende de**: 2.4

- [X] **2.11** [P] Bump de versão em `summary-validate-agent.md`: alterar frontmatter `version: "1.4.2"` → `"1.5.0"`; atualizar `description` (PT-BR, Art. V) para refletir o novo output `deep_audit_json` e a flag `--deep`; confirmar que `allowed-tools` inclui `Bash` (necessário para execução do script com a flag); não adicionar campos além dos permitidos pelo Art. II (`name`, `version`, `description`, `allowed-tools`). **Arquivo**: `src/modules/ava-fabric-agents/summary/agents/summary-validate-agent.md`. **Esforço**: P. **Categoria**: 2. **Depende de**: 2.5

- [X] **2.12** [P] Bump de versão em `summary-remediation-agent.md`: alterar frontmatter `version: "1.5.0"` → `"1.6.0"`; atualizar `description` (PT-BR, Art. V) para refletir `--force-promote` e o loop estruturado CLEAN/PARTIAL/BLOCKED; não adicionar campos além dos permitidos pelo Art. II. **Arquivo**: `src/modules/ava-fabric-agents/summary/agents/summary-remediation-agent.md`. **Esforço**: P. **Categoria**: 2. **Depende de**: 2.10

- [X] **2.13** Adicionar hook de auto-trigger ao final da seção de execução de `summary-agent.md` (PT-BR, Art. V): após `build_summary_comprehensive.py` concluir com sucesso, invocar `validate_summary.py --deep --project {project_name}`; se `deep-audit-report.json.summary.promotable == false` ou exit code ≠ 0, invocar `remediate_summary.py --project {project_name}`; documentar que sem a flag `--deep` o comportamento do summary permanece inalterado para compatibilidade retroativa; sem reimplementação de lógica Python no corpo do agente (invariante: HTML exclusivo de `build_summary_comprehensive.py`, spec §4.5). **Arquivo**: `src/modules/ava-fabric-agents/summary/agents/summary-agent.md`. **Esforço**: M. **Categoria**: 2. **Depende de**: 2.5 (`--deep` funcional), 2.6 (loop de remediação funcional)

---

## Categoria 3 — Config / Metadata

> Tasks de configuração e manifesto sem código de agente. Todas podem ser executadas em **paralelo às
> tasks de Categoria 2**. Dentro desta categoria, 3.3 depende de 3.2 (mesmo arquivo, edições sequenciais).

- [X] **3.1** [P] Bump `version` em `src/modules/ava-fabric-agents/summary/module.yaml`: alterar `version: "1.4.1"` → `"1.5.0"`; preservar todos os demais campos do arquivo (`name`, `display_name`, `agents`, `bmad_version`); confirmar que `bmad_version: ">=6.0.0"` está intacto. _Esta task não registra novos agentes (Category 4 N/A) — é bump de metadata do módulo que reflete o comportamento dos agentes existentes (plan.md §6, spec §1)._ **Arquivo**: `src/modules/ava-fabric-agents/summary/module.yaml`. **Esforço**: P. **Categoria**: 3. **Depende de**: —

- [X] **3.2** [P] Adicionar entrada `f3_prototype` em `src/modules/ava-fabric-agents/summary/data/artifact-map.yaml`: agente responsável `ava-prototype`; `primary_output: project/outputs/tobe/prototype/index.html`; seção HTML: `s-f3-proto`; listar todos os artefatos contratuais da fase F3 Prototype, incluindo `design-input-traceability.json` (adicionado em spec 039-prototype-design-input); manter indentação YAML e estrutura consistente com as entradas `f1_asis`/`f2_tobe` já presentes. _Gap confirmado por auditoria 2026-08-18: `artifact-map.yaml` v1.0.1 cobre 6 fases mas não tem `f3_prototype` (phase adicionada em Constitution v1.4.0). Task obrigatória: `_c12da_3` depende de manifesto completo para classificar corretamente `missing_artifact`._ **Arquivo**: `src/modules/ava-fabric-agents/summary/data/artifact-map.yaml`. **Esforço**: P. **Categoria**: 3. **Depende de**: —

- [X] **3.3** Adicionar entrada `f8_summary` em `src/modules/ava-fabric-agents/summary/data/artifact-map.yaml` (executar **após 3.2** para evitar conflito de edição no mesmo arquivo): agente responsável `ava-summary`; outputs declarados: `AVA-FABRIC-SUMMARY-{PROJECT_NAME}-{DATE}.html`, `validation-report.md`, `validation-report.json`, `deep-audit-report.json` (novo, schema v1.0), `remediation-report.json` (schema v2.0). _Gap confirmado por auditoria 2026-08-18: `f8_summary` ausente do manifesto; sem esta entrada, `_c12da_3` produziria falso-negativo para artefatos do próprio Summary._ **Arquivo**: `src/modules/ava-fabric-agents/summary/data/artifact-map.yaml`. **Esforço**: P. **Categoria**: 3. **Depende de**: 3.2

- [X] **3.4** _(Nota de rastreamento — FUNDIDA com task 2.10)_ `cat3-force-promote-flag` (plan.md §9): a implementação de `--force-promote` em `remediate_summary.py` foi integralmente absorvida pela task **2.10** (mesma implementação, mesmo arquivo). Esta entrada existe apenas como rastreabilidade do ID de task documentado no plan. **Nenhuma ação adicional necessária.** **Arquivo**: _N/A — ver task 2.10_. **Esforço**: —. **Categoria**: 3. **Depende de**: 2.10 _(já entregue)_

---

## Categoria 5 — Validação Manual

> **Task única desta categoria.** Sem suíte automatizada em Python — spec §8, decisão SpecKit
> 039-prototype-design-input. Resultado documentado como comentário/anexo da PR, não como arquivo
> no repositório. Esta task é **sempre a última** — executar somente após todas as tasks de
> Categoria 2 e Categoria 3 estarem completas.

- [X] **5.1** Executar o protocolo de validação manual completo do plan.md §10 contra um projeto de referência existente em `projects/` com pipeline F1 completo (artefatos `ava-asis/` e `AVA-FABRIC-SUMMARY-*.html` já gerados). **Passos obrigatórios**: **(a) Validação nominal** — `python validate_summary.py --project {NOME} --deep`; inspecionar `projects/{NOME}/outputs/summary/deep-audit-report.json`: confirmar `summary.promotable: true` em projeto saudável; confirmar que fases não-executadas classificam como INFO (zero CRITICAL/HIGH por fase não-done); confirmar que C12.5 aparece como finding quando há diagrama Mermaid sabidamente inválido no HTML. **(b) Teste de C12.1** — remover temporariamente um artefato fonte (ex.: renomear `risk-register.md`), regenerar summary, rodar `--deep`, confirmar finding HIGH com `finding_type: empty_by_failure` e `agent_responsible` correto; restaurar o artefato. **(c) Teste do loop completo** — `python remediate_summary.py --project {NOME}`; confirmar que `remediation-report.json` contém `final_status: CLEAN|PARTIAL|BLOCKED` com campo `attempts` correto e `schema_version: "2.0"`; confirmar que `"forced": false` está presente mesmo sem `--force-promote`. **(d) Teste de `--force-promote`** — com projeto em estado BLOCKED, executar `python remediate_summary.py --project {NOME} --force-promote`; confirmar `"forced": true` no `remediation-report.json`, header `[WARN] FORCED PROMOTION` no console, exit code `1`. **(e) Retrocompatibilidade** — executar `python validate_summary.py --project {NOME}` (sem `--deep`); confirmar que comportamento C1–C11 + C13.x permanece idêntico ao baseline e nenhum `deep-audit-report.json` é gerado. Documentar resultado final (aprovado/reprovado + observações) como **comentário ou anexo da PR** — não criar arquivo de resultado no repositório. **Arquivo**: _comentário/anexo da PR_. **Esforço**: M. **Categoria**: 5. **Depende de**: todas as tasks 2.1–2.13 e 3.1–3.3 completas

---

## Dependências entre Tasks

```
2.1 (renumeração CHECKS + CHANGELOG)
  └─→ 2.2 (argparse --deep retrocompatível)
        └─→ 2.3 (DEEP_CHECKS: _c12da_1 a _c12da_7)
                │  ← 3.2/3.3 prontas para testar _c12da_3 end-to-end
              └─→ 2.4 (_run_deep_checks + _write_deep_audit_json)
                    ├─→ 2.5 (run_all aceita deep=bool)
                    │     └─→ 2.11 [P]  (bump summary-validate-agent.md 1.4.2→1.5.0)   ──┐
                    ├─→ 2.7 [P]  (_is_agent_resolvable)                                   │
                    │     └─→ 2.8      (_dispatch_correction transiente/estrutural)  ──┐   │
                    ├─→ 2.9 [P]  (_resolve_max_attempts cascata config)  ──────────────┤   │
                    └─→ 2.10 [P] (argparse --force-promote + override) ────────────────┤   │
                          └─→ 2.12 [P] (bump summary-remediation-agent.md)             │   │
                                              [todos prontos: 2.8 + 2.9 + 2.10] ──────┘   │
                                                          └─→ 2.6 (run_remediation_loop — orquestrador)
                                                                    └─→ 2.13 (hook auto-trigger em summary-agent.md) ←──┘

Categoria 3 (paralela a toda a Categoria 2):
  3.1 [P]  (module.yaml version bump 1.4.1→1.5.0)            ← independente
  3.2 [P]  (artifact-map.yaml: adicionar f3_prototype)        ← independente
    └─→ 3.3  (artifact-map.yaml: adicionar f8_summary)        ← mesmo arquivo, sequencial

Categoria 5 (sempre última):
  5.1 (protocolo de validação manual)   ← depende de 2.1–2.13 + 3.1–3.3
```

**Janelas de paralelismo recomendadas**:
- Iniciar 3.1 + 3.2 imediatamente (sem dependências), em paralelo com o início da sequência 2.1→2.2→2.3.
- Após 2.4 concluir, iniciar **2.5, 2.7, 2.9 e 2.10 em paralelo** (todos dependem apenas de 2.4, saídas independentes entre si).
- Após 2.5, iniciar 2.11 [P].
- Após 2.7, iniciar 2.8 (`_dispatch_correction` consome `_is_agent_resolvable`).
- Após 2.10, iniciar 2.12 [P] (bump de agent.md não depende do loop finalizado).
- Após **2.8 + 2.9 + 2.10 concluírem**, iniciar 2.6 (orquestrador integra todos os helpers prontos).
- Após 2.6, iniciar 2.13 (hook auto-trigger depende de 2.5 e 2.6 — aguardar ambos).
- Após 3.2 concluir (artifact-map), prosseguir imediatamente com 3.3.

---

## Definition of Done

- [X] `validate_summary.py`: renumeração C11.39-41 completa (IDs nos `Check(...)`, funções Python intactas); `--deep` retrocompatível implementado; `DEEP_CHECKS` com 7 funções (`_c12da_1`–`_c12da_7`) implementadas conforme deduplicação Opção C (2026-08-18); `_run_deep_checks()` e `_write_deep_audit_json()` implementados; `run_all()` aceita `deep=True`; `deep-audit-report.json` (schema v1.0) emitido com todos os campos obrigatórios.
- [X] `remediate_summary.py`: `run_remediation_loop()` com loop CLEAN/PARTIAL/BLOCKED e BREAK antecipado para PARTIAL em qualquer iteração; `_is_agent_resolvable()` e bifurcação transiente/estrutural em `_dispatch_correction()` implementadas; `_resolve_max_attempts()` com cascata 3 níveis; `--force-promote` com `"forced": true` no schema v2.0 e exit code 1 preservado; `remediation-report.json` schema v2.0 com campo `forced` sempre presente.
- [X] `summary-validate-agent.md`: frontmatter `version: "1.5.0"`, description atualizado (PT-BR), `allowed-tools` inclui Bash.
- [X] `summary-remediation-agent.md`: frontmatter `version: "1.6.0"`, description atualizado (PT-BR, reflete `--force-promote` e loop estruturado).
- [X] `summary-agent.md`: hook de auto-trigger `--deep` + invocação condicional de remediação adicionado (PT-BR).
- [X] `module.yaml`: `version: "1.5.0"` confirmado; `bmad_version: ">=6.0.0"` preservado.
- [X] `artifact-map.yaml`: entradas `f3_prototype` e `f8_summary` adicionadas com todos os outputs contratuais.
- [X] `CHANGELOG.md`: breaking change C12.x → C11.39-41 documentada com orientação de migração para consumidores do `validation-report.json`.
- [X] Protocolo de validação manual (5.1) executado, resultado (aprovado/reprovado + observações) documentado como comentário/anexo da PR.
- [X] Zero arquivo de suíte de testes Python gerado (spec §8).
