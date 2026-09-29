/**
 * ============================================================================
 * FastQA — Azure DevOps Configuration
 * ============================================================================
 * Configuração centralizada para integração com Azure DevOps REST API v7.1.
 * Todas as credenciais são carregadas do arquivo .env na raiz do fastqa/.
 *
 * Uso:
 *   import { config } from '../azure-devops.config';
 *   console.log(config.orgUrl); // https://dev.azure.com/sua-org
 * ============================================================================
 */

import * as dotenv from 'dotenv';
import * as path from 'path';
import * as fs from 'fs';

// Carrega variáveis de ambiente do .env na raiz do fastqa/
// override:true garante que o .env tem precedência sobre vars do SO
const envPath = path.resolve(__dirname, '../../.env');
if (fs.existsSync(envPath)) {
  dotenv.config({ path: envPath, override: true });
} else {
  console.warn(`⚠️  Arquivo .env não encontrado em: ${envPath}`);
  console.warn('   Copie .env.example para .env e preencha com seus valores.');
  dotenv.config({ override: true });
}

// ---------------------------------------------------------------------------
// Validação de variáveis obrigatórias
// ---------------------------------------------------------------------------

interface AzureDevOpsConfig {
  /** URL da organização: https://dev.azure.com/{org} */
  orgUrl: string;
  /** Personal Access Token (PAT) */
  pat: string;
  /** Nome do projeto padrão */
  project: string;
  /** Versão da API (default: 7.1) */
  apiVersion: string;
  /** Header de autorização Basic (Base64 de :PAT) */
  authHeader: string;
  /** URL base da API: {orgUrl}/{project}/_apis */
  apiBaseUrl: string;
  /** Timeout padrão para requests em ms (default: 30000) */
  requestTimeout: number;
  /** Número máximo de retries (default: 3) */
  maxRetries: number;
  /** Delay base para retry em ms (default: 1000) */
  retryBaseDelay: number;
  /** Tamanho máximo de arquivo para upload em bytes (default: 130MB) */
  maxFileSize: number;
  /** Diretório de logs */
  logsDir: string;
  /** Extensões de arquivo permitidas para upload de evidências */
  allowedExtensions: string[];
}

function validateEnvVar(name: string, friendlyName: string): string {
  const value = process.env[name];
  if (!value || value.trim() === '' || value.includes('seu-')) {
    console.error(`❌ Variável de ambiente '${name}' (${friendlyName}) não configurada.`);
    console.error(`   Configure no arquivo: ${envPath}`);
    process.exit(1);
  }
  return value.trim();
}

function getEnvVar(name: string, defaultValue: string): string {
  const value = process.env[name];
  return value && value.trim() !== '' ? value.trim() : defaultValue;
}

// ---------------------------------------------------------------------------
// Construção da configuração
// ---------------------------------------------------------------------------

const orgUrl = validateEnvVar('AZURE_DEVOPS_ORG_URL', 'URL da Organização');
const pat = validateEnvVar('AZURE_DEVOPS_PAT', 'Personal Access Token');
const project = validateEnvVar('AZURE_DEVOPS_DEFAULT_PROJECT', 'Projeto Padrão');
const apiVersion = getEnvVar('AZURE_DEVOPS_API_VERSION', '7.1');

// Basic Auth: Base64 encode de ":{PAT}"
const authHeader = `Basic ${Buffer.from(`:${pat}`).toString('base64')}`;

// URL base da API
const apiBaseUrl = `${orgUrl}/${encodeURIComponent(project)}/_apis`;

export const config: AzureDevOpsConfig = {
  orgUrl,
  pat,
  project,
  apiVersion,
  authHeader,
  apiBaseUrl,
  requestTimeout: parseInt(getEnvVar('AZURE_DEVOPS_TIMEOUT', '30000'), 10),
  maxRetries: parseInt(getEnvVar('AZURE_DEVOPS_MAX_RETRIES', '3'), 10),
  retryBaseDelay: parseInt(getEnvVar('AZURE_DEVOPS_RETRY_DELAY', '1000'), 10),
  maxFileSize: 130 * 1024 * 1024, // 130 MB — limite do Azure DevOps
  logsDir: path.resolve(__dirname, 'logs'),
  allowedExtensions: [
    '.mp4', '.webm', '.avi', '.mkv',       // Vídeo
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', // Imagem
    '.pdf', '.html', '.htm',                 // Documento
    '.txt', '.md', '.json', '.xml', '.csv',  // Texto
    '.xlsx', '.xls', '.docx', '.doc',        // Office
    '.zip', '.7z',                           // Compactado
    '.log',                                  // Log
  ],
};

