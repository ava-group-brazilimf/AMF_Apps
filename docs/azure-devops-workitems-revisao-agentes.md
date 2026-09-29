# Work Items de Revisao dos Agentes (Azure DevOps)

Total: 42 work items (1 por agente)

Formato sugerido:
- Work Item Type: Task
- Prefixo de titulo: Revisao do agente
- Tags: ava-fabric;review;fase

## F1 - AS-IS Diagnostic

1. Titulo: Revisao do agente ava-asis-orchestrator  
Descricao: Revisar se o orchestrator valida entradas, aciona corretamente os 7 subagentes e consolida o master-report com quality gate.
2. Titulo: Revisao do agente ava-asis-solution-delphi  
Descricao: Revisar se a analise Delphi identifica padroes arquiteturais, bounded contexts e gera diagramas C4/API map consistentes.
3. Titulo: Revisao do agente ava-asis-db-analyzer  
Descricao: Revisar se o agente detecta o SGBD, reconstrui schema, documenta SPs/triggers e gera ER diagram com qualidade.
4. Titulo: Revisao do agente ava-asis-security-review  
Descricao: Revisar cobertura OWASP/LGPD, classificacao de vulnerabilidades e clareza das recomendacoes de mitigacao.
5. Titulo: Revisao do agente ava-asis-documentation  
Descricao: Revisar se regras de negocio, requisitos funcionais e fluxo de telas foram extraidos com rastreabilidade ao codigo.
6. Titulo: Revisao do agente ava-asis-inventory  
Descricao: Revisar acuracia das metricas (LOC, classes, metodos, complexidade) e consistencia do inventario por modulo.
7. Titulo: Revisao do agente ava-asis-test-qa  
Descricao: Revisar se o baseline AS-IS cobre casos criticos e se os gaps de teste estao priorizados de forma util para o TO-BE.
8. Titulo: Revisao do agente ava-asis-gaps-risks  
Descricao: Revisar consolidacao de achados, calculo de risk score e priorizacao P0-P3 com justificativa.

## F2 - TO-BE Architecture

9. Titulo: Revisao do agente ava-tobe-orchestrator  
Descricao: Revisar sequenciamento da fase TO-BE, dependencia do master-report e aplicacao correta do quality gate.
10. Titulo: Revisao do agente ava-tobe-architecture-design  
Descricao: Revisar coerencia dos bounded contexts, diagramas C4 e mapeamento de APIs com requisitos do AS-IS.
11. Titulo: Revisao do agente ava-tobe-architecture-technical  
Descricao: Revisar escolhas tecnicas, versionamento de pacotes, estrutura da solution e configuracoes de observabilidade/segredos.
12. Titulo: Revisao do agente ava-tobe-measure-size  
Descricao: Revisar premissas de sizing, calculo de esforco e estimativas de infraestrutura por wave.
13. Titulo: Revisao do agente ava-tobe-migration-plan  
Descricao: Revisar plano em waves, dependencias, criterios de aceite/rollback e consistencia do Gantt.
14. Titulo: Revisao do agente ava-coder-dotnet  
Descricao: Revisar qualidade do codigo .NET 10 gerado (DDD/CQRS/Clean), padroes de teste e aderencia a boas praticas.
15. Titulo: Revisao do agente ava-docs-tobe  
Descricao: Revisar completude da documentacao TO-BE (OpenAPI, ADRs, TDD) e alinhamento com implementacao.
16. Titulo: Revisao do agente ava-test-plan-tobe  
Descricao: Revisar piramide de testes, smoke suite e plano de carga quanto a cobertura e viabilidade de execucao.

## F3 - Prototype

17. Titulo: Revisao do agente ava-prototype  
Descricao: Revisar prototipo navegavel, fidelidade da especificacao e aderencia da jornada demonstrada ao TO-BE.

## F4 - Tech Stack

18. Titulo: Revisao do agente ava-stack-orchestrator  
Descricao: Revisar coordenacao backend/frontend e consistencia entre contratos de API e artefatos gerados.
19. Titulo: Revisao do agente ava-stack-dotnet-backend  
Descricao: Revisar controllers, validacoes, EF Core/migrations e seguranca de autenticacao no backend.
20. Titulo: Revisao do agente ava-stack-angular-frontend  
Descricao: Revisar arquitetura Angular, roteamento/guards/interceptors, autenticacao e qualidade de componentes/services.

