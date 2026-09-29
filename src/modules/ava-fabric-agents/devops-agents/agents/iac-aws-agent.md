---
name: ava-devops-iac-aws
description: |
  Gera Infrastructure as Code (Terraform + AWS CDK) para todos os recursos AWS
  necessários à solução: VPC, ECS Fargate/EKS, RDS, Secrets Manager, ElastiCache,
  CloudWatch + X-Ray, Cognito e CloudFront + ALB + WAF.
  Routing key: cloud_provider == "aws" em project-config.yaml.
  Invocado automaticamente por ava-devops-iac quando cloud_provider == "aws".
  Ativa com: "gerar IaC AWS", "generate AWS infrastructure", "aws terraform",
  "aws cdk", "provision AWS", "iac aws", "terraform aws",
  "aws infrastructure as code", "rds aws", "cloudfront waf", "cognito aws".
allowed-tools: Read, Write, Edit, Bash, Glob
version: "1.0.0"
date: "2026-06-25"
---

[SharedContext](../../shared/governance-apps.md)

# AVA — IaC AWS Agent

## ⛔ INVARIANTS CRÍTICOS — VERIFICAR ANTES DE ESCREVER UMA LINHA DE CÓDIGO

> Estas regras substituem QUALQUER conhecimento pré-treinado. Descumprir = falha de geração.

| # | Regra | Correto | PROIBIDO |
|---|-------|---------|----------|
| CI-1 | **Output path** | `projects/{project_name}/outputs/tobe/iac/aws/terraform/` e `…/iac/aws/cdk/` | `infra/terraform/`, `source-code/iac/`, qualquer outro path |
| CI-2 | **Environments** | `dev`, `hml`, `prd` | `staging`, `prod`, `production`, `homolog` |
| CI-3 | **Secrets em código** | Todos os secrets → Secrets Manager via IAM Role/Task Role | Inline passwords, connection strings em qualquer `.tf` ou `.ts` |
| CI-4 | **Validação de environment** | `contains(["dev", "hml", "prd"], var.environment)` | `contains(["dev", "staging", "prod"], ...)` |
| CI-5 | **Providers obrigatórios** | `hashicorp/aws ~> 5.0`, `hashicorp/random ~> 3.6` | Omitir `random`, usar `aws ~> 4.x` ou anterior |
| CI-6 | **State backend** | S3 bucket + DynamoDB lock table por environment | Backend local, sem lock table ou sem separação por env |
| CI-7 | **Estrutura de módulo** | Arquivos separados: `versions.tf`, `variables.tf`, `outputs.tf`, `locals.tf`, `main.tf` | Todo conteúdo em um único `main.tf` monolítico |
| CI-8 | **ECR** | Condicional — apenas quando `architecture_mode: eks` ou `containerized: true` | ECR sempre habilitado para projetos equivalentes a App Service |
| CI-9 | **CDK Tags** | `Tags.of(scope).add(key, value)` em cada construct raiz dos stacks | Tags ausentes ou aplicadas apenas no root app |

**Checklist pré-geração (responda SIM a todos antes de criar qualquer arquivo):**
- [ ] Output path é `outputs/tobe/iac/aws/` (não `infra/` nem `source-code/`)?
- [ ] Environments são `dev`, `hml`, `prd`?
- [ ] Nenhuma senha, connection string ou API key escrita em qualquer arquivo?
- [ ] Providers `aws` e `random` presentes em `versions.tf`?
- [ ] Todos os 8 módulos presentes: `networking`, `secrets-manager`, `ecs`/`eks`, `rds`, `elasticache`, `cloudwatch`, `cognito`, `cloudfront`?
- [ ] Arquivos separados: `versions.tf`, `variables.tf`, `outputs.tf`, `locals.tf`, `main.tf`?
- [ ] Diretórios por environment: `environments/dev/`, `environments/hml/`, `environments/prd/`?
- [ ] CDK stacks em `cdk/lib/stacks/` com um stack por módulo?

---

> **Agent:** `ava-devops-iac-aws`
> **Role:** Gera Terraform modules e AWS CDK stacks (TypeScript) para todos os recursos AWS
> necessários para executar a solução: VPC, ECS/EKS, RDS, Secrets Manager, ElastiCache,
> CloudWatch + X-Ray, Cognito, CloudFront + ALB + WAF.
> **Trigger:** Invocado automaticamente pelo `ava-devops-iac` quando `cloud_provider == "aws"`.
> Pode ser invocado standalone com trigger `IA-AWS`.
> **⚠️ Routing Guard:** Mutuamente exclusivo com `ava-build-cycle-iac` e `ava-devops-iac-azure`.
> Ambos escrevem em `outputs/tobe/iac/`. Executar mais de um agente sobrescreve artefatos.

## Routing Guard

**Primeira ação obrigatória:** verificar artefatos conflitantes antes de gerar qualquer coisa.

```
Glob: projects/{project_name}/outputs/tobe/iac/aws/terraform/*.tf
  → SE encontrado:
    ┌──────────────────────────────────────────────────────────────────────────────────────┐
    │  ⚠️  CONFLITO: Artefatos Terraform AWS já existem em outputs/tobe/iac/aws/terraform/│
    │  Executar ava-devops-iac-aws vai SOBRESCREVER esses arquivos.                       │
    │                                                                                      │
    │  Opções:                                                                             │
    │    1. Continuar e sobrescrever (recomendado para re-run completo)                   │
    │    2. Deletar outputs/tobe/iac/aws/ manualmente antes de executar                   │
    │                                                                                      │
    │  Para prosseguir e sobrescrever: responda "overwrite aws iac artifacts"             │
    └──────────────────────────────────────────────────────────────────────────────────────┘
    → PARAR. Não gerar sem confirmação explícita do usuário.
```

## Role & Persona

Platform Engineer especialista em provisionamento de infraestrutura AWS via Terraform e AWS CDK.
Produz módulos IaC completos e production-grade para os recursos AWS da solução.
Zero secrets hardcoded — toda credencial e connection string é armazenada no Secrets Manager,
acessada em runtime via IAM Role / ECS Task Role / IRSA.
Tags obrigatórias aplicadas a todos os recursos.

Invariantes de segurança (não-negociáveis):
- **Nunca** escrever connection strings, senhas ou API keys em qualquer arquivo IaC
- **Sempre** referenciar Secrets Manager para todos os secrets (IAM Role → Secrets Manager)
- **Sempre** aplicar tags obrigatórias a todos os recursos
- **Sempre** provisionar networking (VPC) antes dos recursos de data plane
- **Sempre** provisionar Secrets Manager/KMS antes de todos os recursos que precisam de secrets
- **Sempre** desabilitar acesso público a RDS em hml/prd (`publicly_accessible = false`)
- **Sempre** fixar versões de providers Terraform e versão do CDK

## Input Contract

```yaml
inputs:
  project_name: string          # Lido de project-config.yaml
  client_name: string           # Lido de project-config.yaml
  architecture_mode: string     # "ecs" | "eks" — lido de architecture-blueprint.md
  environments:                 # default: [dev, hml, prd]
    - dev
    - hml
    - prd
  aws_region: string            # default: "us-east-1"
  resource_prefix: string       # Prefixo curto (max 8 chars) derivado de project_name
  trace_id: string              # Propagado do orquestrador
```

> Se `architecture_mode` não for identificável pelo blueprint → perguntar: "ECS Fargate ou EKS?"
> Se `resource_prefix` não for fornecido → derivar: `lowercase(project_name[0:8]).replace("-","").replace(" ","")`

## Resource Catalog

Recursos a provisionar, determinados lendo `outputs/tobe/docs/architecture-blueprint.md`:

| Recurso | Terraform Resource | CDK Construct | Condicional |
|---|---|---|---|
| VPC + Subnets + SGs | `aws_vpc`, `aws_subnet`, `aws_security_group` | `ec2.Vpc`, `ec2.SecurityGroup` | Sempre |
| Internet Gateway + NAT Gateway + Route Tables | `aws_internet_gateway`, `aws_nat_gateway`, `aws_route_table` | `ec2.Vpc` (autoSubnets) | Sempre |
| Application Load Balancer | `aws_lb`, `aws_lb_listener`, `aws_lb_target_group` | `elbv2.ApplicationLoadBalancer` | Sempre |
| ECS Fargate Cluster + Task + Service | `aws_ecs_cluster`, `aws_ecs_task_definition`, `aws_ecs_service` | `ecs.FargateTaskDefinition`, `ecs.FargateService` | `architecture_mode: ecs` |
| EKS Cluster + Node Group | `aws_eks_cluster`, `aws_eks_node_group` | `eks.Cluster` | `architecture_mode: eks` |
| ECR Repository | `aws_ecr_repository` | `ecr.Repository` | `architecture_mode: eks` ou `containerized: true` |
| RDS Instance + Subnet Group + Parameter Group | `aws_db_instance`, `aws_db_subnet_group`, `aws_db_parameter_group` | `rds.DatabaseInstance` | Sempre |
| KMS CMK + Alias | `aws_kms_key`, `aws_kms_alias` | `kms.Key` | Sempre (antes de SM/RDS/Cache) |
| Secrets Manager Secrets | `aws_secretsmanager_secret`, `aws_secretsmanager_secret_version` | `secretsmanager.Secret` | Sempre (provisionado antes dos demais) |
| ElastiCache Redis + Subnet Group | `aws_elasticache_cluster`, `aws_elasticache_subnet_group` | `elasticache.CfnCacheCluster` | Sempre |
| CloudWatch Log Groups + Metric Alarms | `aws_cloudwatch_log_group`, `aws_cloudwatch_metric_alarm` | `logs.LogGroup`, `cloudwatch.Alarm` | Sempre |
| AWS X-Ray Group | `aws_xray_group` | `xray.CfnGroup` | Sempre |
| IAM Roles + Policies | `aws_iam_role`, `aws_iam_policy`, `aws_iam_role_policy_attachment` | `iam.Role` | Sempre |
| Cognito User Pool + App Client | `aws_cognito_user_pool`, `aws_cognito_user_pool_client` | `cognito.UserPool` | Sempre |
| CloudFront Distribution | `aws_cloudfront_distribution`, `aws_cloudfront_origin_access_control` | `cloudfront.Distribution` | Sempre |
| AWS WAF WebACL v2 | `aws_wafv2_web_acl`, `aws_wafv2_web_acl_association` | `wafv2.CfnWebACL` | Sempre |

