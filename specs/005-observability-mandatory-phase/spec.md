# Agent Specification: Observability Mandatory Phase (repo-wide)

**Feature Branch**: `005-observability-mandatory-phase`
**Created**: 2026-07-04
**Status**: Implemented
**Change Type**: modify-existing (97 agent files, bulk) + 2 shared docs
**Input**: "Verifique a implementação da observabilidade... A specs/004... não corrigiu o problema... crie uma fase nos agentes para executar o script de observabilidade de modo obrigatório... a implementação não pode só funcionar para Meu-ERP... Documente via spec-kit."

---

## 1. Problem Statement

`specs/004-observability-self-report-activation-fix/` moved the self-report
call into each of 5 orchestrator files' real completion gate. The user tested
this directly (running `orchestrator-asis.md` standalone) and confirmed: it
**still did not fire**. Critically, when asked whether other, previously
"proven-reliable" Bash calls in that same file (NTP timing,
`build_summary_comprehensive.py`) fired, the answer was **no — nothing
executed at all**.

A fresh investigation established a **two-level root cause**:

1. **Environmental** (new finding, not previously identified): there is no
   enforced technical wiring anywhere in this repo connecting the
   ava-fabric-agents' `allowed-tools:` frontmatter to any real tool-calling
   harness. The only proven-working tool-calling pattern in this repo is the
   unrelated speckit `.agent.md`/`.prompt.md` convention (GitHub Copilot
   Agent Mode), which does not use `allowed-tools:` at all. There is no
   runner/wrapper script anywhere — "paste the `.md` into a chat" is the
   entire invocation mechanism. **No markdown wording can force tool
   execution if the invoking surface has no live tool access** — this is a
   real, unavoidable constraint, stated explicitly rather than glossed over.
2. **Structural/phrasing**: independent of #1, the previous instruction —
   `- Registrar auto-observabilidade (ver \`@observability-self-report\`...)`
   — read as a parenthetical, documentation-style note (like the passive
   `@governance-apps` i18n reference), not an unambiguous directive to invoke
   a tool right now. The user's own report (the orchestrator printed/narrated
   the instruction rather than executing it) is direct evidence of this.

## 2. Decision

Per explicit user instruction, keep the mechanism inside each agent file as
a dedicated, self-contained, mandatory **Phase** (not indirection via a
shared reference doc for the actionable command). To maximize reliability
within the environmental constraint:

- **No reference-doc indirection for the actionable command** — every agent
  now carries the full command, including standalone-fallback and
  failure-isolation logic, written out literally in its own file.
- **Maximally imperative language**: `⛔ EXECUÇÃO OBRIGATÓRIA — ISTO NÃO É
  TEXTO DESCRITIVO. Você DEVE invocar... Não narre esta etapa — EXECUTE-A.`
- **Concrete values baked in** at edit time (`--agent`, `--phase`,
  `--version` are the agent's real, current values, not placeholders to
  infer) — only `{project_name}` (already resolved earlier in each agent),
  `--status`, and token/duration estimates remain runtime values.
- Applied to **all 97 previously-touched agent files** (92 leaf agents this
  pass + the 5 orchestrator-tier files re-strengthened), not just the 5
  orchestrators.
- The tool itself already works for **any** project name — verified directly
  in this session with both `Meu-ERP-001` and an arbitrary
  `Another-Random-Project-XYZ` project, producing correct, isolated output
  in both cases. The fix here is entirely about the agent-side instruction,
  not the tool.
