# Agent Specification: Scaffold .NET deterministico com harness de validacao

**Feature Branch**: `044-dotnet-scaffold-deterministic-harness`
**Created**: 2026-08-24
**Status**: Draft

## Problem Statement

O scaffold .NET e hoje uma receita CLI interpretada pelo agente. Ela nao possui
gerador, matriz de SDK/TFM ou verificador proprio. O agente acaba decidindo em tempo
de execucao como criar projetos, referencias e Central Package Management (CPM).

Esta feature torna a fundacao uma operacao deterministica: o agente resolve o
contexto, fornece parametros explicitos ao script e inicia o codegen de dominio apenas
depois do gate da solution.

## Acceptance Scenarios

### Nominal

```gherkin
Dado um projeto com backend_version e dotnet_sdk_version validos
  E um blueprint com os bounded contexts Vendas e Estoque
Quando f4s_dotnet_scaffold.py recebe os parametros resolvidos pelo agente
Entao cria SharedKernel e as camadas Domain, Application, Infrastructure e Api por contexto
  E cria os testes Domain e Application, solution folders e referencias permitidas
  E centraliza no CPM as versoes emitidas pelos templates oficiais
```

### Edge

```gherkin
Dado backend_version igual a 42.0
Quando o script resolve o TFM
Entao retorna ERROR com os TFMs suportados
  E nao cria arquivos na raiz de destino
```

### Gate

```gherkin
Dado uma solution sem uma camada obrigatoria
Quando o verificador do scaffold executa
Entao interrompe antes de restore, build ou test
  E as tasks de dominio da stack nao podem iniciar
```

## Quality Gate

- [ ] `pytest tests/tools/test_f4s_dotnet_scaffold.py` verde
- [ ] Gerador e verificador retornam `PASS` para uma solution recem-criada
- [ ] Reexecucao sem `--force` preserva projetos existentes
