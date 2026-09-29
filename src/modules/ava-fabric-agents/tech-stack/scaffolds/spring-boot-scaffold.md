---
id: 000-scaffold
name: Scaffold Java Spring Boot
stack: spring-boot
---

# F4S Scaffold Spec — Java / Spring Boot Backend

## Objetivo

Criar a estrutura base (scaffold) da solução Java 21 + Spring Boot 3 no repo
`outputs/tobe/source-code/{target_stack}`. Este é o **primeiro spec** da F4S.
Todo spec posterior deve respeitar os `groupId`, nomes de módulos, camadas e
convenções estabelecidas aqui.

## Entradas obrigatórias

- `projects/{project_name}/context/project-config.yaml`
- `projects/{project_name}/outputs/tobe/docs/architecture-blueprint.md`
- `projects/{project_name}/outputs/tobe/speckit/constitution.md` (se existir)
- `src/modules/ava-fabric-agents/tech-stack/templates/build-cycle-java-scaffold.md`
  (leia como referência de engenharia)

## Estrutura a gerar

Gere um projeto multi-módulo Maven:

```
pom.xml                    (parent BOM)
{solution-prefix}/
  pom.xml
  shared/
    pom.xml
  {BC1}/
    {BC1}-domain/pom.xml
    {BC1}-application/pom.xml
    {BC1}-infrastructure/pom.xml
    {BC1}-api/pom.xml
  {BC2}/
    ...
tests/
  {BC1}-domain-tests/
```

- Derive `{solution-prefix}` de `project_name` em kebab-case.
- Derive `group_id` de `tobe_stack.java_group_id` ou use `com.avanade` como fallback.
- Derive os bounded contexts (`BC1`, `BC2`, ...) de `architecture-blueprint.md`.
- Use Java `tobe_stack.backend_version` (ex: `21`) e Spring Boot `tobe_stack.spring_boot_version`.
- Respeite as decisões de `constitution.md`: CQRS/CRUD, ORM, cache, auth, etc.
- Não gere ainda entidades completas, handlers nem regras de negócio — apenas a
  estrutura esqueleto, dependências Maven e referências entre módulos.

## Restrições

- Não altere arquivos fora de `outputs/tobe/source-code/{target_stack}`.
- Todos os módulos devem compilar (`mvn -B verify`) com zero erros.
- O scaffold deve ser idempotente: se algo já existir, preserve e adapte, não
  sobrescreva sem necessidade.
