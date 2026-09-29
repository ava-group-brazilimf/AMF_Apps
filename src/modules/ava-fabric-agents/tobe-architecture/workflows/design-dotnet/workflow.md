---
name: design-dotnet-tobe
display_name: "Design Arquitetura TO-BE"
description: "Workflow completo de design da arquitetura TO-BE (stack definido em project-config.yaml) com base no AS-IS Master Report"
version: "1.1.0"
orchestrator: ava-tobe-orchestrator
input_required:
  - "projects/{project_name}/outputs/asis/AS-IS-MASTER-REPORT.md"
phases:
  - id: blueprint
    name: Blueprint arquitetural
    agent: ava-tobe-architecture-design
  - id: technical
    name: Detalhamento técnico
    agent: ava-tobe-architecture-technical
    depends_on: [blueprint]
  - id: sizing
    name: Estimativas e sizing
    agent: ava-tobe-measure-size
    depends_on: [blueprint]
    parallel: true
  - id: migration-plan
    name: Plano de migração
    agent: ava-tobe-migration-plan
    depends_on: [blueprint, sizing]
  - id: documentation
    name: Documentação TO-BE
    agent: ava-docs-tobe
    depends_on: [technical]
  - id: test-plan
    name: Plano de testes
    agent: ava-test-plan-tobe
    depends_on: [blueprint, migration-plan]
    parallel: true
  - id: human-gate
    name: Aprovação arquitetura
    depends_on: [blueprint, technical]
inputs:
  language:
    required: false
    default: "pt"
    description: "Idioma dos artefatos gerados (pt | en)"