- The environmental constraint (#1) is documented prominently, not hidden —
  in `observability-self-report.md`, `src/shared/tools/README.md`, and here.

## 3. Anchor Detection Strategy

A structural survey of the repo (10 sampled files + a full 91-file scan)
found no single universal heading for "the real last step" — 5 different
vocabularies are in use. A tiered detector was built and applied:

| Tier | Pattern | Files matched |
|---|---|---|
| 1 | `Handoff` / `Completion Signal` heading | 23 |
| 2 | `Validation Gate` / `Verification Protocol` / `Integrity Check` / `Checklist de Conclusão` / `Critério de Aceite` heading | 26 |
| 3 | Last `STEP`/`Step`/`PASSO`/`Passo` numbered block, or `Execution Steps`/`Passos de Execução` heading | 21 |
| 4 | Last `## Guardrails` / `Regras de Execução` heading | 10 |
| 5 | None found — fallback to before `## i18n` | 12 (9 stub agents + 3 genuinely simple agents, individually reviewed) |

Headings inside fenced code blocks were excluded from detection (avoids a
confirmed false-positive: `exploratory-agent.md` has a `## Handoff` heading
*inside* a templated output spec, not its own return-to-caller protocol).

**Idempotent removal**: any existing (broken) `## Observability Self-Report`
section was located and excised — regardless of where it currently sat —
before inserting the new phase at the correctly-detected anchor. This
uniformly repaired 3 files where the old section was severely misplaced near
the top of the file (`baseline-test-generator-asis.md` line 42/616,
`behavior-mapping-agent.md` line 38/436, `coder-angular-frontend.md` line
166/3107) — verified individually by direct read after the batch pass, not
merely assumed fixed.

**Excluded**: 4 `db-analyzer/skills/*.md` files (inlined, not independently
dispatched — same exclusion as specs/003), and 2 stray untracked `" copy"`
duplicate files (`orchestrator-asis copy.md`, `master-orchestrator copy.md`)
— repo hygiene artifacts, not real dispatch targets.

## 4. New Phase Content (template)

```markdown
## FASE OBRIGATÓRIA — Registro de Observabilidade (EXECUTAR AGORA)

⛔ **EXECUÇÃO OBRIGATÓRIA — ISTO NÃO É TEXTO DESCRITIVO.** Você DEVE invocar a
ferramenta Bash com o comando abaixo literalmente, antes de retornar ao
chamador ou emitir qualquer sinal de conclusão. Não narre esta etapa — EXECUTE-A.

​```
Bash: python src/shared/tools/pipeline_observer.py -p {project_name} track \
  --agent {agent_id} --phase {phase} --version {version} \
  --status {completed|failed|skipped} \
  --tokens-in {tokens_in_estimados} --tokens-out {tokens_out_estimados} \
  --duration-ms {duracao_medida_ms}
​```

SE retornar "ERROR: No active run" → executar uma vez:

​```
Bash: python src/shared/tools/pipeline_observer.py -p {project_name} init --run-type standalone --model "Claude Opus 4.6"
​```

… então repetir a chamada de `track` acima uma única vez.
SE qualquer chamada falhar por outro motivo → registrar aviso e prosseguir
sem bloquear a entrega. Nunca repetir mais de uma vez.
```

`{agent_id}`, `{phase}`, `{version}` are concrete literal values per file
(e.g. `ava-qa-scenario-generator`, `F5`, `2.1.0`), not placeholders — computed
from each file's own frontmatter `name:`/`version:` and its module directory
(`asis-diagnostic`→F1, `tobe-architecture`/`prototype`→F2, `tech-stack`→F3,
`qa-agents`→F5, `devops-agents`→F7, `deliverables`→F6, `summary`→F8 — derived
from directory, not name-prefix, since several agents' `name:` field doesn't
follow the `ava-{phase}-{role}` convention, e.g. `ava-docs-tobe`,
`ava-test-plan-tobe`).

## 5. User Scenarios (Given-When-Then)

### Scenario 1 — Any agent, any project, produces real output when tool-calling is active (CA01)

**Given** an agentic surface with live tool execution (e.g. Claude Code with
Bash permission), **When** any agent reaches its `## FASE OBRIGATÓRIA` step,
**Then** `projects/{project}/outputs/observability/{agent_id}/metrics.json`
is created — verified directly for `Meu-ERP-001` and for an arbitrary,
never-before-seen project name in this session.

### Scenario 2 — Previously-misplaced files now anchor correctly (CA02)

**Given** the 3 known severely-misplaced files, **When** the batch fix runs,
**Then** each file's `## FASE OBRIGATÓRIA` section is found immediately after
its real completion point (Completion Signal / STEP 6 COMPLETION-SIGNAL /
10.4 Handoff respectively), not near the top of the file.

### Scenario 3 — No agent lost its command in the rewrite (CA03)

**Given** all 97 touched files, **When** grepped for the literal command,
**Then** every one contains exactly one
`pipeline_observer.py -p {project_name} track` invocation with balanced
code fences.

### Scenario 4 — Honest environmental limitation (CA04, negative)

**Given** a surface without live tool-calling (e.g. a plain narrative chat),
**When** an agent "runs" there, **Then** no observability output is produced
— and this is documented as an inherent, unfixable-by-markdown limitation,
not silently promised away.

## 6. Quality Gate Requirements

- [x] No agent `name:`/`description:`/`allowed-tools:` contract fields changed
- [x] BDD scenarios cover success, repaired-misplacement, completeness, and the honest environmental limitation
- [x] No `[NEEDS CLARIFICATION]` markers remain
- [x] The environmental root cause is stated as a real, unresolved constraint — not implied fixed

## 7. Dependencies

- `pipeline_observer.py` (unchanged, already proven to work for any project name)
- `specs/002`-`specs/004` (prior iterations; this spec supersedes their agent-side approach, not their tool-level work)

## 8. Exclusions

- The 4 `db-analyzer/skills/*.md` files and 2 stray `" copy"` files — excluded, not dispatched targets / repo hygiene.
- No change to `pipeline_observer.py` itself.
- No fix for the pre-existing, unrelated fence imbalance in `solution-vb.md` (confirmed present in git HEAD, predates all observability work) — out of scope.
- No guarantee of execution on surfaces without live tool-calling — explicitly a non-goal, since it's not fixable from within `.md` files.

## 9. Assumptions

- Phase derivation by module directory is more reliable than by `name:` prefix, since several agents' names don't follow the `ava-{phase}-{role}` convention.
- Baking concrete `agent_id`/`phase`/`version` into each file (rather than leaving them as agent-resolved placeholders) removes one more point of possible LLM hedging/paraphrasing.

## Success Criteria

| Criterion | Measure |
|---|---|
| Coverage | 97/97 previously-touched files now have exactly one, correctly-placed, self-contained mandatory phase |
| Structural integrity | 0 unexpected fence imbalances (1 pre-existing, unrelated case documented) |
| Tool genericity | Verified directly against 2 different project names in the same session |
| Honesty | Environmental constraint documented in 3 places (shared doc, tools README, this spec), not hidden |
