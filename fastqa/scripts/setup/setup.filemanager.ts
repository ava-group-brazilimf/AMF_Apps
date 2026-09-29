/**
 * FastQA Setup - File Manager
 * Gerenciador de criação de pastas e persistência de configuração
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import { ProjectConfigJson, WizardResult, PlatformType, AzureDevOpsSetupConfig } from './setup.types';
import { Logger } from './setup.logger';
import { validateFolderPath } from './setup.validator';

const logger = new Logger();

export async function createFolders(
  platform: PlatformType,
  baseFolders: string[],
  conditionalFolders: Record<string, string[]>
): Promise<void> {
  const projectRoot = path.resolve(process.cwd());
  const fastqaRoot = path.join(projectRoot, 'fastqa');

  function resolveFolderTarget(relativeFolder: string): string {
    if (relativeFolder.startsWith('automated_test/')) {
      return path.join(projectRoot, relativeFolder);
    }
    return path.join(fastqaRoot, relativeFolder);
  }
  
  // Criar todas as pastas base
  for (const folder of baseFolders) {
    const fullPath = resolveFolderTarget(folder);
    
    if (!validateFolderPath(fullPath)) {
      continue;
    }

    try {
      await fs.mkdir(fullPath, { recursive: true });
      
      // Criar .gitkeep se a pasta estiver vazia
      const gitkeepPath = path.join(fullPath, '.gitkeep');
      try {
        await fs.writeFile(gitkeepPath, '', 'utf-8');
      } catch (err) {
        // Ignorar erro se arquivo já existe
      }
    } catch (error: any) {
      logger.error(`Erro ao criar pasta ${folder}: ${error.message}`);
    }
  }

  // Criar pastas condicionais baseadas na plataforma
  const platformFolders = conditionalFolders[platform] || [];
  for (const folder of platformFolders) {
    const fullPath = resolveFolderTarget(folder);
    
    if (!validateFolderPath(fullPath)) {
      continue;
    }

    try {
      await fs.mkdir(fullPath, { recursive: true });
      
      // Criar .gitkeep
      const gitkeepPath = path.join(fullPath, '.gitkeep');
      try {
        await fs.writeFile(gitkeepPath, '', 'utf-8');
      } catch (err) {
        // Ignorar erro se arquivo já existe
      }
    } catch (error: any) {
      logger.error(`Erro ao criar pasta ${folder}: ${error.message}`);
    }
  }

  logger.success('✅ Estrutura de pastas criada com sucesso!');
}

export async function saveConfig(config: ProjectConfigJson): Promise<void> {
  const projectRoot = path.resolve(process.cwd());
  const configPath = path.join(projectRoot, 'fastqa', 'scripts', 'project_config.json');

  try {
    // Criar diretório se não existir
    await fs.mkdir(path.dirname(configPath), { recursive: true });

    // Salvar configuração formatada
    const jsonContent = JSON.stringify(config, null, 4);
    await fs.writeFile(configPath, jsonContent, 'utf-8');

    logger.success(`💾 Configuração salva em: fastqa/scripts/project_config.json`);
  } catch (error: any) {
    logger.error(`Erro ao salvar configuração: ${error.message}`);
    throw error;
  }
}

export function buildProjectConfig(result: WizardResult): ProjectConfigJson {
  const now = new Date().toISOString();

  const config: ProjectConfigJson = {
    metadata: {
      created_at: now,
      updated_at: now,
      version: '5.0',
      status: 'configured'
    },
    analysis: {
      purpose: result.purpose,
      application_description: '',
      domain: ''
    },
    project_management: {
      tool: result.toolManagement === 'Nenhuma' ? 'none' : result.toolManagement,
      azure_devops: {
        enabled: result.toolManagement === 'Azure DevOps',
        org_url: result.azureDevOps?.org_url || '',
        project: result.azureDevOps?.default_project || '',
        pat: result.azureDevOps?.configure_mcp ? '***configurado***' : '',
        test_plan_id: null,
        test_suite_id: null
      },
      jira: {
        enabled: result.toolManagement === 'Jira',
        url: '',
        project_key: '',
        api_token: ''
      }
    },
    platform: {
      type: result.platform,
      details: {
        browsers: result.platform === 'Web' ? ['Chrome', 'Firefox', 'Edge'] : [],
        devices: result.platform === 'Mobile' ? ['Android', 'iOS'] : [],
        api_base_url: '',
        swagger_url: '',
        apk_path: '',
        desktop_app_path: ''
      }
    },
    testing_approach: {
      use_gherkin_bdd: result.useBDD,
      test_levels: ['Funcional', 'E2E']
    },
    connectors: {
      output: {
        automation_framework: result.framework.name,
        language: result.framework.language
      },
      input: {
        type: result.inputs[0] || '',
        sources: result.inputs
      }
    },
    folder_structure: {
      root: 'fastqa',
      directories: []
    },
    avanade_code: {
      enabled: result.avanadeCode.enabled,
      mode: result.avanadeCode.mode,
      configured_at: result.avanadeCode.configuredAt
    }
  };

  return config;
}

export async function createReadmeFiles(): Promise<void> {
  const projectRoot = path.resolve(process.cwd());
  const fastqaRoot = path.join(projectRoot, 'fastqa');

  const readmes = [
    {
      path: path.join(fastqaRoot, 'manual_test', 'README.md'),
      content: `# Manual Test

Pasta para armazenar artefatos de testes manuais:

- **US/** - User Stories e requisitos
- **gap_analysis/** - Análise de gaps
- **estimate_effort/** - Estimativas de esforço
- **requirements_analysis/** - Análise de requisitos
- **behavior_analysis/** - Análise de comportamentos
- **test_cases/** - Cenários de teste (Gherkin .feature)
- **evidence/** - Evidências de execução (screenshots, vídeos)
`
    },
    {
      path: path.join(projectRoot, 'automated_test', 'README.md'),
      content: `# Automated Test

Pasta para armazenar código de automação de testes:

- **web/** - Testes Web (Playwright, Cypress, Selenium)
- **api/** - Testes API (Supertest, Requests, RestAssured, Karate)
- **mobile/** - Testes Mobile (WebdriverIO, Selenium + Appium)
- **shared/** - Recursos compartilhados (helpers, fixtures, types)
`
    }
  ];

  for (const readme of readmes) {
    try {
      await fs.mkdir(path.dirname(readme.path), { recursive: true });
      await fs.writeFile(readme.path, readme.content, 'utf-8');
    } catch (error: any) {
      // Ignorar erro se arquivo já existe
    }
  }
}

/**
 * Configura o servidor Azure DevOps MCP no arquivo .vscode/mcp.json
 * Lê o arquivo existente, adiciona/atualiza a entrada azureDevOps e salva
 */
