#!/usr/bin/env node
/**
 * FastQA Setup Wizard - Main Command
 * Wizard configuração do projeto FastQA via argumentos de linha de comando
 * 
 * Uso: npx tsx fastqa/scripts/setup/setup-wizard.command.ts --purpose "..." --integration "1" [--integration-custom "Nome"] --test-case-format "1" --platform "1" --framework "1" --inputs "todas" --avanade-code "1"
 */

import { execSync } from 'child_process';
import * as path from 'path';
import { WizardResult, PlatformType, IntegrationType, AvanadeCodeConfig, AzureDevOpsSetupConfig } from './setup.types';
import { FRAMEWORKS, DATA_FORMATS, INPUTS, BASE_FOLDERS, CONDITIONAL_FOLDERS, TEST_LEVELS, BROWSERS, MOBILE_PLATFORMS } from './setup.config';
import { validateWizardResult, validateProjectConfig } from './setup.validator';
import { createFolders, saveConfig, buildProjectConfig, createReadmeFiles, configureMcpJson, createEnvFile } from './setup.filemanager';
import { Logger } from './setup.logger';

const logger = new Logger();

// Parse arguments from command line
function parseArguments(): Record<string, string> {
  const args = process.argv.slice(2);
  const parsed: Record<string, string> = {};
  
  for (let i = 0; i < args.length; i += 2) {
    if (args[i].startsWith('--')) {
      const key = args[i].substring(2);
      const value = args[i + 1] || '';
      parsed[key] = value;
    }
  }
  
  return parsed;
}

function getInputSelection(inputsArg: string): string[] {
  if (inputsArg === 'todas' || inputsArg === 'all') {
    return ['1', '2', '3', '4', '5', '6', '7']; // All data formats
  }
  return inputsArg.split(',').map(s => s.trim());
}

