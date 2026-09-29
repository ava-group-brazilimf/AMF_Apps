# Scripts Azure DevOps - FastQA

Scripts PowerShell para integração com Azure DevOps Test Plans.

## Scripts Disponíveis

| Script | Descrição |
|--------|-----------|
| `Complete-TestExecution.ps1` | Fluxo completo: cria Test Run + upload + atualiza status |
| `Complete-TestExecution-Batch.ps1` | Upload em lote de múltiplas evidências |
| `Add-TestCase-To-Suite.ps1` | Adicionar Test Case a uma Test Suite |
| `List-Suite-Content.ps1` | Diagnóstico de Test Points na Suite |
| `Upload-Evidence.ps1` | Upload simples de evidência |
| `Upload-Evidence-Batch.ps1` | Upload em lote |
| `Simple-Upload-Evidence.ps1` | Upload direto ao Work Item |
| `Create-TestRun.ps1` | Criar Test Run |
| `Complete-TestRun.ps1` | Finalizar Test Run |
| `Verify-Upload.ps1` | Verificar evidências anexadas |
| `Test-Attachment-Methods.ps1` | Diagnóstico de métodos de attachment |

## Configuração

Antes de usar, configure as variáveis de ambiente:

```powershell
$env:AZURE_DEVOPS_ORG_URL = "https://dev.azure.com/sua-org"
$env:AZURE_DEVOPS_PAT = "seu-pat-token"
$env:AZURE_DEVOPS_DEFAULT_PROJECT = "seu-projeto"
```

## Exemplo de Uso

```powershell
.\Complete-TestExecution.ps1 `
  -TestPlanId 110 `
  -TestSuiteId 112 `
  -TestCaseId 47 `
  -EvidencePath "C:\evidencias\teste.mp4" `
  -TestResult "Passed" `
  -Comment "Teste executado com sucesso"
```