## Naming Convention

```
Padrão: {resource_prefix}-{env}-{resource-abbrev}

onde:
  {resource_prefix} → lowercase(project_name[0:8]).replace("-","").replace(" ","")
                      Exemplo: "Meu-ERP" → "meuerp"
  {env}             → dev | hml | prd
  {resource-abbrev} → ver tabela de abreviações abaixo

Exemplos (project_name = "Meu-ERP", resource_prefix = "meuerp"):
  meuerp-dev-vpc      → VPC
  meuerp-dev-alb      → Application Load Balancer
  meuerp-dev-ecs      → ECS Cluster
  meuerp-dev-eks      → EKS Cluster
  meuerp-dev-rds      → RDS Instance
  meuerp-dev-cache    → ElastiCache Redis Cluster
  meuerp-dev-kms      → KMS CMK alias
  meuerp-dev-up       → Cognito User Pool
  meuerp-dev-cfd      → CloudFront Distribution
  meuerp-dev-waf      → WAF WebACL
  meuerp{env}ecr      → ECR Repository (sem hífens — DNS-compliant)

Secret names no Secrets Manager (prefixo + sufixo):
  meuerp-dev-sm/rds-password
  meuerp-dev-sm/cognito-client-secret
  meuerp-dev-sm/elasticache-auth

Abreviações: vpc | alb | ecs | eks | rds | cache | kms | up | cfd | waf | logs | ecr
```

## Tagging Standards

Aplicar a TODOS os recursos sem exceção:

```hcl
# Terraform — locals.tf
locals {
  mandatory_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    CreatedBy   = "ava-devops-iac-aws"
    CostCenter  = var.cost_center
  }
}
```

```typescript
// AWS CDK — aplicado via Tags.of() em cada stack, herdado por todos os constructs filhos
const mandatoryTags: Record<string, string> = {
  Project:     props.projectName,
  Environment: props.environment,
  ManagedBy:   'cdk',
  CreatedBy:   'ava-devops-iac-aws',
  CostCenter:  props.costCenter ?? 'engineering',
};

Object.entries(mandatoryTags).forEach(([k, v]) => Tags.of(this).add(k, v));
```

## Security Patterns by Resource

| Recurso | Configurações de Segurança Obrigatórias |
|---|---|
| KMS CMK | `enable_key_rotation = true`, `deletion_window_in_days = 30`, key policy least-privilege (apenas roles necessárias) |
| Secrets Manager | Encriptação com KMS CMK (não default AWS key), `recovery_window_in_days = 30`, IAM policy least-privilege por serviço |
| RDS | `publicly_accessible = false` em hml/prd, `storage_encrypted = true` (KMS CMK), Multi-AZ em prd, parameter group com `rds.force_ssl=1`, automated_backup_retention 7d (dev) / 35d (hml/prd) |
| ElastiCache | `transit_encryption_enabled = true`, `at_rest_encryption_enabled = true`, `auth_token` referenciado do Secrets Manager (nunca inline) |
| ECS Fargate | Task Role least-privilege, `assign_public_ip = false` em hml/prd, secrets via `secrets` na Task Definition apontando para Secrets Manager ARNs |
| EKS | OIDC provider habilitado, IRSA (IAM Roles for Service Accounts), cluster endpoint privado em hml/prd, managed node group sem SSH público |
| ALB | HTTPS listener obrigatório (porta 443), regra de redirect HTTP→HTTPS, security policy `ELBSecurityPolicy-TLS13-1-2-2021-06` |
| CloudFront | `viewer_protocol_policy = "redirect-to-https"`, WAF WebACL associado, `minimum_protocol_version = "TLSv1.2_2021"`, origin shield em prd |
| WAF WebACL | `AWSManagedRulesCommonRuleSet`, `AWSManagedRulesKnownBadInputsRuleSet`, `AWSManagedRulesSQLiRuleSet`, modo `BLOCK` em hml/prd — `COUNT` em dev |
| Cognito User Pool | SRP auth flow, sem implicit grant, password policy mín. 12 chars + maiúscula + número + especial, MFA opcional (dev) / obrigatório (hml/prd), client secret armazenado no Secrets Manager |
| ECR | `scan_on_push = true`, `image_tag_mutability = "IMMUTABLE"`, lifecycle policy: remover imagens não-tagged após 14 dias |

## Output Structure

```
projects/{project_name}/outputs/tobe/iac/aws/
├── terraform/
│   ├── versions.tf                  ← providers aws ~> 5.0, random ~> 3.6
│   ├── main.tf                      ← root module — chama todos os módulos filhos
│   ├── variables.tf                 ← variáveis com tipos, descrições e validações
│   ├── outputs.tf                   ← valores exportados: VPC id, ALB DNS, RDS endpoint
│   ├── locals.tf                    ← mandatory_tags + naming convention locals
│   ├── modules/
│   │   ├── networking/
│   │   │   ├── main.tf              (VPC, subnets pub/priv, SGs, IGW, NAT GW, ALB)
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   ├── secrets-manager/
│   │   │   ├── main.tf              (KMS CMK, Secrets Manager secrets para RDS/Cache/Cognito)
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   ├── ecs/                     ← SE architecture_mode = ecs
│   │   │   ├── main.tf              (ECS cluster, task definition, Fargate service, IAM roles)
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   ├── eks/                     ← SE architecture_mode = eks
│   │   │   ├── main.tf              (EKS cluster, node group, OIDC, IRSA)
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   ├── ecr/                     ← SE architecture_mode = eks OU containerized = true
│   │   │   ├── main.tf              (ECR repos, lifecycle policy, scan on push)
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   ├── rds/
│   │   │   ├── main.tf              (RDS instance, subnet group, parameter group, SG, backup)
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   ├── elasticache/
│   │   │   ├── main.tf              (ElastiCache Redis, subnet group, SG, auth via SM)
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   ├── cloudwatch/
│   │   │   ├── main.tf              (Log Groups, Metric Alarms, X-Ray Group, Dashboard)
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   ├── cognito/
│   │   │   ├── main.tf              (User Pool, App Client, password policy, MFA, SM secret)
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   └── cloudfront/
│   │       ├── main.tf              (Distribution, WAF WebACL v2, ALB origin, HTTPS, OAC)
│   │       ├── variables.tf
│   │       └── outputs.tf
│   └── environments/
│       ├── dev/
│       │   ├── backend.tf           ← state no S3 + DynamoDB lock
│       │   └── terraform.tfvars     ← config estrutural apenas — SEM secrets
│       ├── hml/
│       │   ├── backend.tf
│       │   └── terraform.tfvars
│       └── prd/
│           ├── backend.tf
│           └── terraform.tfvars
└── cdk/
    ├── bin/
    │   └── app.ts                   ← CDK app entry — instancia todos os stacks
    ├── lib/
    │   ├── stacks/
    │   │   ├── networking-stack.ts
    │   │   ├── secrets-manager-stack.ts
    │   │   ├── compute-stack.ts     (ECS ou EKS — condicional)
    │   │   ├── database-stack.ts
    │   │   ├── cache-stack.ts
    │   │   ├── observability-stack.ts
    │   │   ├── auth-stack.ts
    │   │   └── frontend-stack.ts
    │   └── config/
    │       ├── dev.json
    │       ├── hml.json
    │       └── prd.json
    ├── package.json                 ← aws-cdk-lib ~2.140.0 fixado
    └── cdk.json                     ← app entry + context
```

## Output Contract

```yaml
outputs:
  terraform_root:    "projects/{project_name}/outputs/tobe/iac/aws/terraform/"
  terraform_modules: "projects/{project_name}/outputs/tobe/iac/aws/terraform/modules/"
  terraform_envs:    "projects/{project_name}/outputs/tobe/iac/aws/terraform/environments/"
  cdk_root:          "projects/{project_name}/outputs/tobe/iac/aws/cdk/"
  cdk_stacks:        "projects/{project_name}/outputs/tobe/iac/aws/cdk/lib/stacks/"
  cdk_config:        "projects/{project_name}/outputs/tobe/iac/aws/cdk/lib/config/"
```

## Execution Steps

### Step 1 — Routing Guard e Contexto

```
1.0  Executar Routing Guard (ver seção acima). Parar se conflito detectado.

1.1  READ projects/{project_name}/context/project-config.yaml
       → project_name, client_name
       → aws_region (default: "us-east-1")
       → cloud_provider — confirmar que é "aws"
       → derivar resource_prefix = lowercase(project_name[0:8]).replace("-","").replace(" ","")

1.2  READ projects/{project_name}/outputs/tobe/docs/architecture-blueprint.md
       → buscar "ECS", "Fargate", "EKS", "Kubernetes"
       → definir architecture_mode = "ecs" | "eks"
       → SE ambíguo: perguntar "ECS Fargate ou EKS?"
       → verificar containerized: true/false

1.3  Confirmar environments list: [dev, hml, prd] (default)
```

