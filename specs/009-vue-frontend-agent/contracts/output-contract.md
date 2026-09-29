# Output Contract — ava-prototype v1.1.0

> O `ava-prototype` é um **agente LLM** que produz arquivos HTML e Markdown.
> Não expõe API REST ou CLI. O contrato a seguir especifica os **outputs produzidos**
> e as **regras de conformidade** que cada output deve satisfazer.

---

## Output Contract (YAML)

```yaml
outputs:
  prototype_index:
    path: "projects/{project_name}/outputs/tobe/prototype/index.html"
    type: "text/html"
    required: true
    rules:
      - "Arquivo único autocontido (sem dependências externas CDN)"
      - "CSS custom properties derivadas de design-system.md"
      - "Navegação funcional entre telas via links e botões inline"
      - "Todas as telas de user-journeys.md com status 'applies_design_system: true'"
      - "Formulários com validação JS usando Constraint Validation API"
      - "Padrão de erro em 3 camadas: modal / toast / inline banner"
      - "Heurísticas H1–H10 aplicadas (breadcrumb, labels, cancelar, confirmação)"
      - "Metadado <!-- Prototype metadata --> em cada tela"
      - "Abre corretamente com file:// sem servidor HTTP"

  screen_list:
    path: "projects/{project_name}/outputs/tobe/prototype/screen-list.md"
    type: "text/markdown"
    required: true
    rules:
      - "Colunas: Screen | Bounded Context | API Endpoint | AS-IS Reference | Status | api_source"
      - "Toda tela de user-journeys.md aparece (status included ou excluded)"
      - "Telas 'excluded' referenciam entrada em design-system.md > Non-Applicable Cases"

  demo_script:
    path: "projects/{project_name}/outputs/tobe/prototype/demo-script.md"
    type: "text/markdown"
    required: true
    rules:
      - "Inclui duração estimada em minutos"
      - "Roteiro por jornada com passos numerados"
      - "Seção 'Checklist H1-H10 por Tela'"
      - "Seção 'Cenários de Erro (CA03)' com passos para demonstrar validações"

  figma_spec:
    path: "projects/{project_name}/outputs/tobe/prototype/figma-spec.md"
    type: "text/markdown"
    required: true
    rules:
      - "Tabela de Design Tokens (CSS custom property → valor Figma)"
      - "Inventário de componentes com variantes"
      - "Tabela UX Heuristics Checklist: H1-H10 × telas (✅ / ⚠️ / N/A)"
```

---

## Gate Result Contract

O agente DEVE emitir o bloco `prototype_gate_result` antes de declarar `COMPLETED`:

```yaml
prototype_gate_result:
  # Campos existentes (v1.0.0 — não modificados)
  status: "PASS" | "FAIL"
  screen_count: integer
  covered_bcs: [string]
  excluded_bcs: [string]
  demo_duration_min: integer
  api_source: "api-map" | "openapi-derived" | "none"
  missing_inputs: [string]
  artifacts:
    index_html: string
    demo_script: string
    figma_spec: string
    screen_list: string

  # Campos novos (v1.1.0)
  ux_heuristics_applied: [string]     # ex: ["H1","H2","H4","H5","H6","H9"]
  form_validation_applied: boolean    # true se ao menos 1 formulário com validação
  error_pattern_applied: boolean      # true se ao menos 1 padrão de erro implementado
```

**Condições PASS** (todos obrigatórios):

1. `index.html` gerado e autocontido
2. `screen-list.md` completo (toda tela listada)
3. `demo-script.md` presente com seção CA03
4. `screen_count > 0`
5. `form_validation_applied = true` se user-journeys.md contém ao menos 1 formulário
6. `ux_heuristics_applied` contém ao menos H1, H4, H6, H9

**Condições FAIL** (qualquer uma):

- `index.html` ausente
- `screen_count = 0`
- `form_validation_applied = false` quando formulários existem nas jornadas

---

## Backward Compatibility

| Campo                     | v1.0.0    | v1.1.0              | Breaking?             |
| ------------------------- | --------- | ------------------- | --------------------- |
| `status`                  | ✅        | ✅ (mesmos valores) | NÃO                   |
| `screen_count`            | ✅        | ✅                  | NÃO                   |
| `covered_bcs`             | ✅        | ✅                  | NÃO                   |
| `excluded_bcs`            | ✅        | ✅                  | NÃO                   |
| `demo_duration_min`       | ✅        | ✅                  | NÃO                   |
| `api_source`              | ✅        | ✅                  | NÃO                   |
| `missing_inputs`          | ✅        | ✅                  | NÃO                   |
| `artifacts`               | ✅        | ✅                  | NÃO                   |
| `ux_heuristics_applied`   | ❌ (novo) | ✅                  | NÃO (campo adicional) |
| `form_validation_applied` | ❌ (novo) | ✅                  | NÃO (campo adicional) |
| `error_pattern_applied`   | ❌ (novo) | ✅                  | NÃO (campo adicional) |

> Conclusão: **MINOR bump confirmado** — nenhuma quebra de contrato downstream.
> `ava-master-orchestrator` e `ava-tobe-orchestrator` não precisam de alteração.
