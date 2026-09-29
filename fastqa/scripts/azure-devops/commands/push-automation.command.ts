/**
 * ============================================================================
 * FastQA — Push Automation Code to Azure DevOps Repos
 * ============================================================================
 * Coleta arquivos de automação (automated_test/{platform}/) e faz push
 * para um repositório Azure DevOps, criando branch se necessário.
 *
 * Uso:
 *   npx tsx fastqa/scripts/azure-devops/commands/push-automation.command.ts \
 *     --repo "meu-repo" \
 *     --branch "feature/automation" \
 *     --platform web \
 *     --message "feat: adiciona testes automatizados web" \
 *     [--create-branch] \
 *     [--source-branch main] \
 *     [--target-path "tests/automated"] \
 *     [--include-shared]
 *
 * ============================================================================
 */

import * as fs from 'fs';
import * as path from 'path';
import { AzureDevOpsClient, withClient } from '../azure-devops.client';
import { config } from '../azure-devops.config';
import { Logger } from '../utils/logger.util';
import type {
  GitChange,
  GitPushPayload,
  GitRef,
  PushAutomationResult,
} from '../types/azure-devops.types';

// ---------------------------------------------------------------------------
// Constantes
// ---------------------------------------------------------------------------

const FASTQA_ROOT = path.resolve(__dirname, '..', '..', '..');
const MAX_PUSH_SIZE = 100 * 1024 * 1024; // 100 MB (limite prático de push)
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

// ---------------------------------------------------------------------------
// Parsing de Argumentos
// ---------------------------------------------------------------------------

interface PushArgs {
  repo: string;
  branch: string;
  platform: 'web' | 'api' | 'mobile';
  message: string;
  createBranch: boolean;
  sourceBranch: string;
  targetPath: string;
  includeShared: boolean;
  basePath?: string;
  dryRun: boolean;
}

function parseArgs(): PushArgs {
  const args = process.argv.slice(2);
  const parsed: Partial<PushArgs> = {
    createBranch: false,
    sourceBranch: 'main',
    targetPath: '',
    includeShared: false,
    dryRun: false,
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    switch (arg) {
      case '--repo':
      case '--repository':
        parsed.repo = args[++i];
        break;
      case '--branch':
        parsed.branch = args[++i];
        break;
      case '--platform':
        parsed.platform = args[++i] as 'web' | 'api' | 'mobile';
        break;
      case '--message':
      case '--commit-message':
        parsed.message = args[++i];
        break;
      case '--create-branch':
        parsed.createBranch = true;
        break;
      case '--source-branch':
        parsed.sourceBranch = args[++i];
        break;
      case '--target-path':
        parsed.targetPath = args[++i];
        break;
      case '--include-shared':
        parsed.includeShared = true;
        break;
      case '--base-path':
        parsed.basePath = args[++i];
        break;
      case '--dry-run':
        parsed.dryRun = true;
        break;
      default:
        if (arg.startsWith('--')) {
          console.warn(`⚠️  Argumento desconhecido: ${arg}`);
        }
    }
  }

  // Validações
  if (!parsed.repo) throw new Error('--repo é obrigatório');
  if (!parsed.branch) throw new Error('--branch é obrigatório');
  if (!parsed.platform) throw new Error('--platform é obrigatório (web | api | mobile)');
  if (!['web', 'api', 'mobile'].includes(parsed.platform!)) {
    throw new Error('--platform deve ser: web | api | mobile');
  }
  if (!parsed.message) {
    parsed.message = `feat(fastqa): push automação ${parsed.platform}`;
  }

  return parsed as PushArgs;
}

// ---------------------------------------------------------------------------
// Coleta de Arquivos
// ---------------------------------------------------------------------------

function shouldIgnore(filePath: string): boolean {
  return IGNORE_PATTERNS.some((pattern) =>
    filePath.split(path.sep).includes(pattern)
  );
}

function isBinaryFile(filePath: string): boolean {
  const ext = path.extname(filePath).toLowerCase();
  return BINARY_EXTENSIONS.has(ext);
}

interface CollectedFile {
  localPath: string;
  repoPath: string;
  size: number;
  isBinary: boolean;
}