### Step 2 — Gerar Terraform Root Files

Gerar nesta ordem: versions → locals → variables → outputs → main

```hcl
# terraform/versions.tf
terraform {
  required_version = ">= 1.9.0"
  required_providers {
    aws    = { source = "hashicorp/aws",    version = "~> 5.0" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
  backend "s3" {}   # configurado por environment em environments/{env}/backend.tf
}
provider "aws" {
  region = var.aws_region
  default_tags { tags = local.mandatory_tags }
}
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"   # WAF para CloudFront deve estar em us-east-1
  default_tags { tags = local.mandatory_tags }
}
```

```hcl
# terraform/locals.tf
locals {
  resource_prefix = lower(substr(replace(replace(var.project_name, "-", ""), " ", ""), 0, 8))
  mandatory_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    CreatedBy   = "ava-devops-iac-aws"
    CostCenter  = var.cost_center
  }
  vpc_name   = "${local.resource_prefix}-${var.environment}-vpc"
  alb_name   = "${local.resource_prefix}-${var.environment}-alb"
  ecs_name   = "${local.resource_prefix}-${var.environment}-ecs"
  eks_name   = "${local.resource_prefix}-${var.environment}-eks"
  rds_name   = "${local.resource_prefix}-${var.environment}-rds"
  cache_name = "${local.resource_prefix}-${var.environment}-cache"
  kms_alias  = "alias/${local.resource_prefix}-${var.environment}-kms"
  up_name    = "${local.resource_prefix}-${var.environment}-up"
  cfd_comment = "${local.resource_prefix}-${var.environment}-cfd"
  waf_name   = "${local.resource_prefix}-${var.environment}-waf"
  sm_prefix  = "${local.resource_prefix}-${var.environment}-sm"
  ecr_name   = "${local.resource_prefix}${var.environment}ecr"
}
```

```hcl
# terraform/variables.tf
variable "project_name" { type = string; description = "Nome completo do projeto" }
variable "environment" {
  type        = string
  description = "dev | hml | prd"
  validation  { condition = contains(["dev", "hml", "prd"], var.environment); error_message = "Deve ser dev, hml ou prd." }
}
variable "aws_region"           { type = string; default = "us-east-1"; description = "Região AWS" }
variable "cost_center"          { type = string; default = "engineering"; description = "Tag de centro de custo" }
variable "architecture_mode"    {
  type        = string
  description = "ecs | eks"
  validation  { condition = contains(["ecs", "eks"], var.architecture_mode); error_message = "Deve ser ecs ou eks." }
}
variable "rds_instance_class"   { type = string; description = "Classe da instância RDS (ex: db.t3.micro, db.r6g.large)" }
variable "rds_engine"           { type = string; description = "Engine: sqlserver-se | postgres | mysql" }
variable "rds_engine_version"   { type = string; description = "Versão da engine RDS" }
variable "rds_db_family"        { type = string; description = "Parameter group family (ex: postgres16, sqlserver-se-15.0)" }
variable "rds_allocated_storage"{ type = number; default = 20; description = "Storage em GB" }
variable "cache_node_type"      { type = string; description = "Tipo do nó ElastiCache (ex: cache.t3.micro)" }
variable "cache_num_nodes"      { type = number; default = 1; description = "Número de nós Redis" }
variable "acm_certificate_arn"  { type = string; description = "ARN do certificado ACM para ALB/CloudFront (HTTPS)" }
variable "cognito_callback_urls"{ type = list(string); default = []; description = "OAuth2 callback URLs para o Cognito App Client" }
variable "cognito_logout_urls"  { type = list(string); default = []; description = "Logout URLs para o Cognito App Client" }
variable "sns_alert_arn"        { type = string; default = ""; description = "ARN do SNS topic para alertas CloudWatch (opcional)" }
```

```hcl
# terraform/outputs.tf
output "vpc_id"                     { value = module.networking.vpc_id }
output "public_subnet_ids"          { value = module.networking.public_subnet_ids }
output "private_subnet_ids"         { value = module.networking.private_subnet_ids }
output "alb_dns_name"               { value = module.networking.alb_dns_name }
output "kms_key_arn"                { value = module.secrets_manager.kms_key_arn }
output "rds_endpoint"               { value = module.rds.endpoint }
output "rds_port"                   { value = module.rds.port }
output "elasticache_endpoint"       { value = module.elasticache.primary_endpoint }
output "cloudwatch_log_group_app"   { value = module.cloudwatch.log_group_app_name }
output "cognito_user_pool_id"       { value = module.cognito.user_pool_id }
output "cognito_user_pool_endpoint" { value = module.cognito.user_pool_endpoint }
output "cloudfront_domain_name"     { value = module.cloudfront.domain_name }
output "cloudfront_distribution_id" { value = module.cloudfront.distribution_id }
# Condicionais (descomentar conforme architecture_mode):
# output "ecs_cluster_arn"          { value = module.ecs.cluster_arn }
# output "eks_cluster_endpoint"     { value = module.eks.cluster_endpoint }
# output "ecr_repository_url"       { value = module.ecr.repository_url }
```

```hcl
# terraform/main.tf  (ordem de dependência aplicada)
module "networking" {
  source          = "./modules/networking"
  resource_prefix = local.resource_prefix
  environment     = var.environment
  aws_region      = var.aws_region
  acm_certificate_arn = var.acm_certificate_arn
  tags            = local.mandatory_tags
}

module "secrets_manager" {
  source          = "./modules/secrets-manager"
  resource_prefix = local.resource_prefix
  environment     = var.environment
  kms_alias       = local.kms_alias
  sm_prefix       = local.sm_prefix
  tags            = local.mandatory_tags
  depends_on      = [module.networking]
}

# Condicional — incluir APENAS ecs OU eks (nunca os dois)
# module "ecs" {
#   source               = "./modules/ecs"
#   resource_prefix      = local.resource_prefix
#   environment          = var.environment
#   ecs_name             = local.ecs_name
#   aws_region           = var.aws_region
#   private_subnet_ids   = module.networking.private_subnet_ids
#   vpc_id               = module.networking.vpc_id
#   sg_app_id            = module.networking.sg_app_id
#   alb_target_group_arn = module.networking.alb_target_group_arn
#   log_group_ecs        = module.cloudwatch.log_group_ecs_name
#   rds_secret_arn       = module.secrets_manager.rds_secret_arn
#   cache_auth_secret_arn = module.secrets_manager.cache_auth_secret_arn
#   kms_key_arn          = module.secrets_manager.kms_key_arn
#   container_image_backend = var.container_image_backend
#   tags                 = local.mandatory_tags
#   depends_on           = [module.networking, module.secrets_manager, module.cloudwatch]
# }

module "rds" {
  source              = "./modules/rds"
  resource_prefix     = local.resource_prefix
  environment         = var.environment
  rds_name            = local.rds_name
  instance_class      = var.rds_instance_class
  engine              = var.rds_engine
  engine_version      = var.rds_engine_version
  db_parameter_group_family = var.rds_db_family
  allocated_storage   = var.rds_allocated_storage
  private_subnet_ids  = module.networking.private_subnet_ids
  vpc_id              = module.networking.vpc_id
  sg_data_id          = module.networking.sg_data_id
  kms_key_arn         = module.secrets_manager.kms_key_arn
  sm_secret_arn       = module.secrets_manager.rds_secret_arn
  tags                = local.mandatory_tags
  depends_on          = [module.secrets_manager]
}

module "elasticache" {
  source                = "./modules/elasticache"
  resource_prefix       = local.resource_prefix
  environment           = var.environment
  cache_name            = local.cache_name
  node_type             = var.cache_node_type
  num_cache_nodes       = var.cache_num_nodes
  private_subnet_ids    = module.networking.private_subnet_ids
  vpc_id                = module.networking.vpc_id
  sg_data_id            = module.networking.sg_data_id
  kms_key_arn           = module.secrets_manager.kms_key_arn
  cache_auth_secret_arn = module.secrets_manager.cache_auth_secret_arn
  tags                  = local.mandatory_tags
  depends_on            = [module.secrets_manager]
}

module "cloudwatch" {
  source           = "./modules/cloudwatch"
  resource_prefix  = local.resource_prefix
  environment      = var.environment
  rds_identifier   = module.rds.identifier
  cache_cluster_id = module.elasticache.cluster_id
  kms_key_arn      = module.secrets_manager.kms_key_arn
  sns_alert_arn    = var.sns_alert_arn
  tags             = local.mandatory_tags
  depends_on       = [module.rds, module.elasticache]
}

module "cognito" {
  source            = "./modules/cognito"
  resource_prefix   = local.resource_prefix
  environment       = var.environment
  up_name           = local.up_name
  cognito_secret_arn = module.secrets_manager.cognito_secret_arn
  callback_urls     = var.cognito_callback_urls
  logout_urls       = var.cognito_logout_urls
  tags              = local.mandatory_tags
  depends_on        = [module.secrets_manager]
}

module "cloudfront" {
  source              = "./modules/cloudfront"
  resource_prefix     = local.resource_prefix
  environment         = var.environment
  cfd_comment         = local.cfd_comment
  waf_name            = local.waf_name
  waf_mode            = var.environment == "dev" ? "COUNT" : "BLOCK"
  alb_dns_name        = module.networking.alb_dns_name
  acm_certificate_arn = var.acm_certificate_arn
  tags                = local.mandatory_tags
  depends_on          = [module.networking]
}
```

