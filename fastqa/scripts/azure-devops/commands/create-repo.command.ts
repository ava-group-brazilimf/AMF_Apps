#!/usr/bin/env npx tsx
// ==========================================================================
// FastQA — Comando #18: Criar Repositório no Azure DevOps
// ==========================================================================
//
// Cria um novo repositório Git no Azure DevOps, opcionalmente em outro projeto,
// e faz o push inicial com os arquivos de automação selecionados — garantindo
// que a execução isolada da pipeline funcione no Azure DevOps.
//
// Uso:
//   npx tsx fastqa/scripts/azure-devops/commands/create-repo.command.ts \
//     --repo "meu-repo-automacao" \
//     --automation-dir "web" \
//     [--project "outro-projeto"] \
//     [--description "Repositório de testes automatizados"] \
//     [--branch "main"] \
//     [--target-path ""] \
//     [--include-shared] \
//     [--generate-gitignore] \
//     [--dry-run]
//
// ==========================================================================

import * as fs from 'fs';
import * as path from 'path';
import { AzureDevOpsClient, withClient } from '../azure-devops.client';
import { config } from '../azure-devops.config';
import { Logger } from '../utils/logger.util';
import type {
  GitChange,
  GitPushPayload,
  GitRepository,
  CreateRepoResult,
  AzureDevOpsProject,
} from '../types/azure-devops.types';

// ---------------------------------------------------------------------------
// Constantes
// ---------------------------------------------------------------------------

const FASTQA_ROOT = path.resolve(__dirname, '..', '..', '..');
const MAX_PUSH_SIZE = 100 * 1024 * 1024; // 100 MB

const BINARY_EXTENSIONS = new Set([
  '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.svg',
  '.mp4', '.webm', '.avi', '.mov',
  '.pdf', '.zip', '.tar', '.gz', '.7z',
  '.woff', '.woff2', '.ttf', '.eot',
  '.exe', '.dll', '.so', '.dylib',
  '.xlsx', '.docx', '.pptx',
]);

const IGNORE_PATTERNS = [
  'node_modules', '.git', 'dist', 'build', '.cache',
  'results', 'logs', '__pycache__', '.pytest_cache',
  '.tox', 'coverage', '.nyc_output', 'allure-results',
];

/** 40 zeros — objectId necessário para push inicial em repositório vazio */
const NULL_OBJECT_ID = '0000000000000000000000000000000000000000';

// ---------------------------------------------------------------------------
// Parsing de Argumentos
// ---------------------------------------------------------------------------

interface CreateRepoArgs {
  repo: string;
  automationDir: string;
  project: string;          // vazio = projeto padrão do .env
  description: string;
  branch: string;
  targetPath: string;
  includeShared: boolean;
  generateGitignore: boolean;
  dryRun: boolean;
}

function parseArgs(): CreateRepoArgs {
  const args = process.argv.slice(2);
  const parsed: Partial<CreateRepoArgs> = {
    project: '',
    description: '',
    branch: 'main',
    targetPath: '',
    includeShared: false,
    generateGitignore: false,
    dryRun: false,
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    const nextVal = () => {
      const v = arg.includes('=') ? arg.split('=').slice(1).join('=') : args[++i];
      if (!v) { console.error(`Valor ausente para ${arg}`); process.exit(1); }
      return v;
    };

    switch (true) {
      case arg.startsWith('--repo'):          parsed.repo = nextVal(); break;
      case arg.startsWith('--automation-dir'): parsed.automationDir = nextVal(); break;
      case arg.startsWith('--project'):       parsed.project = nextVal(); break;
      case arg.startsWith('--description'):   parsed.description = nextVal(); break;
      case arg.startsWith('--branch'):        parsed.branch = nextVal(); break;
      case arg.startsWith('--target-path'):   parsed.targetPath = nextVal(); break;
      case arg === '--include-shared':        parsed.includeShared = true; break;
      case arg === '--generate-gitignore':    parsed.generateGitignore = true; break;
      case arg === '--dry-run':               parsed.dryRun = true; break;
      default:
        console.error(`Argumento desconhecido: ${arg}`);
        process.exit(1);
    }
  }

  if (!parsed.repo) {
    console.error('❌  Parâmetro --repo é obrigatório.');
    process.exit(1);
  }
  if (!parsed.automationDir) {
    console.error('❌  Parâmetro --automation-dir é obrigatório (web | api | mobile ou caminho relativo).');
    process.exit(1);
  }

  return parsed as CreateRepoArgs;
}

