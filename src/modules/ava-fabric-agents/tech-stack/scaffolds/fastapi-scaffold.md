---
id: 000-scaffold
name: Scaffold Python FastAPI
stack: fastapi
---

# F4S Scaffold Spec — Python / FastAPI Backend

## Objetivo

Criar a estrutura base (scaffold) da solução Python 3.12 + FastAPI no repo
`outputs/tobe/source-code/{target_stack}`. Este é o **primeiro spec** da F4S.
Todo spec posterior deve respeitar os nomes de pacotes, camadas e convenções
estabelecidas aqui.

## Entradas obrigatórias

- `projects/{project_name}/context/project-config.yaml`
- `projects/{project_name}/outputs/tobe/docs/architecture-blueprint.md`
- `projects/{project_name}/outputs/tobe/speckit/constitution.md` (se existir)
- `src/modules/ava-fabric-agents/tech-stack/templates/build-cycle-python-scaffold.md`
  (leia como referência de engenharia)

## Estrutura a gerar

Gere um projeto Python com `pyproject.toml` raiz e estrutura por bounded context:

```
pyproject.toml
README.md
.env.example
docker-compose.yml
src/
  shared_kernel/
    __init__.py
  {bc1}/
    domain/
    application/
      commands/
      queries/
      handlers/
    infrastructure/
    api/
  {bc2}/
    ...
tests/
  conftest.py
  unit/
  integration/
```

- Derive os bounded contexts de `architecture-blueprint.md`.
- Use Python `tobe_stack.backend_version` (ex: `3.12`) e FastAPI canônico.
- Respeite as decisões de `constitution.md`: CQRS/CRUD, ORM (SQLModel/SQLAlchemy),
  cache, auth, etc.
- Não gere ainda models completos, endpoints de negócio nem regras — apenas a
  estrutura esqueleto, dependências e configuração de testes.

## Restrições

- Não altere arquivos fora de `outputs/tobe/source-code/{target_stack}`.
- O projeto deve passar na verificação (`python -m pytest`) com zero erros de
  importação.
- O scaffold deve ser idempotente: se algo já existir, preserve e adapte, não
  sobrescreva sem necessidade.
