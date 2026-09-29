# Compilar o `ava_ast_cli` no Linux — passo a passo

O `ava_ast_cli` é o wrapper CLI do DelphiAST que a tool usa no STEP 1
(`src/ast_bridge.py` → `load_ast`).

> ⚠️ **Atenção**: o binário `bin/ava_ast_cli` incluído neste pacote está
> **desatualizado** — foi compilado antes da correção de um bug de recursão
> infinita em `TStringStreamHelper.GetDataString` (`SimpleParser.pas`), que
> causava `EStackOverflow` ao parsear praticamente qualquer `.pas`. O
> `bin/ava_ast_cli.exe` (Windows) já foi regerado com a correção; o binário
> Linux bundled ainda não. **Não use o binário bundled em produção** — gere o
> seu com o kit abaixo antes.

Kit de build (em `bin/build-linux/`):
```
build-fpc.sh       build via Free Pascal — usa o mesmo wrapper portável de
                   bin/build-windows/ava_ast_cli.lpr (sem código condicional
                   de plataforma, não precisa de cópia própria)
```
Fonte do parser: `examples/DelphiAST/Source` (clone do RomanYankovsky/DelphiAST,
já com o fix do bug de recursão infinita aplicado nesta sessão).

---

## Caminho A — Free Pascal (FPC)

### 1. Instalar o FPC

```bash
# Debian/Ubuntu
sudo apt install fp-compiler

# Fedora
sudo dnf install fpc

# Arch
sudo pacman -S fpc
```
Nome do pacote varia por distro/versão — se `fp-compiler` não existir no seu
repositório, procure por `fpc` ou baixe direto de https://www.freepascal.org.

### 2. Confirmar o FPC no PATH

```bash
fpc -iV
```
Deve imprimir a versão (ex.: `3.2.2`). Se der "command not found", ajuste o
PATH ou instale conforme o passo 1.

### 3. Compilar

```bash
cd bin/build-linux
chmod +x build-fpc.sh
./build-fpc.sh
```

Gera `bin/ava_ast_cli` e imprime o "Usage" ao final (sinal de que rodou).

> Se o FPC reclamar de `Generics.Collections`, edite `build-fpc.sh` e remova
> a linha `-Fu"$SRC/FreePascalSupport/Generics.Collection"` — o FPC já traz a
> própria implementação e essa linha extra pode conflitar.

---

## 3. Verificar o binário

Com um `.pas` de exemplo do ERP:

```bash
bin/ava_ast_cli examples/Meu-ERP/Classes/uClassContasCorrente.pas out.xml
cat out.xml
```

Deve escrever `OK: AST written to out.xml` e o XML conter tags em MAIÚSCULAS
(`<UNIT ...>`, `<METHOD ...>`, `<TYPESECTION ...>`).

## 4. Ligar na tool

```bash
export AVA_AST_CLI=./bin/ava_ast_cli
python src/run_pipeline.py ./examples/Meu-ERP \
    --extraction ./.ava-fabric/extraction --compressed ./.ava-fabric/compressed
```

Confirme no console `AST real: sim` e no `manifest.json` que os 9 artefatos
foram gerados. Sem o binário, a tool ainda roda em modo regex (fallback por
arquivo).

---

## Notas

- O contrato do XML que a tool lê é o mesmo do Windows: tags em MAIÚSCULAS e
  os atributos `begin_line/end_line/kind/name/value/type`. O
  `TSyntaxTreeWriter.ToXML(Tree, True)` já produz isso — não altere essa
  chamada.
- Lembre do `chmod +x` no binário gerado (já incluído no `build-fpc.sh`) —
  a saída do FPC nem sempre preserva o bit de execução dependendo do umask.
- Se um arquivo específico falhar no parse (`PARSE_ERROR` no stderr), a tool
  captura e cai no regex só para aquele arquivo; o resto do projeto segue via
  AST.
- Para CI, dá para rodar este kit headless (FPC via linha de comando) sem IDE,
  igual ao Caminho A do `docs/BUILD_WINDOWS.md`.