// ---------------------------------------------------------------------------
// Helpers de Arquivos (mesmo padrão de push-automation)
// ---------------------------------------------------------------------------

function shouldIgnore(name: string): boolean {
  return IGNORE_PATTERNS.includes(name);
}

function isBinaryFile(filePath: string): boolean {
  return BINARY_EXTENSIONS.has(path.extname(filePath).toLowerCase());
}

interface CollectedFile {
  /** Caminho relativo no repositório destino (e.g. "tests/login.spec.ts") */
  repoPath: string;
  /** Caminho absoluto local */
  localPath: string;
  /** Tamanho em bytes */
  size: number;
}

/**
 * Coleta recursivamente os arquivos de um diretório, mapeando-os para
 * caminhos relativos dentro do repositório.
 */
function collectFiles(sourceDir: string, targetPrefix: string): CollectedFile[] {
  const files: CollectedFile[] = [];

  function walk(dir: string, relBase: string): void {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      if (shouldIgnore(entry.name)) continue;
      const fullPath = path.join(dir, entry.name);
      const relPath = relBase ? `${relBase}/${entry.name}` : entry.name;

      if (entry.isDirectory()) {
        walk(fullPath, relPath);
      } else if (entry.isFile()) {
        const stat = fs.statSync(fullPath);
        const repoPath = targetPrefix ? `${targetPrefix}/${relPath}` : relPath;
        files.push({ repoPath, localPath: fullPath, size: stat.size });
      }
    }
  }

  if (fs.existsSync(sourceDir)) {
    walk(sourceDir, '');
  }
  return files;
}

// ---------------------------------------------------------------------------
// Geração de .gitignore por Framework
// ---------------------------------------------------------------------------

interface ProjectConfig {
  connectors?: {
    output?: {
      automation_framework?: string;
      language?: string;
    };
  };
  platform?: {
    type?: string;
  };
}

function loadProjectConfig(): ProjectConfig {
  const configPath = path.join(FASTQA_ROOT, 'scripts', 'project_config.json');
  if (!fs.existsSync(configPath)) return {};
  try {
    return JSON.parse(fs.readFileSync(configPath, 'utf-8'));
  } catch {
    return {};
  }
}

