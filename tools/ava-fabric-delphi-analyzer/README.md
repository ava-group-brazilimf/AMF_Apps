# AVA Fabric — Delphi Analyzer Solution

Tool determinística que extrai o levantamento de um legado Delphi em **9 artefatos
JSON estruturados** (via DelphiAST real) e os **comprime com Headroom** antes de
entregá-los a um agente `.md` do GitHub Copilot, que os interpreta para produzir o
levantamento de modernização. É o **Caminho 2** do AVA Fabric: pré-compressão
offline, sem depender de proxy nem de BYOK.

```
Legado Delphi (.pas/.dfm)
  └─ src/ast_bridge.py       load_ast (DelphiAST) → normalize_ast → IR
       └─ src/delphi_ast_analyzer.py   → .ava-fabric/extraction/  (9 JSONs)   [IR | fallback regex]
            └─ src/headroom_precompress.py → .ava-fabric/compressed/ (+ manifest.json)
                 └─ agents/delphi-analyzer.prompt.md  (skill do Copilot: interpreta)
```

## Estrutura

```
ava-fabric-delphi-analyzer/
├── src/                    código da tool (6 módulos)
├── agents/
│   └── delphi-analyzer.prompt.md   agente/skill do GitHub Copilot
├── bin/
│   ├── ava_ast_cli         binário DelphiAST (Linux x86-64) + como recompilar
│   └── README.md
├── examples/
│   ├── Meu-ERP/            clone RogerioAP/Meu-ERP (alvo de teste, sem build)
│   └── DelphiAST/          clone RomanYankovsky/DelphiAST (fonte do parser)
├── docs/GUIA_HEADROOM.md   uso detalhado do Headroom (real e fallback)
├── docs/GUIA_ESTEIRA.md    integração como tool na esteira AVA Fabric Agents
├── requirements.txt
└── README.md
```

---

## Passo a passo

### 1. Pré-requisitos

- Python 3.10+
- (Opcional, recomendado) Headroom real: `pip install -r requirements.txt`
  Sem ele, a compressão usa o fallback SmartCrusher-lite embutido.
- (Opcional, recomendado) o binário `bin/ava_ast_cli`. Sem ele, a extração cai no
  fallback regex por arquivo. Veja `bin/README.md` para recompilar do DelphiAST.

```bash
pip install -r requirements.txt
```

### 2. Apontar o binário DelphiAST

```bash
# Linux/macOS
export AVA_AST_CLI=./bin/ava_ast_cli
chmod +x ./bin/ava_ast_cli

# Windows (PowerShell) — use o seu build .exe do DelphiAST
$env:AVA_AST_CLI = ".\bin\ava_ast_cli.exe"
```

> O binário incluído é Linux x86-64. **No Windows**, gere o `.exe` com o kit em
> `bin/build-windows/` — passo a passo em `docs/BUILD_WINDOWS.md` (FPC ou Delphi).
> Ou rode em WSL. Sem binário, a tool funciona em modo regex.

### 3. Rodar o pipeline no projeto de exemplo

```bash
python src/run_pipeline.py ./examples/Meu-ERP \
    --extraction ./.ava-fabric/extraction \
    --compressed ./.ava-fabric/compressed
```

Saída esperada (Headroom real):

```
== 1/2  Extração Delphi AST ==
   ok  01_business_rules.json ... 08_code_overview.json
== 2/2  Pré-compressão Headroom ==
   05_procedures   40703 -> 16092 tok (-60.5%) [router:smart_crusher]
   ...
   TOTAL: 54907 -> 23567 tok (-57.1%)
```

### 4. Rodar no seu próprio legado

```bash
python src/run_pipeline.py /caminho/do/seu/legado-delphi \
    --extraction ./.ava-fabric/extraction \
    --compressed ./.ava-fabric/compressed
```

Os `.dcu`/`Win32`/build são ignorados automaticamente (só `.pas` e `.dfm`).

### 5. Usar o agente no GitHub Copilot Chat

1. Copie `agents/delphi-analyzer.prompt.md` para `.github/prompts/` do repositório alvo.
2. No chat do Copilot (agent mode):

```
/delphi-analyzer  analise o legado em ./examples/Meu-ERP
```

O agente roda o STEP 1 (a tool) e depois interpreta os 9 artefatos comprimidos,
produzindo o Levantamento de Modernização. Detalhes em `agents/delphi-analyzer.prompt.md`.

### 6. Usar como tool dentro da esteira AVA Fabric Agents

Caminho alternativo ao item 5: plugar esta tool como **Step 0** determinístico
do agente `ava-asis-solution-delphi` na esteira "AVA Fabric Agents" (framework
BMAD), em vez de rodar como skill standalone do Copilot. Pré-requisitos,
passo a passo e validação completos em `docs/GUIA_ESTEIRA.md`.

---

## Os 9 artefatos

| Arquivo | Conteúdo | Caminho |
|---|---|---|
| 01_business_rules | Validações, cálculos, CASE (por método) | IR (IF/ASSIGN/CASE) + fallback |
| 02_form_business_rules | Forms, campos, handlers, máscaras | regex `.dfm` |
| 03_database_rules | Write ops + transações | IR (SQL literais) + fallback |
| 04_database_schemas | Tabelas/colunas (DDL + inferidas do SQL) | IR + fallback |
| 05_procedures | Procedures/functions (só implementações) | IR + fallback |
| 06_integrations | DLL, COM, socket, e-mail, **ACBr** (boleto/fiscal) | IR + fallback |
| 07_apis | Clientes HTTP/REST/SOAP + URLs | IR + fallback |
| 08_code_overview | LOC, classes, procs, telas, complexidade | IR + fallback |
| 09_test_coverage | Frameworks DUnit/DUnitX, fixtures, testes, artefatos auxiliares | IR (uses/herança/atributos/published) + fallback |

Envelope comum: campos voláteis (`_volatile`) isolados no fim → prefixo estável para
o CacheAligner do Headroom.

---

## Resultado de referência (examples/Meu-ERP)

- 30 units `.pas` + 22 `.dfm`, 4.630 LOC, 30 classes, 341 procedures, 22 telas.
- 11 tabelas do modelo de dados inferidas do SQL; 27 operações de escrita.
- 6 cálculos financeiros reais (baixa de título: `saldo := saldo ± valor`).
- Integração bancária ACBrBoleto detectada.
- Compressão Headroom real: **54.907 → 23.567 tokens (−57,1%)**.

Ver `docs/GUIA_HEADROOM.md` e o `manifest.json` gerado.

---

## Limitações conhecidas

- `.dfm` é analisado por regex (DelphiAST cobre só `.pas`).
- `insert into t values(...)` posicional não expõe nomes de coluna; correlacionar
  com os campos privados das classes `uClass*` é o próximo passo.
- Contagem de tokens do fallback é `chars/4`; o Headroom real usa o tokenizer correto.
