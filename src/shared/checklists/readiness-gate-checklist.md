---
name: readiness-gate-checklist
description: "Checklist obrigatório de readiness gate a ser preenchido pelo PO/PM antes de iniciar cada wave de implementação do Build Cycle. Todos os critérios devem ser atendidos antes de executar @ava-readiness-gate."
version: "1.0.0"
---

# Readiness Gate Checklist — Human Gate Pré-Wave

> **Instrução:** Preencher este checklist ANTES de invocar `@ava-readiness-gate`.
> Todos os bloqueadores absolutos (🔴) devem estar marcados. Gates com qualquer item 🔴 desmarcado resultarão em `BLOCKED`.
> Após preenchimento, atualizar a seção `signoffs` do `project-config.yaml` do projeto.

---

## Identificação da Wave

| Campo | Valor |
|-------|-------|
| **Projeto** | <!-- project_name --> |
| **Cliente** | <!-- client_name --> |
| **Wave Nº** | <!-- 1 / 2 / 3 ... --> |
| **Escopo da Wave** | <!-- descrição do que será implementado --> |
| **Data de Avaliação** | <!-- YYYY-MM-DD --> |
| **Responsável pelo Gate** | <!-- nome do PO/PM --> |

---

## C0 — Screen Flow Completude (F1 AS-IS Documentation)

> Valida que o agente `ava-asis-documentation` (Screen Flow Mapper) produziu o artefato de assertion de completude e que a cobertura está dentro do threshold aceitável.

- [ ] 🔴 `screen-flow-completeness.json` existe em `outputs/asis/docs/screen-flow-completeness.json`
- [ ] 🔴 `status == "PASS"` (ou `human_gate_required == true` com aprovação explícita do PM)
- [ ] 🔴 `coverage_pct >= 80` (threshold mínimo de cobertura de formas)
- [ ] ⚠️ Per-BC intermediários `screen-flow-*.mmd` estão presentes em `outputs/asis/docs/` (debugging e auditoria)
- [ ] ⚠️ `retry_count <= 3` (não houve estouro de retry que exigisse human gate)

**Evidência de assertion:**
> <!-- Path do screen-flow-completeness.json -->

---

## C1 — Arquitetura aprovada pelo Cliente

> Valida que o design TO-BE foi formalmente revisado e aprovado pelo Cliente antes de qualquer geração de código.

- [ ] 🔴 O artefato `outputs/tobe/docs/architecture-blueprint.md` foi gerado e está completo
- [ ] 🔴 O Cliente recebeu e revisou a arquitetura TO-BE (C4, diagramas, bounded contexts)
- [ ] 🔴 A aprovação formal foi registrada (e-mail, ata de reunião ou documento assinado)
- [ ] 🔴 O campo `signoffs.architecture_approved_by_client: true` foi atualizado no `project-config.yaml`
- [ ] ⚠️ Comentários ou ressalvas do Cliente foram documentados e tratados

**Evidência de aprovação:**
> <!-- Link para e-mail, ata ou documento de aprovação formal -->

---

## C2 — Spec Kit completo e aprovado

> Valida que o Spec Kit está completo com todas as 6 seções obrigatórias e formalmente aprovado antes de iniciar a implementação.

- [ ] 🔴 O Spec Kit existe em `outputs/tobe/docs/spec-kit/` ou `outputs/tobe/docs/spec.md`
- [ ] 🔴 Seção `## Context` presente e preenchida
- [ ] 🔴 Seção `## Input` presente com contratos de entrada definidos
- [ ] 🔴 Seção `## Processing` presente com lógica de processamento documentada
- [ ] 🔴 Seção `## Output` presente com contratos de saída definidos
- [ ] 🔴 Seção `## Examples` presente com exemplos de uso
- [ ] 🔴 Seção `## Failure Modes` presente com cenários de falha e ações
- [ ] 🔴 Spec Kit revisado e aprovado pela equipe técnica
- [ ] 🔴 O campo `signoffs.spec_kit_approved: true` foi atualizado no `project-config.yaml`
- [ ] ⚠️ Use cases mapeados correspondem aos bounded contexts identificados no AS-IS

**Localização do Spec Kit:**
> <!-- Path do arquivo ou diretório -->

---

## C3 — Infraestrutura provisionada

> Valida que os módulos IaC (Terraform ou Bicep) foram gerados e estão prontos para provisionamento.

