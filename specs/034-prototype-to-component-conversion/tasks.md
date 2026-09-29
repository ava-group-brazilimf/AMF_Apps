# Agent Development Tasks: Prototype → Component Conversion (P2C)

**Plan**: `specs/034-prototype-to-component-conversion/plan.md`
**Agents**: `ava-stack-angular-frontend` · `ava-stack-react-frontend` · `ava-stack-orchestrator` | **Phase**: F4 | **Module**: `tech-stack`

> Change type: `modify-existing` — 3 agent files + 3 new shared (non-agent) files
> Targets: `coder-angular-frontend.md` (3.0.0) · `coder-react-frontend.md` (2.0.0) · `orchestrator-stack.md` (bugfix)
> Complete categories sequentially. Mark [P] for tasks parallelizable within a category.

---

## Category 1 — Agent Frontmatter & Contract Definition

Both agents are `modify-existing`; no new agent file is created. SKILL.md files are unchanged.

- [X] **1.1** Verify `coder-angular-frontend.md` frontmatter contains only the four allowed keys.
  **Defect found**: `date: 2026-06-10` present (Article II violation) → remove.
- [X] **1.2** Bump `coder-angular-frontend.md` to `version: "3.0.0"` and add `Bash` to
  `allowed-tools` (Steps 2.17/10.1/11 already invoke it; the declaration was wrong).
- [X] **1.3** Verify `coder-react-frontend.md` frontmatter. **Defect found**: `date: "2026-07-14"`
  present → remove. Bump to `version: "2.0.0"`.
- [X] **1.4** Rewrite both `description` values (Portuguese, ending with the `Ativa com:` trigger
  list) to state the prototype-conversion role.
- [X] **1.5** Angular `## Input Contract`: move `prototype_screens` / `design_tokens` out of
  `# CRÍTICOS — HARD STOP` into a new `# OPCIONAIS — degradam com WARN` group; add
  `prototype_index`, `prototype_figma_spec`, `business_rules_catalog`, `coverage_threshold` and
  the `p2c_protocol` binding reference.
- [X] **1.6** Angular `## Output Contract`: add `prototype_conversion_map`, `screen_page`,
  `screen_spec` and `business-rules-implementation-frontend.json`.
- [X] **1.7** React `## Input Contract`: add the same optional prototype group plus
  `business_rules_catalog` (critical), `coverage_threshold`, `react_patterns` and `p2c_protocol`.
- [X] **1.8** React `## Output Contract`: add `prototype_conversion_map`, `screen_page`,
  `screen_test` and the five `mandatory_docs`.

## Category 2 — Agent Behavior & Instructions

- [X] **2.1** Create `src/modules/ava-fabric-agents/shared/prototype-conversion-protocol.md` with
  §1 authority rules, §2 passes P1–P4 + discrepancy matrix, §3 `prototype-conversion-map.json`
  schema, §4 business-rule binding, §5 API join, §6 assertion, §7 `P2C-W001..W009`,
  §8 `prototype_fidelity` enum, §9 Handoff fields, §10 RNF04 note.
- [X] **2.2** Add the `> Protocolo: [@prototype-conversion-protocol]` pointer to both agents, and
  the missing `> Governança: [@frontend-governance]` pointer to React.
- [X] **2.3** [P] Angular: new `#### 1.2d — Inventário do Protótipo (P2C — Passe 1)` after 1.2c and
  **before** 1.3 (it can add bounded contexts).
- [X] **2.4** [P] Angular `#### 1.3`: add `{screens}`, `{screens_by_bc}`, `{prototype_fidelity}`,
  `{coverage_threshold}`; `{bounded_contexts}` becomes a union with the map's BCs.
- [X] **2.5** [P] Angular `#### 1.4` PRE-FLIGHT: prototype rows `[CRÍTICO]` → `[OPCIONAL]`, moved to
  the WARNING list with the `master-orchestrator.md` rationale.
- [X] **2.6** Angular `### Guardrail G-DT` Passo 1: replace HARD STOP with the P2C-W004 fallback
  chain (`design-tokens.json` → `:root` of `index.html` → documented defaults) and record
  `design_tokens_source`.
- [X] **2.7** Angular: new `### Guardrail G-P2C` after G-DT, before Step 2 — master rule, archetype
  table, construct mapping, anti-stub marker. A guardrail (not a numbered step) → zero renumbering.
- [X] **2.8** [P] Angular Step 5: new `#### 5.9.1–5.9.6` (DS-010 breadcrumb, DS-011 data-table,
  DS-012 error-dialog, DS-013 help-panel, Toast/Confirm services, correlation-id interceptor edit);
  decimal numbering preserves 5.10–5.13.
