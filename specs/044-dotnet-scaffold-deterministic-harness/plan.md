# Plan - Spec 044: Scaffold .NET deterministico com harness de validacao

## Constitution Check

- **Article I**: TFM e SDK sao resolvidos de parametros, configuracao e matriz versionada.
- **Article II / XI**: nao ha agente novo; o scaffold interno passa a orquestrar scripts.
- **Article V / VI**: spec e cenarios BDD estao em pt-BR.
- **Article VIII**: o resultado inclui argv, cwd, exit code, stdout e stderr.
- **Article IX**: referencias seguem `Domain -> Application -> Infrastructure -> Api`.
- **Article X**: o changelog sera atualizado ao concluir a implementacao.

## Architecture

```text
configuracao + blueprint + constitution
                |
                v
agente resolve prefixo, tfm, sdk e bounded contexts
                |
                v
f4s_dotnet_scaffold.py -> dotnet new / sln / add reference -> CPM
                |
                v
verify_dotnet_solution.py -> structure -> restore -> build -> test
```

## Decisions

- **CLI oficial**: a solution e os projetos nascem de `dotnet new`, e as referencias de
  `dotnet add reference`, sempre por argv. O script consulta `--help` para saber se o
  SDK selecionado suporta `--format sln`.
- **CPM por normalizacao**: as versoes emitidas por templates oficiais em projetos novos
  sao extraidas para `Directory.Packages.props`; os `PackageReference` ficam sem `Version`.
- **Idempotencia conservadora**: projetos nunca sao sobrescritos. `--force` afeta apenas
  `global.json`, `Directory.Build.props`, `Directory.Packages.props` e `.gitignore`.
