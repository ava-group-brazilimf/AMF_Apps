# bin/ — binário DelphiAST (ava_ast_cli)

`ava_ast_cli <arquivo.pas> <saida.xml>` — parseia um `.pas` e emite a AST em XML.
É consumido por `src/ast_bridge.py` (`load_ast`). Sem ele, a tool cai no fallback regex.

O binário incluído é **Linux x86-64** (compilado do DelphiAST via FPC).

> ⚠️ **Atenção:** o `bin/ava_ast_cli` incluído neste pacote está
> desatualizado — foi compilado antes da correção de um bug de recursão
> infinita em `TStringStreamHelper.GetDataString` (`SimpleParser.pas`), que
> causava `EStackOverflow` ao parsear a maioria dos arquivos `.pas`. O
> `bin/ava_ast_cli.exe` (Windows) já foi regerado com a correção; o binário
> Linux ainda não. Não use o `bin/ava_ast_cli` bundled em produção —
> recompile com o kit abaixo antes.

Observação: o XML precisa manter as tags em MAIÚSCULAS e os atributos
`begin_line/end_line/kind/name/value/type` — é o contrato que o `normalize_ast` lê.

## Windows (.exe)

Kit turnkey em `bin/build-windows/` (wrapper portável + `build-fpc.bat` +
`build-delphi.bat`). Passo a passo completo em `docs/BUILD_WINDOWS.md`.
Resumo:
```bat
cd bin\build-windows
build-fpc.bat        REM  ou  build-delphi.bat
```
Gera `bin\ava_ast_cli.exe`.

## Linux (regerar o binário bundled)

Kit turnkey em `bin/build-linux/` (`build-fpc.sh`, reaproveita o mesmo
wrapper portável de `bin/build-windows/ava_ast_cli.lpr`). Passo a passo
completo em `docs/BUILD_LINUX.md`. Resumo:
```bash
cd bin/build-linux
chmod +x build-fpc.sh && ./build-fpc.sh
```
Gera `bin/ava_ast_cli`.

## Outras plataformas (macOS etc.)

Sem kit turnkey ainda. O fonte do parser está em `examples/DelphiAST`
(RomanYankovsky/DelphiAST):

1. Instale o Free Pascal Compiler (FPC) 3.2+ ou use Delphi.
2. Compile `bin/build-windows/ava_ast_cli.lpr` (wrapper portável, sem código
   condicional de plataforma) apontando os mesmos `-Fu` do
   `examples/DelphiAST/Source` (ver `build-fpc.bat`/`build-fpc.sh` para a
   lista exata de diretórios).
3. Gere o executável e aponte `AVA_AST_CLI` para ele:
   ```bash
   export AVA_AST_CLI=/caminho/para/ava_ast_cli
   ```
