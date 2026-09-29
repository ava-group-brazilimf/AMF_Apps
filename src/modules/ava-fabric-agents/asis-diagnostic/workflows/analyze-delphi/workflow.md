---
name: analyze-delphi-full
display_name: "Análise Completa Delphi AS-IS"
description: "Workflow completo de diagnóstico de aplicação Delphi — do repositório ao AS-IS Master Report"
version: "1.0.0"
orchestrator: ava-asis-orchestrator
phases:
  - id: validate
    name: Validação de inputs
  - id: code-analysis
    name: Análise de código
    parallel: true
  - id: documentation
    name: Documentação funcional
    depends_on: [code-analysis]
  - id: db-analysis
    name: Análise de banco de dados
    parallel: true
  - id: security
    name: Review de segurança
    parallel: true
  - id: inventory
    name: Inventário e métricas
    parallel: true
  - id: test-qa
    name: Cobertura de testes AS-IS
    parallel: true
  - id: consolidation
    name: Consolidação e gaps
    depends_on: [documentation, db-analysis, security, inventory, test-qa]
  - id: human-gate
    name: Aprovação humana
    depends_on: [consolidation]
  - id: master-report
    name: Geração do Master Report
    depends_on: [human-gate]
inputs:
  language:
    required: false
    default: "pt"
    description: "Idioma dos artefatos gerados (pt | en)"