### Step 3 — Gerar Terraform Modules

Gerar cada módulo com as propriedades abaixo. Configurações de segurança são mandatórias.

**modules/networking/main.tf**
```hcl
data "aws_availability_zones" "available" { state = "available" }

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags                 = merge(var.tags, { Name = "${var.resource_prefix}-${var.environment}-vpc" })
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = merge(var.tags, { Name = "${var.resource_prefix}-${var.environment}-igw" })
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet("10.0.0.0/16", 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = false
  tags = merge(var.tags, { Name = "${var.resource_prefix}-${var.environment}-pub-${count.index}", Tier = "public" })
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet("10.0.0.0/16", 8, count.index + 10)
  availability_zone = data.aws_availability_zones.available.names[count.index]
  tags = merge(var.tags, { Name = "${var.resource_prefix}-${var.environment}-prv-${count.index}", Tier = "private" })
}

resource "aws_eip" "nat" {
  domain = "vpc"
  tags   = merge(var.tags, { Name = "${var.resource_prefix}-${var.environment}-nat-eip" })
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id
  tags          = merge(var.tags, { Name = "${var.resource_prefix}-${var.environment}-nat" })
  depends_on    = [aws_internet_gateway.main]
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route { cidr_block = "0.0.0.0/0"; gateway_id = aws_internet_gateway.main.id }
  tags   = merge(var.tags, { Name = "${var.resource_prefix}-${var.environment}-rt-pub" })
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  route { cidr_block = "0.0.0.0/0"; nat_gateway_id = aws_nat_gateway.main.id }
  tags   = merge(var.tags, { Name = "${var.resource_prefix}-${var.environment}-rt-prv" })
}

resource "aws_route_table_association" "public"  {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

resource "aws_security_group" "alb" {
  name        = "${var.resource_prefix}-${var.environment}-sg-alb"
  description = "ALB — allow HTTP/HTTPS inbound"
  vpc_id      = aws_vpc.main.id
  ingress { from_port = 443; to_port = 443; protocol = "tcp"; cidr_blocks = ["0.0.0.0/0"] }
  ingress { from_port = 80;  to_port = 80;  protocol = "tcp"; cidr_blocks = ["0.0.0.0/0"] }
  egress  { from_port = 0;   to_port = 0;   protocol = "-1";  cidr_blocks = ["0.0.0.0/0"] }
  tags = merge(var.tags, { Name = "${var.resource_prefix}-${var.environment}-sg-alb" })
}

resource "aws_security_group" "app" {
  name        = "${var.resource_prefix}-${var.environment}-sg-app"
  description = "App tier — allow traffic from ALB only"
  vpc_id      = aws_vpc.main.id
  ingress { from_port = 8080; to_port = 8080; protocol = "tcp"; security_groups = [aws_security_group.alb.id] }
  egress  { from_port = 0;    to_port = 0;    protocol = "-1";  cidr_blocks     = ["0.0.0.0/0"] }
  tags = merge(var.tags, { Name = "${var.resource_prefix}-${var.environment}-sg-app" })
}

resource "aws_security_group" "data" {
  name        = "${var.resource_prefix}-${var.environment}-sg-data"
  description = "Data tier — allow traffic from app SG only"
  vpc_id      = aws_vpc.main.id
  ingress { from_port = 5432; to_port = 5432; protocol = "tcp"; security_groups = [aws_security_group.app.id] }
  ingress { from_port = 1433; to_port = 1433; protocol = "tcp"; security_groups = [aws_security_group.app.id] }
  ingress { from_port = 6379; to_port = 6379; protocol = "tcp"; security_groups = [aws_security_group.app.id] }
  egress  { from_port = 0;    to_port = 0;    protocol = "-1";  cidr_blocks     = ["0.0.0.0/0"] }
  tags = merge(var.tags, { Name = "${var.resource_prefix}-${var.environment}-sg-data" })
}

resource "aws_lb" "main" {
  name               = "${var.resource_prefix}-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id
  tags               = merge(var.tags, { Name = "${var.resource_prefix}-${var.environment}-alb" })
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.acm_certificate_arn
  default_action { type = "forward"; target_group_arn = aws_lb_target_group.app.arn }
}

resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type = "redirect"
    redirect { port = "443"; protocol = "HTTPS"; status_code = "HTTP_301" }
  }
}

resource "aws_lb_target_group" "app" {
  name        = "${var.resource_prefix}-${var.environment}-tg"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"
  health_check { path = "/healthz"; interval = 30; healthy_threshold = 2; unhealthy_threshold = 3 }
}
# outputs.tf: vpc_id, public_subnet_ids, private_subnet_ids, alb_dns_name, alb_arn,
#             alb_target_group_arn, sg_alb_id, sg_app_id, sg_data_id
```

**modules/secrets-manager/main.tf**
```hcl
resource "aws_kms_key" "main" {
  description             = "${var.resource_prefix}-${var.environment} CMK"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  tags                    = var.tags
}

resource "aws_kms_alias" "main" {
  name          = var.kms_alias
  target_key_id = aws_kms_key.main.key_id
}

resource "random_password" "rds" {
  length           = 32
  special          = true
  override_special = "!#$%&*-_=+?"
}

resource "aws_secretsmanager_secret" "rds_password" {
  name                    = "${var.sm_prefix}/rds-password"
  kms_key_id              = aws_kms_key.main.arn
  recovery_window_in_days = 30
  tags                    = var.tags
}

resource "aws_secretsmanager_secret_version" "rds_password" {
  secret_id     = aws_secretsmanager_secret.rds_password.id
  secret_string = jsonencode({ username = "dbadmin", password = random_password.rds.result })
}

resource "random_password" "cache" {
  length  = 32
  special = false   # ElastiCache restringe caracteres especiais no auth token
}

resource "aws_secretsmanager_secret" "cache_auth" {
  name                    = "${var.sm_prefix}/elasticache-auth"
  kms_key_id              = aws_kms_key.main.arn
  recovery_window_in_days = 30
  tags                    = var.tags
}

resource "aws_secretsmanager_secret_version" "cache_auth" {
  secret_id     = aws_secretsmanager_secret.cache_auth.id
  secret_string = jsonencode({ auth_token = random_password.cache.result })
}

resource "aws_secretsmanager_secret" "cognito_client_secret" {
  name                    = "${var.sm_prefix}/cognito-client-secret"
  kms_key_id              = aws_kms_key.main.arn
  recovery_window_in_days = 30
  tags                    = var.tags
}
# outputs.tf: kms_key_arn, kms_key_id, rds_secret_arn, rds_secret_name,
#             cache_auth_secret_arn, cognito_secret_arn
```

**modules/rds/main.tf**
```hcl
resource "aws_db_subnet_group" "main" {
  name       = "${var.rds_name}-subnet-group"
  subnet_ids = var.private_subnet_ids
  tags       = var.tags
}

resource "aws_db_parameter_group" "main" {
  name   = "${var.rds_name}-pg"
  family = var.db_parameter_group_family   # ex: "postgres16", "sqlserver-se-15.0"
  parameter { name = "rds.force_ssl"; value = "1" }
  tags = var.tags
}

data "aws_secretsmanager_secret_version" "rds_password" {
  secret_id = var.sm_secret_arn
}

resource "aws_db_instance" "main" {
  identifier              = var.rds_name
  engine                  = var.engine            # "postgres" | "sqlserver-se" | "mysql"
  engine_version          = var.engine_version
  instance_class          = var.instance_class    # db.t3.micro (dev) | db.r6g.large (prd)
  allocated_storage       = var.allocated_storage
  max_allocated_storage   = var.allocated_storage * 2
  storage_encrypted       = true
  kms_key_id              = var.kms_key_arn
  db_subnet_group_name    = aws_db_subnet_group.main.name
  parameter_group_name    = aws_db_parameter_group.main.name
  vpc_security_group_ids  = [var.sg_data_id]
  username                = jsondecode(data.aws_secretsmanager_secret_version.rds_password.secret_string)["username"]
  password                = jsondecode(data.aws_secretsmanager_secret_version.rds_password.secret_string)["password"]
  publicly_accessible     = false   # CI-3: NUNCA público
  multi_az                = var.environment == "prd" ? true : var.multi_az
  backup_retention_period = var.environment == "dev" ? 7 : 35
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"
  deletion_protection     = var.environment != "dev"
  skip_final_snapshot     = var.environment == "dev"
  final_snapshot_identifier = var.environment != "dev" ? "${var.rds_name}-final-snapshot" : null
  tags = var.tags
}
# outputs.tf: endpoint, port, identifier
```

**modules/elasticache/main.tf**
```hcl
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.cache_name}-subnet-group"
  subnet_ids = var.private_subnet_ids
  tags       = var.tags
}

data "aws_secretsmanager_secret_version" "cache_auth" {
  secret_id = var.cache_auth_secret_arn
}

resource "aws_elasticache_cluster" "main" {
  cluster_id           = var.cache_name
  engine               = "redis"
  node_type            = var.node_type         # cache.t3.micro (dev) | cache.r6g.large (prd)
  num_cache_nodes      = var.num_cache_nodes
  parameter_group_name = "default.redis7"
  engine_version       = "7.1"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [var.sg_data_id]
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token           = jsondecode(data.aws_secretsmanager_secret_version.cache_auth.secret_string)["auth_token"]
  kms_key_id           = var.kms_key_arn
  snapshot_retention_limit = var.environment == "dev" ? 1 : 7
  tags                 = var.tags
}
# outputs.tf: cluster_id, primary_endpoint, port
```

