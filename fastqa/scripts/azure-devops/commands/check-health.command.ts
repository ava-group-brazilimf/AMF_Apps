#!/usr/bin/env npx tsx
// ==========================================================================
// FastQA — Comando: Diagnóstico da Integração Azure DevOps
// ==========================================================================
//
// Verifica se a integração com o Azure DevOps está corretamente configurada,
// realizando checks sequenciais de ambiente, configuração e conectividade REST.
//
// Uso:
//   npx tsx fastqa/scripts/azure-devops/commands/check-health.command.ts
//
// Exit code:
//   0 — todos os checks passaram
//   1 — um ou mais checks falharam
//
// ==========================================================================

import * as fs from 'fs';
import * as path from 'path';

// ---------------------------------------------------------------------------
// Tipos
// ---------------------------------------------------------------------------

interface CheckResult {
  label: string;
  ok: boolean;
  detail?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Lê o arquivo .env manualmente, sem chamar process.exit em falha. */
function loadEnvFile(envPath: string): Record<string, string> {
  if (!fs.existsSync(envPath)) {
    return {};
  }
  const lines = fs.readFileSync(envPath, 'utf-8').split('\n');
  const vars: Record<string, string> = {};
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) { continue; }
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx === -1) { continue; }
    const key = trimmed.slice(0, eqIdx).trim();
    const value = trimmed.slice(eqIdx + 1).trim().replace(/^["']|["']$/g, '');
    vars[key] = value;
  }
  return vars;
}

function isPlaceholder(value: string): boolean {
  const lower = value.toLowerCase();
  return (
    lower.includes('seu-') ||
    lower.includes('sua-') ||
    lower.includes('your-') ||
    lower === '' ||
    lower.includes('example') ||
    lower.includes('<') ||
    lower.includes('>')
  );
}

function buildBasicAuth(pat: string): string {
  return Buffer.from(`:${pat}`).toString('base64');
}

