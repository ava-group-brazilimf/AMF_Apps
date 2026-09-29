# Guia — Integração com a esteira AVA Fabric Agents

Este guia cobre como configurar e rodar esta tool (`ava-fabric-delphi-analyzer`)
**em conjunto com** a esteira de agentes "AVA Fabric Agents" (framework BMAD,
42+ agentes), de forma que o agente `ava-asis-solution-delphi` use os 8 artefatos
JSON determinísticos desta tool como fonte primária em vez de depender só de
`Glob`/`Grep`/`Read` pelo LLM.

Ponto de integração: novo **Step 0 — Deterministic AST Extraction** no agente
`src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md`, que
chama o script `src/modules/ava-fabric-agents/asis-diagnostic/utils/ run_delphi_ast_analysis.py` da esteira, que por sua vez invoca
`src/run_pipeline.py` **desta** tool. É um passo **estritamente aditivo**: se
falhar ou não estiver configurado, o agente cai no comportamento anterior
(Grep/Read), sem bloquear a entrega.

```
Esteira (ava-fabric-apps-agents)                    Esta tool (ava-fabric-delphi-analyzer)
─────────────────────────────────                    ──────────────────────────────────────
ava-asis-orchestrator
  └─ dispatch: ava-asis-solution-delphi
       └─ Step 0 (Bash)
            └─ utils/run_delphi_ast_analysis.py  ──▶  src/run_pipeline.py
                                                         ├─ src/delphi_ast_analyzer.py  (8 JSONs)
                                                         ├─ src/validate_artifacts.py   (schema)
                                                         └─ src/headroom_precompress.py (+ metrics.jsonl)
       └─ Step 3 (ClassRegistry) ← 08_code_overview.json.payload.classes
       └─ Steps 6/7/9/10/12      ← 03/04/05/06/07_*.json
```

---

## 1. Pré-requisitos

### 1.1 Nesta tool (`ava-fabric-delphi-analyzer`)

| Item                              | Como verificar                                                         | Onde resolver                       |
| --------------------------------- | ---------------------------------------------------------------------- | ----------------------------------- |
| Python 3.10+                      | `python --version`                                                   | —                                  |
| Dependências Python              | `pip show headroom-ai jsonschema xlsxwriter`                         | `pip install -r requirements.txt` |
| Binário`ava_ast_cli` compilado | existe`bin/ava_ast_cli.exe` (Windows) ou `bin/ava_ast_cli` (Linux) | `docs/BUILD_WINDOWS.md`           |

```bash
pip install -r requirements.txt
```

> **Windows**: o binário incluído no pacote é Linux x86-64. Gere o `.exe` local
> com o kit em `bin/build-windows/` — passo a passo completo em
> `docs/BUILD_WINDOWS.md`. O fonte vendorizado em `examples/DelphiAST/` já
> inclui as correções necessárias para compilar e rodar corretamente no FPC do
> Windows (submódulos `FreePascalSupport` e o fix do bug de recursão infinita
> em `SimpleParser.pas`/`TStringStreamHelper`) — não é necessário reaplicá-las.

Confirme que a tool funciona isoladamente antes de plugar na esteira:

```bash
# Windows (PowerShell)
$env:AVA_AST_CLI = ".\bin\ava_ast_cli.exe"
python src\run_pipeline.py .\examples\Meu-ERP --extraction .\extraction --compressed .\compressed
```

Saída esperada: `schema OK` e `mode: "ast+regex-fallback"` (ou `"regex-only"` se
o binário não foi encontrado — funciona, mas com menos precisão).

### 1.2 Na esteira (`ava-fabric-apps-agents`)

| Item                           | Como verificar                                         | Onde resolver                                   |
| ------------------------------ | ------------------------------------------------------ | ----------------------------------------------- |
| Python 3.10+ com PyYAML        | `python -c "import yaml"`                            | `pip install pyyaml`                          |
| Caminho desta tool configurado | ver abaixo                                             | variável de ambiente ou`--ava-analyzer-path` |
| Projeto configurado            | `projects/{nome}/context/project-config.yaml` existe | ver 1.2.2                                       |

#### 1.2.1 Apontar a esteira para esta tool

```powershell
# Uma vez por ambiente/máquina (evita passar --ava-analyzer-path toda vez)
setx AVA_DELPHI_ANALYZER_HOME "C:\caminho\para\ava-fabric-delphi-analyzer"
```

