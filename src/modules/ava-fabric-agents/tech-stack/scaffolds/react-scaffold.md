---
id: 000-scaffold
name: Scaffold React Frontend
stack: react
---

# F4S Scaffold Spec — React Frontend

## Objetivo

Criar a estrutura base (scaffold) da aplicação React 18 + Vite + TypeScript no
repo `outputs/tobe/source-code/{target_stack}`. Este é o **primeiro spec** da
F4S. Todo spec posterior deve respeitar os módulos, rotas e convenções
estabelecidas aqui.

## Entradas obrigatórias

- `projects/{project_name}/context/project-config.yaml`
- `projects/{project_name}/outputs/tobe/docs/architecture-blueprint.md`
- `projects/{project_name}/outputs/tobe/speckit/constitution.md` (se existir)
- `src/modules/ava-fabric-agents/tech-stack/templates/build-cycle-react-scaffold.md`
  (leia como referência de engenharia)

## Estrutura a gerar

Gere um projeto React com Vite:

```
package.json
vite.config.ts
tsconfig.json
index.html
src/
  main.tsx
  App.tsx
  router.tsx
  core/
    auth/
    api/
    providers/
  shared/
  features/
    {bc1}/
    {bc2}/
tests/
  setup.ts
```

- Derive os bounded contexts de `architecture-blueprint.md`.
- Use React/Vite/TypeScript canônicos e `tobe_stack.frontend_version` quando aplicável.
- Configure ESLint, TypeScript strict, lazy loading e MSAL/Auth conforme
  `constitution.md`.
- Não gere ainda componentes de telas, stores completos nem regras de negócio —
  apenas a estrutura esqueleto, dependências e configuração de build.

## Restrições

- Não altere arquivos fora de `outputs/tobe/source-code/{target_stack}`.
- O projeto deve compilar (`npm run build`) com zero erros.
- O scaffold deve ser idempotente: se algo já existir, preserve e adapte, não
  sobrescreva sem necessidade.
