# Required Secrets — CI Pipelines

> ⚠️ **Configure todos os secrets listados abaixo ANTES de executar o pipeline.**
> Pipelines sem estes secrets configurados falharão com erros de "secret não encontrado".

---

## GitHub Actions (`ci.yml`)

| Secret | Descrição | Formato esperado | Obrigatório | Instruções de configuração |
|---|---|---|---|---|
| `SONAR_TOKEN` | Token de autenticação SonarCloud para análise SAST e quality gate | String alfanumérica (40+ chars) gerada no SonarCloud | ✅ Sim | 1. Acesse [sonarcloud.io](https://sonarcloud.io) → My Account → Security<br>2. Gere um token com escopo de análise<br>3. No GitHub: Settings → Secrets and variables → Actions → New repository secret<br>4. Nome: `SONAR_TOKEN`, Valor: token gerado |
| `GITHUB_TOKEN` | Token automático do GitHub para push de imagens GHCR | Gerado automaticamente pelo GitHub Actions | ⚙️ Automático | Não requer configuração manual — provido automaticamente pelo GitHub Actions. Verificar apenas que o repositório tem `packages: write` habilitado em Settings → Actions → General → Workflow permissions |

---

## Azure DevOps (`azure-pipelines.yml`)

| Secret / Configuração | Descrição | Formato esperado | Obrigatório | Instruções de configuração |
|---|---|---|---|---|
| `SonarCloudServiceConnection` | Service Connection para SonarCloud | Nome da Service Connection no Azure DevOps | ✅ Sim | 1. Azure DevOps → Project Settings → Service connections<br>2. New service connection → SonarCloud<br>3. Inserir o token do SonarCloud<br>4. Nomear como `SonarCloudServiceConnection` (ou ajustar no pipeline) |
| `SonarOrganization` | Organização no SonarCloud | String (slug da org, ex: `minha-org`) | ✅ Sim | 1. Azure DevOps → Pipelines → Library → Variable Groups<br>2. Criar grupo ou adicionar variável `SonarOrganization`<br>3. Valor: slug da organização no SonarCloud |
| `SonarProjectKey` | Chave do projeto no SonarCloud | String (ex: `org_projeto-name`) | ✅ Sim | 1. SonarCloud → Administration → Projects → criar projeto<br>2. Copiar o Project Key<br>3. Azure DevOps → Pipelines → variável `SonarProjectKey` |

---

## Verificação Rápida

### GitHub Actions
```bash
# Verificar se SONAR_TOKEN está configurado (GitHub CLI)
gh secret list --repo <owner>/<repo> | grep SONAR_TOKEN
```

### Azure DevOps
```bash
# Verificar Service Connections (Azure CLI)
az devops service-endpoint list --organization https://dev.azure.com/<org> --project <project> --query "[?name=='SonarCloudServiceConnection']"
```

---

## Checklist Pré-Execução

- [ ] `SONAR_TOKEN` configurado no GitHub Secrets
- [ ] Workflow permissions inclui `packages: write` (para GHCR)
- [ ] `SonarCloudServiceConnection` criada no Azure DevOps
- [ ] `SonarOrganization` definida como variável de pipeline
- [ ] `SonarProjectKey` definida como variável de pipeline
- [ ] Projeto criado no SonarCloud com o Project Key correspondente