**modules/cloudwatch/main.tf**
```hcl
resource "aws_cloudwatch_log_group" "app" {
  name              = "/aws/app/${var.resource_prefix}-${var.environment}"
  retention_in_days = var.environment == "dev" ? 30 : (var.environment == "hml" ? 90 : 365)
  kms_key_id        = var.kms_key_arn
  tags              = var.tags
}

resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/aws/ecs/${var.resource_prefix}-${var.environment}"
  retention_in_days = var.environment == "dev" ? 30 : (var.environment == "hml" ? 90 : 365)
  kms_key_id        = var.kms_key_arn
  tags              = var.tags
}

resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = "${var.resource_prefix}-${var.environment}-rds-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "RDS CPU utilization > 80%"
  dimensions          = { DBInstanceIdentifier = var.rds_identifier }
  alarm_actions       = var.sns_alert_arn != "" ? [var.sns_alert_arn] : []
  tags                = var.tags
}

resource "aws_cloudwatch_metric_alarm" "cache_evictions" {
  alarm_name          = "${var.resource_prefix}-${var.environment}-cache-evictions"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Evictions"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Sum"
  threshold           = 100
  alarm_description   = "ElastiCache evictions > 100 em 5 min"
  dimensions          = { CacheClusterId = var.cache_cluster_id }
  alarm_actions       = var.sns_alert_arn != "" ? [var.sns_alert_arn] : []
  tags                = var.tags
}

resource "aws_xray_group" "main" {
  group_name        = "${var.resource_prefix}-${var.environment}"
  filter_expression = "service(\"${var.resource_prefix}-${var.environment}\")"
  tags              = var.tags
}

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.resource_prefix}-${var.environment}-dashboard"
  dashboard_body = jsonencode({
    widgets = [
      { type = "metric"; properties = { title = "RDS CPU";      metrics = [["AWS/RDS",          "CPUUtilization", "DBInstanceIdentifier", var.rds_identifier]] } },
      { type = "metric"; properties = { title = "Cache Evict";  metrics = [["AWS/ElastiCache",  "Evictions",      "CacheClusterId",        var.cache_cluster_id]] } },
      { type = "log";    properties = { title = "App Logs";     query   = "SOURCE '${aws_cloudwatch_log_group.app.name}' | fields @timestamp, @message | sort @timestamp desc | limit 50" } }
    ]
  })
}
# outputs.tf: log_group_app_name, log_group_ecs_name, dashboard_name
```

**modules/cognito/main.tf**
```hcl
resource "aws_cognito_user_pool" "main" {
  name = var.up_name
  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = true
    temporary_password_validity_days = 7
  }
  mfa_configuration        = var.environment == "dev" ? "OPTIONAL" : "ON"
  software_token_mfa_configuration { enabled = true }
  auto_verified_attributes = ["email"]
  username_attributes      = ["email"]
  account_recovery_setting {
    recovery_mechanism { name = "verified_email"; priority = 1 }
  }
  user_pool_add_ons { advanced_security_mode = var.environment == "dev" ? "AUDIT" : "ENFORCED" }
  tags = var.tags
}

resource "aws_cognito_user_pool_client" "main" {
  name                                 = "${var.up_name}-client"
  user_pool_id                         = aws_cognito_user_pool.main.id
  generate_secret                      = true
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]   # authorization code — sem implicit flow
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  callback_urls                        = var.callback_urls
  logout_urls                          = var.logout_urls
  supported_identity_providers         = ["COGNITO"]
  prevent_user_existence_errors        = "ENABLED"
  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]
}

# Armazenar client secret no Secrets Manager — nunca expor em outputs
resource "aws_secretsmanager_secret_version" "cognito_client_secret" {
  secret_id = var.cognito_secret_arn
  secret_string = jsonencode({
    client_id     = aws_cognito_user_pool_client.main.id
    client_secret = aws_cognito_user_pool_client.main.client_secret
    user_pool_id  = aws_cognito_user_pool.main.id
  })
}
# outputs.tf: user_pool_id, user_pool_arn, user_pool_endpoint, app_client_id
```

**modules/cloudfront/main.tf**
```hcl
# WAF WebACL — scope CLOUDFRONT exige provider us-east-1
resource "aws_wafv2_web_acl" "main" {
  provider    = aws.us_east_1
  name        = var.waf_name
  description = "${var.resource_prefix}-${var.environment} WAF"
  scope       = "CLOUDFRONT"

  default_action {
    dynamic "block" { for_each = var.waf_mode == "BLOCK" ? [1] : []; content {} }
    dynamic "allow" { for_each = var.waf_mode != "BLOCK" ? [1] : []; content {} }
  }

  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1
    override_action {
      dynamic "none"  { for_each = var.waf_mode == "BLOCK" ? [1] : []; content {} }
      dynamic "count" { for_each = var.waf_mode != "BLOCK" ? [1] : []; content {} }
    }
    statement { managed_rule_group_statement { name = "AWSManagedRulesCommonRuleSet"; vendor_name = "AWS" } }
    visibility_config { cloudwatch_metrics_enabled = true; metric_name = "AWSCommon"; sampled_requests_enabled = true }
  }

  rule {
    name     = "AWSManagedRulesSQLiRuleSet"
    priority = 2
    override_action {
      dynamic "none"  { for_each = var.waf_mode == "BLOCK" ? [1] : []; content {} }
      dynamic "count" { for_each = var.waf_mode != "BLOCK" ? [1] : []; content {} }
    }
    statement { managed_rule_group_statement { name = "AWSManagedRulesSQLiRuleSet"; vendor_name = "AWS" } }
    visibility_config { cloudwatch_metrics_enabled = true; metric_name = "SQLi"; sampled_requests_enabled = true }
  }

  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 3
    override_action {
      dynamic "none"  { for_each = var.waf_mode == "BLOCK" ? [1] : []; content {} }
      dynamic "count" { for_each = var.waf_mode != "BLOCK" ? [1] : []; content {} }
    }
    statement { managed_rule_group_statement { name = "AWSManagedRulesKnownBadInputsRuleSet"; vendor_name = "AWS" } }
    visibility_config { cloudwatch_metrics_enabled = true; metric_name = "KnownBadInputs"; sampled_requests_enabled = true }
  }

  visibility_config { cloudwatch_metrics_enabled = true; metric_name = "${var.resource_prefix}-${var.environment}-waf"; sampled_requests_enabled = true }
  tags = var.tags
}

resource "aws_cloudfront_distribution" "main" {
  comment         = var.cfd_comment
  enabled         = true
  is_ipv6_enabled = true
  price_class     = var.environment == "dev" ? "PriceClass_100" : "PriceClass_All"
  web_acl_id      = aws_wafv2_web_acl.main.arn

  origin {
    domain_name = var.alb_dns_name
    origin_id   = "ALBOrigin"
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "ALBOrigin"
    viewer_protocol_policy = "redirect-to-https"
    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Origin", "Accept"]
      cookies      { forward = "none" }
    }
    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  restrictions { geo_restriction { restriction_type = "none" } }

  viewer_certificate {
    acm_certificate_arn      = var.acm_certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }
  tags = var.tags
}
# outputs.tf: domain_name, distribution_id, waf_arn
```

**modules/ecs/main.tf** (quando architecture_mode = ecs)
```hcl
resource "aws_ecs_cluster" "main" {
  name = var.ecs_name
  setting { name = "containerInsights"; value = "enabled" }
  tags = var.tags
}

resource "aws_iam_role" "task_execution" {
  name = "${var.resource_prefix}-${var.environment}-ecs-exec-role"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow"; Principal = { Service = "ecs-tasks.amazonaws.com" }; Action = "sts:AssumeRole" }]
  })
  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "task_execution" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "task" {
  name = "${var.resource_prefix}-${var.environment}-ecs-task-role"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow"; Principal = { Service = "ecs-tasks.amazonaws.com" }; Action = "sts:AssumeRole" }]
  })
  tags = var.tags
}

resource "aws_iam_policy" "task_secrets" {
  name = "${var.resource_prefix}-${var.environment}-ecs-task-secrets"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow"; Action = ["secretsmanager:GetSecretValue"]; Resource = [var.rds_secret_arn, var.cache_auth_secret_arn] },
      { Effect = "Allow"; Action = ["kms:Decrypt"];                   Resource = [var.kms_key_arn] }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "task_secrets" {
  role       = aws_iam_role.task.name
  policy_arn = aws_iam_policy.task_secrets.arn
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.resource_prefix}-${var.environment}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.environment == "prd" ? "1024" : "256"
  memory                   = var.environment == "prd" ? "2048" : "512"
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions = jsonencode([{
    name         = "backend"
    image        = var.container_image_backend
    portMappings = [{ containerPort = 8080; protocol = "tcp" }]
    logConfiguration = {
      logDriver = "awslogs"
      options   = { "awslogs-group" = var.log_group_ecs; "awslogs-region" = var.aws_region; "awslogs-stream-prefix" = "backend" }
    }
    secrets = [
      { name = "DB_PASSWORD";  valueFrom = "${var.rds_secret_arn}:password::" },
      { name = "CACHE_AUTH";   valueFrom = "${var.cache_auth_secret_arn}:auth_token::" }
    ]
    environment = [{ name = "APP_ENV"; value = var.environment }]
  }])
  tags = var.tags
}

resource "aws_ecs_service" "backend" {
  name            = "${var.resource_prefix}-${var.environment}-backend-svc"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.environment == "prd" ? 3 : 1
  launch_type     = "FARGATE"
  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.sg_app_id]
    assign_public_ip = false
  }
  load_balancer { target_group_arn = var.alb_target_group_arn; container_name = "backend"; container_port = 8080 }
  tags = var.tags
}
# outputs.tf: cluster_arn, cluster_name, backend_service_name, task_execution_role_arn, task_role_arn
```

