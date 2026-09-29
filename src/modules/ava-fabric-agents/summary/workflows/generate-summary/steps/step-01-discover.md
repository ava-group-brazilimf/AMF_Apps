# Step 01 — Contexto & Descoberta

## Objetivo
Ler o contexto do projeto e inventariar todos os artefatos disponíveis em
`projects/{project_name}/outputs/` antes de extrair qualquer dado.

## Inputs Esperados
```yaml
outputs_base_path: "projects/{project_name}/outputs/"   # default
```

## Ações

### 1.1 — Ler contexto do projeto
```
Ler: projects/{project_name}/context/project-config.yaml
Extrair:
  - project.name          → PROJECT_NAME
  - legacy.technology     → LEGACY_TECH
  - legacy.repository_path → REPO_PATH
  - target.technology     → TARGET_TECH
  - team.cleinte_name         → CLIENTE_NAME

Se não encontrar → usar defaults: "{{PROJECT_NAME}}", "Delphi", "{tobe_stack.backend_framework} {tobe_stack.backend_version}"
```

### 1.2 — Ler estado da esteira
```
Ler: projects/{project_name}/context/shared-context.md
Extrair:
  - trace_id (se disponível)
  - Status por fase (AS-IS, TO-BE, QA, Entregáveis, DevOps)
  - Última atualização

Se não encontrar → assumir que todas as fases são "unknown"
```

### 1.3 — Inventariar artefatos por fase
```
Glob: projects/{project_name}/outputs/asis/**/*     → F1_FILES[]
Glob: projects/{project_name}/outputs/tobe/**/*     → F2_FILES[]
Glob: projects/{project_name}/outputs/qa/**/*       → F5_FILES[]
Glob: projects/{project_name}/outputs/deliverables/**/* → F6_FILES[]

Para cada lista → contar por extensão:
  .md   → relatórios de texto
  .json → dados estruturados
  .mmd  → diagramas Mermaid
  .html → protótipos ou reports
  .cs   → código C# gerado
  .ts   → código TypeScript/Angular gerado
  .yml  → pipelines e configs
```

### 1.3b — Construir FILE_TREE_JSON (explorador completo)

```
Glob: projects/{project_name}/outputs/**/*  → ALL_FILES[]

Para cada arquivo em ALL_FILES:
  1. Remover prefixo "projects/{project_name}/outputs/"
  2. parts = caminho_relativo.split("/")
  3. top_key = parts[0]   (ex: "asis", "tobe", "qa", "deliverables", "summary")
  4. Se len(parts) == 1 → arquivo na raiz de outputs (raro) → registrar em top_key
  5. Se len(parts) > 1  → navegar/criar nós recursivos em subdirs para parts[1..-2]
                          → adicionar {name, path, ext, dir, content?, truncated?} ao nó folha

Excluir:
  - Diretórios (apenas arquivos)
  - O próprio HTML sendo gerado: "AVA-FABRIC-SUMMARY-*.html"
  - Cache local "mermaid.min.js"
  - Scripts auxiliares "generate-summary.py" e "summary-data.json" (se na pasta summary/)

Labels canônicos por top_key:
  asis         → "F1 — AS-IS"
  tobe         → "F2–F4 — TO-BE, Protótipo & Stack"
  qa           → "F5 — QA"
  deliverables → "F7 — Entregáveis"
  devops       → "F6 — DevOps"
  summary      → "F8 — Summary"
  (outros)     → usar o top_key como label

Formato do nó:
  { label: string, files: [{name, path, ext, dir, content, truncated}], subdirs: {key: nó} }
```

### 1.3c — Embedar conteúdo dos arquivos (Content Embedder)

**Crítico**: o template HTML é autocontido (offline `file://`) e não pode buscar arquivos locais via XHR. O viewer (`viewFileContent()` no template) só habilita o botão "Visualizar" se `file.content` for string não-vazia. Portanto cada `file` do FILE_TREE_JSON DEVE incluir o campo `content` para arquivos de texto.

