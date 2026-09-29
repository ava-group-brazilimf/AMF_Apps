# Data Model — 025 Summary Test Cases AS-IS Menu

## New D.* Field: `D.testCases`

**Type**: `Array<TestCaseEntry>`

**Source**: `projects/{project_name}/outputs/asis/qa/test-cases.md`

**Producer**: `ava-asis-bridge-fastqa` (Step 17b — consolidation from `fastqa/manual_test/test_cases/**/PBI-*.md`)

**Serialisation**: `safe_json(test_cases)` — identical to `testGaps` serialisation

**Empty value**: `[]` — when `test-cases.md` is absent or has no `## CT-` headings

---

### `TestCaseEntry` schema

```typescript
interface TestCaseEntry {
  id:              string;   // "CT-001" — extracted from ## CT-NNN heading
  title:           string;   // "Baixa Completa de Conta a Pagar (Happy Path)"
  priority:        string;   // "P0" — from **Prioridade**: field
  type:            string;   // "Funcional" — from **Tipo**: field
  module:          string;   // "Contas a Pagar — Baixa" — from **Módulo**: field
  rules:           string;   // "BR-0001, BR-0002" — from **Regras**: field
  steps:           number;   // count of data rows in ### Passos table (excludes header/separator rows)
  preconditions:   string;   // raw text under ### Pré-condições subsection
  steps_raw:       string;   // raw Markdown of the ### Passos table (for future detail modal)
  postconditions:  string;   // raw text under ### Pós-condições subsection
}
```

---

### Parsing rules

| Field | Source pattern | Default when absent |
|---|---|---|
| `id` | `^## (CT-\d+)` heading | — (block skipped if no CT- heading) |
| `title` | text after `—` or `-` on heading line | `""` |
| `priority` | `\*{1,2}Prioridade\*{1,2}\s*:\s*([^|\n*]+)` | `""` |
| `type` | `\*{1,2}Tipo\*{1,2}\s*:\s*([^|\n*]+)` | `""` |
| `module` | `\*{1,2}Módulo\*{1,2}\s*:\s*([^\n]+)` | `""` |
| `rules` | `\*{1,2}Regras\*{1,2}\s*:\s*([^\n]+)` | `""` |
| `steps` | count of `|`-rows in `### Passos` table body (exclude header, separator, and `#` column) | `0` |
| `preconditions` | body of `### Pré-condições` subsection | `""` |
| `steps_raw` | full text of `### Passos` subsection | `""` |
| `postconditions` | body of `### Pós-condições` subsection | `""` |

---

### Example parsed entry (from `Meu-ERP_w_AST/test-cases.md` CT-001)

```json
{
  "id": "CT-001",
  "title": "Baixa Completa de Conta a Pagar (Happy Path)",
  "priority": "P0",
  "type": "Funcional",
  "module": "Contas a Pagar — Baixa",
  "rules": "BR-0001, BR-0002",
  "steps": 8,
  "preconditions": "- Conta a pagar cadastrada: valor R$ 1.000,00, vencimento 30/07/2026\n- Conta corrente cadastrada: Banco Bradesco, saldo R$ 5.000,00\n- Lançamentos anteriores ausentes para esta conta",
  "steps_raw": "| # | Ação | Resultado Esperado |\n|---|---|---|\n| 1 | Abrir frmBaixarTituloLancamentosCP... | ...",
  "postconditions": "- Conta a pagar com status \"pago\"\n- Saldo da conta corrente debitado corretamente\n- Lançamento registrado para auditoria"
}
```

---

## No existing schema changes

No existing `D.*` fields are modified. `D.testCases` is a purely additive new field.
