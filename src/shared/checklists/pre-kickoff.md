---
name: pre-kickoff-checklist
description: "Checklist obrigatório antes do kickoff da Fábrica de Agentes AVA"
version: "1.0.0"
---

# Pre-Kickoff Checklist — AVA Fabric Factory

## Bloqueadores Absolutos (100% antes do Dia 0)

### Contratos e Formal
- [ ] NDA assinado (ambas as partes)
- [ ] DPA / LGPD agreement assinado
- [ ] Contrato de prestação de serviços assinado
- [ ] SOW com critérios de aceite assinado
- [ ] Sponsor executivo designado (com SLA de 24h)

### Acesso ao Ambiente do Cliente
- [ ] Repositório legado: acesso read-only via Git
- [ ] Schema do banco de dados (DDL scripts ou conexão isolada)
- [ ] SME disponível (mínimo 4h/semana garantido)
- [ ] Ambiente de homologação acessível

### Infraestrutura AVA
- [ ] Azure OpenAI Service provisionado (quota ≥ 100K TPM)
- [ ] AKS / Azure Container Apps configurado
- [ ] Azure Service Bus configurado
- [ ] Key Vault + Managed Identity configurados
- [ ] Application Insights + Log Analytics ativos
- [ ] GitHub / ADO com PAT configurado

### Processos
- [ ] Runbook de aprovação (human gates) documentado e aprovado
- [ ] Git flow e branch strategy definidos
- [ ] Processo de escalonamento acordado
- [ ] Relatório semanal de progresso: template e destinatários definidos
