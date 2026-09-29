# Tasks: Date Format Guardrails

**Plan**: `specs/007-date-format-guardrails/plan.md`
**Status**: Ready for implementation

> **Context** (research finding): All guardrail content (G10, G-DATE, Padrões de Data e Hora)
> already exists in the target files. These tasks cover the remaining administrative steps:
> version bumps, frontmatter deduplication, and CHANGELOG entry.

---

## Category 1 — Pre-flight: Confirm current state

- [ ] **1.1** Confirm G10 is present in `coder-dotnet-backend.md` and current version is `1.0.0`
  ```powershell
  Select-String "src\modules\ava-fabric-agents\tech-stack\agents\coder-dotnet-backend.md" -Pattern "G10|version:"
  ```
  **Expected**: G10 heading present; `version: "1.0.0"` on line 10.

- [ ] **1.2** Confirm G-DATE is present in `coder-angular-frontend.md` and duplicate frontmatter exists
  ```powershell
  $lines = Get-Content "src\modules\ava-fabric-agents\tech-stack\agents\coder-angular-frontend.md"
  $lines | Select-String "version:|G-DATE" | Select-Object LineNumber, Line
  ```
  **Expected**: G-DATE heading present; two `version:` lines (lines 3 and 12).

- [ ] **1.3** Confirm "Padrões de Data e Hora" section exists in `angular-patterns-reference.md`
  ```powershell
  Select-String "src\shared\data\patterns\angular\angular-patterns-reference.md" -Pattern "Padrões de Data"
  ```
  **Expected**: one match.

---

## Category 2 — Implementation

All three file targets are independent. T2.1a and T2.1 are sequential (same file); T2.2 and T2.3 can run in parallel with each other and with T2.1a/T2.1.

- [ ] **2.1a** `coder-dotnet-backend.md` — add missing G10 rules (findings F1 + U3)
  - File: `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`
  - In G10 "Regras obrigatórias" list, insert after `DateTimeKind.Local → PROIBIDO` bullet:
    - `` `DateTimeKind.Unspecified` → **PROIBIDO** em DTOs de API; aplicar `DateTime.SpecifyKind(value, DateTimeKind.Utc)` ou `ToUniversalTime()` antes de retornar ``
    - `Quando disponível, **prefira `DateTimeOffset`** a `DateTime` em tipos de resposta de API — o offset é explícito e elimina ambiguidade de fuso horário`

- [ ] **2.1** `coder-dotnet-backend.md` — bump `version: "1.0.0"` → `version: "1.1.0"` *(after 2.1a)*
  - File: `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`
  - Line 10: change `version: "1.0.0"` to `version: "1.1.0"`

- [ ] **2.2** [P] `coder-angular-frontend.md` — fix duplicate frontmatter + bump version
  - File: `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md`
  - Replace the entire frontmatter block (lines 1–13, between the two `---` delimiters) with:
    ```yaml
    ---
    name: ava-stack-angular-frontend
    version: "1.1.0"
    date: 2026-07-07
    description: |
      Gera código Angular production-ready com boas práticas: standalone
      components, signals, lazy loading, MSAL para auth, NgRx para state.
      Versão lida de `tobe_stack.frontend_version` em project-config.yaml.
      Ativa com: "gerar componente Angular", "criar tela", "Angular frontend",
      "NgRx store", "MSAL authentication".
    allowed-tools: Read, Write, Edit, Glob
    ---
    ```
  - Result: single `version` field (no duplicates), `date` updated to `2026-07-07`.

- [ ] **2.3** [P] `CHANGELOG.md` — add two version bump entries under `## [Unreleased]`
  - File: `CHANGELOG.md` (repo root)
  - Add inside the `## [Unreleased]` block (create the block if absent):
    ```markdown
    ### Changed
    - `coder-dotnet-backend` 1.0.0 → 1.1.0: Added G10 — DateTime Serialization guardrail
      enforcing ISO 8601 UTC (`DateTimeKind.Utc`, format `"o"`); `DateTimeKind.Local`
      proibido em tipos retornados pela API.
    - `coder-angular-frontend` 1.0.0 → 1.1.0: Added G-DATE — Formato de Data pt-BR guardrail
      enforcing `LOCALE_ID=pt-BR`, `registerLocaleData`, `MAT_DATE_LOCALE=pt-BR` e
      `DatePipe:'dd/MM/yyyy'` explícito. Fixed duplicate `version`/`date` frontmatter keys.
    ```

---

## Category 3/4 — Module Registration

**SKIP** — modify-existing change; no new agents; `module.yaml` unaffected.

---

## Category 5 — Quality Gate Checklists

- [ ] **5.1** After 2.1: confirm single `version: "1.1.0"` in `coder-dotnet-backend.md`
  ```powershell
  Select-String "src\modules\ava-fabric-agents\tech-stack\agents\coder-dotnet-backend.md" -Pattern "version:"
  ```
  **Expected**: exactly one match → `version: "1.1.0"`.

- [ ] **5.2** After 2.2: confirm single `version: "1.1.0"` and no duplicate keys in `coder-angular-frontend.md`
  ```powershell
  $f = "src\modules\ava-fabric-agents\tech-stack\agents\coder-angular-frontend.md"
  $vCount = (Select-String $f -Pattern "^version:").Count
  Write-Host "version: lines = $vCount"   # must be 1
  Select-String $f -Pattern 'version: "1.1.0"'  # must match
  ```

- [ ] **5.3** Constitution Article II compliance: frontmatter block is well-formed YAML (no duplicate keys, name unchanged, SemVer pattern `1.1.0` valid).

- [ ] **5.4** Constitution Article X compliance: change is MINOR (new behavior, no Output Contract change) — version increment `1.0.0 → 1.1.0` is correct.

---

## Category 6 — Acceptance Validation

Run quickstart scenarios from [quickstart.md](quickstart.md):

- [ ] **6.1** Scenario A — G10 present + version 1.1.0 in `coder-dotnet-backend.md` → **PASS**
- [ ] **6.2** Scenario B — G-DATE present + no duplicate keys + version 1.1.0 in `coder-angular-frontend.md` → **PASS**
- [ ] **6.3** Scenario C — "Padrões de Data e Hora" present in `angular-patterns-reference.md` → **PASS**
- [ ] **6.4** Scenario D — `CHANGELOG.md` contains both version bump entries → **PASS**

---

## Category 7 — Documentation

- [ ] **7.1** `CHANGELOG.md` updated (covered by task 2.3 above).
- [x] **7.2** SpecKit documentation complete: spec / plan / research / data-model / quickstart / checklists.

---

## Completion Checklist

- [ ] `coder-dotnet-backend.md` at version `1.1.0`
- [ ] `coder-angular-frontend.md` at version `1.1.0`, single `version`/`date` in frontmatter
- [ ] `CHANGELOG.md` has entries for both bumps
- [ ] All 4 quickstart validation scenarios pass
