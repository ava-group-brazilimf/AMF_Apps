---
id: 000-scaffold
name: Scaffold .NET Clean Architecture
component_type: backend
stack: dotnet
generator: src/shared/tools/f4s_dotnet_scaffold.py
verifier: src/shared/utils/verify_dotnet_solution.py
template_path: src/shared/templates/dotnet-scaffold
version_source: versions.yaml
build_command: dotnet build
manifest: dotnet
---

# F4S Scaffold Spec — .NET Backend

## Objetivo

Criar a estrutura base (scaffold) da solução .NET no repo
`outputs/tobe/source-code/{target_stack}`. Este é o **primeiro spec** da F4S.
Todo spec posterior deve respeitar os nomes de projetos, camadas, namespaces e
convenções estabelecidas aqui.

## Entradas obrigatórias

- `projects/{project_name}/context/project-config.yaml`
- `projects/{project_name}/outputs/tobe/docs/architecture-blueprint.md`
- `projects/{project_name}/outputs/tobe/speckit/constitution.md` (se existir)
- `src/modules/ava-fabric-agents/tech-stack/templates/build-cycle-dotnet-scaffold-agent.md`
  (leia como referência de engenharia — não precisa seguir passo a passo se
  conflitar com a constituição do projeto)

## Estrutura a gerar

### Execucao deterministica obrigatoria

O agente resolve os parametros das entradas e invoca o gerador como argv, a partir da
raiz do repositorio. Ele nao cria `.sln`, `.csproj`, `global.json` ou arquivos CPM
manualmente.

```text
python src/shared/tools/f4s_dotnet_scaffold.py \
  --project {project_name} \
  --root projects/{project_name}/outputs/tobe/source-code/backend \
  --solution-prefix {solution_prefix} \
  --tfm net{backend_version} \
  --sdk {dotnet_sdk_version} \
  --bcs {bc1},{bc2} \
  --json

python src/shared/utils/verify_dotnet_solution.py \
  --root projects/{project_name}/outputs/tobe/source-code/dotnet --json
```

Antes da execucao, validar os parametros no pre-flight: `solution_prefix` em PascalCase,
TFM e SDK resolvidos pela ordem `overrides -> ConfigStackDotNet.yaml -> defaults`, e ao
menos um bounded context do blueprint. O gerador consulta `dotnet new <template> --help`,
usa somente `dotnet new`, `dotnet sln` e `dotnet add reference`, registra argv/cwd/exit
code/stdout/stderr e falha sem iniciar codegen se qualquer comando retornar erro.

`--force` somente reescreve arquivos de configuracao administrados pelo scaffold;
projetos e codigo existentes sao sempre preservados.

Gere uma solution `.sln` e projetos por bounded context, seguindo Clean
Architecture:

```
{solution_prefix}.sln
global.json
Directory.Build.props
Directory.Packages.props
src/
  SharedKernel/
      {solution_prefix}.SharedKernel/
        {solution_prefix}.SharedKernel.csproj
  {BC1}/
    {BC1}.Domain/
    {BC1}.Application/
    {BC1}.Infrastructure/
    {BC1}.Api/
  {BC2}/
    ...
tests/
  {BC1}/
    {BC1}.Domain.Tests/
    {BC1}.Application.Tests/
```

- Derive `{solution_prefix}` de `project_name` em PascalCase sem espaços/hífens.
- Derive os bounded contexts (`BC1`, `BC2`, ...) de
  `architecture-blueprint.md`.
- Use `net{backend_version}` como TargetFramework (ex: `net9.0`).
- Respeite as decisões de `constitution.md`: CQRS/CRUD, ORM, cache, auth, etc.
- Não gere ainda handlers, entidades completas nem regras de negócio — apenas a
  estrutura esqueleto, pacotes NuGet e referências entre camadas.
- As versoes de pacotes criadas pelos templates oficiais sao migradas para
  `Directory.Packages.props`; os `.csproj` usam `PackageReference` sem `Version`.

## Restrições

- Não altere arquivos fora de `outputs/tobe/source-code/{target_stack}`.
- Todos os projetos devem compilar (`dotnet build`) com zero erros.
- O scaffold deve ser idempotente: se algo já existir, preserve e adapte, não
  sobrescreva sem necessidade.
- **⛔ NUNCA declare um `PackageReference` em um `.csproj` individual se ele já
  estiver presente em `Directory.Build.props`.** Isso gera `NU1504` (duplicate
  PackageReference). Pacotes comuns — como analisadores (`Microsoft.CodeAnalysis.NetAnalyzers`)
  — devem permanecer centralizados apenas em `Directory.Build.props`.
- **⛔ Com CPM (`ManagePackageVersionsCentrally=true`), todo `<PackageReference>`
  em `.csproj` deve ter um `<PackageVersion>` correspondente em `Directory.Packages.props`.**
  Nunca coloque `Version="..."` no `.csproj` quando CPM está ativo. Pacotes usados em código
  (`Serilog`, `OpenTelemetry`, `Azure.*`, etc.) devem aparecer em ambos os arquivos.