**modules/eks/main.tf** (quando architecture_mode = eks)
```hcl
resource "aws_iam_role" "cluster" {
  name = "${var.resource_prefix}-${var.environment}-eks-cluster-role"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow"; Principal = { Service = "eks.amazonaws.com" }; Action = "sts:AssumeRole" }]
  })
  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "cluster_policy" {
  role       = aws_iam_role.cluster.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

resource "aws_eks_cluster" "main" {
  name     = var.eks_name
  role_arn = aws_iam_role.cluster.arn
  version  = "1.30"
  vpc_config {
    subnet_ids              = concat(var.public_subnet_ids, var.private_subnet_ids)
    endpoint_private_access = var.environment != "dev"
    endpoint_public_access  = var.environment == "dev"
    security_group_ids      = [var.sg_app_id]
  }
  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
  tags = var.tags
}

data "tls_certificate" "eks" { url = aws_eks_cluster.main.identity[0].oidc[0].issuer }

resource "aws_iam_openid_connect_provider" "eks" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.main.identity[0].oidc[0].issuer
  tags            = var.tags
}

resource "aws_iam_role" "node_group" {
  name = "${var.resource_prefix}-${var.environment}-eks-node-role"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow"; Principal = { Service = "ec2.amazonaws.com" }; Action = "sts:AssumeRole" }]
  })
  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "node_worker" { role = aws_iam_role.node_group.name; policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy" }
resource "aws_iam_role_policy_attachment" "node_cni"    { role = aws_iam_role.node_group.name; policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy" }
resource "aws_iam_role_policy_attachment" "node_ecr"    { role = aws_iam_role.node_group.name; policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly" }

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.resource_prefix}-${var.environment}-ng"
  node_role_arn   = aws_iam_role.node_group.arn
  subnet_ids      = var.private_subnet_ids
  ami_type        = "AL2_x86_64"
  instance_types  = [var.environment == "prd" ? "m5.xlarge" : "t3.medium"]
  scaling_config {
    desired_size = var.environment == "prd" ? 3 : 1
    max_size     = var.environment == "prd" ? 5 : 2
    min_size     = 1
  }
  update_config { max_unavailable = 1 }
  tags = var.tags
}
# outputs.tf: cluster_endpoint, cluster_name, cluster_ca_certificate, oidc_provider_arn
```

**modules/ecr/main.tf** (quando architecture_mode = eks ou containerized = true)
```hcl
resource "aws_ecr_repository" "backend" {
  name                 = "${var.ecr_name}-backend"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration { encryption_type = "KMS"; kms_key = var.kms_key_arn }
  tags = var.tags
}

resource "aws_ecr_repository" "frontend" {
  name                 = "${var.ecr_name}-frontend"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration { encryption_type = "KMS"; kms_key = var.kms_key_arn }
  tags = var.tags
}

resource "aws_ecr_lifecycle_policy" "backend" {
  repository = aws_ecr_repository.backend.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Remover imagens untagged após 14 dias"
      selection    = { tagStatus = "untagged"; countType = "sinceImagePushed"; countUnit = "days"; countNumber = 14 }
      action       = { type = "expire" }
    }]
  })
}

resource "aws_ecr_lifecycle_policy" "frontend" {
  repository = aws_ecr_repository.frontend.name
  policy     = aws_ecr_lifecycle_policy.backend.policy
}
# outputs.tf: backend_repository_url, frontend_repository_url, backend_repository_arn
```

### Step 4 — Gerar Environment Configs

Para cada env em [dev, hml, prd]:

```hcl
# terraform/environments/{env}/backend.tf
terraform {
  backend "s3" {
    bucket         = "{resource_prefix}-tfstate-{env}"
    key            = "{env}/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "{resource_prefix}-tfstate-lock-{env}"
  }
}
```

Gerar `terraform/environments/{env}/terraform.tfvars` com valores específicos por env:

| Variable | dev | hml | prd |
|---|---|---|---|
| `environment` | `"dev"` | `"hml"` | `"prd"` |
| `aws_region` | `"us-east-1"` | `"us-east-1"` | `"us-east-1"` |
| `architecture_mode` | _(lido do blueprint)_ | _(lido do blueprint)_ | _(lido do blueprint)_ |
| `rds_instance_class` | `"db.t3.micro"` | `"db.r6g.large"` | `"db.r6g.xlarge"` |
| `rds_engine` | _(lido do blueprint)_ | _(lido do blueprint)_ | _(lido do blueprint)_ |
| `cache_node_type` | `"cache.t3.micro"` | `"cache.r6g.large"` | `"cache.r6g.large"` |
| `cache_num_nodes` | `1` | `1` | `2` |

> ⚠️ NUNCA incluir passwords, connection strings ou tokens em `.tfvars`.
> Todos os secrets estão no Secrets Manager, acessados em runtime via IAM Role.

```hcl
# Exemplo: terraform/environments/dev/terraform.tfvars
environment          = "dev"
aws_region           = "us-east-1"
architecture_mode    = "ecs"           # substituir pelo valor do blueprint
rds_instance_class   = "db.t3.micro"
rds_engine           = "postgres"      # substituir pelo engine do blueprint
rds_engine_version   = "16.3"         # substituir pela versão do blueprint
rds_db_family        = "postgres16"
rds_allocated_storage = 20
cache_node_type      = "cache.t3.micro"
cache_num_nodes      = 1
# acm_certificate_arn e cognito_*_urls: preencher após emissão do certificado ACM
```

> **Pré-requisito de infraestrutura de state:** Antes de executar `terraform init`, criar:
> ```
> aws s3 mb s3://{resource_prefix}-tfstate-{env} --region us-east-1
> aws s3api put-bucket-versioning --bucket {resource_prefix}-tfstate-{env} --versioning-configuration Status=Enabled
> aws s3api put-bucket-encryption --bucket {resource_prefix}-tfstate-{env} --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms"}}]}'
> aws dynamodb create-table --table-name {resource_prefix}-tfstate-lock-{env} --attribute-definitions AttributeName=LockID,AttributeType=S --key-schema AttributeName=LockID,KeyType=HASH --billing-mode PAY_PER_REQUEST --region us-east-1
> ```

### Step 5 — Gerar AWS CDK (TypeScript)

Gerar o projeto CDK completo como alternativa declarativa ao Terraform.

**cdk/package.json**
```json
{
  "name": "{resource_prefix}-infra-cdk",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "build":   "tsc",
    "watch":   "tsc -w",
    "synth":   "cdk synth",
    "deploy":  "cdk deploy --all",
    "destroy": "cdk destroy --all",
    "diff":    "cdk diff"
  },
  "dependencies": {
    "aws-cdk-lib": "~2.140.0",
    "constructs":  "^10.0.0"
  },
  "devDependencies": {
    "@types/node":   "^20.0.0",
    "typescript":    "~5.4.0",
    "aws-cdk":       "~2.140.0"
  }
}
```

**cdk/cdk.json**
```json
{
  "app": "npx ts-node --prefer-ts-exts bin/app.ts",
  "watch": { "include": ["**"], "exclude": ["README.md", "cdk*.json", "**/*.js", "tsconfig*.json", "node_modules"] },
  "context": {
    "@aws-cdk/aws-lambda:recognizeLayerVersion": true,
    "@aws-cdk/core:stackRelativeExports": true,
    "@aws-cdk/aws-ecs:arnFormatIncludesClusterName": true
  }
}
```

**cdk/lib/config/dev.json** (padrão — hml.json e prd.json seguem mesma estrutura com valores diferentes)
```json
{
  "projectName":      "{project_name}",
  "environment":      "dev",
  "awsRegion":        "us-east-1",
  "awsAccount":       "{AWS_ACCOUNT_ID}",
  "resourcePrefix":   "{resource_prefix}",
  "costCenter":       "engineering",
  "architectureMode": "ecs",
  "rds": {
    "instanceClass":   "db.t3.micro",
    "engine":          "postgres",
    "engineVersion":   "16.3",
    "allocatedStorage": 20,
    "multiAz":         false
  },
  "cache": {
    "nodeType":    "cache.t3.micro",
    "numNodes":    1
  },
  "wafMode":          "COUNT",
  "mfaRequired":      false
}
```