- [ ] 🔴 Módulos IaC gerados em `outputs/tobe/iac/` (`.tf` ou `.bicep`)
- [ ] 🔴 Recursos cobertos: AKS/App Service, Azure SQL, Redis Cache, Key Vault, Application Insights, Container Registry
- [ ] 🔴 Naming conventions corporativas aplicadas nos recursos
- [ ] 🔴 Tags obrigatórias configuradas (projeto, ambiente, centro de custo, responsável)
- [ ] 🔴 State backend do Terraform ou equivalente Bicep configurado
- [ ] ⚠️ IaC validado com `terraform validate` ou `az bicep build` sem erros
- [ ] ⚠️ Módulos de rede (VNet, subnets, NSGs, private endpoints) incluídos se aplicável

**Número de arquivos IaC gerados:**
> <!-- N arquivos .tf / .bicep em outputs/tobe/iac/ -->

---

## C4 — Ambientes configurados

> Valida que os arquivos de configuração por ambiente estão presentes e sem credenciais hardcoded.

- [ ] 🔴 Diretório `outputs/tobe/iac/environments/dev/` existe com arquivos de variáveis
- [ ] 🔴 Diretório `outputs/tobe/iac/environments/staging/` existe com arquivos de variáveis
- [ ] 🔴 Arquivos de variáveis por ambiente: `*.tfvars`, `*.parameters.json` ou `*.bicepparam`
- [ ] 🔴 Nenhuma credencial hardcoded — todos os secrets referenciam Key Vault
- [ ] 🔴 Variáveis sensíveis marcadas como `sensitive = true` (Terraform) ou equivalente
- [ ] ⚠️ Diretório `outputs/tobe/iac/environments/prod/` configurado (pode ser wave posterior)
- [ ] ⚠️ Revisão de diff entre ambientes documentada (o que muda de dev para staging/prod)

**Ambientes configurados:**
> - [ ] dev
> - [ ] staging
> - [ ] prod *(opcional nesta wave)*

---

## C5 — Sign-offs formais dos stakeholders

> Valida que os responsáveis formais do projeto registraram aprovação antes do início da implementação.

- [ ] 🔴 Sponsor do projeto assinou o sign-off formal para esta wave
- [ ] 🔴 Stakeholders técnicos e de negócio foram notificados e não apresentaram objeções
- [ ] 🔴 Data do sign-off registrada no `project-config.yaml` (`signoffs.signoff_date`)
- [ ] 🔴 Nome do responsável pelo sign-off registrado (`signoffs.signed_by`)
- [ ] 🔴 O campo `signoffs.sponsor_signoff: true` foi atualizado no `project-config.yaml`
- [ ] 🔴 O campo `signoffs.stakeholder_signoff: true` foi atualizado no `project-config.yaml`
- [ ] ⚠️ Sign-off datado há menos de 90 dias (sign-offs mais antigos exigem renovação)
- [ ] ⚠️ Ata ou registro formal do sign-off arquivado no repositório do projeto

**Sponsor:** <!-- nome -->
**Data do sign-off:** <!-- YYYY-MM-DD -->
**Documento de referência:** <!-- link ou path -->

---

## Resumo de Status

| Critério | Todos os itens 🔴 marcados? | Observações |
|----------|:--------------------------:|-------------|
| C1 — Arquitetura aprovada | ☐ Sim / ☐ Não | |
| C2 — Spec Kit completo | ☐ Sim / ☐ Não | |
| C3 — Infraestrutura provisionada | ☐ Sim / ☐ Não | |
| C4 — Ambientes configurados | ☐ Sim / ☐ Não | |
| C5 — Sign-offs formais | ☐ Sim / ☐ Não | |

**Pré-condição para executar `@ava-readiness-gate`:** todos os critérios acima com "Sim".

---

## Próximo Passo

Após preencher este checklist e atualizar o `project-config.yaml`, invocar o gate agent:

```
@ava-readiness-gate
project_name: "{project_name}"
wave_number: {N}
wave_scope: "{escopo da wave}"
```

O agente lerá o `project-config.yaml` e produzirá a decisão formal:
- ✅ **APPROVED** — wave liberada para início
- ❌ **BLOCKED** — critérios faltantes com ações corretivas
- ⚠️ **CONDITIONAL** — todos PASS mas com advertências; requer confirmação do PM