function collectFiles(sourceDir: string, targetPrefix: string): CollectedFile[] {
  const files: CollectedFile[] = [];

  function walk(dir: string, relativeTo: string): void {
    if (!fs.existsSync(dir)) return;

    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (shouldIgnore(fullPath)) continue;

      if (entry.isDirectory()) {
        walk(fullPath, relativeTo);
      } else if (entry.isFile()) {
        const relPath = path.relative(relativeTo, fullPath).replace(/\\/g, '/');
        const repoPath = targetPrefix ? `${targetPrefix}/${relPath}` : relPath;
        const stats = fs.statSync(fullPath);

        files.push({
          localPath: fullPath,
          repoPath: `/${repoPath}`,
          size: stats.size,
          isBinary: isBinaryFile(fullPath),
        });
      }
    }
  }

  walk(sourceDir, sourceDir);
  return files;
}

// ---------------------------------------------------------------------------
// Execução Principal
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const logger = new Logger('push-automation');
  const startTime = Date.now();

  try {
    const args = parseArgs();

    logger.info('═══════════════════════════════════════════════════════════');
    logger.info('FastQA — Push Automation Code to Azure DevOps');
    logger.info('═══════════════════════════════════════════════════════════');
    logger.info(`Repositório: ${args.repo}`);
    logger.info(`Branch:      ${args.branch}`);
    logger.info(`Plataforma:  ${args.platform}`);
    logger.info(`Criar Branch: ${args.createBranch}`);
    if (args.createBranch) logger.info(`Branch Origem: ${args.sourceBranch}`);
    if (args.targetPath) logger.info(`Path Destino:  ${args.targetPath}`);
    logger.info(`Include Shared: ${args.includeShared}`);
    logger.info('');

    // 1. Coletar arquivos
    logger.info('📁 Coletando arquivos de automação...');

    const sourceDir = args.basePath
      ? path.resolve(args.basePath)
      : path.join(FASTQA_ROOT, 'automated_test', args.platform);

    if (!fs.existsSync(sourceDir)) {
      throw new Error(`Diretório não encontrado: ${sourceDir}`);
    }

    const targetPrefix = args.targetPath || `automated_test/${args.platform}`;
    const files = collectFiles(sourceDir, targetPrefix);

    // Incluir shared se solicitado
    if (args.includeShared) {
      const sharedDir = path.join(FASTQA_ROOT, 'automated_test', 'shared');
      if (fs.existsSync(sharedDir)) {
        const sharedTargetPrefix = args.targetPath
          ? `${args.targetPath}/../shared`
          : 'automated_test/shared';
        const sharedFiles = collectFiles(sharedDir, sharedTargetPrefix);
        files.push(...sharedFiles);
      }
    }

    if (files.length === 0) {
      throw new Error(`Nenhum arquivo encontrado em: ${sourceDir}`);
    }

    const totalSize = files.reduce((sum, f) => sum + f.size, 0);
    logger.info(`   Arquivos encontrados: ${files.length}`);
    logger.info(`   Tamanho total: ${(totalSize / 1024 / 1024).toFixed(2)} MB`);

    if (totalSize > MAX_PUSH_SIZE) {
      throw new Error(
        `Tamanho total (${(totalSize / 1024 / 1024).toFixed(2)} MB) excede o limite de ${MAX_PUSH_SIZE / 1024 / 1024} MB`
      );
    }

    // Lista resumida de arquivos
    for (const file of files.slice(0, 20)) {
      logger.info(`   → ${file.repoPath} (${(file.size / 1024).toFixed(1)} KB)`);
    }
    if (files.length > 20) {
      logger.info(`   ... e mais ${files.length - 20} arquivos`);
    }

    if (args.dryRun) {
      logger.info('');
      logger.info('🔍 DRY RUN — Nenhuma alteração foi enviada.');
      logger.info(`   Total: ${files.length} arquivos, ${(totalSize / 1024 / 1024).toFixed(2)} MB`);
      return;
    }

    // 2. Conectar ao Azure DevOps e obter repositório
    logger.info('');
    logger.info('🔗 Conectando ao Azure DevOps...');

    await withClient(async (client) => {
      // 2a. Obter repositório
      const repo = await client.getRepository(args.repo);
      logger.success(`Repositório encontrado: ${repo.name} (${repo.id})`);

      // 2b. Obter SHA da branch de referência
      let oldObjectId: string;
      const cleanBranch = args.branch.replace(/^refs\/heads\//, '');

      if (args.createBranch) {
        // Se criar branch, pegar SHA da branch de origem
        const sourceClean = args.sourceBranch.replace(/^refs\/heads\//, '');
        const sourceBranch = await client.getBranch(repo.id, sourceClean);
        if (!sourceBranch) {
          throw new Error(`Branch de origem "${args.sourceBranch}" não encontrada no repositório "${repo.name}"`);
        }
        oldObjectId = sourceBranch.objectId;
        logger.info(`Branch de origem: ${sourceClean} (SHA: ${oldObjectId.substring(0, 8)})`);
        logger.info(`Será criada nova branch: ${cleanBranch}`);
      } else {
        // Se branch existente, pegar SHA atual
        const existingBranch = await client.getBranch(repo.id, cleanBranch);
        if (!existingBranch) {
          throw new Error(
            `Branch "${cleanBranch}" não encontrada. Use --create-branch para criar.`
          );
        }
        oldObjectId = existingBranch.objectId;
        logger.info(`Branch existente: ${cleanBranch} (SHA: ${oldObjectId.substring(0, 8)})`);
      }

      // 3. Construir changes (leituras de arquivo)
      logger.info('');
      logger.info('📦 Preparando commits...');

      const changes: GitChange[] = [];
      for (const file of files) {
        const content = fs.readFileSync(file.localPath);
        const base64Content = content.toString('base64');

        changes.push({
          changeType: 'add',
          item: { path: file.repoPath },
          newContent: {
            content: base64Content,
            contentType: 'base64encoded',
          },
        });
      }

      // 4. Criar payload de push
      const pushPayload: GitPushPayload = {
        refUpdates: [
          {
            name: `refs/heads/${cleanBranch}`,
            oldObjectId: oldObjectId,
          },
        ],
        commits: [
          {
            comment: args.message,
            changes: changes,
          },
        ],
      };

      // 5. Executar push
      logger.info('🚀 Enviando push para Azure DevOps...');
      const result = await client.createGitPush(repo.id, pushPayload);

      // 6. Relatório
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
      const commitId = result.commits?.[0]?.commitId || 'N/A';
      const commitUrl = result.commits?.[0]?.url || '';

      logger.info('');
      logger.info('═══════════════════════════════════════════════════════════');
      logger.success('✅ PUSH REALIZADO COM SUCESSO!');
      logger.info('═══════════════════════════════════════════════════════════');
      logger.info(`   Push ID:      ${result.pushId}`);
      logger.info(`   Commit ID:    ${commitId}`);
      logger.info(`   Repositório:  ${repo.name}`);
      logger.info(`   Branch:       ${cleanBranch}`);
      logger.info(`   Arquivos:     ${files.length}`);
      logger.info(`   Tamanho:      ${(totalSize / 1024 / 1024).toFixed(2)} MB`);
      logger.info(`   Duração:      ${elapsed}s`);
      logger.info('');

      // URL do repositório no Azure DevOps
      const repoWebUrl = `${config.orgUrl}/${encodeURIComponent(config.project)}/_git/${encodeURIComponent(repo.name)}`;
      const branchUrl = `${repoWebUrl}?version=GB${encodeURIComponent(cleanBranch)}`;
      logger.info(`   🔗 Repo: ${repoWebUrl}`);
      logger.info(`   🔗 Branch: ${branchUrl}`);

      if (commitUrl) {
        logger.info(`   🔗 Commit: ${commitUrl}`);
      }

      // Salvar resultado em JSON
      const resultData: PushAutomationResult = {
        pushId: result.pushId,
        commitId: commitId,
        commitUrl: commitUrl,
        repositoryName: repo.name,
        branchName: cleanBranch,
        filesCount: files.length,
        totalSize: totalSize,
        files: files.map((f) => ({
          path: f.repoPath,
          size: f.size,
          changeType: 'add' as const,
        })),
      };

      const logFileName = `push-automation-${Date.now()}.json`;
      const logPath = path.join(__dirname, '..', 'logs', logFileName);
      fs.mkdirSync(path.dirname(logPath), { recursive: true });
      fs.writeFileSync(logPath, JSON.stringify(resultData, null, 2), 'utf-8');
      logger.info(`   📝 Log salvo: ${logPath}`);
    }, 'push-automation');

  } catch (error) {
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    logger.error(`❌ Erro após ${elapsed}s: ${error instanceof Error ? error.message : error}`);
    process.exit(1);
  }
}

main();