function generateGitignoreContent(framework?: string, language?: string): string {
  const lines: string[] = [
    '# === Dependências ===',
    'node_modules/',
    '.venv/',
    'venv/',
    '__pycache__/',
    '*.pyc',
    '',
    '# === Build / Output ===',
    'dist/',
    'build/',
    'out/',
    'target/',
    'bin/',
    'obj/',
    '',
    '# === Resultados de Testes ===',
    'results/',
    'allure-results/',
    'allure-report/',
    'test-results/',
    'playwright-report/',
    'coverage/',
    '.nyc_output/',
    'mochawesome-report/',
    '',
    '# === IDE / SO ===',
    '.idea/',
    '.vscode/',
    '*.suo',
    '*.user',
    '.DS_Store',
    'Thumbs.db',
    '',
    '# === Credenciais ===',
    '.env',
    '.env.local',
    '*.pem',
    '*.key',
    '',
    '# === Logs ===',
    'logs/',
    '*.log',
    'npm-debug.log*',
    '',
  ];

  // Adições específicas por framework
  const fw = (framework ?? '').toLowerCase();
  const lang = (language ?? '').toLowerCase();

  if (fw === 'playwright') {
    lines.push('# === Playwright ===', 'blob-report/', 'playwright/.cache/', '');
  }
  if (fw === 'cypress') {
    lines.push('# === Cypress ===', 'cypress/videos/', 'cypress/screenshots/', 'cypress/downloads/', '');
  }
  if (fw === 'robot') {
    lines.push('# === Robot Framework ===', 'output.xml', 'log.html', 'report.html', '');
  }
  if (fw === 'selenium') {
    lines.push('# === Selenium ===', 'geckodriver.log', 'chromedriver.log', '');
  }
  if (fw === 'webdriverio') {
    lines.push('# === WebdriverIO ===', 'allure-results/', 'wdio-logs/', '*.apk', '*.ipa', 'apps/', '');
  }

  if (['typescript', 'javascript'].includes(lang)) {
    lines.push('# === Node.js ===', 'package-lock.json', '*.tsbuildinfo', '');
  }
  if (lang === 'python') {
    lines.push('# === Python ===', '.pytest_cache/', '.tox/', 'htmlcov/', '*.egg-info/', '');
  }
  if (lang === 'java') {
    lines.push('# === Java / Maven ===', '*.class', '*.jar', '.gradle/', 'gradle/', '');
  }
  if (lang === 'csharp') {
    lines.push('# === C# / .NET ===', '*.dll', '*.exe', '*.nupkg', 'packages/', '');
  }

  return lines.join('\n');
}

// ---------------------------------------------------------------------------
// Geração de README.md para o repositório
// ---------------------------------------------------------------------------

function generateReadmeContent(repoName: string, framework?: string, language?: string, platform?: string): string {
  const fw = framework ?? 'N/A';
  const lang = language ?? 'N/A';
  const plat = platform ?? 'N/A';

  return [
    `# ${repoName}`,
    '',
    `Repositório de testes automatizados gerado via **FastQA** — Comando \`@fastqa:azdo_create_repo\`.`,
    '',
    '## Stack',
    '',
    `| Item | Valor |`,
    `|------|-------|`,
    `| **Plataforma** | ${plat} |`,
    `| **Framework** | ${fw} |`,
    `| **Linguagem** | ${lang} |`,
    '',
    '## Execução local',
    '',
    '```bash',
    '# Instalar dependências',
    fw === 'playwright' && ['typescript', 'javascript'].includes(lang.toLowerCase())
      ? 'npm ci\nnpx playwright install --with-deps'
      : fw === 'cypress'
        ? 'npm ci'
        : lang.toLowerCase() === 'python'
          ? 'pip install -r requirements.txt'
          : lang.toLowerCase() === 'java'
            ? 'mvn install'
            : 'npm ci',
    '',
    '# Executar testes',
    fw === 'playwright' && ['typescript', 'javascript'].includes(lang.toLowerCase())
      ? 'npx playwright test'
      : fw === 'cypress'
        ? 'npx cypress run'
        : fw === 'robot'
          ? 'robot --outputdir results tests/'
          : lang.toLowerCase() === 'python'
            ? 'pytest tests/ --junitxml=results/junit.xml'
            : lang.toLowerCase() === 'java'
              ? 'mvn test'
              : 'npx playwright test',
    '```',
    '',
    '## Pipeline CI/CD',
    '',
    'Use `@fastqa:azdo_generate_pipeline` para gerar o YAML de pipeline otimizado para este repositório.',
    '',
    '---',
    `*Gerado em: ${new Date().toISOString()} por FastQA*`,
    '',
  ].join('\n');
}

