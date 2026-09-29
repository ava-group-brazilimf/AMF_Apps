---
name: ava-build-cycle-java-persistence
description: "Java/Spring Boot build-cycle persistence — gera JPA entities, Spring Data repositories, Flyway migrations e read model via JdbcClient. Pré-requisito: ava-build-cycle-java-scaffold. Requer pipeline_mode = "build-cycle" AND backend_framework = "spring-boot"."
---

Determine o PROJECT_NAME antes de executar:
1. Leia `projects/_template/context/project-config.yaml` → campo `project_name`
2. Se não existir ou estiver vazio, pergunte ao usuário: "Qual é o nome do projeto? (ex: Meu-ERP)"
3. Use esse PROJECT_NAME para resolver todos os caminhos: `projects/{PROJECT_NAME}/`

Antes de iniciar, leia o contexto do projeto em:
`projects/{PROJECT_NAME}/context/shared-context.md`

Leia e siga as instruções do agente em:
`src/modules/ava-fabric-agents/tech-stack/templates/build-cycle-java-persistence.md`