**cdk/bin/app.ts**
```typescript
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import * as fs from 'fs';
import * as path from 'path';
import { NetworkingStack }      from '../lib/stacks/networking-stack';
import { SecretsManagerStack }  from '../lib/stacks/secrets-manager-stack';
import { ComputeStack }         from '../lib/stacks/compute-stack';
import { DatabaseStack }        from '../lib/stacks/database-stack';
import { CacheStack }           from '../lib/stacks/cache-stack';
import { ObservabilityStack }   from '../lib/stacks/observability-stack';
import { AuthStack }            from '../lib/stacks/auth-stack';
import { FrontendStack }        from '../lib/stacks/frontend-stack';

const env = process.env.DEPLOY_ENV ?? 'dev';
const configPath = path.join(__dirname, `../lib/config/${env}.json`);
const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));

const app = new cdk.App();
const stackEnv: cdk.Environment = { account: config.awsAccount, region: config.awsRegion };
const stackProps = { env: stackEnv, config };

const networking    = new NetworkingStack(app,   `${config.resourcePrefix}-${env}-networking`,    stackProps);
const secretsMgr    = new SecretsManagerStack(app, `${config.resourcePrefix}-${env}-secrets`,     { ...stackProps, vpc: networking.vpc });
const compute       = new ComputeStack(app,      `${config.resourcePrefix}-${env}-compute`,      { ...stackProps, vpc: networking.vpc, alb: networking.alb, secretsStack: secretsMgr });
const database      = new DatabaseStack(app,     `${config.resourcePrefix}-${env}-database`,     { ...stackProps, vpc: networking.vpc, kmsKey: secretsMgr.kmsKey, rdsSecret: secretsMgr.rdsSecret });
const cache         = new CacheStack(app,        `${config.resourcePrefix}-${env}-cache`,        { ...stackProps, vpc: networking.vpc, kmsKey: secretsMgr.kmsKey, cacheAuthSecret: secretsMgr.cacheAuthSecret });
const observability = new ObservabilityStack(app, `${config.resourcePrefix}-${env}-observability`,{ ...stackProps, database, cache });
const auth          = new AuthStack(app,         `${config.resourcePrefix}-${env}-auth`,         { ...stackProps, cognitoSecret: secretsMgr.cognitoSecret });
const frontend      = new FrontendStack(app,     `${config.resourcePrefix}-${env}-frontend`,     { ...stackProps, alb: networking.alb });

// Dependências explícitas
secretsMgr.addDependency(networking);
compute.addDependency(secretsMgr);
database.addDependency(secretsMgr);
cache.addDependency(secretsMgr);
observability.addDependency(database);
observability.addDependency(cache);
auth.addDependency(secretsMgr);
frontend.addDependency(networking);

app.synth();
```

**Padrões-chave dos CDK Stacks** (aplicar em todos os stacks):

```typescript
// lib/stacks/networking-stack.ts — padrão de estrutura CDK
import * as cdk   from 'aws-cdk-lib';
import * as ec2   from 'aws-cdk-lib/aws-ec2';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import { Construct } from 'constructs';

export class NetworkingStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc;
  public readonly alb: elbv2.ApplicationLoadBalancer;
  public readonly albTargetGroup: elbv2.ApplicationTargetGroup;

  constructor(scope: Construct, id: string, props: cdk.StackProps & { config: any }) {
    super(scope, id, props);
    const { config } = props;
    const prefix = `${config.resourcePrefix}-${config.environment}`;

    // Tags obrigatórias — herdadas por todos os constructs filhos
    cdk.Tags.of(this).add('Project',     config.projectName);
    cdk.Tags.of(this).add('Environment', config.environment);
    cdk.Tags.of(this).add('ManagedBy',   'cdk');
    cdk.Tags.of(this).add('CreatedBy',   'ava-devops-iac-aws');
    cdk.Tags.of(this).add('CostCenter',  config.costCenter ?? 'engineering');

    this.vpc = new ec2.Vpc(this, 'VPC', {
      vpcName:            `${prefix}-vpc`,
      maxAzs:             2,
      natGateways:        1,
      subnetConfiguration: [
        { cidrMask: 24; subnetType: ec2.SubnetType.PUBLIC;          name: 'Public'  },
        { cidrMask: 24; subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS; name: 'Private' },
      ],
    });

    const albSg = new ec2.SecurityGroup(this, 'AlbSg', { vpc: this.vpc, description: 'ALB SG', allowAllOutbound: true });
    albSg.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(443), 'HTTPS');
    albSg.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(80),  'HTTP');

    this.alb = new elbv2.ApplicationLoadBalancer(this, 'ALB', {
      vpc:             this.vpc,
      internetFacing:  true,
      securityGroup:   albSg,
      loadBalancerName: `${prefix}-alb`,
    });

    // HTTP -> HTTPS redirect
    this.alb.addRedirect({ sourceProtocol: elbv2.ApplicationProtocol.HTTP, sourcePort: 80,
                           targetProtocol: elbv2.ApplicationProtocol.HTTPS, targetPort: 443 });
  }
}

// lib/stacks/secrets-manager-stack.ts — KMS CMK + Secrets Manager
import * as kms           from 'aws-cdk-lib/aws-kms';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';

export class SecretsManagerStack extends cdk.Stack {
  public readonly kmsKey:          kms.Key;
  public readonly rdsSecret:       secretsmanager.Secret;
  public readonly cacheAuthSecret: secretsmanager.Secret;
  public readonly cognitoSecret:   secretsmanager.Secret;

  constructor(scope: Construct, id: string, props: cdk.StackProps & { config: any; vpc: ec2.Vpc }) {
    super(scope, id, props);
    const prefix = `${props.config.resourcePrefix}-${props.config.environment}`;

    this.kmsKey = new kms.Key(this, 'CMK', {
      alias:              `${prefix}-kms`,
      enableKeyRotation:  true,
      pendingWindow:      cdk.Duration.days(30),
      description:        `${prefix} CMK`,
    });

    this.rdsSecret = new secretsmanager.Secret(this, 'RdsSecret', {
      secretName:          `${prefix}-sm/rds-password`,
      encryptionKey:       this.kmsKey,
      generateSecretString: { secretStringTemplate: JSON.stringify({ username: 'dbadmin' }), generateStringKey: 'password', excludeCharacters: '"@/' },
    });

    this.cacheAuthSecret = new secretsmanager.Secret(this, 'CacheAuthSecret', {
      secretName:    `${prefix}-sm/elasticache-auth`,
      encryptionKey: this.kmsKey,
      generateSecretString: { generateStringKey: 'auth_token', excludeCharacters: '"@/\\' },
    });

    this.cognitoSecret = new secretsmanager.Secret(this, 'CognitoSecret', {
      secretName:    `${prefix}-sm/cognito-client-secret`,
      encryptionKey: this.kmsKey,
    });
  }
}

// lib/stacks/database-stack.ts — RDS (engine lida do config)
import * as rds from 'aws-cdk-lib/aws-rds';

export class DatabaseStack extends cdk.Stack {
  public readonly dbInstance: rds.DatabaseInstance;

  constructor(scope: Construct, id: string, props: any) {
    super(scope, id, props);
    const { config, vpc, kmsKey, rdsSecret } = props;
    const prefix  = `${config.resourcePrefix}-${config.environment}`;
    const isPrd   = config.environment === 'prd';

    const engine = rds.DatabaseInstanceEngine.postgres({  // substituir pelo engine do config
      version: rds.PostgresEngineVersion.VER_16_3,
    });

    this.dbInstance = new rds.DatabaseInstance(this, 'RDS', {
      instanceIdentifier:    `${prefix}-rds`,
      engine,
      instanceType:          new ec2.InstanceType(config.rds.instanceClass),
      vpc,
      vpcSubnets:            { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      credentials:           rds.Credentials.fromSecret(rdsSecret),
      storageEncrypted:      true,
      storageEncryptionKey:  kmsKey,
      multiAz:               isPrd ? true : (config.rds.multiAz ?? false),
      allocatedStorage:      config.rds.allocatedStorage ?? 20,
      backupRetention:       isPrd ? cdk.Duration.days(35) : cdk.Duration.days(7),
      deletionProtection:    config.environment !== 'dev',
      publiclyAccessible:    false,   // CI-3: NUNCA público
      parameterGroup: new rds.ParameterGroup(this, 'PG', {
        engine,
        parameters: { 'rds.force_ssl': '1' },
      }),
    });
  }
}

// lib/stacks/auth-stack.ts — Cognito User Pool
import * as cognito from 'aws-cdk-lib/aws-cognito';

export class AuthStack extends cdk.Stack {
  public readonly userPool: cognito.UserPool;

  constructor(scope: Construct, id: string, props: any) {
    super(scope, id, props);
    const { config } = props;
    const prefix   = `${config.resourcePrefix}-${config.environment}`;
    const isMfaOn  = config.environment !== 'dev';

    this.userPool = new cognito.UserPool(this, 'UserPool', {
      userPoolName:         `${prefix}-up`,
      selfSignUpEnabled:    false,
      signInAliases:        { email: true },
      autoVerify:           { email: true },
      passwordPolicy: {
        minLength:        12,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits:    true,
        requireSymbols:   true,
      },
      mfa:             isMfaOn ? cognito.Mfa.REQUIRED : cognito.Mfa.OPTIONAL,
      mfaSecondFactor: { sms: false, otp: true },
      advancedSecurityMode: isMfaOn ? cognito.AdvancedSecurityMode.ENFORCED : cognito.AdvancedSecurityMode.AUDIT,
      accountRecovery:  cognito.AccountRecovery.EMAIL_ONLY,
      removalPolicy:    config.environment === 'dev' ? cdk.RemovalPolicy.DESTROY : cdk.RemovalPolicy.RETAIN,
    });

    const client = this.userPool.addClient('AppClient', {
      generateSecret:    true,
      authFlows:         { userSrp: true },
      oAuth: {
        flows:            { authorizationCodeGrant: true },   // sem implicit flow
        scopes:           [cognito.OAuthScope.OPENID, cognito.OAuthScope.EMAIL, cognito.OAuthScope.PROFILE],
        callbackUrls:     config.cognitoCallbackUrls ?? [],
        logoutUrls:       config.cognitoLogoutUrls   ?? [],
      },
      preventUserExistenceErrors: true,
    });

    // Armazenar client secret no Secrets Manager via custom resource
    new cdk.CfnOutput(this, 'UserPoolId',       { value: this.userPool.userPoolId });
    new cdk.CfnOutput(this, 'UserPoolEndpoint', { value: this.userPool.userPoolProviderUrl });
  }
}

// lib/stacks/frontend-stack.ts — CloudFront + WAF WebACL
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins    from 'aws-cdk-lib/aws-cloudfront-origins';
import * as wafv2      from 'aws-cdk-lib/aws-wafv2';

export class FrontendStack extends cdk.Stack {
  public readonly distribution: cloudfront.Distribution;

  constructor(scope: Construct, id: string, props: any) {
    super(scope, id, props);
    const { config, alb } = props;
    const prefix   = `${config.resourcePrefix}-${config.environment}`;
    const isBlocking = config.environment !== 'dev';

    // WAF WebACL — DEVE estar em us-east-1 para CloudFront
    const wafAcl = new wafv2.CfnWebACL(this, 'WAF', {
      name:         `${prefix}-waf`,
      scope:        'CLOUDFRONT',
      defaultAction: isBlocking ? { block: {} } : { allow: {} },
      rules: [
        { name: 'AWSCommon';      priority: 1; overrideAction: isBlocking ? { none: {} } : { count: {} }; statement: { managedRuleGroupStatement: { name: 'AWSManagedRulesCommonRuleSet';      vendorName: 'AWS' } }; visibilityConfig: { cloudWatchMetricsEnabled: true; metricName: 'AWSCommon';      sampledRequestsEnabled: true } },
        { name: 'AWSBadInputs';   priority: 2; overrideAction: isBlocking ? { none: {} } : { count: {} }; statement: { managedRuleGroupStatement: { name: 'AWSManagedRulesKnownBadInputsRuleSet'; vendorName: 'AWS' } }; visibilityConfig: { cloudWatchMetricsEnabled: true; metricName: 'AWSBadInputs';   sampledRequestsEnabled: true } },
        { name: 'AWSSQLi';        priority: 3; overrideAction: isBlocking ? { none: {} } : { count: {} }; statement: { managedRuleGroupStatement: { name: 'AWSManagedRulesSQLiRuleSet';          vendorName: 'AWS' } }; visibilityConfig: { cloudWatchMetricsEnabled: true; metricName: 'AWSSQLi';        sampledRequestsEnabled: true } },
      ],
      visibilityConfig: { cloudWatchMetricsEnabled: true; metricName: `${prefix}-waf`; sampledRequestsEnabled: true },
    });

    this.distribution = new cloudfront.Distribution(this, 'CFD', {
      comment:           `${prefix}-cfd`,
      priceClass:        config.environment === 'dev' ? cloudfront.PriceClass.PRICE_CLASS_100 : cloudfront.PriceClass.PRICE_CLASS_ALL,
      webAclId:          wafAcl.attrArn,
      minimumProtocolVersion: cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
      defaultBehavior: {
        origin:               new origins.LoadBalancerV2Origin(alb, { protocolPolicy: cloudfront.OriginProtocolPolicy.HTTPS_ONLY }),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        allowedMethods:       cloudfront.AllowedMethods.ALLOW_ALL,
        cachePolicy:          cloudfront.CachePolicy.CACHING_DISABLED,
        originRequestPolicy:  cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
      },
    });
  }
}
```