// ---------------------------------------------------------------------------
// Programa Principal
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const args = parseArgs();

  const log = new Logger('create-repo');
  const startTime = Date.now();

  log.info('');
  log.info('═══════════════════════════════════════════════════════════════');
  log.info('  FastQA — Criar Repositório no Azure DevOps (Comando #18)  ');
  log.info('═══════════════════════════════════════════════════════════════');
  log.info('');
  log.info(`  Repositório:      ${args.repo}`);
  log.info(`  Projeto:          ${args.project || config.project + ' (padrão)'}`);
  log.info(`  Automação dir:    ${args.automationDir}`);
  log.info(`  Branch:           ${args.branch}`);
  log.info(`  Target path:      ${args.targetPath || '(raiz)'}`);
  log.info(`  Incluir shared:   ${args.includeShared}`);
  log.info(`  Gerar .gitignore: ${args.generateGitignore}`);
  log.info(`  Dry-run:          ${args.dryRun}`);
  log.info('');

  // -----------------------------------------------------------------------
  // 1. Resolver diretório de automação local
  // -----------------------------------------------------------------------
  const knownPlatforms = ['web', 'api', 'mobile'];
  let sourceDir: string;

  if (knownPlatforms.includes(args.automationDir.toLowerCase())) {
    sourceDir = path.join(FASTQA_ROOT, 'automated_test', args.automationDir.toLowerCase());
  } else {
    // Aceita caminho relativo a FASTQA_ROOT ou caminho absoluto
    sourceDir = path.isAbsolute(args.automationDir)
      ? args.automationDir
      : path.join(FASTQA_ROOT, args.automationDir);
  }

  if (!fs.existsSync(sourceDir)) {
    log.error(`Diretório de automação não encontrado: ${sourceDir}`);
    process.exit(1);
  }

  log.info(`📂  Diretório de automação: ${sourceDir}`);

  // -----------------------------------------------------------------------
  // 2. Coletar arquivos
  // -----------------------------------------------------------------------
  const targetPrefix = args.targetPath.replace(/^\/+|\/+$/g, '');
  const files: CollectedFile[] = collectFiles(sourceDir, targetPrefix);

  // Incluir shared/ se solicitado
  if (args.includeShared) {
    const sharedDir = path.join(FASTQA_ROOT, 'automated_test', 'shared');
    if (fs.existsSync(sharedDir)) {
      const sharedPrefix = targetPrefix ? `${targetPrefix}/shared` : 'shared';
      files.push(...collectFiles(sharedDir, sharedPrefix));
      log.info(`📂  Incluindo shared/ (${sharedPrefix})`);
    } else {
      log.warn('Pasta shared/ não encontrada — ignorando --include-shared');
    }
  }

  // Carregar configuração do projeto para gitignore/readme
  const projCfg = loadProjectConfig();
  const framework = projCfg.connectors?.output?.automation_framework;
  const language = projCfg.connectors?.output?.language;
  const platform = projCfg.platform?.type;

  // Gerar .gitignore se solicitado
  if (args.generateGitignore) {
    const gitignoreContent = generateGitignoreContent(framework, language);
    const gitignorePath = targetPrefix ? `${targetPrefix}/.gitignore` : '.gitignore';
    files.push({
      repoPath: gitignorePath,
      localPath: '', // virtual — conteúdo gerado
      size: Buffer.byteLength(gitignoreContent, 'utf-8'),
    });
    log.info('📝  .gitignore será gerado automaticamente');
    // Marcar para tratar especialmente no loop de criação de changes
    (files[files.length - 1] as any).__virtualContent = gitignoreContent;
  }

  // Gerar README.md para o repositório
  const readmeContent = generateReadmeContent(args.repo, framework, language, platform);
  const readmePath = targetPrefix ? `${targetPrefix}/README.md` : 'README.md';
  // Só adiciona se não existe um README.md coletado
  const hasReadme = files.some(f => f.repoPath.toLowerCase() === readmePath.toLowerCase());
  if (!hasReadme) {
    files.push({
      repoPath: readmePath,
      localPath: '',
      size: Buffer.byteLength(readmeContent, 'utf-8'),
    });
    (files[files.length - 1] as any).__virtualContent = readmeContent;
    log.info('📝  README.md será gerado automaticamente');
  }

  // -----------------------------------------------------------------------
  // 3. Validar tamanho e quantidade
  // -----------------------------------------------------------------------
  if (files.length === 0) {
    log.error('Nenhum arquivo encontrado no diretório de automação.');
    process.exit(1);
  }

  const totalSize = files.reduce((s, f) => s + f.size, 0);
  log.info(`📦  Arquivos coletados: ${files.length} (${(totalSize / 1024).toFixed(1)} KB)`);

  if (totalSize > MAX_PUSH_SIZE) {
    log.error(`Tamanho total (${(totalSize / 1024 / 1024).toFixed(1)} MB) excede o limite de ${MAX_PUSH_SIZE / 1024 / 1024} MB.`);
    process.exit(1);
  }

  // -----------------------------------------------------------------------
  // 4. Modo dry-run — apenas listar
  // -----------------------------------------------------------------------
  if (args.dryRun) {
    log.info('');
    log.info('🏁  DRY-RUN — Arquivos que seriam enviados:');
    log.info('─'.repeat(72));
    for (const f of files) {
      const sizeKB = (f.size / 1024).toFixed(1);
      const label = f.localPath === '' ? '(gerado)' : '';
      log.info(`  ${f.repoPath.padEnd(55)} ${sizeKB.padStart(8)} KB  ${label}`);
    }
    log.info('─'.repeat(72));
    log.info(`  Total: ${files.length} arquivos, ${(totalSize / 1024).toFixed(1)} KB`);
    log.info('');
    log.info('  Nenhuma alteração foi realizada (modo dry-run).');
    process.exit(0);
  }

  // -----------------------------------------------------------------------
  // 5. Criar repositório e fazer push inicial via API
  // -----------------------------------------------------------------------
  await withClient(async (client: AzureDevOpsClient) => {
    // 5a. Resolver projeto
    const targetProjectName = args.project || config.project;
    const isCrossProject = !!args.project && args.project !== config.project;

    log.info(`🔍  Resolvendo projeto "${targetProjectName}"...`);
    let project: AzureDevOpsProject;
    try {
      project = await client.getProject(targetProjectName);
    } catch (err: any) {
      log.error(`Falha ao resolver projeto "${targetProjectName}": ${err.message ?? err}`);
      process.exit(1);
    }
    log.info(`✅  Projeto resolvido: ${project.name} (ID: ${project.id})`);

    // 5b. Criar repositório
    log.info(`📦  Criando repositório "${args.repo}" no projeto "${project.name}"...`);
    let repo: GitRepository;
    try {
      repo = await client.createRepository(args.repo, project.id, project.name);
    } catch (err: any) {
      // Tratar caso de repositório já existente (409 Conflict)
      if (err.message?.includes('409') || err.message?.includes('already exists') || err.message?.includes('TF401019')) {
        log.error(`Repositório "${args.repo}" já existe no projeto "${project.name}".`);
        log.error('Use @fastqa:azdo_push_automation para enviar código a um repositório existente.');
        process.exit(1);
      }
      log.error(`Falha ao criar repositório: ${err.message ?? err}`);
      process.exit(1);
    }

    log.info(`✅  Repositório criado com sucesso!`);
    log.info(`    ID:        ${repo.id}`);
    log.info(`    Nome:      ${repo.name}`);
    log.info(`    Clone URL: ${repo.remoteUrl ?? 'N/A'}`);
    log.info(`    Web URL:   ${repo.webUrl ?? 'N/A'}`);
    log.info('');

    // 5c. Construir GitChanges
    log.info(`🔧  Preparando ${files.length} arquivos para push inicial...`);
    const changes: GitChange[] = [];

    for (const file of files) {
      let content: string;
      const virtualContent = (file as any).__virtualContent as string | undefined;

      if (virtualContent) {
        // Arquivo virtual (gerado em memória)
        content = Buffer.from(virtualContent, 'utf-8').toString('base64');
      } else if (isBinaryFile(file.localPath)) {
        content = fs.readFileSync(file.localPath).toString('base64');
      } else {
        const raw = fs.readFileSync(file.localPath, 'utf-8');
        content = Buffer.from(raw, 'utf-8').toString('base64');
      }

      // Normalizar path — sempre com / e começando com /
      const normalizedPath = '/' + file.repoPath.replace(/\\/g, '/').replace(/^\/+/, '');

      changes.push({
        changeType: 'add',
        item: { path: normalizedPath },
        newContent: {
          content,
          contentType: 'base64encoded',
        },
      });
    }

    // 5d. Montar payload de push (repositório vazio: oldObjectId = 40 zeros)
    const commitMessage = args.description
      ? `feat: ${args.description}`
      : `feat: push inicial de automação (${args.automationDir}) via FastQA`;

    const pushPayload: GitPushPayload = {
      refUpdates: [
        {
          name: `refs/heads/${args.branch}`,
          oldObjectId: NULL_OBJECT_ID,
        },
      ],
      commits: [
        {
          comment: commitMessage,
          changes,
        },
      ],
    };

    // 5e. Executar push
    log.info(`🚀  Executando push inicial (${files.length} arquivos, branch "${args.branch}")...`);

    const pushMethod = isCrossProject
      ? () => client.createGitPushInProject(project.name, repo.id, pushPayload)
      : () => client.createGitPush(repo.id, pushPayload);

    let pushResult;
    try {
      pushResult = await pushMethod();
    } catch (err: any) {
      log.error(`Falha no push inicial: ${err.message ?? err}`);
      process.exit(1);
    }

    const commitId = pushResult.commits?.[0]?.commitId ?? 'N/A';
    const commitUrl = pushResult.commits?.[0]?.url ?? '';

    // -----------------------------------------------------------------------
    // 6. Relatório final
    // -----------------------------------------------------------------------
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

    log.info('');
    log.info('═══════════════════════════════════════════════════════════════');
    log.info('  ✅  REPOSITÓRIO CRIADO COM SUCESSO');
    log.info('═══════════════════════════════════════════════════════════════');
    log.info('');
    log.info(`  Repositório:    ${repo.name}`);
    log.info(`  Projeto:        ${project.name}${isCrossProject ? ' (cross-project)' : ''}`);
    log.info(`  Branch:         ${args.branch}`);
    log.info(`  Commit:         ${commitId.substring(0, 8)}`);
    log.info(`  Arquivos:       ${files.length}`);
    log.info(`  Tamanho total:  ${(totalSize / 1024).toFixed(1)} KB`);
    log.info(`  Duração:        ${elapsed}s`);
    log.info('');
    log.info(`  🔗  Repo URL:   ${repo.webUrl ?? 'N/A'}`);
    log.info(`  🔗  Clone URL:  ${repo.remoteUrl ?? 'N/A'}`);
    log.info(`  🔗  Commit:     ${commitUrl || 'N/A'}`);
    log.info('');
    log.info('  📌  Próximos passos:');
    log.info('       1. @fastqa:azdo_generate_pipeline — Gerar pipeline CI/CD');
    log.info('       2. @fastqa:azdo_push_automation   — Push de atualizações futuras');
    log.info('');

    // -----------------------------------------------------------------------
    // 7. Salvar log JSON
    // -----------------------------------------------------------------------
    const result: CreateRepoResult = {
      repository: repo,
      pushId: pushResult.pushId ?? 0,
      commitId,
      commitUrl,
      filesCount: files.length,
      totalSize,
      repoUrl: repo.webUrl ?? '',
      cloneUrl: repo.remoteUrl ?? '',
      files: files.map(f => ({ path: f.repoPath, size: f.size })),
    };

    const logsDir = path.join(__dirname, '..', 'logs');
    if (!fs.existsSync(logsDir)) fs.mkdirSync(logsDir, { recursive: true });

    const logFile = path.join(logsDir, `create-repo-${Date.now()}.json`);
    fs.writeFileSync(logFile, JSON.stringify(result, null, 2), 'utf-8');
    log.info(`  📝  Log salvo: ${logFile}`);
    log.info('');

  }, 'create-repo');
}

// ---------------------------------------------------------------------------
// Execução
// ---------------------------------------------------------------------------
main().catch((err) => {
  console.error('❌  Erro fatal:', err);
  process.exit(1);
});