- [X] **2.9** [P] Angular `#### 5.2` / `#### 5.7`: add the optional `severity`/`message` and
  `messages` inputs (backwards compatible — zero-input mode keeps the original behaviour).
- [X] **2.10** [P] Angular `#### 5.12` / `#### 5.13`: export the new components and services;
  update the file count 29 → 43.
- [X] **2.11** Angular `#### 7.3`–`#### 7.6`: **replace bodies, keep numbers** — one page per
  screen under `src/app/{bc}/pages/{screen_id}/`, template chosen by archetype, one route per
  screen with `redirectTo` for the initial view. This is where the `<ul>@for … <li>{{ item.id }}</li>`
  stub dies.
- [X] **2.12** Angular `#### 7.7`: operation set = union(contract operations, screen `API:`
  metadata); divergence classification and the "contract wins" rule.
- [X] **2.13** [P] Angular `#### 9.1` / `#### 9.2`: `navItems` from `shell.nav_items`, grouped,
  in the prototype's sidebar order; `#### 9.4`: note on the default route.
- [X] **2.14** Angular `#### 9.5.1`: add `codeCoverageReporters` including `json-summary` and a
  `karma.conf.js` with a no-sandbox headless launcher.
- [X] **2.15** Angular: new `#### 9.5.6` — one spec per converted screen, including the literal
  title assertion and one `it()` per bound BR-XXXX.
- [X] **2.16** Angular: new `### Step 9.8` — fidelity assertion (existence + anti-stub), bounded
  repair loop (max 3), map rewrite with `phase: "verified"`, business-rule assertion.
- [X] **2.17** Angular: new `### Step 9.9` — `npm ci` → `ng build` → `CHROME_BIN` probe →
  `ng test --code-coverage` → coverage read → production build.
- [X] **2.18** Angular `#### 10.1`: add the `CONVERSÃO DE PROTÓTIPO (P2C)` block to the Consistency
  Gate; extend the unit-test block.
- [X] **2.19** Angular `#### 10.2` / `#### 10.3`: `## Fidelidade ao Protótipo`,
  `## Divergências Protótipo × Contrato de API`, `## Regras de Negócio Espelhadas`, the mandatory
  deferred-screens list, and a screen-level `ChangedScreens.md`.
- [X] **2.20** Angular `## Handoff` + `## Consistency Verification Gate`: new P2C fields and
  `COMPLETED` preconditions; **delete** the now-satisfied `<ul>` TODO from `## TODOs Pendentes`.
- [X] **2.21** Angular `### Step 11`: `--version 3.0.0` (rule E3 of `verify_agent_observability.py`).
- [X] **2.22** React: rewrite the agent body — `## Padrões Obrigatórios`, PRE-FLIGHT (1.8),
  `Guardrail G-DT`, `Guardrail G-P2C-React`, Steps 1.4 (P2C) / 1.5 (business rules) / 1.6 (API
  contract) / 1.7 (tokens), 2.7 (vitest + test utils) / 2.8 (Scaffold Gate), Step 3 (RX-001..RX-014),
  Step 4 (per-BC data layer), Step 5 (converted screens + tests), Step 6 (router/AppShell),
  Step 6.5 (assertion), Step 7 (quality gate), Step 8 (delivery docs),
  `## Consistency Verification Gate`, `## Handoff`, `## Security Compliance Review Gate`,
  `## Accessibility Invariants`, `## Testing Requirements`, `### Step 10` with `--version 2.0.0`.
- [X] **2.23** `orchestrator-stack.md`: replace the hardcoded `--manifest angular` in the frontend
  scaffold verification with `--manifest {frontend_framework}`, plus the non-blocking WARNING rule
  when no manifest exists for the stack.

## Category 3 — Shared Schema Updates

- [X] **3.1** Create `src/shared/data/patterns/react/react-patterns-reference.md` mirroring the six
  sections of the Angular reference (naming, RHF+Zod, smart/dumb, money/date formatting, PT-BR
  Unicode-safe regex, dates) plus TanStack query-key and Zustand slice conventions.
- [X] **3.2** Create `src/shared/data/scaffold-manifests/react-scaffold-manifest.yaml`.
  ⚠️ Keep the flat shape (`path`/`category`/`blocking`/`error_if_missing`) — the no-PyYAML fallback
  parser in `verify_scaffold.py` recognises nothing else. `error_if_missing` carries the real build
  error text.
- [X] **3.3** Create `contracts/prototype-conversion-map.schema.json` (draft-07,
  `additionalProperties: false` at every level, `const` on `schema_version`/`artifact_id`,
  `definitions` for repeated shapes).

## Category 4 — Module Registration

- [X] **4.1** `tech-stack/module.yaml`: version `1.4.0` → `1.5.0`. Both agents are already
  registered with the correct `routing_key`; no entry added or removed.
