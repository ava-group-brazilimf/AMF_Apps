---
name: asis-quality-gate
description: "Checklist de quality gate para aprovação do diagnóstico AS-IS"
version: "1.0.0"
applies_to: asis-diagnostic
---

# AS-IS Quality Gate Checklist

## Obrigatório (todos os itens devem ser ✅ antes de avançar para TO-BE)

### Cobertura de Análise
- [ ] 100% dos arquivos analisados
- [ ] Todos os bounded contexts identificados e documentados
- [ ] C4 Blueprint gerado nos 3 níveis (Contexto, Container, Componente)
- [ ] Todos os Diagrama de classes gerado para entidades
- [ ] Todos os diagrama de sequência por fluxo de modulo de negocio
- [ ] Todos os KPIS preenchidos 
- [ ] Lista de todas as integrações e componetes externas listados e categorizados

### Documentação Funcional
- [ ] Cadeia de Valor documentada contemplando 100% dos modulos funcionais em sequencia logica de execução em um diagrama de Blocos.
- [ ] Cobertura de 100% dos requisitos funcionais extraídos de 100% dos documentos documentados, codigos, banco de dados, classes e telas.
- [ ] Todas as regras de negócio identificadas, categoizadas entre regra funcional, regra de banco, regra de tela.
- [ ] Fluxo de telas (mapa de navegação) **Completo**
- [ ] Regras de tela documentadas todas as telas identificadas
- [ ] Designer System gerado pra todas as telas com a referencias para as regras de negocio levantadas, palheta de cores, fontes, tipografica, compontes de telas e padroes de UI

### Testes
- [ ] Todos os cenarios de testes criados, categorizados
- [ ] Os cenarios de testes fazem a cobertura de todas as regras de negocio,regras funcionais, regras de tela e regras de banco
- [ ] Os cenarios de teste cobrem 100% de todas as APIS expostas
- [ ] Os cenarios de integrado estão espeficificados e categorizados

### Banco de Dados
- [ ] SGBD identificado e versão documentada
- [ ] Schema completo extraído (todas as tabelas e colunas)
- [ ] Diagrama ER gerado
- [ ] Todas as Stored Procedures listadas e classificadas
- [ ] Todas as tabelas e views listadas e classificadas com a volumetria
- [ ] Todos os jobs de banco de dados listadas e classificadas
- [ ] Business logic em SP: mapeada e flagged (se existir)

### Segurança
- [ ] OWASP avaliado
- [ ] Credenciais hardcoded verificadas (zero tolerância)
- [ ] PII identificado e mapeado
- [ ] Security map gerado

### Inventário
- [ ] LOC total e por módulo calculado
- [ ] Complexidade ciclomática calculada ( arquivos destacados)
- [ ] Número de classes, métodos, camadas documentado
- [ ] Acoplamento entre módulos mapeado
- [ ] Módulos de negocio mapeados

### Riscos e Gaps
- [ ] Risk register completo (todos os findings consolidados)
- [ ] `risk-register.json` validado como JSON puro (array sem wrapper de objeto, sem comentários)
- [ ] Campos obrigatórios do parser presentes: `id`, `category`, `description`, `priority`, `evidence`, `mitigation`
- [ ] Score de risco global calculado (0–100)
- [ ] Priorização P0/P1/P2 aplicada
- [ ] Mitigações sugeridas para todos os P0

### Aprovação
- [ ] Cliente revisou e aprovou o AS-IS Master Report
- [ ] PM validou escopo e completude do diagnóstico (AS-IS Master Report)
- [ ] CTO/Tech Lead autorizou avanço para TO-BE

## Avisos (podem avançar com ressalvas documentadas)
- [ ] Testes AS-IS baseline gerado (recomendado mas não bloqueador)
- [ ] Documentação de integrações externas completa
- [ ] Protótipos AS-IS gerados para todas as telas
