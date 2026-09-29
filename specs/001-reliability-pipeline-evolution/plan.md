# Agent Implementation Plan: Reliability Pipeline Evolution

**Spec**: `specs/001-reliability-pipeline-evolution/spec.md`
**Tech Stack**: See `src/shared/data/reference-architecture.yaml` — do not hardcode versions.

---

## Summary

| Field | Value |
|---|---|
| **Change Type** | `modify-existing` (4 components + 1 config template) |
| **Phase** | `F3 — Tech Stack` (orchestrated by `ava-stack-orchestrator`) |
| **Module** | `tech-stack` |
| **Primary Requirement** | Tornar o pipeline de build confiável, portável e governado — suporte a Podman, CVE policy configurável, recuperação de lockfile e scaffolding ESLint automático. |
| **Technical Approach** | Todas as funcionalidades já estão implementadas nos agentes. A única lacuna é a seção `cve_policy` ausente no template `project-config.yaml`. |
| **Implementation Status** | 4/5 componentes já implementados — 1 item de configuração pendente. |

---

## Constitution Check

- [x] **Article I** — Nenhuma versão hardcoded nos agentes. ESLint usa variáveis `{angular_eslint_version}` / `{typescript_eslint_version}`. `node_version` lido de `project-config.yaml`. ✅
- [x] **Article II** — Frontmatter correto nos 3 agentes. Padrão `^ava-[a-z0-9-]+$` respeitado. ✅
- [x] **Article III** — Componentes pertencem ao F3; `ava-stack-orchestrator` os coordena. ✅
- [x] **Article IV** — `modify-existing`: nenhum `module.yaml` precisa de alteração. ✅
- [x] **Article V** — Corpos dos agentes em pt-BR. ✅
- [x] **Article VI** — BDD scenarios definidos em spec seção 4 (6 cenários, 18 CAs). ✅
- [x] **Article VII** — Sem impacto no F1 security pipeline. CVE policy aprimora segurança. ✅
- [x] **Article VIII** — `trace_id` propagado por `shared-context.md`. Sem alterações no schema JSON. ✅
- [x] **Article IX** — N/A — modificações em arquivos `.md` de instrução LLM, não em código gerado. ✅
- [x] **Article X** — Bumps MINOR já aplicados: build-validator v2.3.0, build-fixer v1.1.0. ✅
- [x] **Article XI** — Agentes user-facing com SKILL.md existentes. `build_runner.py` é utilitário interno. ✅

### Quality Gate Check

- [x] Nenhum `[NEEDS CLARIFICATION]` na spec
- [x] Todos os outputs seguem `projects/{project_name}/outputs/...`
- [x] `next_agent` downstream confirmado (build-validator → build-fixer; orchestrator → ava-summary)

---

## 1. Technical Context

| Dimension | Choice | Source |
|---|---|---|
| Container runtime | Docker (padrão) / Podman (`--runtime podman`) | `build_runner.py` — runtime-aware path normalization |
| Frontend framework | Angular (versão lida de config) | `project-config.yaml → tobe_stack.frontend_version` |
| Node.js version | Independente do frontend | `project-config.yaml → tobe_stack.node_version` |
| CVE policy | `zero_tolerance` (padrão) / `exceptions_allowed` com expiração ISO | `project-config.yaml → quality_gates.cve_policy` |
| ESLint | Flat config (`eslint.config.js`) ou legacy (`.eslintrc.*`) | Detectado em Step F3 do build-validator |
| Lockfile | `package-lock.json` — regenerado se `package.json` for modificado | `build-fixer-agent.md` → protocolo de lockfile |

**Project overrides**: `projects/{project_name}/context/project-config.yaml`

---

## 2. Phase Placement

```
F2 → ava-summary → F3 (Tech Stack)
                    └─ ava-stack-orchestrator (Step 1.5) → ava-stack-docs-researcher
                    └─ ava-stack-orchestrator (Step 3)   → {resolved_backend_agent}
                    └─ ava-stack-orchestrator (Step 5)   → {resolved_frontend_agent}
                    │                                       └─ coder-angular-frontend (RF15–RF17)
                    └─ ava-stack-orchestrator (Step 6a)  → ava-stack-build-validator  ← RF05–RF12
                    │   └─ (retry cicles)                → ava-stack-build-fixer      ← RF13–RF14
                    └─ ava-stack-orchestrator (Step 8)   → ava-stack-build-validator (frontend)
→ ava-summary → F5 → ...
```