async function runWizardFromArgs(): Promise<WizardResult> {
  logger.header('🚀 FastQA Setup Wizard');
  logger.info('Configurando projeto FastQA com parâmetros fornecidos...\n');
  logger.separator();

  const args = parseArguments();
  
  // Validar argumentos obrigatórios
  if (!args.purpose || !args.integration || !args['test-case-format'] || !args.platform || !args.framework || !args.inputs || !args['avanade-code']) {
    logger.error('❌ Argumentos obrigatórios em falta:');
    logger.error('   --purpose "Descrição da aplicação"');
    logger.error('   --integration "1" (1=Azure DevOps + Test Plans | 2=Azure DevOps sem Test Plans | 3=Jira + Xray | 4=Jira + Zephyr Scale | 5=Jira + AssertThat | 6=Jira sem gerenciamento | 7=Nenhuma | 8=Outro)');
    logger.error('   --test-case-format "1" (1=Gherkin | 2=Step by Step | 3=Outro | 4=Nenhum)');
    logger.error('   --platform "1" (1=Web | 2=Mobile | 3=API | 4=Desktop)');
    logger.error('   --framework "1" (1-7 conforme plataforma)');
    logger.error('   --inputs "todas" ou "1,2,3"');
    logger.error('   --avanade-code "1" (1=Isolada | 2=Integrada | 3=Não instalar)');
    process.exit(1);
  }

  // ═══════════════════════════════════════════════════════════════════
  // Processar Pergunta 1: Propósito da Aplicação
  // ═══════════════════════════════════════════════════════════════════
  logger.step(1, 'Propósito/Objetivo da Aplicação');
  const purpose = args.purpose;
  logger.success(`✅ "${purpose}"`);

  if (!purpose || purpose.trim().length < 5) {
    logger.error('O propósito deve ter no mínimo 5 caracteres.');
    process.exit(1);
  }

  // ═══════════════════════════════════════════════════════════════════
  // Processar Pergunta 2: Integração, Gestão e Testes
  // ═══════════════════════════════════════════════════════════════════
  logger.step(2, 'Integração, Gestão e Testes');
  const integrationChoice = args.integration;
  const integrationOptions: IntegrationType[] = [
    'Azure DevOps + Test Plans',
    'Azure DevOps (sem Test Plans)',
    'Jira + Xray',
    'Jira + Zephyr Scale',
    'Jira + AssertThat',
    'Jira (sem gerenciamento de testes)',
    'Nenhuma',
    'Outro'
  ];
  const selectedIntegration = integrationOptions[parseInt(integrationChoice) - 1];

  if (!selectedIntegration) {
    logger.error('Opção inválida. Escolha entre 1 e 8.');
    process.exit(1);
  }
  logger.success(`✅ ${selectedIntegration}`);

  // Se Outro, aceita valor customizado via --integration-custom
  let customIntegrationLabel = selectedIntegration as string;
  if (selectedIntegration === 'Outro') {
    const customValue = args['integration-custom'];
    if (!customValue || !customValue.trim()) {
      logger.error('Opção "Outro" selecionada. Informe --integration-custom "Nome da ferramenta".');
      process.exit(1);
    }
    customIntegrationLabel = customValue.trim();
    logger.success(`✅ Personalizada: ${customIntegrationLabel}`);
  }

  // Deriva integration e testManagementTool
  const integrationMap: Partial<Record<IntegrationType, { integration: string; testManagementTool: string }>> = {
    'Azure DevOps + Test Plans':          { integration: 'Azure DevOps', testManagementTool: 'Azure DevOps Test Plans' },
    'Azure DevOps (sem Test Plans)':      { integration: 'Azure DevOps', testManagementTool: 'Nenhuma' },
    'Jira + Xray':                        { integration: 'Jira', testManagementTool: 'Jira + Xray' },
    'Jira + Zephyr Scale':                { integration: 'Jira', testManagementTool: 'Jira + Zephyr Scale' },
    'Jira + AssertThat':                  { integration: 'Jira', testManagementTool: 'Jira + AssertThat' },
    'Jira (sem gerenciamento de testes)': { integration: 'Jira', testManagementTool: 'Nenhuma' },
    'Nenhuma':                            { integration: 'Nenhuma', testManagementTool: 'Nenhuma' },
  };
  const mapped = integrationMap[selectedIntegration];
  const integration = mapped?.integration ?? customIntegrationLabel;
  const testManagementTool = mapped?.testManagementTool ?? 'Nenhuma';
  const toolManagement = integration;

  // ═══════════════════════════════════════════════════════════════════
  // Sub-Pergunta 2.1: Configurar MCP Azure DevOps (se Azure DevOps)
  // ═══════════════════════════════════════════════════════════════════
  let azureDevOpsConfig: AzureDevOpsSetupConfig | undefined;

  if (toolManagement === 'Azure DevOps') {
    const azdoConfigure = args['azdo-configure'];

    if (azdoConfigure === '1' || azdoConfigure === 'sim') {
      logger.section('  📌 Pergunta 2.1: Configuração do MCP Azure DevOps');

      const azdoOrgUrl = args['azdo-org-url'];
      const azdoPat = args['azdo-pat'];
      const azdoProject = args['azdo-project'];

      if (!azdoOrgUrl || !azdoPat || !azdoProject) {
        logger.error('Para configurar Azure DevOps MCP, informe:');
        logger.error('   --azdo-org-url "https://dev.azure.com/sua-org"');
        logger.error('   --azdo-pat "seu-token-pat"');
        logger.error('   --azdo-project "seu-projeto"');
        process.exit(1);
      }

      azureDevOpsConfig = {
        configure_mcp: true,
        org_url: azdoOrgUrl,
        pat: azdoPat,
        default_project: azdoProject
      };

      logger.success(`✅ Azure DevOps MCP será configurado`);
      logger.info(`   Org URL: ${azdoOrgUrl}`);
      logger.info(`   Projeto: ${azdoProject}`);
      logger.info(`   PAT: ${'*'.repeat(10)}...`);
    } else {
      logger.info('ℹ️  Configuração do MCP Azure DevOps ignorada. Pode ser configurado depois.');
      azureDevOpsConfig = {
        configure_mcp: false,
        org_url: '',
        pat: '',
        default_project: ''
      };
    }
  }

  // ═══════════════════════════════════════════════════════════════════
  // Processar Pergunta 3: Plataforma
  // ═══════════════════════════════════════════════════════════════════
  logger.step(3, 'Plataforma de Teste');
  const platformChoice = args.platform;
  const platformOptions: PlatformType[] = ['Web', 'Mobile', 'API', 'Desktop'];
  const platform = platformOptions[parseInt(platformChoice) - 1];

  if (!platform) {
    logger.error('Opção inválida. Escolha entre 1, 2, 3 ou 4.');
    process.exit(1);
  }
  logger.success(`✅ ${platform}`);

  // ═══════════════════════════════════════════════════════════════════
  // Processar Pergunta 4: Formato de Casos de Teste
  // ═══════════════════════════════════════════════════════════════════
  logger.step(4, 'Formato de Casos de Teste');
  const testCaseFormatChoice = args['test-case-format'];
  const testCaseFormatOptions = ['gherkin', 'step_by_step', 'outro', 'none'];
  const testCaseFormatLabels = ['Gherkin (BDD)', 'Step by Step', 'Outro', 'Nenhum'];
  const testCaseFormatIndex = parseInt(testCaseFormatChoice) - 1;
  let testCaseFormat = testCaseFormatOptions[testCaseFormatIndex] || 'gherkin';
  const testCaseFormatLabel = testCaseFormatLabels[testCaseFormatIndex] || testCaseFormatChoice;
  if (testCaseFormat === 'outro' && args['test-case-format-custom']) {
    testCaseFormat = args['test-case-format-custom'].toLowerCase().replace(/\s+/g, '_');
  }
  const useBDD = testCaseFormat === 'gherkin';
  logger.success(`✅ ${testCaseFormatLabel}`);

  // ═══════════════════════════════════════════════════════════════════
  // Processar Pergunta 5: Framework + Linguagem
  // ═══════════════════════════════════════════════════════════════════
  logger.step(5, 'Framework de Automação + Linguagem');
  
  const filteredFrameworks = FRAMEWORKS.filter(f => f.supportedPlatforms.includes(platform));
  
  if (filteredFrameworks.length === 0) {
    logger.error(`Nenhum framework disponível para a plataforma ${platform}`);
    process.exit(1);
  }

  const frameworkChoice = args.framework;
  const selectedFramework = filteredFrameworks[parseInt(frameworkChoice) - 1];

  if (!selectedFramework) {
    logger.error('Opção inválida.');
    process.exit(1);
  }
  logger.success(`✅ ${selectedFramework.name} (${selectedFramework.language})`);

  // ═══════════════════════════════════════════════════════════════════
  // Processar Pergunta 6: Formatos de Massa de Dados
  // ═══════════════════════════════════════════════════════════════════
  logger.step(6, 'Formatos de Massa de Dados');
  logger.info('📂 Os dados serão armazenados na pasta data/ de cada plataforma');
  
  const filteredInputs = INPUTS.filter(inp => inp.supportedPlatforms.includes(platform));
  const inputSelection = getInputSelection(args.inputs);
  
  const selectedInputs = inputSelection
    .map(choice => {
      const index = parseInt(choice) - 1;
      return filteredInputs[index];
    })
    .filter(Boolean);

  if (selectedInputs.length === 0) {
    logger.error('Pelo menos um formato de massa de dados deve ser selecionado.');
    process.exit(1);
  }
  
  const inputNames = selectedInputs.map(inp => inp.name).join(', ');
  logger.success(`✅ ${inputNames}`);

  // ═══════════════════════════════════════════════════════════════════
  // Processar Pergunta 7: Avanade CODE
  // ═══════════════════════════════════════════════════════════════════
  logger.step(7, 'Configuração do Avanade CODE');
  
  const avanadeChoice = args['avanade-code'];
  const avanadeOptions = ['Isolada', 'Integrada com o Time', 'Não instalar no momento'];
  const avanadeMode = avanadeOptions[parseInt(avanadeChoice) - 1];
  
  if (!avanadeMode) {
    logger.error('Opção inválida. Escolha entre 1, 2 ou 3.');
    process.exit(1);
  }
  
  const avanadeConfig: AvanadeCodeConfig = {
    enabled: avanadeChoice !== '3',
    mode: avanadeChoice === '1' ? 'isolated' : avanadeChoice === '2' ? 'team' : null,
    configured_at: avanadeChoice !== '3' ? new Date().toISOString() : null
  };
  
  logger.success(`✅ ${avanadeMode}`);
  logger.separator();

  // ═══════════════════════════════════════════════════════════════════
  // Montar Resultado
  // ═══════════════════════════════════════════════════════════════════
  const result: WizardResult = {
    purpose,
    integration: selectedIntegration,
    testManagementTool,
    toolManagement,
    platform,
    testCaseFormat,
    useBDD,
    framework: {
      name: selectedFramework.name,
      language: selectedFramework.language
    },
    inputs: selectedInputs,
    azureDevOps: azureDevOpsConfig,
    avanadeCode: {
      enabled: avanadeMode !== 'Não instalar no momento',
      mode: avanadeMode,
      configuredAt: avanadeMode !== 'Não instalar no momento' ? new Date().toISOString() : null
    }
  };

  // ═══════════════════════════════════════════════════════════════════
  // Exibir Resumo
  // ═══════════════════════════════════════════════════════════════════
  logger.header('📋 Resumo da Configuração');
  logger.summary('Propósito', purpose);
  logger.summary('Integração e Gestão', selectedIntegration === 'Outro' ? customIntegrationLabel : selectedIntegration);
  logger.summary('Ferramenta de Gestão de Testes', testManagementTool);
  logger.summary('Formato de Casos de Teste', testCaseFormatLabel);
  logger.summary('Plataforma', platform);
  logger.summary('Framework', `${selectedFramework.name} (${selectedFramework.language})`);
  logger.summary('Inputs', inputNames);
  if (azureDevOpsConfig?.configure_mcp) {
    logger.summary('Azure DevOps MCP', `${azureDevOpsConfig.org_url} / ${azureDevOpsConfig.default_project}`);
  }
  logger.summary('Avanade CODE', avanadeMode);
  logger.separator();

  return result;
}

