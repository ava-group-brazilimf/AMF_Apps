#!/usr/bin/env node
// ==========================================================================
// FastQA — MCP Azure DevOps Wrapper
// ==========================================================================
//
// Carrega credenciais do arquivo fastqa/.env e spawna o MCP server
// @tiberriver256/mcp-server-azure-devops com as variáveis injetadas.
//
// Isso garante que o MCP e os scripts TypeScript usem a MESMA fonte de
// credenciais (fastqa/.env), eliminando divergências com ${env:...} do SO.
//
// Uso (em .vscode/mcp.json):
//   "command": "node",
//   "args": ["fastqa/scripts/mcp-azdo-wrapper.js"]
//
// ==========================================================================

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

// ---------------------------------------------------------------------------
// Parser de .env (sem dependência de dotenv)
// ---------------------------------------------------------------------------

function loadEnvFile(envPath) {
  if (!fs.existsSync(envPath)) {
    return {};
  }
  const lines = fs.readFileSync(envPath, 'utf-8').split('\n');
  const vars = {};
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) { continue; }
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx === -1) { continue; }
    const key = trimmed.slice(0, eqIdx).trim();
    let value = trimmed.slice(eqIdx + 1).trim();
    // Remove aspas envolventes (simples ou duplas)
    if ((value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    vars[key] = value;
  }
  return vars;
}

// ---------------------------------------------------------------------------
// Resolução do .env
// ---------------------------------------------------------------------------

// Tenta localizar fastqa/.env relativo ao workspace (cwd)
const workspaceRoot = process.cwd();
const envCandidates = [
  path.join(workspaceRoot, 'fastqa', '.env'),
  // Fallback: se o cwd já estiver dentro de fastqa/
  path.join(workspaceRoot, '.env'),
];

let envPath = '';
for (const candidate of envCandidates) {
  if (fs.existsSync(candidate)) {
    envPath = candidate;
    break;
  }
}

if (!envPath) {
  // Escreve em stderr para não corromper o protocolo JSON-RPC (stdout)
  process.stderr.write(
    '[FastQA MCP Wrapper] AVISO: fastqa/.env não encontrado. ' +
    'O MCP server será iniciado sem credenciais do .env.\n'
  );
}

const envVars = envPath ? loadEnvFile(envPath) : {};

// ---------------------------------------------------------------------------
// Monta environment para o MCP server
// ---------------------------------------------------------------------------

const mcpEnv = Object.assign({}, process.env, {
  AZURE_DEVOPS_ORG_URL: envVars.AZURE_DEVOPS_ORG_URL || process.env.AZURE_DEVOPS_ORG_URL || '',
  AZURE_DEVOPS_AUTH_METHOD: 'pat',
  AZURE_DEVOPS_PAT: envVars.AZURE_DEVOPS_PAT || process.env.AZURE_DEVOPS_PAT || '',
  AZURE_DEVOPS_DEFAULT_PROJECT: envVars.AZURE_DEVOPS_DEFAULT_PROJECT || process.env.AZURE_DEVOPS_DEFAULT_PROJECT || '',
  AZURE_DEVOPS_API_VERSION: envVars.AZURE_DEVOPS_API_VERSION || process.env.AZURE_DEVOPS_API_VERSION || '7.1',
  NODE_ENV: 'production',
});

// ---------------------------------------------------------------------------
// Spawn do MCP server
// ---------------------------------------------------------------------------

const child = spawn('npx', ['-y', '@tiberriver256/mcp-server-azure-devops'], {
  env: mcpEnv,
  stdio: 'inherit',  // JSON-RPC passa direto: stdin/stdout/stderr
  shell: true,        // Necessário no Windows para resolver npx
});

// Propaga sinais para graceful shutdown
function forwardSignal(signal) {
  if (child && !child.killed) {
    child.kill(signal);
  }
}

process.on('SIGTERM', () => forwardSignal('SIGTERM'));
process.on('SIGINT', () => forwardSignal('SIGINT'));

child.on('exit', (code, signal) => {
  process.exit(code !== null ? code : 1);
});

child.on('error', (err) => {
  process.stderr.write(`[FastQA MCP Wrapper] Erro ao iniciar MCP server: ${err.message}\n`);
  process.exit(1);
});