Ou passe explicitamente em cada invocação com `--ava-analyzer-path`.

#### 1.2.2 Configurar o projeto na esteira

Em `projects/{nome_do_projeto}/context/project-config.yaml`, garanta:

```yaml
project_name: "{nome_do_projeto}"
repository_path: "C:\\caminho\\absoluto\\do\\legado\\delphi"   # repo REAL a analisar
legacy_technology: "delphi"
```

> Sem `legacy_technology: "delphi"`, o Step 0 detecta a tecnologia diferente e
> faz *no-op* (exit 0, sem rodar) — comportamento esperado para projetos
> não-Delphi (VB6, COBOL etc.), que não têm cobertura desta tool.

---

## 2. Passo a passo de execução

### 2.1 (Opcional) Testar o wrapper da esteira isoladamente

Antes de rodar o workflow completo, valide a integração sozinha:

```bash
cd <raiz-da-esteira>
python src/modules/ava-fabric-agents/asis-diagnostic/utils/run_delphi_ast_analysis.py \
  --project {nome_do_projeto} --ava-analyzer-path "C:\caminho\para\ava-fabric-delphi-analyzer"
```

Saída esperada:

```
🔧 Rodando extração AST Delphi para {nome_do_projeto}...
   repository_path: C:\...\legado
   analyzer: C:\...\ava-fabric-delphi-analyzer
   ✅ projects/{nome_do_projeto}/outputs/asis/delphi-ast-raw/extraction
   ✅ projects/{nome_do_projeto}/outputs/asis/delphi-ast-raw/compressed
   🔵 modo: ast+regex-fallback  |  unidades: N  |  classes: N  |  regras de negócio: N
```

Exit code `0` = sucesso. Qualquer outro valor = ver `run_delphi_ast_analysis.log`
na mesma pasta de saída (seção 3.6 — Troubleshooting).

### 2.2 Rodar dentro do fluxo real da esteira

1. Garanta que o projeto está configurado (passo 1.2.2).
2. Invoque o agente/orquestrador normalmente (Copilot Chat `@ava-asis-orchestrator`
   ou Claude Code, conforme o host configurado na esteira) para o workflow
   `analyze-delphi`.
3. O `ava-asis-solution-delphi` executa automaticamente o **Step 0** como
   pré-requisito, antes do Step 1 (Repository Inventory):
   - **Sucesso** → Steps 3 (ClassRegistry), 6, 7, 9, 10 e 12 passam a usar os
     JSONs de `outputs/asis/delphi-ast-raw/extraction/` como fonte primária;
     `Grep` continua rodando nesses steps só como checagem pontual de achados
     de alto risco.
   - **Falha/indisponível** → aviso registrado, agente prossegue 100% via
     `Glob`/`Grep`/`Read` (comportamento histórico, sem regressão).
4. O restante do workflow (`documentation`, `db-analysis`, `security`,
   `inventory`, `consolidation`, `master-report`) segue normalmente — nenhum
   outro agente/step precisa de mudança.

---

## 3. Validação dos resultados gerados

### 3.1 Existência dos artefatos

Confirme que todos os arquivos abaixo existem em
`projects/{nome_do_projeto}/outputs/asis/delphi-ast-raw/`:

```
extraction/01_business_rules.json     extraction/05_procedures.json
extraction/02_form_business_rules.json extraction/06_integrations.json
extraction/03_database_rules.json     extraction/07_apis.json
extraction/04_database_schemas.json   extraction/08_code_overview.json
compressed/manifest.json
compressed/metrics.jsonl
run_delphi_ast_analysis.log
```

### 3.2 Conformidade de schema

`run_pipeline.py` já valida automaticamente contra
`src/schemas/artifacts.schema.json` (sai com erro se algo estiver fora do
contrato — ex.: chave errada num tipo de regra de negócio). Para revalidar
manualmente um `extraction/` já gerado:

```bash
python src/validate_artifacts.py <extraction_dir>
# saída esperada: "OK: todos os artefatos conformes ao schema."
```

### 3.3 Indicador de modo — AST real vs. fallback regex

Abra `extraction/08_code_overview.json` e confira `payload.totals.mode`:

