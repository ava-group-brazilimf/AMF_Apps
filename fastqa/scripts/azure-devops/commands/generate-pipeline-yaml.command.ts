/**
 * ============================================================================
 * FastQA — Generate Pipeline YAML for Azure DevOps
 * ============================================================================
 * Gera arquivo YAML de pipeline para Azure DevOps baseado no framework e
 * linguagem configurados em project_config.json. Opcionalmente faz push
 * do YAML para o repositório.
 *
 * Uso:
 *   npx tsx fastqa/scripts/azure-devops/commands/generate-pipeline-yaml.command.ts \
 *     --framework playwright \
 *     --language typescript \
 *     --platform web \
 *     [--pipeline-name "FastQA - Web Tests"] \
 *     [--trigger-branch main] \
 *     [--test-results-path "automated_test/web/results"] \
 *     [--output-path "azure-pipelines.yml"] \
 *     [--push --repo "meu-repo" --branch "main"]
 *
 * ============================================================================
 */

import * as fs from 'fs';
import * as path from 'path';
import { AzureDevOpsClient, withClient } from '../azure-devops.client';
import { config } from '../azure-devops.config';
import { Logger } from '../utils/logger.util';
import type { GitChange, GitPushPayload } from '../types/azure-devops.types';

// ---------------------------------------------------------------------------
// Constantes e Tipos
// ---------------------------------------------------------------------------

const FASTQA_ROOT = path.resolve(__dirname, '..', '..', '..');

type Framework = 'playwright' | 'cypress' | 'selenium' | 'robot' | 'webdriverio' | 'supertest' | 'requests' | 'restassured' | 'karate';
type Language = 'typescript' | 'javascript' | 'python' | 'java' | 'csharp';
type Platform = 'web' | 'api' | 'mobile';

interface PipelineYamlArgs {
  framework: Framework;
  language: Language;
  platform: Platform;
  pipelineName: string;
  triggerBranch: string;
  testResultsPath: string;
  outputPath: string;
  push: boolean;
  repo?: string;
  branch?: string;
  envVars?: Record<string, string>;
}

// ---------------------------------------------------------------------------
// Parsing de Argumentos
// ---------------------------------------------------------------------------

