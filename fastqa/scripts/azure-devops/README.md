# FastQA — Scripts Azure DevOps (TypeScript Nativo)

Scripts de integração com Azure DevOps REST API v7.1 via Node.js `fetch()` nativo.

> **📌 NOTA IMPORTANTE:** Os comandos `@fastqa:azdo_get_work_item_by_id_or_title`, `@fastqa:azdo_list_work_items_by_sprint` e `@fastqa:azdo_create_work_item` **NÃO** utilizam estes scripts. Eles utilizam **exclusivamente** o **MCP Azure DevOps** (`azureDevOps` em `.vscode/mcp.json`). Os scripts abaixo são utilizados pelos **demais** comandos `@fastqa:azdo_*`.

## Pré-requisitos

- Node.js v22+
- `npm install dotenv tsx`
- Variáveis configuradas no `.env` (veja `.env.example` na raiz do fastqa/)

## ⚙️ Configuração de Credenciais

> **⚠️ IMPORTANTE:** As credenciais do arquivo `.env` devem ser **idênticas** às configuradas no `.vscode/mcp.json` (servidor `azureDevOps`).

**Passos para configurar:**

1. **Copiar as credenciais do MCP:**
   - Abra o arquivo `.vscode/mcp.json`
   - Localize a seção `azureDevOps` → `env`
   - Copie os valores de:
     - `AZURE_DEVOPS_ORG_URL`
     - `AZURE_DEVOPS_PAT`
     - `AZURE_DEVOPS_DEFAULT_PROJECT`

2. **Criar o arquivo `.env`:**
   - Na raiz do `fastqa/`, copie `.env.example` para `.env`
   - Cole os mesmos valores do MCP:
     ```env
     AZURE_DEVOPS_ORG_URL=https://dev.azure.com/leandroifarias-hubqa
     AZURE_DEVOPS_PAT=9iMKuDcDtJKdIn059WVylEc2vEauAQxJCNTXWvAjftsV7tGwIINdJQQJ99CBACAAAAAQ2eabAAASAZDOyVNo
     AZURE_DEVOPS_DEFAULT_PROJECT=hub-qa-playwright-agents
     AZURE_DEVOPS_API_VERSION=7.1
     ```

3. **Verificar sincronização:**
   - As credenciais devem ser **exatamente iguais** em ambos os arquivos
   - Qualquer divergência causará erros de autenticação

**Por que manter sincronizado?**
- O **MCP Azure DevOps** é usado para comandos de leitura (get, list, create via MCP)
- Os **scripts TypeScript** são usados para comandos de upload, anexos e execução de testes
- Ambos precisam das mesmas credenciais para acessar a mesma organização/projeto

## Estrutura

```
azure-devops/
├── azure-devops.config.ts          # Configuração centralizada
├── azure-devops.client.ts          # Client principal (fetch nativo)
├── types/
│   └── azure-devops.types.ts       # Interfaces TypeScript
├── utils/
│   ├── base64.util.ts              # Encoding de arquivos
│   ├── logger.util.ts              # Logger estruturado
│   └── report-generator.util.ts    # Gerador de relatórios
├── commands/                        # Scripts executáveis
│   ├── get-work-item.command.ts
│   ├── create-work-item.command.ts
│   ├── create-bug.command.ts
│   ├── create-test-case.command.ts
│   ├── update-work-item.command.ts
│   ├── link-work-items.command.ts
│   ├── upload-evidence.command.ts
│   ├── upload-folder-evidence.command.ts
│   ├── upload-folder-test-result.command.ts
│   ├── upload-test-execution.command.ts
│   ├── list-test-plans.command.ts
│   ├── add-testcase-to-suite.command.ts
│   └── generate-report.command.ts
└── logs/                            # Logs de execução (auto-gerados)
```

## Execução

```bash
# Formato padrão
npx tsx fastqa/scripts/azure-devops/commands/<command>.command.ts [--args]

# Exemplos
npx tsx fastqa/scripts/azure-devops/commands/get-work-item.command.ts --id 123
npx tsx fastqa/scripts/azure-devops/commands/create-bug.command.ts --title "Erro no login" --severity "2 - High"
npx tsx fastqa/scripts/azure-devops/commands/upload-test-execution.command.ts \
  --test-plan-id 110 --test-suite-id 112 --test-case-id 45 \
  --evidence-path "manual_test/evidence/TS-001/video.webm" --result Passed
```

## Variáveis de Ambiente

```env
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/sua-org
AZURE_DEVOPS_PAT=seu-personal-access-token
AZURE_DEVOPS_DEFAULT_PROJECT=seu-projeto
AZURE_DEVOPS_API_VERSION=7.1
```

## Permissões do PAT

| Escopo | Permissão |
|--------|-----------|
| Work Items | Read & Write |
| Test Management | Read & Write |
| Project and Team | Read |

## Documentação Completa

Consulte: `.github/instructions/fastQAAzureDevOps.instructions.md`