async function setupAvanadeCode(mode: AvanadeCodeConfig): Promise<void> {
  if (mode === 'Isolada') {
    logger.section('⚙️  Configurando Avanade CODE (modo Isolada)...\n');
    
    try {
      execSync('npm run setup:bmad', { 
        cwd: 'fastqa/', 
        stdio: 'inherit' 
      });
      logger.success('✅ Avanade CODE configurado com sucesso!');
    } catch (error: any) {
      logger.error(`Erro ao configurar Avanade CODE: ${error.message}`);
      logger.warning('Você pode executar "npm run setup:bmad" manualmente depois.');
    }
  } else if (mode === 'Integrada com o Time') {
    logger.section('\nℹ️  Configuração Avanade CODE será feita posteriormente.\n');
    logger.info('📋 Próximos passos:');
    logger.info('   - Verificar com o time a configuração de acesso ao BMAD Method');
    logger.info('   - Aguardar orientações sobre credenciais e repositórios compartilhados');
    logger.info('   - Executar `npm run setup:bmad` quando orientado pelo time');
  }
}

async function main() {
  try {
    // Step 0: Instalar dependências antes de iniciar o wizard
    logger.section('📦 Instalando dependências do FastQA Scripts...');
    try {
      const scriptsDir = path.resolve(__dirname, '..');
      execSync('npm install', { cwd: scriptsDir, stdio: 'inherit' });
      logger.success('✅ Dependências instaladas com sucesso!');
    } catch (installError: any) {
      logger.error(`❌ Erro ao instalar dependências: ${installError.message}`);
      logger.info('💡 Tente executar manualmente: cd fastqa/scripts && npm install');
      process.exit(1);
    }

    // Executar wizard
    const result = await runWizardFromArgs();

    // Validar resultado
    logger.info('\n🔍 Validando configuração...');
    if (!validateWizardResult(result)) {
      logger.error('Configuração inválida. Verifique os erros acima.');
      process.exit(1);
    }

    // Construir configuração JSON
    logger.info('🔧 Construindo arquivo de configuração...');
    const config = buildProjectConfig(result);

    // Validar configuração JSON
    if (!validateProjectConfig(config)) {
      logger.error('Configuração JSON inválida. Verifique os erros acima.');
      process.exit(1);
    }

    // Criar estrutura de pastas
    logger.section('\n📁 Criando estrutura de pastas...');
    await createFolders(result.platform, BASE_FOLDERS, CONDITIONAL_FOLDERS);

    // Criar READMEs
    logger.info('📄 Criando arquivos README...');
    await createReadmeFiles();

    // Salvar configuração
    logger.info('💾 Salvando configuração...');
    await saveConfig(config);

    // Configurar MCP servers (.vscode/mcp.json) — Azure DevOps e/ou Appium (Mobile)
    if (result.azureDevOps?.configure_mcp || result.platform === 'Mobile') {
      logger.section('\n\uD83D\uDD27 Configurando servidores MCP...');
      await configureMcpJson(result.azureDevOps, result.platform);

      if (result.azureDevOps?.configure_mcp) {
        logger.info('\uD83D\uDD27 Criando arquivo .env para scripts Azure DevOps...');
        await createEnvFile(result.azureDevOps);
      }
    }

    // Configurar Avanade CODE (se aplicável)
    if (result.avanadeCode.enabled && result.avanadeCode.mode) {
      await setupAvanadeCode(result.avanadeCode.mode);
    }

    // Sucesso
    logger.header('✅ Setup Concluído com Sucesso!');
    logger.success('📄 Configuração salva em: fastqa/scripts/project_config.json');
    logger.success('📁 Estrutura de pastas criada em: fastqa/');
    logger.info('\n🚀 Próximos passos:');
    logger.info('   - Execute @fastqa:help para ver todos os comandos disponíveis');
    logger.info('   - Comece com @fastqa:load_pbi ou @fastqa:identify_gaps');
    logger.info('   - Consulte a documentação em .github/instructions/');

  } catch (error: any) {
    logger.error(`❌ Erro durante setup: ${error.message}`);
    if (error.stack) {
      logger.error(`\nStack trace:\n${error.stack}`);
    }
    process.exit(1);
  } finally {
    // Cleanup se necessário
  }
}

// Executar wizard
main();