**Quality gates nesta fase**: Requestor Inspection (pré-F3) + Package Approval + Summary Validator (pós-F3).

`human_gate_required: true` quando:
- `build_validator.status == TOOLCHAIN_UNAVAILABLE` (infra bloqueante)
- `cve_policy` com exceções expiradas detectadas (risk.level ≥ high)

---

## 3. Clean Architecture Alignment

```
Domain         → NO  — PBI modifica agentes LLM (.md), não código de domínio gerado
Application    → NO  — idem
Infrastructure → NO  — idem
Presentation   → NO  — idem
```

> **N/A** — todos os artefatos são arquivos de instrução LLM (`.md`, `.py`, `.yaml`).
> Clean Architecture aplica-se ao código **gerado** pelos agentes, não aos próprios agentes.

---

## 4. Agent File Structure

Todos os componentes são **modify-existing** — nenhum novo arquivo de agente criado.

```
# Agentes (implementados — sem alterações adicionais no corpo)
src/modules/ava-fabric-agents/tech-stack/agents/
├── build-validator-agent.md    (v2.3.0  — Podman, node_version guardrail, CVE policy, lockfile, ESLint)
├── build-fixer-agent.md        (v1.1.0  — lockfile_updated protocol)
└── coder-angular-frontend.md   (v1.0.0  — ESLint deps, angular.json lint target, .eslintrc.json)

# Utilitário (implementado)
src/shared/utils/
└── build_runner.py             (516 linhas — --runtime podman, --normalize-path, --node-version)

# Template de configuração — ÚNICA lacuna a corrigir
projects/_template/context/
└── project-config.yaml         ← adicionar bloco cve_policy em quality_gates
```

**Dispatch mode**: todos user-facing com SKILL.md existentes. `build_runner.py` invocado via `Bash:`.

---

## 5. module.yaml Impact

**Nenhuma alteração.** Todos os agentes já registrados:

```yaml
# src/modules/ava-fabric-agents/tech-stack/module.yaml
agents:
  - id: ava-stack-build-validator   # ✅ já registrado
  - id: ava-stack-build-fixer       # ✅ já registrado
  - id: ava-stack-angular-frontend  # ✅ já registrado
```

---

## 6. Observability & Trace Propagation

`trace_id` propagado via `shared-context.md`. Sem alterações nos schemas JSON.
`lockfile_updated: boolean` é rastreabilidade operacional no `fix_result` do build-fixer.

---

## 7. Schema Changes

| Schema | Change Required | Description |
|---|---|---|
| `agent-task.schema.json` | NO | Sem novos campos de input |
| `agent-result.schema.json` | NO | `lockfile_updated` é interno ao `fix_result` |
| `project-config.yaml` (template) | **YES** | Adicionar `quality_gates.cve_policy` |

---

## 8. Implementation Phases

### Phase 0 — Research ✅ CONCLUÍDO

Ver [research.md](./research.md). Resultado: 4/5 componentes implementados.
Único trabalho restante: `cve_policy` no template de configuração.

---

### Phase 1 — Config Template Update

#### Task 1.1 — Adicionar `cve_policy` ao template `project-config.yaml`

**Arquivo**: `projects/_template/context/project-config.yaml`

**Posição**: após a linha `dast_tool: "none"` dentro da seção `quality_gates`.

**Bloco a inserir**:

```yaml
  # ── CVE Policy ─────────────────────────────────────────────────────────────
  cve_policy:
    # Modo de tratamento de CVEs detectadas pelo npm audit / govulncheck / pip-audit.
    # zero_tolerance   : qualquer CVE high/critical bloqueia o build (padrão).
    # exceptions_allowed: CVEs listadas em accepted_exceptions são permitidas
    #                     até a data de expiração (campo expiry).
    mode: "zero_tolerance"             # zero_tolerance | exceptions_allowed
    accepted_exceptions: []
    # Exemplo de exceção (ativar apenas com mode: exceptions_allowed):
    # accepted_exceptions:
    #   - cve_id: "CVE-2024-XXXXX"
    #     package: "nome-do-pacote"
    #     reason:  "upstream fix indisponível — mitigado via WAF rule #42"
    #     expiry:  "2026-12-31"        # ISO date — exceção expirada é tratada como bloqueante
```

**Critério de aceite**: `grep -n "cve_policy" projects/_template/context/project-config.yaml`
retorna a linha inserida; build-validator (Step F3.5) lê o campo sem `KeyError`.

---

#### Task 1.2 — Sincronizar `projects/Meu-ERP/context/project-config.yaml`