// ---------------------------------------------------------------------------
// Helpers de URL
// ---------------------------------------------------------------------------

/** Constrói URL completa da API com query params */
export function buildApiUrl(
  path: string,
  queryParams?: Record<string, string | number | boolean>
): string {
  const baseUrl = `${config.apiBaseUrl}/${path}`;
  const params = new URLSearchParams();
  params.set('api-version', config.apiVersion);

  if (queryParams) {
    for (const [key, value] of Object.entries(queryParams)) {
      params.set(key, String(value));
    }
  }

  return `${baseUrl}?${params.toString()}`;
}

/** Constrói URL para área de Test Plan (usa endpoint diferente) */
export function buildTestPlanApiUrl(
  path: string,
  queryParams?: Record<string, string | number | boolean>
): string {
  const baseUrl = `${config.orgUrl}/${encodeURIComponent(config.project)}/_apis/testplan/${path}`;
  const params = new URLSearchParams();
  params.set('api-version', config.apiVersion);

  if (queryParams) {
    for (const [key, value] of Object.entries(queryParams)) {
      params.set(key, String(value));
    }
  }

  return `${baseUrl}?${params.toString()}`;
}

/** Constrói URL para área de Test Runs */
export function buildTestRunApiUrl(
  path: string,
  queryParams?: Record<string, string | number | boolean>
): string {
  const baseUrl = `${config.orgUrl}/${encodeURIComponent(config.project)}/_apis/test/${path}`;
  const params = new URLSearchParams();
  params.set('api-version', config.apiVersion);

  if (queryParams) {
    for (const [key, value] of Object.entries(queryParams)) {
      params.set(key, String(value));
    }
  }

  return `${baseUrl}?${params.toString()}`;
}

// ---------------------------------------------------------------------------
// URL Builders — Git Repositories (Fase 6)
// ---------------------------------------------------------------------------

/** Constrói URL para API Git (repos, refs, pushes) */
export function buildGitApiUrl(
  path: string,
  queryParams?: Record<string, string | number | boolean>
): string {
  const baseUrl = `${config.orgUrl}/${encodeURIComponent(config.project)}/_apis/git/${path}`;
  const params = new URLSearchParams();
  params.set('api-version', config.apiVersion);

  if (queryParams) {
    for (const [key, value] of Object.entries(queryParams)) {
      params.set(key, String(value));
    }
  }

  return `${baseUrl}?${params.toString()}`;
}

/** Constrói URL para API Build (builds, definitions) */
export function buildBuildApiUrl(
  path: string,
  queryParams?: Record<string, string | number | boolean>
): string {
  const baseUrl = `${config.orgUrl}/${encodeURIComponent(config.project)}/_apis/build/${path}`;
  const params = new URLSearchParams();
  params.set('api-version', config.apiVersion);

  if (queryParams) {
    for (const [key, value] of Object.entries(queryParams)) {
      params.set(key, String(value));
    }
  }

  return `${baseUrl}?${params.toString()}`;
}

/** Constrói URL para API Core (projetos, etc.) — sem project no path */
export function buildCoreApiUrl(
  path: string,
  queryParams?: Record<string, string | number | boolean>
): string {
  const baseUrl = `${config.orgUrl}/_apis/${path}`;
  const params = new URLSearchParams();
  params.set('api-version', config.apiVersion);

  if (queryParams) {
    for (const [key, value] of Object.entries(queryParams)) {
      params.set(key, String(value));
    }
  }

  return `${baseUrl}?${params.toString()}`;
}

/** Constrói URL para API Git de um projeto específico (cross-project) */
export function buildGitApiUrlForProject(
  projectName: string,
  path: string,
  queryParams?: Record<string, string | number | boolean>
): string {
  const baseUrl = `${config.orgUrl}/${encodeURIComponent(projectName)}/_apis/git/${path}`;
  const params = new URLSearchParams();
  params.set('api-version', config.apiVersion);

  if (queryParams) {
    for (const [key, value] of Object.entries(queryParams)) {
      params.set(key, String(value));
    }
  }

  return `${baseUrl}?${params.toString()}`;
}