function padEnd(str: string, len: number): string {
  return str.length >= len ? str : str + ' '.repeat(len - str.length);
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const results: CheckResult[] = [];

  // Localiza .env relativo ao próprio script: commands/ → azure-devops/ → scripts/ → fastqa/
  // Funciona independentemente do cwd de onde o script é executado.
  const envPath = path.resolve(__dirname, '..', '..', '..', '.env');
  const envExists = fs.existsSync(envPath);

  // -------------------------------------------------------------------
  // Check 1: .env existe
  // -------------------------------------------------------------------
  results.push({
    label: 'Arquivo fastqa/.env existe',
    ok: envExists,
    detail: envExists ? envPath : `Não encontrado em: ${envPath}`,
  });

  const envVars = loadEnvFile(envPath);

  // .env tem precedência sobre process.env (alinhado com mcp-azdo-wrapper.js)
  const get = (key: string): string =>
    envVars[key] || process.env[key] || '';

  const orgUrl = get('AZURE_DEVOPS_ORG_URL');
  const pat = get('AZURE_DEVOPS_PAT');
  const project = get('AZURE_DEVOPS_DEFAULT_PROJECT');

  // -------------------------------------------------------------------
  // Check 2: AZURE_DEVOPS_ORG_URL
  // -------------------------------------------------------------------
  const orgUrlOk = !!orgUrl && !isPlaceholder(orgUrl);
  results.push({
    label: 'AZURE_DEVOPS_ORG_URL definida',
    ok: orgUrlOk,
    detail: orgUrlOk
      ? orgUrl
      : orgUrl
        ? `Valor de placeholder detectado: "${orgUrl}"`
        : 'Variável não encontrada no .env',
  });

  // -------------------------------------------------------------------
  // Check 3: AZURE_DEVOPS_PAT
  // -------------------------------------------------------------------
  const patOk = !!pat && !isPlaceholder(pat);
  const patSource = envVars['AZURE_DEVOPS_PAT'] ? '.env' : process.env['AZURE_DEVOPS_PAT'] ? 'process.env' : '';
  results.push({
    label: 'AZURE_DEVOPS_PAT definida',
    ok: patOk,
    detail: patOk ? `(ocultado — fonte: ${patSource})` : pat ? 'Valor de placeholder detectado' : 'Variável não encontrada no .env',
  });

  // -------------------------------------------------------------------
  // Check 4: AZURE_DEVOPS_DEFAULT_PROJECT
  // -------------------------------------------------------------------
  const projectOk = !!project && !isPlaceholder(project);
  results.push({
    label: 'AZURE_DEVOPS_DEFAULT_PROJECT definida',
    ok: projectOk,
    detail: projectOk ? project : project ? `Valor de placeholder detectado: "${project}"` : 'Variável não encontrada no .env',
  });

  // -------------------------------------------------------------------
  // Check 5: Conectividade REST
  // -------------------------------------------------------------------
  let projectList: string[] = [];
  let restOk = false;
  let restDetail = '';

  if (orgUrlOk && patOk) {
    let controller: AbortController | undefined;
    let timeoutHandle: ReturnType<typeof setTimeout> | undefined;

    try {
      controller = new AbortController();
      timeoutHandle = setTimeout(() => controller!.abort(), 10_000);

      const url = `${orgUrl.replace(/\/$/, '')}/_apis/projects?api-version=7.1`;
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Authorization': `Basic ${buildBasicAuth(pat)}`,
          'Content-Type': 'application/json',
        },
        signal: controller.signal,
      });

      if (response.ok) {
        const body = await response.json() as { value?: Array<{ name: string }> };
        projectList = (body.value || []).map((p) => p.name);
        restOk = true;
        restDetail = `${projectList.length} projeto(s) acessível(is)`;
      } else {
        restDetail = `HTTP ${response.status} — ${response.statusText}`;
        if (response.status === 401) {
          restDetail += ' (PAT inválido ou expirado)';
          // Diagnóstico: detectar conflito entre .env e process.env
          const envPat = envVars['AZURE_DEVOPS_PAT'] || '';
          const sysPat = process.env['AZURE_DEVOPS_PAT'] || '';
          if (envPat && sysPat && envPat !== sysPat) {
            restDetail += '\n    ⚠️  CONFLITO: AZURE_DEVOPS_PAT do .env difere do process.env (variável do SO). Usando valor do .env.';
          }
        } else if (response.status === 403) {
          restDetail += ' (PAT sem permissão)';
        }
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      if (message.includes('abort') || message.includes('timeout') || message.includes('ETIMEDOUT')) {
        restDetail = 'Timeout — verifique conectividade de rede';
      } else {
        restDetail = `Erro: ${message}`;
      }
    } finally {
      if (timeoutHandle !== undefined) { clearTimeout(timeoutHandle); }
    }
  } else {
    restDetail = 'Ignorado (credenciais ausentes)';
  }

  results.push({
    label: 'Conectividade REST com Azure DevOps',
    ok: restOk,
    detail: restDetail,
  });

  // -------------------------------------------------------------------
  // Check 6: Projeto existe
  // -------------------------------------------------------------------
  let projectFoundOk = false;
  let projectFoundDetail = '';

  if (restOk && projectOk) {
    projectFoundOk = projectList.some(
      (p) => p.toLowerCase() === project.toLowerCase()
    );
    projectFoundDetail = projectFoundOk
      ? `Projeto "${project}" encontrado`
      : `Projeto "${project}" NÃO encontrado. Disponíveis: ${projectList.join(', ') || '(nenhum)'}`;
  } else {
    projectFoundDetail = 'Ignorado (falha em check anterior)';
  }

  results.push({
    label: `Projeto "${project || '(não definido)'}" existe na organização`,
    ok: projectFoundOk,
    detail: projectFoundDetail,
  });

  // -------------------------------------------------------------------
  // Check 7: MCP wrapper existe
  // -------------------------------------------------------------------
  const wrapperPath = path.resolve(__dirname, '..', '..', 'mcp-azdo-wrapper.js');
  const wrapperExists = fs.existsSync(wrapperPath);
  results.push({
    label: 'MCP wrapper (mcp-azdo-wrapper.js) existe',
    ok: wrapperExists,
    detail: wrapperExists
      ? wrapperPath
      : `Não encontrado em: ${wrapperPath}. Execute @fastqa_ /update para regenerar.`,
  });

  // -------------------------------------------------------------------
  // Check 8: .vscode/mcp.json usa wrapper (não ${env:...} legado)
  // -------------------------------------------------------------------
  const mcpJsonPath = path.resolve(__dirname, '..', '..', '..', '..', '.vscode', 'mcp.json');
  let mcpConfigOk = false;
  let mcpConfigDetail = '';

  if (fs.existsSync(mcpJsonPath)) {
    try {
      const mcpContent = fs.readFileSync(mcpJsonPath, 'utf-8');
      const mcpJson = JSON.parse(mcpContent);
      const azdoServer = mcpJson?.servers?.azureDevOps;

      if (!azdoServer) {
        mcpConfigDetail = 'Servidor "azureDevOps" não encontrado em mcp.json';
      } else if (mcpContent.includes('${env:AZURE_DEVOPS_PAT}')) {
        mcpConfigDetail = 'Usa ${env:...} legado — credenciais vêm do SO, não do .env. Execute @fastqa_ /update para migrar para o wrapper.';
      } else if (azdoServer.args?.some((a: string) => a.includes('mcp-azdo-wrapper'))) {
        mcpConfigOk = true;
        mcpConfigDetail = 'Configurado para usar wrapper (credenciais do .env)';
      } else {
        mcpConfigDetail = 'Configuração não reconhecida — verifique .vscode/mcp.json';
      }
    } catch {
      mcpConfigDetail = 'Erro ao ler/parsear .vscode/mcp.json';
    }
  } else {
    mcpConfigDetail = `Arquivo não encontrado: ${mcpJsonPath}`;
  }

  results.push({
    label: '.vscode/mcp.json usa wrapper (não ${env:} legado)',
    ok: mcpConfigOk,
    detail: mcpConfigDetail,
  });

  // ---------------------------------------------------------------------------
  // Exibição da tabela
  // ---------------------------------------------------------------------------
  const allOk = results.every((r) => r.ok);

  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('  FastQA — Diagnóstico: Integração Azure DevOps');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

  const labelWidth = Math.max(...results.map((r) => r.label.length)) + 2;

  for (const r of results) {
    const icon = r.ok ? '✅' : '❌';
    const label = padEnd(r.label, labelWidth);
    const detail = r.detail ? `  →  ${r.detail}` : '';
    console.log(`  ${icon}  ${label}${detail}`);
  }

  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

  if (allOk) {
    console.log('  ✅ INTEGRAÇÃO OK — Azure DevOps configurado corretamente.\n');
  } else {
    const failed = results.filter((r) => !r.ok).length;
    console.log(`  ❌ ${failed} check(s) falharam. Revise os itens acima.\n`);
  }

  process.exit(allOk ? 0 : 1);
}

main().catch((err) => {
  console.error('❌ Erro inesperado:', err instanceof Error ? err.message : err);
  process.exit(1);
});