| Valor                  | Significado                                                                                                                                                 |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ast+regex-fallback` | Parser AST real rodou (pelo menos parte dos arquivos); é o esperado e mais preciso.                                                                        |
| `regex-only`         | O binário`ava_ast_cli` não foi encontrado/não rodou — a extração ainda funciona, mas com precisão de regex, não de AST real. Ver troubleshooting. |

`payload.totals.units_parsed_ast` vs. `payload.totals.units_total` mostra
quantos arquivos, dos analisados, passaram pelo parser real.

### 3.4 Sanity check do `ClassRegistry`

O Step 3 do `solution-delphi.md` usa `payload.classes` (em
`08_code_overview.json`) como `ClassRegistry[]` — a fonte única e obrigatória
para os diagramas de classe do agente. Confirme que veio populado:

```bash
python -c "import json; d=json.load(open('extraction/08_code_overview.json', encoding='utf-8')); \
print(len(d['payload']['classes']), 'classes'); print(d['payload']['classes'][0])"
```

Cada entrada deve ter `name`, `parent` (ou `null`), `file` e `line`. Depois que
o agente gerar `class-diagram.mmd`, nenhuma classe/herança ali deve estar
ausente desta lista (invariante anti-alucinação já embutida no próprio agente).

### 3.5 Métricas e dashboard (opcional, mas recomendado)

```bash
# Resumo da última execução (tokens, modo, contagens, duração)
python src/metrics_viewer.py --metrics-file <compressed_dir>/metrics.jsonl --last 1

# Dashboard Excel navegável (Estrutura / Regras_Negocio / Dashboard com gráficos)
python src/generate_excel_report.py <extraction_dir> -o report.xlsx
```

### 3.6 Troubleshooting rápido

| Sintoma                                                                                   | Causa provável                                                                                                                      | Resolução                                                                                                                                                                                                                        |
| ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `mode: "regex-only"` mesmo com o `.exe` compilado                                     | `AVA_AST_CLI`/binário não localizado pelo subprocess da esteira                                                                  | Confirmar`bin/ava_ast_cli.exe` existe no caminho de `--ava-analyzer-path`/`AVA_DELPHI_ANALYZER_HOME`; `run_delphi_ast_analysis.py` já seta `AVA_AST_CLI` automaticamente, mas confira o `run_delphi_ast_analysis.log` |
| Step 0 não roda / não aparece na saída do agente                                       | Host do agente não suporta`Bash`/`runCommands`, ou `allowed-tools` do agente não inclui `Bash`                             | Conferir frontmatter`allowed-tools` em `solution-delphi.md`; sem Bash, o agente cai automaticamente no modo Grep-only                                                                                                          |
| `run_delphi_ast_analysis.py` sai com "repository_path não encontrado"                  | `project-config.yaml` sem `repository_path` preenchido                                                                           | Preencher conforme 1.2.2                                                                                                                                                                                                           |
| `run_delphi_ast_analysis.py` faz *no-op* (exit 0, sem gerar nada)                     | `legacy_technology` ≠ `"delphi"` no `project-config.yaml`                                                                     | Esperado para projetos não-Delphi; não é erro                                                                                                                                                                                   |
| `validate_artifacts.py` acusa violação de schema                                      | Alteração recente em`ast_bridge.py`/`regex_extractors.py` quebrou o contrato de algum artefato (ex.: chave `type` renomeada) | Ver a mensagem de erro (aponta o artefato + o caminho JSON exato da violação)                                                                                                                                                    |
| Erro de encoding (`UnicodeEncodeError`) rodando os scripts direto no console do Windows | Console usando codepage cp1252, que não suporta os emoji/caracteres usados nas mensagens                                            | Já corrigido nos scripts desta integração (`sys.stdout.reconfigure(encoding="utf-8")`); se acontecer em outro script, aplicar o mesmo fix                                                                                     |

---

## 4. Referências

- `docs/BUILD_WINDOWS.md` — compilar `ava_ast_cli.exe` no Windows.
- `docs/GUIA_HEADROOM.md` — detalhes da pré-compressão (Headroom real vs. fallback).
- `agents/delphi-analyzer.prompt.md` — uso desta tool como skill standalone do
  GitHub Copilot (fora da esteira AVA Fabric Agents), caminho alternativo ao
  descrito neste guia.