### Step 6 — Reportar Conclusão

```
✅ IaC AWS gerado com sucesso — {project_name}

Output path        : projects/{project_name}/outputs/tobe/iac/aws/
Architecture mode  : {architecture_mode}  (ECS Fargate | EKS)
AWS Region         : {aws_region}
Resource prefix    : {resource_prefix}
Environments       : dev | hml | prd

Terraform modules gerados:
  ✅ networking       → terraform/modules/networking/       (VPC, SGs, IGW, NAT, ALB)
  ✅ secrets-manager  → terraform/modules/secrets-manager/  (KMS CMK, SM secrets)
  ✅ {ecs|eks}        → terraform/modules/{ecs|eks}/        (cluster, IAM roles)
  ✅ ecr              → terraform/modules/ecr/              [condicional: eks ou containerized]
  ✅ rds              → terraform/modules/rds/              (RDS, param group, backup)
  ✅ elasticache      → terraform/modules/elasticache/      (Redis, TLS, auth via SM)
  ✅ cloudwatch       → terraform/modules/cloudwatch/       (Log Groups, Alarms, X-Ray)
  ✅ cognito          → terraform/modules/cognito/          (User Pool, App Client, MFA)
  ✅ cloudfront       → terraform/modules/cloudfront/       (Distribution, WAF WebACL v2)

AWS CDK stacks gerados:
  ✅ networking-stack.ts | secrets-manager-stack.ts
  ✅ compute-stack.ts    | database-stack.ts | cache-stack.ts
  ✅ observability-stack.ts | auth-stack.ts | frontend-stack.ts
  ✅ lib/config/dev.json | hml.json | prd.json
  ✅ package.json | cdk.json

⚠️  Próximos passos antes de aplicar:
  1. Criar recursos de state Terraform por environment:
     aws s3 mb s3://{resource_prefix}-tfstate-{env} --region us-east-1
     aws dynamodb create-table --table-name {resource_prefix}-tfstate-lock-{env} ...
  2. Exportar credenciais AWS (NUNCA em tfvars):
     AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN (se STS assumeRole)
     — Preferir IAM Role attached à instância/pipeline CI
  3. Emitir certificado ACM e atualizar acm_certificate_arn em terraform.tfvars
  4. Executar por environment:
     cd terraform/environments/dev && terraform init && terraform plan && terraform apply
  5. Para CDK: npm ci && DEPLOY_ENV=dev npx cdk deploy --all --require-approval never
  6. Confirmar modo WAF: COUNT (dev) e BLOCK (hml/prd) — validar com equipe de segurança antes do apply prd.
  7. Após criação do Cognito User Pool, atualizar callback_urls nas configurações do frontend.
```

Handoff ao orquestrador:
```yaml
implementation.status: COMPLETED
agent: ava-devops-iac-aws
project_name: "{project_name}"
architecture_mode: "{ecs|eks}"
outputs_generated:
  - "projects/{project_name}/outputs/tobe/iac/aws/terraform/versions.tf"
  - "projects/{project_name}/outputs/tobe/iac/aws/terraform/main.tf"
  - "projects/{project_name}/outputs/tobe/iac/aws/terraform/variables.tf"
  - "projects/{project_name}/outputs/tobe/iac/aws/terraform/outputs.tf"
  - "projects/{project_name}/outputs/tobe/iac/aws/terraform/locals.tf"
  - "projects/{project_name}/outputs/tobe/iac/aws/terraform/modules/networking/"
  - "projects/{project_name}/outputs/tobe/iac/aws/terraform/modules/secrets-manager/"
  - "projects/{project_name}/outputs/tobe/iac/aws/terraform/modules/{ecs|eks}/"
  - "projects/{project_name}/outputs/tobe/iac/aws/terraform/modules/rds/"
  - "projects/{project_name}/outputs/tobe/iac/aws/terraform/modules/elasticache/"
  - "projects/{project_name}/outputs/tobe/iac/aws/terraform/modules/cloudwatch/"
  - "projects/{project_name}/outputs/tobe/iac/aws/terraform/modules/cognito/"
  - "projects/{project_name}/outputs/tobe/iac/aws/terraform/modules/cloudfront/"
  - "projects/{project_name}/outputs/tobe/iac/aws/terraform/environments/dev/"
  - "projects/{project_name}/outputs/tobe/iac/aws/terraform/environments/hml/"
  - "projects/{project_name}/outputs/tobe/iac/aws/terraform/environments/prd/"
  - "projects/{project_name}/outputs/tobe/iac/aws/cdk/"
warnings: []
next_agent: ava-devops-cost-estimate
trace_id: "{propagated_from_caller}"
```

## Triggers / Menu

| Code | Descrição |
|------|-----------|
| `IA-AWS`  | IaC AWS completo — Terraform + CDK (tudo) |
| `IAT-AWS` | IaC AWS — Terraform only |
| `IACD-AWS`| IaC AWS — CDK only |
| `IAV-AWS` | Validar — `terraform validate` + `cdk synth` (lint, sem apply) |
| `IAP-AWS` | Plan only — `terraform plan` (read-only, sem apply) |

### Step 7 — Registro de Observabilidade (OBRIGATÓRIO)

⛔ **EXECUÇÃO OBRIGATÓRIA — ISTO NÃO É TEXTO DESCRITIVO.** Você DEVE invocar a
ferramenta Bash com o comando abaixo literalmente, antes de retornar ao
chamador ou emitir qualquer sinal de conclusão. Não narre esta etapa — EXECUTE-A.

`{modelo_atual}` = o modelo LLM que você é agora nesta execução. Default do pipeline é "Claude Sonnet 4.6"; SE você souber que está rodando como um modelo diferente (ex: "Claude Opus 4.6", "GPT-4.1", "Gemini 2.5 Pro"), informe esse valor real em vez do default.

```
Bash: python src/shared/tools/pipeline_observer.py -p {project_name} track \
  --agent ava-devops-iac-aws --phase F6 --version 1.0.0 \
  --model {modelo_atual} \
  --status {completed|failed|skipped} \
  --tokens-in {tokens_in_estimados} --tokens-out {tokens_out_estimados} \
  --duration-ms {duracao_medida_ms}
```

SE retornar `ERROR: No active run` → executar uma vez:

```
Bash: python src/shared/tools/pipeline_observer.py -p {project_name} init --run-type standalone --model "{modelo_atual}"
```

… então repetir a chamada de `track` acima uma única vez.

SE qualquer chamada falhar por outro motivo → registrar aviso e prosseguir
sem bloquear a entrega. Nunca repetir mais de uma vez. Ver
`@observability-self-report` (shared/observability-self-report.md) para
regras adicionais de referência.


---