function parseArgs(): PipelineYamlArgs {
  const args = process.argv.slice(2);
  const parsed: Partial<PipelineYamlArgs> = {
    triggerBranch: 'main',
    push: false,
    envVars: {},
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    switch (arg) {
      case '--framework':
        parsed.framework = args[++i] as Framework;
        break;
      case '--language':
        parsed.language = args[++i] as Language;
        break;
      case '--platform':
        parsed.platform = args[++i] as Platform;
        break;
      case '--pipeline-name':
        parsed.pipelineName = args[++i];
        break;
      case '--trigger-branch':
        parsed.triggerBranch = args[++i];
        break;
      case '--test-results-path':
        parsed.testResultsPath = args[++i];
        break;
      case '--output-path':
        parsed.outputPath = args[++i];
        break;
      case '--push':
        parsed.push = true;
        break;
      case '--repo':
      case '--repository':
        parsed.repo = args[++i];
        break;
      case '--branch':
        parsed.branch = args[++i];
        break;
      case '--env':
        // Formato: --env KEY=VALUE
        const envPair = args[++i];
        if (envPair && envPair.includes('=')) {
          const [key, ...valueParts] = envPair.split('=');
          parsed.envVars![key] = valueParts.join('=');
        }
        break;
    }
  }

  // Auto-detect from project_config.json if not provided
  if (!parsed.framework || !parsed.language || !parsed.platform) {
    try {
      const configPath = path.join(FASTQA_ROOT, 'scripts', 'project_config.json');
      const projectConfig = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
      if (!parsed.framework && projectConfig.connectors?.output?.automation_framework) {
        parsed.framework = projectConfig.connectors.output.automation_framework.toLowerCase() as Framework;
      }
      if (!parsed.language && projectConfig.connectors?.output?.language) {
        parsed.language = projectConfig.connectors.output.language.toLowerCase() as Language;
      }
      if (!parsed.platform && projectConfig.platform?.type) {
        parsed.platform = projectConfig.platform.type.toLowerCase() as Platform;
      }
    } catch {
      // Ignorar erro de leitura do config
    }
  }

  if (!parsed.framework) throw new Error('--framework é obrigatório');
  if (!parsed.language) throw new Error('--language é obrigatório');
  if (!parsed.platform) throw new Error('--platform é obrigatório (web | api | mobile)');

  // Defaults
  if (!parsed.pipelineName) {
    parsed.pipelineName = `FastQA - ${capitalize(parsed.platform)} Tests (${capitalize(parsed.framework)})`;
  }
  if (!parsed.testResultsPath) {
    parsed.testResultsPath = `automated_test/${parsed.platform}/results`;
  }
  if (!parsed.outputPath) {
    parsed.outputPath = 'azure-pipelines.yml';
  }

  if (parsed.push && !parsed.repo) {
    throw new Error('--repo é obrigatório quando --push é usado');
  }
  if (parsed.push && !parsed.branch) {
    parsed.branch = parsed.triggerBranch;
  }

  return parsed as PipelineYamlArgs;
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

// ---------------------------------------------------------------------------
// Templates de Pipeline YAML
// ---------------------------------------------------------------------------

function generateYaml(args: PipelineYamlArgs): string {
  const key = `${args.framework}:${args.language}`;

  switch (key) {
    // ------ Playwright ------
    case 'playwright:typescript':
    case 'playwright:javascript':
      return generatePlaywrightNodeYaml(args);
    case 'playwright:python':
      return generatePlaywrightPythonYaml(args);
    case 'playwright:java':
      return generatePlaywrightJavaYaml(args);
    case 'playwright:csharp':
      return generatePlaywrightCSharpYaml(args);

    // ------ Cypress ------
    case 'cypress:typescript':
    case 'cypress:javascript':
      return generateCypressYaml(args);

    // ------ Selenium ------
    case 'selenium:python':
      return generateSeleniumPythonYaml(args);
    case 'selenium:java':
      return generateSeleniumJavaYaml(args);
    case 'selenium:csharp':
      return generateSeleniumCSharpYaml(args);

    // ------ Robot Framework ------
    case 'robot:python':
      return generateRobotYaml(args);

    // ------ WebdriverIO ------
    case 'webdriverio:typescript':
    case 'webdriverio:javascript':
      return generateWebdriverIOYaml(args);

    // ------ API: Supertest ------
    case 'supertest:typescript':
    case 'supertest:javascript':
      return generateSupertestYaml(args);

    // ------ API: Requests ------
    case 'requests:python':
      return generateRequestsYaml(args);

    // ------ API: RestAssured ------
    case 'restassured:java':
      return generateRestAssuredYaml(args);

    // ------ API: Karate ------
    case 'karate:java':
      return generateKarateYaml(args);

    default:
      throw new Error(`Combinação framework/linguagem não suportada: ${args.framework}/${args.language}`);
  }
}

// ---------------------------------------------------------------------------
// Helpers de Geração YAML
// ---------------------------------------------------------------------------

function yamlHeader(args: PipelineYamlArgs): string {
  return `# ===================================================================
# ${args.pipelineName}
# Gerado automaticamente por FastQA — Azure DevOps Pipeline Generator
# Framework: ${args.framework} | Linguagem: ${args.language} | Plataforma: ${args.platform}
# ===================================================================

trigger:
  branches:
    include:
      - ${args.triggerBranch}
  paths:
    include:
      - 'automated_test/${args.platform}/**'

pool:
  vmImage: 'ubuntu-latest'
`;
}

function publishTestResults(args: PipelineYamlArgs, format: 'JUnit' | 'NUnit' | 'VSTest' | 'XUnit' = 'JUnit'): string {
  return `
    - task: PublishTestResults@2
      displayName: 'Publicar Resultados de Testes'
      condition: always()
      inputs:
        testResultsFormat: '${format}'
        testResultsFiles: '${args.testResultsPath}/**/*.xml'
        mergeTestResults: true
        testRunTitle: '${args.pipelineName}'
        failTaskOnFailedTests: true`;
}

function publishPipelineArtifact(args: PipelineYamlArgs, artifactPath: string, artifactName: string): string {
  return `
    - task: PublishPipelineArtifact@1
      displayName: 'Publicar Artefatos (${artifactName})'
      condition: always()
      inputs:
        targetPath: '${artifactPath}'
        artifact: '${artifactName}'
        publishLocation: 'pipeline'`;
}

function envVarsBlock(args: PipelineYamlArgs): string {
  if (!args.envVars || Object.keys(args.envVars).length === 0) return '';
  const lines = Object.entries(args.envVars).map(([k, v]) => `        ${k}: '${v}'`);
  return `\n      env:\n${lines.join('\n')}`;
}

// ---------------------------------------------------------------------------
// Templates Específicos por Framework
// ---------------------------------------------------------------------------

function generatePlaywrightNodeYaml(args: PipelineYamlArgs): string {
  const lang = args.language === 'typescript' ? 'TypeScript' : 'JavaScript';
  return `${yamlHeader(args)}
variables:
  NODE_VERSION: '22.x'
  CI: 'true'

steps:
  - task: NodeTool@0
    displayName: 'Instalar Node.js $(NODE_VERSION)'
    inputs:
      versionSpec: '$(NODE_VERSION)'

  - script: |
      cd automated_test/${args.platform}
      npm ci
    displayName: 'Instalar Dependências'

  - script: |
      cd automated_test/${args.platform}
      npx playwright install --with-deps chromium
    displayName: 'Instalar Playwright Browsers'

  - script: |
      cd automated_test/${args.platform}
      npx playwright test --reporter=junit,html
    displayName: 'Executar Testes ${lang}'${envVarsBlock(args)}
${publishTestResults(args, 'JUnit')}
${publishPipelineArtifact(args, `automated_test/${args.platform}/playwright-report`, 'playwright-report')}
${publishPipelineArtifact(args, `automated_test/${args.platform}/test-results`, 'test-results')}
`;
}

function generatePlaywrightPythonYaml(args: PipelineYamlArgs): string {
  return `${yamlHeader(args)}
variables:
  PYTHON_VERSION: '3.12'
  CI: 'true'

steps:
  - task: UsePythonVersion@0
    displayName: 'Configurar Python $(PYTHON_VERSION)'
    inputs:
      versionSpec: '$(PYTHON_VERSION)'

  - script: |
      cd automated_test/${args.platform}
      pip install -r requirements.txt
      playwright install --with-deps chromium
    displayName: 'Instalar Dependências e Browsers'

  - script: |
      cd automated_test/${args.platform}
      pytest --junitxml=results/test-results.xml -v
    displayName: 'Executar Testes Playwright Python'${envVarsBlock(args)}
${publishTestResults(args, 'JUnit')}
`;
}

function generatePlaywrightJavaYaml(args: PipelineYamlArgs): string {
  return `${yamlHeader(args)}
variables:
  JAVA_VERSION: '17'
  CI: 'true'

steps:
  - task: JavaToolInstaller@0
    displayName: 'Instalar Java $(JAVA_VERSION)'
    inputs:
      versionSpec: '$(JAVA_VERSION)'
      jdkArchitectureOption: 'x64'
      jdkSourceOption: 'PreInstalled'

  - script: |
      cd automated_test/${args.platform}
      mvn install -DskipTests
      mvn exec:java -e -D exec.mainClass=com.microsoft.playwright.CLI -D exec.args="install --with-deps chromium"
    displayName: 'Instalar Dependências e Browsers'

  - script: |
      cd automated_test/${args.platform}
      mvn test
    displayName: 'Executar Testes Playwright Java'${envVarsBlock(args)}
${publishTestResults(args, 'JUnit')}
`;
}

function generatePlaywrightCSharpYaml(args: PipelineYamlArgs): string {
  return `${yamlHeader(args)}
variables:
  DOTNET_VERSION: '8.x'
  CI: 'true'

steps:
  - task: UseDotNet@2
    displayName: 'Instalar .NET $(DOTNET_VERSION)'
    inputs:
      version: '$(DOTNET_VERSION)'

  - script: |
      cd automated_test/${args.platform}
      dotnet restore
      dotnet build
      pwsh -Command "& { .\\bin\\Debug\\net8.0\\playwright.ps1 install --with-deps chromium }"
    displayName: 'Instalar Dependências e Browsers'

  - script: |
      cd automated_test/${args.platform}
      dotnet test --logger "trx;LogFileName=test-results.trx" --results-directory results
    displayName: 'Executar Testes Playwright C#'${envVarsBlock(args)}
${publishTestResults(args, 'VSTest')}
`;
}

function generateCypressYaml(args: PipelineYamlArgs): string {
  return `${yamlHeader(args)}
variables:
  NODE_VERSION: '22.x'
  CI: 'true'

steps:
  - task: NodeTool@0
    displayName: 'Instalar Node.js $(NODE_VERSION)'
    inputs:
      versionSpec: '$(NODE_VERSION)'

  - script: |
      cd automated_test/${args.platform}
      npm ci
    displayName: 'Instalar Dependências'

  - script: |
      cd automated_test/${args.platform}
      npx cypress run --reporter junit --reporter-options "mochaFile=results/test-results-[hash].xml"
    displayName: 'Executar Testes Cypress'${envVarsBlock(args)}
${publishTestResults(args, 'JUnit')}
${publishPipelineArtifact(args, `automated_test/${args.platform}/cypress/screenshots`, 'cypress-screenshots')}
${publishPipelineArtifact(args, `automated_test/${args.platform}/cypress/videos`, 'cypress-videos')}
`;
}

function generateSeleniumPythonYaml(args: PipelineYamlArgs): string {
  return `${yamlHeader(args)}
variables:
  PYTHON_VERSION: '3.12'
  CI: 'true'

steps:
  - task: UsePythonVersion@0
    displayName: 'Configurar Python $(PYTHON_VERSION)'
    inputs:
      versionSpec: '$(PYTHON_VERSION)'

  - script: |
      cd automated_test/${args.platform}
      pip install -r requirements.txt
    displayName: 'Instalar Dependências'

  - script: |
      cd automated_test/${args.platform}
      pytest --junitxml=results/test-results.xml -v --tb=short
    displayName: 'Executar Testes Selenium Python'${envVarsBlock(args)}
${publishTestResults(args, 'JUnit')}
`;
}

function generateSeleniumJavaYaml(args: PipelineYamlArgs): string {
  return `${yamlHeader(args)}
variables:
  JAVA_VERSION: '17'
  CI: 'true'

steps:
  - task: JavaToolInstaller@0
    displayName: 'Instalar Java $(JAVA_VERSION)'
    inputs:
      versionSpec: '$(JAVA_VERSION)'
      jdkArchitectureOption: 'x64'
      jdkSourceOption: 'PreInstalled'

  - script: |
      cd automated_test/${args.platform}
      mvn install -DskipTests
    displayName: 'Instalar Dependências'

  - script: |
      cd automated_test/${args.platform}
      mvn test -Dsurefire.reportFormat=xml
    displayName: 'Executar Testes Selenium Java'${envVarsBlock(args)}
${publishTestResults(args, 'JUnit')}
`;
}

function generateSeleniumCSharpYaml(args: PipelineYamlArgs): string {
  return `${yamlHeader(args)}
variables:
  DOTNET_VERSION: '8.x'
  CI: 'true'

steps:
  - task: UseDotNet@2
    displayName: 'Instalar .NET $(DOTNET_VERSION)'
    inputs:
      version: '$(DOTNET_VERSION)'

  - script: |
      cd automated_test/${args.platform}
      dotnet restore
      dotnet build
    displayName: 'Instalar Dependências'

  - script: |
      cd automated_test/${args.platform}
      dotnet test --logger "trx;LogFileName=test-results.trx" --results-directory results
    displayName: 'Executar Testes Selenium C#'${envVarsBlock(args)}
${publishTestResults(args, 'VSTest')}
`;
}

function generateRobotYaml(args: PipelineYamlArgs): string {
  return `${yamlHeader(args)}
variables:
  PYTHON_VERSION: '3.12'
  CI: 'true'

steps:
  - task: UsePythonVersion@0
    displayName: 'Configurar Python $(PYTHON_VERSION)'
    inputs:
      versionSpec: '$(PYTHON_VERSION)'

  - script: |
      cd automated_test/${args.platform}
      pip install -r requirements.txt
    displayName: 'Instalar Dependências'

  - script: |
      cd automated_test/${args.platform}
      robot --outputdir results --xunit results/xunit-results.xml tests/
    displayName: 'Executar Testes Robot Framework'${envVarsBlock(args)}
${publishTestResults(args, 'JUnit')}
${publishPipelineArtifact(args, `automated_test/${args.platform}/results`, 'robot-results')}
`;
}

function generateWebdriverIOYaml(args: PipelineYamlArgs): string {
  const isMobile = args.platform === 'mobile';
  const appiumSteps = isMobile ? `
  - script: |
      npm install -g appium
      appium driver install uiautomator2
    displayName: 'Instalar Appium'
` : '';

  return `${yamlHeader(args)}
variables:
  NODE_VERSION: '22.x'
  CI: 'true'

steps:
  - task: NodeTool@0
    displayName: 'Instalar Node.js $(NODE_VERSION)'
    inputs:
      versionSpec: '$(NODE_VERSION)'

  - script: |
      cd automated_test/${args.platform}
      npm ci
    displayName: 'Instalar Dependências'
${appiumSteps}
  - script: |
      cd automated_test/${args.platform}
      npx wdio run config/wdio.conf.${args.language === 'typescript' ? 'ts' : 'js'}
    displayName: 'Executar Testes WebdriverIO'${envVarsBlock(args)}
${publishTestResults(args, 'JUnit')}
`;
}

function generateSupertestYaml(args: PipelineYamlArgs): string {
  return `${yamlHeader(args)}
variables:
  NODE_VERSION: '22.x'
  CI: 'true'

steps:
  - task: NodeTool@0
    displayName: 'Instalar Node.js $(NODE_VERSION)'
    inputs:
      versionSpec: '$(NODE_VERSION)'

  - script: |
      cd automated_test/${args.platform}
      npm ci
    displayName: 'Instalar Dependências'

  - script: |
      cd automated_test/${args.platform}
      npx jest --ci --reporters=default --reporters=jest-junit
    displayName: 'Executar Testes Supertest API'${envVarsBlock(args)}
    env:
      JEST_JUNIT_OUTPUT_DIR: 'results'
      JEST_JUNIT_OUTPUT_NAME: 'test-results.xml'
${publishTestResults(args, 'JUnit')}
`;
}

function generateRequestsYaml(args: PipelineYamlArgs): string {
  return `${yamlHeader(args)}
variables:
  PYTHON_VERSION: '3.12'
  CI: 'true'

steps:
  - task: UsePythonVersion@0
    displayName: 'Configurar Python $(PYTHON_VERSION)'
    inputs:
      versionSpec: '$(PYTHON_VERSION)'

  - script: |
      cd automated_test/${args.platform}
      pip install -r requirements.txt
    displayName: 'Instalar Dependências'

  - script: |
      cd automated_test/${args.platform}
      pytest --junitxml=results/test-results.xml -v --tb=short
    displayName: 'Executar Testes API (Requests + Pytest)'${envVarsBlock(args)}
${publishTestResults(args, 'JUnit')}
`;
}

function generateRestAssuredYaml(args: PipelineYamlArgs): string {
  return `${yamlHeader(args)}
variables:
  JAVA_VERSION: '17'
  CI: 'true'

steps:
  - task: JavaToolInstaller@0
    displayName: 'Instalar Java $(JAVA_VERSION)'
    inputs:
      versionSpec: '$(JAVA_VERSION)'
      jdkArchitectureOption: 'x64'
      jdkSourceOption: 'PreInstalled'

  - script: |
      cd automated_test/${args.platform}
      mvn install -DskipTests
    displayName: 'Instalar Dependências'

  - script: |
      cd automated_test/${args.platform}
      mvn test
    displayName: 'Executar Testes REST Assured'${envVarsBlock(args)}
${publishTestResults(args, 'JUnit')}
`;
}

function generateKarateYaml(args: PipelineYamlArgs): string {
  return `${yamlHeader(args)}
variables:
  JAVA_VERSION: '17'
  CI: 'true'

steps:
  - task: JavaToolInstaller@0
    displayName: 'Instalar Java $(JAVA_VERSION)'
    inputs:
      versionSpec: '$(JAVA_VERSION)'
      jdkArchitectureOption: 'x64'
      jdkSourceOption: 'PreInstalled'

  - script: |
      cd automated_test/${args.platform}
      mvn install -DskipTests
    displayName: 'Instalar Dependências'

  - script: |
      cd automated_test/${args.platform}
      mvn test -Dtest=TestRunner
    displayName: 'Executar Testes Karate'${envVarsBlock(args)}
${publishTestResults(args, 'JUnit')}
${publishPipelineArtifact(args, `automated_test/${args.platform}/target/karate-reports`, 'karate-reports')}
`;
}

// ---------------------------------------------------------------------------
// Execução Principal
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const logger = new Logger('generate-pipeline-yaml');

  try {
    const args = parseArgs();

    logger.info('═══════════════════════════════════════════════════════════');
    logger.info('FastQA — Generate Pipeline YAML');
    logger.info('═══════════════════════════════════════════════════════════');
    logger.info(`Framework:   ${args.framework}`);
    logger.info(`Linguagem:   ${args.language}`);
    logger.info(`Plataforma:  ${args.platform}`);
    logger.info(`Pipeline:    ${args.pipelineName}`);
    logger.info(`Trigger:     ${args.triggerBranch}`);
    logger.info(`Output:      ${args.outputPath}`);
    if (args.push) {
      logger.info(`Push p/:     ${args.repo} (${args.branch})`);
    }
    logger.info('');

    // Gerar YAML
    logger.info('📝 Gerando YAML de pipeline...');
    const yamlContent = generateYaml(args);

    // Salvar localmente
    const localOutputPath = path.isAbsolute(args.outputPath)
      ? args.outputPath
      : path.join(FASTQA_ROOT, args.outputPath);

    fs.mkdirSync(path.dirname(localOutputPath), { recursive: true });
    fs.writeFileSync(localOutputPath, yamlContent, 'utf-8');
    logger.success(`YAML salvo localmente: ${localOutputPath}`);

    // Opcional: push para repositório
    if (args.push && args.repo && args.branch) {
      logger.info('');
      logger.info('🚀 Enviando YAML para repositório...');

      await withClient(async (client) => {
        const repo = await client.getRepository(args.repo!);
        const cleanBranch = args.branch!.replace(/^refs\/heads\//, '');
        const branch = await client.getBranch(repo.id, cleanBranch);
        if (!branch) {
          throw new Error(`Branch "${cleanBranch}" não encontrada no repositório "${repo.name}"`);
        }

        const yamlBase64 = Buffer.from(yamlContent, 'utf-8').toString('base64');
        const pushPayload: GitPushPayload = {
          refUpdates: [{
            name: `refs/heads/${cleanBranch}`,
            oldObjectId: branch.objectId,
          }],
          commits: [{
            comment: `ci(fastqa): adicionar pipeline YAML - ${args.pipelineName}`,
            changes: [{
              changeType: 'add',
              item: { path: `/${args.outputPath}` },
              newContent: {
                content: yamlBase64,
                contentType: 'base64encoded',
              },
            }],
          }],
        };

        const result = await client.createGitPush(repo.id, pushPayload);
        logger.success(`YAML enviado para ${repo.name}/${cleanBranch}`);
        logger.info(`   Push ID:   ${result.pushId}`);
        logger.info(`   Commit:    ${result.commits?.[0]?.commitId || 'N/A'}`);
      }, 'generate-pipeline-yaml');
    }

    // Resumo final
    logger.info('');
    logger.info('═══════════════════════════════════════════════════════════');
    logger.success('✅ Pipeline YAML gerado com sucesso!');
    logger.info('═══════════════════════════════════════════════════════════');
    logger.info(`   Framework:   ${args.framework}`);
    logger.info(`   Linguagem:   ${args.language}`);
    logger.info(`   Plataforma:  ${args.platform}`);
    logger.info(`   Arquivo:     ${localOutputPath}`);
    logger.info('');
    logger.info('   Para criar a pipeline no Azure DevOps, use:');
    logger.info('   @fastqa:azdo_create_pipeline');

  } catch (error) {
    logger.error(`❌ Erro: ${error instanceof Error ? error.message : error}`);
    process.exit(1);
  }
}

main();