## F5 - QA Agents

21. Titulo: Revisao do agente ava-qa-orchestrator  
Descricao: Revisar estrategia de QA, ordem de execucao dos subagentes e consolidacao do relatorio mestre.
22. Titulo: Revisao do agente ava-qa-gaps-requirements  
Descricao: Revisar identificacao de lacunas de requisitos e rastreabilidade entre requisito, risco e cobertura de teste.
23. Titulo: Revisao do agente ava-qa-behavior-mapping  
Descricao: Revisar se comportamentos esperados estao claros, testaveis e alinhados com regras de negocio.
24. Titulo: Revisao do agente ava-qa-scenario-generator  
Descricao: Revisar qualidade dos cenarios BDD/Gherkin (clareza, completude e foco em fluxos criticos).
25. Titulo: Revisao do agente ava-qa-test-case-generator  
Descricao: Revisar casos de teste gerados quanto a dados de entrada, saida esperada e criterios de aceitacao.
26. Titulo: Revisao do agente ava-qa-script-generator  
Descricao: Revisar scripts de automacao (xUnit, Playwright, k6) quanto a manutencao, confiabilidade e cobertura.
27. Titulo: Revisao do agente ava-qa-exploratory  
Descricao: Revisar roteiros exploratorios por jornada critica e qualidade dos heuristics/checklists utilizados.
28. Titulo: Revisao do agente ava-qa-evidence-capture  
Descricao: Revisar organizacao das evidencias, padrao de nomenclatura e rastreabilidade para aceite do cliente.
29. Titulo: Revisao do agente ava-qa-defect-identifier  
Descricao: Revisar classificacao e priorizacao de defeitos, incluindo severidade, impacto e recomendacoes de correcao.

## F6 - DevOps

30. Titulo: Revisao do agente ava-devops-iac  
Descricao: Revisar IaC (Terraform/Bicep), seguranca de configuracao e idempotencia de provisionamento Azure.
31. Titulo: Revisao do agente ava-devops-ci  
Descricao: Revisar pipeline CI, gates de qualidade, integracao de SAST/Sonar e confiabilidade de build/teste.
32. Titulo: Revisao do agente ava-devops-cd  
Descricao: Revisar pipeline CD, estrategia de deploy, smoke tests e capacidade de rollback seguro.
33. Titulo: Revisao do agente ava-devops-compare-version  
Descricao: Revisar metodo de comparacao AS-IS x TO-BE, criterios de paridade e analise de divergencias.
34. Titulo: Revisao do agente ava-devops-package-approval  
Descricao: Revisar validacoes de seguranca/licenca dos pacotes e conformidade com pre-requisitos de arquitetura.

## F7 - Deliverables

35. Titulo: Revisao do agente ava-deliverable-packager  
Descricao: Revisar estrutura do pacote de entrega, integridade de artefatos e completude do indice por wave.
36. Titulo: Revisao do agente ava-deliverable-tech-docs  
Descricao: Revisar documentacao tecnica consolidada quanto a clareza, atualizacao e utilidade para handover.
37. Titulo: Revisao do agente ava-deliverable-migration-plan  
Descricao: Revisar publicacao executiva do plano de migracao quanto a consistencia, riscos e cronograma.
38. Titulo: Revisao do agente ava-deliverable-security-compliance  
Descricao: Revisar consolidacao de seguranca/LGPD, evidencias de tratamento de risco e declaracoes de conformidade.
39. Titulo: Revisao do agente ava-deliverable-test-evidence  
Descricao: Revisar empacotamento das evidencias de teste, cobertura reportada e prontidao para aceite formal.
40. Titulo: Revisao do agente ava-deliverable-code-templates  
Descricao: Revisar qualidade e reusabilidade dos templates de codigo para adocao pelo time do cliente.
41. Titulo: Revisao do agente ava-deliverable-client-demo  
Descricao: Revisar roteiro de demo, narrativa executiva e completude do documento de aceite do cliente.

## F8 - Summary

42. Titulo: Revisao do agente ava-summary  
Descricao: Revisar consolidacao do HTML final, integridade dos dados por fase, renderizacao de diagramas e navegacao.