export async function configureMcpJson(azureDevOps: AzureDevOpsSetupConfig | undefined, platform?: PlatformType): Promise<void> {
  const projectRoot = path.resolve(process.cwd());
  const mcpJsonPath = path.join(projectRoot, '.vscode', 'mcp.json');

  try {
    // Garantir que .vscode/ existe
    await fs.mkdir(path.join(projectRoot, '.vscode'), { recursive: true });

    // Ler arquivo existente ou criar estrutura base
    let mcpConfig: any = { servers: {}, inputs: [] };
    try {
      const existingContent = await fs.readFile(mcpJsonPath, 'utf-8');
      // Remover comentários JSONC simples (// e /* */) para parsear
      const cleanJson = existingContent
        .replace(/\/\/.*$/gm, '')
        .replace(/\/\*[\s\S]*?\*\//g, '');
      mcpConfig = JSON.parse(cleanJson);
    } catch {
      // Arquivo não existe, usar estrutura base
    }

    // Garantir que servers existe
    if (!mcpConfig.servers) {
      mcpConfig.servers = {};
    }

    // Adicionar/atualizar entrada azureDevOps (somente se configurado)
    if (azureDevOps?.configure_mcp) {
      mcpConfig.servers.azureDevOps = {
        command: 'npx',
        args: ['-y', '@tiberriver256/mcp-server-azure-devops'],
        env: {
          AZURE_DEVOPS_ORG_URL: azureDevOps.org_url,
          AZURE_DEVOPS_AUTH_METHOD: 'pat',
          AZURE_DEVOPS_PAT: azureDevOps.pat,
          AZURE_DEVOPS_DEFAULT_PROJECT: azureDevOps.default_project,
          AZURE_DEVOPS_API_VERSION: '7.1-preview.3',
          NODE_ENV: 'production'
        }
      };
      logger.success('✅ MCP Azure DevOps configurado em: .vscode/mcp.json');
    }

    // Adicionar/atualizar entrada Playwright MCP (plataformas Web ou API)
    if (platform === 'Web' || platform === 'API') {
      mcpConfig.servers['playwright'] = {
        command: 'npx',
        args: [
          '@playwright/mcp@latest',
          '--viewport-size=1366,768',
          '--caps=devtools'
        ]
      };
      mcpConfig.servers['playwright-api'] = {
        command: 'npx',
        args: ['@playwright/mcp@latest']
      };
      logger.success('✅ MCP Playwright configurado em: .vscode/mcp.json');
      logger.info('   ℹ️  --caps=devtools habilitado para suporte a gravação de vídeo.');
    }

    // Adicionar/atualizar entrada appium-mcp (somente se plataforma Mobile)
    if (platform === 'Mobile') {
      mcpConfig.servers['appium-mcp'] = {
        type: 'stdio',
        command: 'npx',
        args: ['appium-mcp@latest'],
        env: {
          ANDROID_HOME: '/path/to/android/sdk',
          CAPABILITIES_CONFIG: 'fastqa/agents/connectors/mobile/capabilities.json',
          SCREENSHOTS_DIR: 'fastqa/manual_test/evidence'
        }
      };
      logger.success('✅ MCP Appium configurado em: .vscode/mcp.json');
      logger.info('   ⚠️  Atualize ANDROID_HOME com o caminho real do Android SDK antes de usar.');
    }

    // Salvar arquivo formatado
    const jsonContent = JSON.stringify(mcpConfig, null, 2);
    await fs.writeFile(mcpJsonPath, jsonContent, 'utf-8');

  } catch (error: any) {
    logger.error(`Erro ao configurar MCP servers: ${error.message}`);
    throw error;
  }
}

/**
 * Cria o arquivo .env na pasta fastqa/ com as credenciais do Azure DevOps
 * Baseado no template .env.example
 */
export async function createEnvFile(azureDevOps: AzureDevOpsSetupConfig): Promise<void> {
  const projectRoot = path.resolve(process.cwd());
  const envPath = path.join(projectRoot, 'fastqa', '.env');

  try {
    const envContent = `# Variáveis de ambiente do projeto FastQA
# Gerado automaticamente pelo setup wizard em ${new Date().toISOString()}
# ⚠️ IMPORTANTE: Use as MESMAS credenciais configuradas em .vscode/mcp.json (servidor azureDevOps)

# URL base da aplicação
BASE_URL=http://localhost:3000

# URL base da API (se diferente)
API_BASE_URL=http://localhost:3000/api

# Azure DevOps (integração via TypeScript Client)
# ⚠️ Sincronizado com .vscode/mcp.json (servidor azureDevOps)
AZURE_DEVOPS_ORG_URL=${azureDevOps.org_url}
AZURE_DEVOPS_PAT=${azureDevOps.pat}
AZURE_DEVOPS_DEFAULT_PROJECT=${azureDevOps.default_project}
AZURE_DEVOPS_API_VERSION=7.1
# AZURE_DEVOPS_TIMEOUT=30000
# AZURE_DEVOPS_MAX_RETRIES=3
# AZURE_DEVOPS_RETRY_DELAY=1000
`;

    await fs.writeFile(envPath, envContent, 'utf-8');
    logger.success('✅ Arquivo .env criado em: fastqa/.env');
  } catch (error: any) {
    logger.error(`Erro ao criar arquivo .env: ${error.message}`);
    throw error;
  }
}
