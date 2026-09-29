# examples/ — repositórios para rodar localmente

## Meu-ERP  (alvo de teste)
Clone de https://github.com/RogerioAP/Meu-ERP — ERP Delphi brasileiro (financeiro,
clientes/fornecedores, boletos via ACBr). Artefatos de build (`Win32/`, `.dcu`,
`__history/`) foram removidos para reduzir tamanho; os 30 `.pas` + 22 `.dfm` de
fonte estão preservados. Para o repo completo:
```bash
git clone https://github.com/RogerioAP/Meu-ERP.git
```

## DelphiAST  (fonte do parser)
Clone de https://github.com/RomanYankovsky/DelphiAST — o parser Object Pascal usado
para gerar o `bin/ava_ast_cli`. Veja `bin/README.md` para recompilar.

## Rodar
```bash
export AVA_AST_CLI=./bin/ava_ast_cli
python src/run_pipeline.py ./examples/Meu-ERP \
    --extraction ./.ava-fabric/extraction --compressed ./.ava-fabric/compressed
```
