# Compilar o `ava_ast_cli.exe` no Windows — passo a passo

O `ava_ast_cli` é o wrapper CLI do DelphiAST que a tool usa no STEP 1
(`src/ast_bridge.py` → `load_ast`). O binário que acompanha o pacote é **Linux
x86-64**; no Windows você gera o `.exe` a partir do fonte — que já está incluído.

Kit de build (em `bin/build-windows/`):
```
ava_ast_cli.lpr    wrapper portável (compila em FPC e em Delphi)
build-fpc.bat      build via Free Pascal (recomendado — mesmo toolchain do binário Linux)
build-delphi.bat   build via RAD Studio/Delphi
```
Fonte do parser: `examples/DelphiAST/Source` (clone do RomanYankovsky/DelphiAST).

Escolha **um** dos dois caminhos.

---

## Caminho A — Free Pascal (FPC) — recomendado

É o mesmo toolchain que gerou o binário Linux; o wrapper compila igual no Windows.

### 1. Instalar o FPC

Baixe e instale o **Lazarus** (traz o FPC junto): https://www.lazarus-ide.org
Durante a instalação, marque a opção de adicionar ao PATH (ou anote a pasta,
ex.: `C:\lazarus\fpc\3.2.2\bin\x86_64-win64`).

### 2. Confirmar o FPC no PATH

Abra o **Prompt de Comando** e rode:
```bat
fpc -iV
```
Deve imprimir a versão (ex.: `3.2.2`). Se der "não reconhecido", adicione a pasta
`bin` do FPC ao PATH ou use o "Lazarus" → não; mais simples: rode o `.bat` a partir
de um prompt onde `fpc` responda.

### 3. Compilar

```bat
cd bin\build-windows
build-fpc.bat
```

Gera `bin\ava_ast_cli.exe` e imprime o "Usage" ao final (sinal de que rodou).

> Se o FPC reclamar de `Generics.Collections`, edite `build-fpc.bat` e remova a
> linha `-Fu"%SRC%\FreePascalSupport\Generics.Collection"` — o FPC do Windows já
> traz a sua própria implementação e essa linha extra pode conflitar.

---

## Caminho B — Delphi / RAD Studio

Se você já tem o Delphi instalado (provável no seu contexto), é direto — o Delphi
traz `Generics.Collections` nativo e dispensa o `FreePascalSupport`.

### 1. Abrir o prompt do RAD Studio

Menu Iniciar → **RAD Studio Command Prompt** (garante `dcc64.exe` no PATH).

### 2. Compilar

```bat
cd bin\build-windows
build-delphi.bat
```

O `.bat` copia `ava_ast_cli.lpr` → `ava_ast_cli.dpr` (o Delphi compila `.dpr`; a
diretiva `{$MODE Delphi}` fica sob `{$IFDEF FPC}`, então o Delphi a ignora) e gera
`bin\ava_ast_cli.exe`. Para 32-bit, troque `dcc64` por `dcc32` dentro do `.bat`.

### Alternativa pela IDE

Abra `ava_ast_cli.dpr` no RAD Studio, adicione ao *Search path* do projeto:
`..\..\examples\DelphiAST\Source` e `..\..\examples\DelphiAST\Source\SimpleParser`,
e compile (Ctrl+F9). Copie o `.exe` gerado para `bin\`.

---

## 3. Verificar o binário

Com um `.pas` de exemplo do ERP:

```bat
bin\ava_ast_cli.exe examples\Meu-ERP\Classes\uClassContasCorrente.pas out.xml
type out.xml
```

Deve escrever `OK: AST written to out.xml` e o XML conter tags em MAIÚSCULAS
(`<UNIT ...>`, `<METHOD ...>`, `<TYPESECTION ...>`).

## 4. Ligar na tool

```bat
set AVA_AST_CLI=.\bin\ava_ast_cli.exe
python src\run_pipeline.py .\examples\Meu-ERP ^
    --extraction .\.ava-fabric\extraction --compressed .\.ava-fabric\compressed
```

Confirme no console `AST real: sim` e no `manifest.json` que os 8 artefatos foram
gerados. Sem o `.exe`, a tool ainda roda em modo regex (fallback por arquivo).

---

## Notas

- O contrato do XML que a tool lê é: tags em MAIÚSCULAS e os atributos
  `begin_line/end_line/kind/name/value/type`. O `TSyntaxTreeWriter.ToXML(Tree, True)`
  (o `True` = incluir info de linha) já produz isso — não altere essa chamada.
- Se um arquivo específico falhar no parse (`PARSE_ERROR` no stderr), a tool captura
  e cai no regex só para aquele arquivo; o resto do projeto segue via AST.
- Para CI, dá para rodar o Caminho A headless (FPC via linha de comando) sem IDE.
