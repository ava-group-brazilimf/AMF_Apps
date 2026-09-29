---
id: 000-scaffold
name: Scaffold Base
stack: generic
---

# F4S Scaffold Spec — Estrutura Base

## Objetivo

Criar a estrutura base (scaffold) da solução no repo
`outputs/tobe/source-code/{target_stack}`. Este é o **primeiro spec** da F4S.
Todo spec posterior deve respeitar os diretórios, nomes e convenções
estabelecidas aqui.

## Entradas obrigatórias

- `projects/{project_name}/context/project-config.yaml`
- `projects/{project_name}/outputs/tobe/docs/architecture-blueprint.md`
- `projects/{project_name}/outputs/tobe/speckit/constitution.md` (se existir)
- Agente/template de scaffold existente para `{target_stack}` em
  `src/modules/ava-fabric-agents/tech-stack/templates/` ou
  `src/modules/ava-fabric-agents/tech-stack/agents/coder-*-*.md`

## Estrutura a gerar

Gere a estrutura mínima que permite compilação/verificação da stack:

- Arquivos de configuração obrigatórios da stack (`package.json`, `pom.xml`,
  `pyproject.toml`, `go.mod`, `*.csproj`, `*.sln`, etc.).
- Separação por bounded context / módulo, seguindo o `architecture-blueprint.md`.
- Camadas consistentes com a constituição (Domain/Application/Infrastructure/API
  quando aplicável).
- Dependências iniciais resolvidas com versões canônicas.

## Restrições

- Não altere arquivos fora de `outputs/tobe/source-code/{target_stack}`.
- A estrutura deve passar no build padrão da stack com zero erros.
- O scaffold deve ser idempotente: preserve o que já existe e adapte.