/** Constrói URL para API de Pipelines */
export function buildPipelinesApiUrl(
  path: string,
  queryParams?: Record<string, string | number | boolean>
): string {
  const baseUrl = `${config.orgUrl}/${encodeURIComponent(config.project)}/_apis/pipelines/${path}`;
  const params = new URLSearchParams();
  params.set('api-version', config.apiVersion);

  if (queryParams) {
    for (const [key, value] of Object.entries(queryParams)) {
      params.set(key, String(value));
    }
  }

  return `${baseUrl}?${params.toString()}`;
}

/** Constrói URL para API Distributed Task (variable groups, etc.) */
export function buildDistributedTaskApiUrl(
  path: string,
  queryParams?: Record<string, string | number | boolean>
): string {
  const baseUrl = `${config.orgUrl}/${encodeURIComponent(config.project)}/_apis/distributedtask/${path}`;
  const params = new URLSearchParams();
  params.set('api-version', config.apiVersion);

  if (queryParams) {
    for (const [key, value] of Object.entries(queryParams)) {
      params.set(key, String(value));
    }
  }

  return `${baseUrl}?${params.toString()}`;
}

/** Constrói URL para API de Pipeline Permissions */
export function buildPipelinePermissionsApiUrl(
  path: string,
  queryParams?: Record<string, string | number | boolean>
): string {
  const baseUrl = `${config.orgUrl}/${encodeURIComponent(config.project)}/_apis/pipelines/pipelinepermissions/${path}`;
  const params = new URLSearchParams();
  params.set('api-version', config.apiVersion);

  if (queryParams) {
    for (const [key, value] of Object.entries(queryParams)) {
      params.set(key, String(value));
    }
  }

  return `${baseUrl}?${params.toString()}`;
}

// ---------------------------------------------------------------------------
// Constantes de Link Types
// ---------------------------------------------------------------------------

/** Mapeamento amigável → refName para vinculação de work items */
export const LINK_TYPES: Record<string, string> = {
  'parent': 'System.LinkTypes.Hierarchy-Reverse',
  'Parent': 'System.LinkTypes.Hierarchy-Reverse',
  'child': 'System.LinkTypes.Hierarchy-Forward',
  'Child': 'System.LinkTypes.Hierarchy-Forward',
  'related': 'System.LinkTypes.Related',
  'Related': 'System.LinkTypes.Related',
  'duplicate': 'System.LinkTypes.Duplicate-Forward',
  'Duplicate': 'System.LinkTypes.Duplicate-Forward',
  'Duplicate Of': 'System.LinkTypes.Duplicate-Reverse',
  'tests': 'Microsoft.VSTS.Common.TestedBy-Reverse',
  'Tests': 'Microsoft.VSTS.Common.TestedBy-Reverse',
  'tested by': 'Microsoft.VSTS.Common.TestedBy-Forward',
  'Tested By': 'Microsoft.VSTS.Common.TestedBy-Forward',
  'affects': 'Microsoft.VSTS.Common.Affects-Forward',
  'Affects': 'Microsoft.VSTS.Common.Affects-Forward',
  'Affected By': 'Microsoft.VSTS.Common.Affects-Reverse',
};

/** Campos comuns por tipo de work item */
export const WORK_ITEM_FIELDS = {
  common: [
    'System.Title',
    'System.Description',
    'System.State',
    'System.AssignedTo',
    'System.AreaPath',
    'System.IterationPath',
    'System.Tags',
    'System.CreatedBy',
    'System.CreatedDate',
    'System.ChangedDate',
  ],
  bug: [
    'Microsoft.VSTS.TCM.ReproSteps',
    'Microsoft.VSTS.Common.Severity',
    'Microsoft.VSTS.Common.Priority',
    'Microsoft.VSTS.TCM.SystemInfo',
  ],
  testCase: [
    'Microsoft.VSTS.TCM.Steps',
    'Microsoft.VSTS.TCM.Parameters',
    'Microsoft.VSTS.Common.Priority',
  ],
  pbi: [
    'Microsoft.VSTS.Common.AcceptanceCriteria',
    'Microsoft.VSTS.Scheduling.StoryPoints',
    'Microsoft.VSTS.Common.Priority',
  ],
  task: [
    'Microsoft.VSTS.Scheduling.RemainingWork',
    'Microsoft.VSTS.Common.Activity',
    'Microsoft.VSTS.Common.Priority',
  ],
} as const;

// ---------------------------------------------------------------------------
// Export default
// ---------------------------------------------------------------------------

export default config;