- [X] **4.2** Confirm the three new files need no `module.yaml` entry — they are a shared include
  and two data references, not agents, and are invisible to `agent_registry.py`.

## Category 5 — Quality Gate Checklists

- [X] **5.1** Create `checklists/requirements.md` with the `## IMFAI Constitution Compliance`
  block (CHK-C01..CHK-C07) copied **verbatim as the first section**, then the feature-specific
  categories.

## Category 6 — Acceptance Validation & QA Integration

- [ ] **6.1** Run the agent conformance chain:
  ```
  python src/shared/tools/agent_registry.py --agent ava-stack-react-frontend
  python src/shared/utils/verify_agent_observability.py --agent ava-stack-react-frontend
  python src/shared/utils/verify_agent_observability.py --agent ava-stack-angular-frontend
  ```
  Expect exit 0. Rule **E3** compares the observability block's `--version` literal against the
  frontmatter — both were updated in tasks 1.2/1.3 and 2.21/2.22.
- [ ] **6.2** Regenerate the Copilot wrappers and confirm no drift:
  ```
  python src/shared/tools/generate_agent_wrappers.py --phase F4
  python src/shared/tools/generate_agent_wrappers.py --check
  ```
  The wrapper carries `metadata.version`, so `--check` reports drift until regeneration.
- [ ] **6.3** Confirm the React manifest resolves:
  `python src/shared/utils/verify_scaffold.py --manifest react --root <any dir>`
  must fail on missing files, **not** with `FileNotFoundError` on the manifest itself.
  ⚠️ Run from the repository root — the first manifest search path resolves to a non-existent
  `src/shared/shared/data/...`.
- [ ] **6.4** Run the SC-01..SC-11 grep checks from spec §Success Criteria.
- [ ] **6.5** Pipeline run with a prototype present (SC-14).
- [ ] **6.6** Pipeline run with `outputs/tobe/prototype/` renamed away (SC-15) — expect the
  P2C-W001 box, `prototype_fidelity: none`, `assertion.status: SKIPPED`, generation completes.
- [ ] **6.7** Pipeline run on a React project to exercise `--manifest react` and the corrected
  orchestrator gate.

## Category 7 — Documentation & Catalog Update

- [X] **7.1** `CHANGELOG.md`: MAJOR entry for both agents, new files, the orchestrator bugfix and
  the two Article II corrections.
- [X] **7.2** `docs/agents-catalog.md`: update the `ava-stack-angular-frontend` block and **both**
  `ava-stack-react-frontend` blocks (the file has two, at roughly lines 637 and 755).
- [ ] **7.3** Confirm no other doc pins the old versions
  (`docs/full-pipeline-guide.md`, `docs/summary-validator-guide.md`).

---

## Completion Checklist

- [X] Both agents' frontmatters conform to Article II (four keys only)
- [X] Observability `--version` literals match the frontmatters
- [X] Agent bodies written in Brazilian Portuguese (Article V)
- [X] BDD scenarios cover nominal, edge and gate paths (Article VI)
- [X] `module.yaml` version bumped (Article IV)
- [X] `CHANGELOG.md` entry prepared (Article X)
- [X] SKILL.md routing unchanged and still valid (Article XI)
- [ ] Category 6 acceptance chain green
- [ ] End-to-end pipeline validated in both prototype-present and prototype-absent modes

---

## Dependencies

```
Cat 1 ──▶ Cat 2 ──▶ Cat 6
          ▲
Cat 3 ────┘          Cat 4, Cat 5, Cat 7 may run in parallel after Cat 2
```

Task 2.1 (shared protocol) blocks 2.2–2.22 — both agents reference it.
Task 3.1 blocks 2.22 — the React agent declares it as a binding reference.
Task 3.2 blocks 6.3.

## Parallel Execution Within Category 2

`2.3`, `2.4`, `2.5` (Angular Step 1 edits) · `2.8`, `2.9`, `2.10` (Angular Step 5 edits) ·
`2.13` (sidenav) are independent of each other once 2.1 and 2.7 have landed.

`2.22` (React) is independent of every Angular task after 2.1 and 3.1 — different file, greenfield.

## MVP Scope

If the work must be split, land in this order — each step is independently reviewable and safe:

1. **Read-only Angular phase** — Cat 1 + tasks 2.1–2.7. Changes no generated output.
2. **Additive Angular phase** — tasks 2.8–2.10. New shared components; nothing breaks.
3. **Behaviour-changing Angular phase** — tasks 2.11–2.13.
4. **Angular gates** — tasks 2.14–2.21.
5. **React** — tasks 2.22 + 3.1 (greenfield; nothing to preserve).
6. **Orchestrator fix + manifest** — tasks 2.23 + 3.2.
7. **Docs and validation** — Cat 4, 5, 6, 7.
