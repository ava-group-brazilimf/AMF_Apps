# Research: `gen_screen_flow.py` .NET (C#/VB) Compatibility Gap

**Date**: 2026-08-05
**Reporter**: IMFAI pipeline team
**Scope**: `src/shared/tools/gen_screen_flow.py`
**Reference project**: `projects/nopcommerce` (nopCommerce 3.90, .NET Framework/C#)
**Related spec**: [spec.md](spec.md) (Screen-Flow Batch Protocol + Completude Assertion)

---

## 1. Summary

The `gen_screen_flow.py` tool successfully generates Mermaid screen-flow diagrams for Delphi projects, but **fails to recognize C# / VB.NET** projects. On the reference `nopcommerce` project it exits with `ERROR: No forms`, producing zero output even though the .NET AST analyzer extracted 116 form/page records.

This document contains the root-cause analysis and the implementation plan to make the script language-agnostic while preserving Delphi compatibility.

---

## 2. Reproduction

Command used (after `git pull`):

```powershell
python src/shared/tools/gen_screen_flow.py `
  --project nopcommerce `
  --input  "C:\_git\imfai-ava-tools\ava-fabric-dotnet-analyzer\out\nopcommerce\extraction\02_form_business_rules.json" `
  --output "projects/nopcommerce/outputs/asis/docs/screen-flow.mmd"
```

Output observed:

```text
[gen_screen_flow] BC map: 0 BCs, 0 units, 0 tokens
[gen_screen_flow] Navigation map: 1 domains loaded
ERROR: No forms
```

---

## 3. Root-Cause Analysis

### 3.1 Script expects the Delphi AST schema only

Current code in `gen_screen_flow.py` (line 191):

```python
forms = json.load(fh).get('payload', {}).get('forms', [])
```

The .NET analyzer emits a **different envelope** for the same artifact `02_form_business_rules.json`:

| Aspect | Delphi analyzer | .NET analyzer |
|---|---|---|
| Top-level keys | `payload` (lowercase) | `Artifact`, `SchemaVersion`, `Payload`, `_Volatile` (PascalCase) |
| Form collection | `payload.forms` (list) | `Payload` (list, directly) |
| Form record keys | `form_name`, `source_file`, `field_count` … | `Name`, `FormType`, `BaseType`, `Controls`, `EventHandlers`, `SourceRef` |
| Source file field | `source_file` | `SourceRef.file` |
| Field count | `field_count` | `len(Controls)` |

Example .NET entry:

```json
{
  "Name": "ActivityLogController",
  "FormType": "winforms",
  "BaseType": "BaseAdminController",
  "Controls": [],
  "EventHandlers": [],
  "SourceRef": {
    "file": "src\\Presentation\\Nop.Web\\Administration\\Controllers\\ActivityLogController.cs",
    "line": 16,
    "containing_type": "ActivityLogController"
  }
}
```

Because the script looks for `payload.forms[]`, it reads **zero** forms from the .NET artifact.

### 3.2 `bounded-context-map.md` parser is Delphi-oriented

`parse_bc_map()` recognizes only:

- `### BC-XX: Name` headings (H3) followed by `**Units list**: u1.pas, u2.pas, ...`
- A legacy markdown-table fallback.

The .NET solution agents (`ava-asis-solution-dotnet`, `ava-asis-solution-vbnet`) emit:

```markdown
## BC-01: Catalogo
**Forms/Pages**: 12
**Files**: CatalogController.cs, ProductController.cs, ...
**LOC**: 1 234
**Risk**: MEDIUM — ...
```

So even when a BC map exists for a .NET project, the script extracts **zero units/tokens** and falls back to directory-name classification or `Unclassified`.

### 3.3 Tokenizer and noise list favor Delphi vocabulary

Current tokenizer splits PascalCase/camelCase:

```python
def tokenize(text):
    return [p.lower() for p in re.findall(r'[a-z]+|[A-Z][a-z]*', text) if len(p) >= 3]
```

This works for `SysEstq` → `sys`, `estq`, but is too narrow for .NET file names that also contain underscores, hyphens, and ASP.NET suffixes such as `CatalogController.cs`, `OrderDetails.aspx`, `ProductList.ascx`.

`NOISE` currently:

```python
NOISE = {'frm','dfm','pas','web','form','data','unit','main','base','lib','utils','test'}
```

It does not include .NET/ASP.NET noise tokens (`cs`, `vb`, `aspx`, `cshtml`, `ascx`, `svc`, `resx`, `designer`, `xaml`, `config`, `controller`, `view`, `model`, `page`), so these tokens can drown out domain tokens when matching against a BC map.

### 3.4 Form classification relies on stripped file stems

`classify_form()` uses `Path(source_file).stem`. For Delphi this usually equals the unit name (`uSysEstq`). For .NET the stem is `ActivityLogController`, and the meaningful domain part is inside the PascalCase name. The existing tokenization partially handles this, but only when the BC map tokens were correctly loaded (see 3.2).

---

## 4. Required vs. Nice-to-Have

| # | Change | Category | Reason |
|---|---|---|---|
| 1 | Detect both Delphi and .NET JSON schemas in `gen_screen_flow.py` | **Required** | Without this the script sees zero forms on C#/VB projects. |
| 2 | Normalize .NET keys to the internal `form_name`/`source_file`/`field_count` model | **Required** | Needed for reuse of downstream classification/diagram logic. |
| 3 | Parse `## BC-NN: Nome` + `**Files**: ...` in `parse_bc_map()` | **Required** | Without this .NET BC maps are ignored and classification degrades. |
| 4 | Expand `NOISE` and tokenizer for .NET/ASP.NET naming | **Required** | Improves token-based BC matching for C#/VB. |
| 5 | Add automated unit tests for both schemas | **Required** | Prevents Delphi regression and documents .NET support. |
| 6 | Update `solution-dotnet.md` Step 9.4 to remove the "fallback adaptado" | **Should do** | Makes .NET invocation of the script mandatory, matching Delphi behavior. |
| 7 | Apply the same schema normalization to `gen_er_diagram.py` | **Important but separate** | Same `payload` vs `Payload` problem applies to ER diagrams; out of scope for this fix. |

---

## 5. Proposed Implementation Plan

### Phase 1 — Normalizar leitura do JSON de formas

1. Introduzir `extract_forms(raw_data: dict) -> list[dict]` em `gen_screen_flow.py`:
   - Se `payload` existir e for dict com `forms` → retornar `payload['forms']` (Delphi).
   - Se `Payload` existir e for list → retornar `Payload` (.NET).
   - Se `payload` existir e for list → retornar `.NET alias compat`.
2. Introduzir `normalize_form(record: dict) -> dict` que converte para:
   ```python
   {
       "form_name": str,
       "source_file": str,
       "field_count": int,
       "form_type": str   # winforms | webforms | mvc | etc.
   }
   ```
   - Delphi: `form_name` ← `form_name`, `source_file` ← `source_file`, `field_count` ← `field_count`.
   - .NET: `form_name` ← `Name`, `source_file` ← `SourceRef.file`, `field_count` ← `len(Controls or [])`.
3. Garantir que campos ausentes sejam preenchidos com defaults vazios para evitar `KeyError`.

### Phase 2 — Suporte ao formato de BC map .NET

1. Em `parse_bc_map()`, além do parser atual de `### BC-XX` + `**Units list**`, adicionar parser para:
   - `## BC-NN: Nome` ou `## BC-NN — Nome`
   - `**Files**: <arquivos>`
   - `**Forms/Pages**: N` (usado apenas para validação/cruzamento)
2. Manter o parser de tabela markdown como fallback.
3. Armazenar unidades normalizadas (stems minúsculos) e continuar computando tokens.

### Phase 3 — Melhorar tokenização e ruídos

1. Expandir `NOISE` para incluir:
   ```python
   NOISE = {
       'frm','dfm','pas','web','form','data','unit','main','base','lib','utils','test',
       'cs','vb','aspx','cshtml','vbhtml','ascx','svc','resx','designer','xaml','xml','config',
       'controller','view','model','page','webpage','window','dialog','usercontrol','master',
   }
   ```
2. Aprimorar `tokenize()` para separar também por `_` e `-`, além de PascalCase/camelCase:
   ```python
   parts = re.split(r'[^A-Za-z0-9]+', text)
   tokens = []
   for p in parts:
       tokens.extend(re.findall(r'[a-z]+|[A-Z][a-z]*|[A-Z]+(?=[A-Z][a-z]|\b)', p))
   return [t.lower() for t in tokens if len(t) >= 3]
   ```
   Isso permite `CatalogController.cs` → `catalog`, `controller`, `cs` (ruído removido).

### Phase 4 — Testes de regressão e validação

1. Criar `src/shared/tools/test_gen_screen_flow.py` com dois fixtures:
   - `sample-delphi-forms.json` (schema `payload.forms[]`)
   - `sample-dotnet-forms.json` (schema `Payload[]`)
2. Testar:
   - Extração normalizada gera número correto de formas em cada schema.
   - Classificação por BC funciona com `bounded-context-map.md` de ambos os formatos.
   - Diagramas gerados passam por `validate_diagram.py`.
3. Executar o script contra o artefato real de `nopcommerce` e confirmar ~116 formas (ou o número presente no JSON) e geração de `.mmd` sem erro.

### Phase 5 — Atualização de agente (opcional, recomendado)

1. Atualizar `src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-dotnet.md` Step 9.4 para remover a cláusula "quando suportar .NET / fallback adaptado" e tornar a invocação do script obrigatória.
2. Garantir passagem explícita de `--bc-map projects/{project_name}/outputs/asis/bounded-context-map.md`, se existir.

---

## 6. Expected Outcome

After the fix, running the reproduction command against `nopcommerce` should produce:

```text
[gen_screen_flow] BC map: N BCs, M units, K tokens
[gen_screen_flow] Navigation map: X domains loaded
[gen_screen_flow] 116 forms, Y groups, Z classified
[gen_screen_flow] Generated ... files:
  [PASS] screen-flow.mmd (... chars)
  ...
```

and the output directory should contain:

```
projects/nopcommerce/outputs/asis/docs/
├── screen-flow.mmd
├── screen-flow-<bc>.mmd (one or more detail files)
```

---

## 7. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Delphi behavior regression | Keep the exact `payload.forms[]` code path; normalize .NET only when PascalCase `Payload` is detected. Add Delphi fixture test. |
| BC map format ambiguity | Accept both H2 and H3 BC headings; accept `**Units list**` and `**Files**`. |
| Noise list over-filtering | The new tokens are strongly .NET-specific and unlikely to remove meaningful domain words. Existing Delphi noise is preserved. |
| Large BCs exceed Mermaid limits | Existing batch/split logic (120 items per part) remains unchanged. |
| `validate_diagram.py` failures | Keep passing output through the validator; return codes 0 and 2 treated as PASS. |

---

## 8. References

- `src/shared/tools/gen_screen_flow.py`
- `src/shared/tools/gen_er_diagram.py`
- `src/shared/utils/validate_diagram.py`
- `src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-dotnet.md`
- `src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md`
- `projects/nopcommerce/context/project-config.yaml`
- `C:\_git\imfai-ava-tools\ava-fabric-dotnet-analyzer\out\nopcommerce\extraction\02_form_business_rules.json`