Verificar se `cve_policy` já existe:

```bash
grep -n "cve_policy" projects/Meu-ERP/context/project-config.yaml
```

Se ausente: aplicar o mesmo bloco da Task 1.1 na posição equivalente.

---

### Phase 2 — Verification

Ver [quickstart.md](./quickstart.md) para os comandos de validação completos.

Checklist rápido:

```bash
# 1. Confirmar cve_policy no template
grep -n "cve_policy\|zero_tolerance\|accepted_exceptions" projects/_template/context/project-config.yaml

# 2. Confirmar node_version já presente
grep -n "node_version" projects/_template/context/project-config.yaml

# 3. Confirmar Podman support em build_runner.py
python src/shared/utils/build_runner.py --normalize-path "C:\\test" --runtime podman

# 4. Confirmar ESLint scaffolding no angular agent
grep -n "eslintrc\|angular-eslint" src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md | wc -l

# 5. Confirmar lockfile protocol no fixer agent
grep -n "lockfile_updated" src/modules/ava-fabric-agents/tech-stack/agents/build-fixer-agent.md
```

---

### Phase 3 — Documentation

#### Task 3.1 — Atualizar agent context no `copilot-instructions.md`

O bloco entre `<!-- SPECKIT START -->` e `<!-- SPECKIT END -->` deve apontar para este plano:

```markdown
<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan at
`specs/001-reliability-pipeline-evolution/plan.md`
<!-- SPECKIT END -->
```

#### Task 3.2 — Verificar `CHANGELOG.md`

O entry de `[2026-07-01]` documenta estas mudanças como "(staged)". Após conclusão das
Tasks 1.1/1.2, a esteira está completa. Nenhum novo entry de CHANGELOG é necessário — o
entry existente já é preciso. Se desejado, remover "(staged)" do cabeçalho da seção.

---

## 9. Complexity Tracking

| Gate | Status | Justification | Mitigating Controls |
|---|---|---|---|
| Article I — no hardcoded versions | PASS | ESLint usa `{angular_eslint_version}` e `{typescript_eslint_version}`; node_version de config | Variables resolvidas em runtime |
| Article X — version bump | PASS | build-validator já em v2.3.0; build-fixer em v1.1.0 — ambas MINOR | SemVer respeitado |
| CVE policy default behaviour | LOW RISK | Ausência de `cve_policy` no template não quebra agente (usa `zero_tolerance` por default via `\|\| []`) | Agente tem fallback explícito documentado |
| ESLint Angular 18+ compatibility | LOW RISK | ESLint 8 fixado para Angular ≤17; Angular 18+ usa ESLint v9 flat config — documentado no agente | Versão pinada com `^8.57.0`; nota de incompatibilidade no agent |

---

## 10. Test Strategy

| Test Type | Comando / Abordagem | Cenário (spec sec. 4) | CA |
|---|---|---|---|
| Config presence | `grep cve_policy project-config.yaml` | Seção cve_policy presente no template | CA05/CA17 |
| Podman path normalization | `build_runner.py --normalize-path --runtime podman` | Formato `C:/...` em Windows/MSYS2 | CA01/CA02 |
| Node image guardrail | Invocação manual do Step B0.3 com `frontend_version` | Build bloqueado | CA03/CA04 |
| CVE expired exception | Mock date > expiry no Step F3.5 | Build falha com `CVE_POLICY_EXPIRED` | CA06 |
| CVE valid exception | Mock date < expiry + mode: exceptions_allowed | Build prossegue | CA07 |
| Lockfile recovery | Simular `npm ci` out-of-sync + `lockfile_updated: false` | Novo ciclo de fixer disparado | CA08/CA09 |
| Lockfile field presence | `grep lockfile_updated build-fixer-agent.md` | Campo presente no output contract | CA10 |
| ESLint flat config detection | Projeto com `eslint.config.js` | Lint executado | CA11 |
| ESLint legacy detection | Projeto com `.eslintrc.*` | Lint executado | CA12 |
| ESLint absent — no fail | Remover configs ESLint | WARN emitido, build não falha | CA13 |
| Angular ESLint deps | Inspeção do `coder-angular-frontend.md` | 7 deps presentes no template `package.json` | CA14 |
| Angular lint target | Inspeção do `angular.json` gerado | `@angular-eslint/builder:lint` target presente | CA15 |
| `.eslintrc.json` generation | Run `coder-angular-frontend` Step 2.2.1 | Arquivo criado | CA16 |