```
Whitelist de extensões legíveis (READABLE_EXTS):
  md, mmd, json, yaml, yml,
  cs, ts, tsx, js, jsx,
  html, htm, css, scss, sass,
  sql, py, sh, ps1, bat,
  tf, bicep, csproj, sln, props, targets,
  xml, toml, ini, properties, conf, config,
  txt, log, env, dockerfile, gitignore,
  dpr, pas, dfm, dproj

Whitelist de basenames sem extensão (READABLE_BASENAMES):
  Dockerfile, .editorconfig, .gitignore, .gitattributes,
  Makefile, README, LICENSE

Limites:
  MAX_FILE_BYTES  = 256 KB     (256 * 1024)
  MAX_TOTAL_BYTES =   5 MB     (5 * 1024 * 1024)

Algoritmo (manter contador agregado total_embedded entre arquivos):
  Para cada file no FILE_TREE:
    size = stat(file).st_size
    if not (file.ext in READABLE_EXTS or file.name in READABLE_BASENAMES):
      file.content = null
      file.truncated = false
    elif size > MAX_FILE_BYTES:
      file.content = null
      file.truncated = true
    elif total_embedded + size > MAX_TOTAL_BYTES:
      file.content = null
      file.truncated = true
    else:
      file.content = read_text(file, encoding="utf-8", errors="replace")
      file.truncated = false
      total_embedded += size

Output: FILE_TREE_JSON → usado no Step 03 como placeholder {{FILE_TREE_JSON}}
```

### 1.4 — Determinar status de cada agente
Para cada agente da fábrica, verificar se seu arquivo de output principal existe:

| Agente                  | Arquivo principal esperado                             |
|-------------------------|--------------------------------------------------------|
| ava-asis-orchestrator   | projects/{project_name}/outputs/asis/master-report.md                  |
| ava-asis-solution-delphi / ava-asis-solution-vb / (stub) | projects/{project_name}/outputs/asis/architecture-blueprint.md         |
| ava-asis-documentation  | projects/{project_name}/outputs/asis/docs/business-rules.md   |
| ava-asis-security-orchestrator| projects/{project_name}/outputs/asis/security/security-map.md    |
| ava-asis-inventory      | projects/{project_name}/outputs/asis/inventory-report.md               |
| ava-asis-gaps-risks     | projects/{project_name}/outputs/asis/gaps-risks-report.md              |
| ava-asis-db-analyzer    | projects/{project_name}/outputs/asis/db/schema-inventory.md            |
| ava-tobe-orchestrator   | projects/{project_name}/outputs/tobe/docs/architecture-blueprint.md    |
| ava-tobe-arch-design    | projects/{project_name}/outputs/tobe/docs/bounded-context-map.md       |
| ava-tobe-arch-technical | projects/{project_name}/outputs/tobe/docs/tech-framework-document.md   |
| ava-tobe-measure-size   | projects/{project_name}/outputs/tobe/docs/sizing-report.md             |
| ava-tobe-migration-plan | projects/{project_name}/outputs/tobe/docs/migration-plan.md            |
| ava-coder-dotnet / ava-stack-{backend} | projects/{project_name}/outputs/tobe/source-code/                      |
| ava-docs-tobe           | projects/{project_name}/outputs/tobe/docs/technical-design-document.md |
| ava-test-plan-tobe      | projects/{project_name}/outputs/tobe/docs/test-plan-tobe.md            |
| ava-qa-orchestrator     | projects/{project_name}/outputs/qa/quality-strategy.md                 |
| ava-devops-iac          | projects/{project_name}/outputs/tobe/infra/terraform/                  |
| ava-devops-ci           | projects/{project_name}/outputs/tobe/iac/ci/                           |
| ava-devops-compare-ver  | projects/{project_name}/outputs/tobe/parity-test-report.md             |
| ava-deliverable-packager| projects/{project_name}/outputs/deliverables/                          |

Status = "done" se arquivo/pasta existe, "pending" caso contrário.

### 1.5 — Relatório de descoberta
Exibir para o usuário:
```
📊 Descoberta concluída:
   Projeto: {PROJECT_NAME} | {LEGACY_TECH} → {tobe_stack.backend_framework} {tobe_stack.backend_version}
   Trace ID: {TRACE_ID}

   Artefatos por fase:
   F1 AS-IS:        {F1_COUNT} arquivos ({F1_DONE}/{F1_TOTAL} agentes executados)
   F2 TO-BE:        {F2_COUNT} arquivos ({F2_DONE}/{F2_TOTAL} agentes executados)
   F5 QA:           {F5_COUNT} arquivos
   F6 DevOps:       {F6_COUNT} arquivos
   F7 Entregáveis:  {F7_COUNT} arquivos

   Total: {TOTAL} artefatos · {DONE_AGENTS}/70 agentes com outputs

→ Prosseguindo para extração de dados...
```

## Critério de Conclusão
- ProjectContext preenchido (mesmo com defaults)
- ArtifactInventory criado com pelo menos 1 arquivo
- AgentStatusMap criado para todos os 70 agentes (done/pending)

## Se nenhum output encontrado
```
⚠️ Nenhum artefato encontrado em {outputs_base_path}.
   Verifique se o workflow AS-IS ou TO-BE foi executado antes.
   Para usar um caminho alternativo, responda com o path correto.
   Para gerar um summary de demonstração, responda "demo".
```
