/**
 * ═══════════════════════════════════════════════════════════════════════════
 * FastQA — Git Local Provider (Regression Analysis)
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * Provedor de dados de PR via comandos Git locais (fallback universal).
 * Obtém arquivos alterados comparando a branch atual com a branch alvo.
 *
 * Uso:
 *   import { getGitLocalChanges } from './git-local.provider';
 *   const result = await getGitLocalChanges('/path/to/app-repo', 'develop');
 *
 * @module git-local-provider
 */

import { execSync } from 'child_process';
import type { PrAnalysisResult, PrFileChange } from '../types/regression.types';

/**
 * Executa um comando Git no diretório informado.
 * Retorna a saída como string limpa.
 */
function git(appRepoPath: string, args: string): string {
  return execSync(`git -C "${appRepoPath}" ${args}`, {
    encoding: 'utf-8',
    timeout: 30_000,
  }).trim();
}

/**
 * Detecta a branch alvo padrão do repositório.
 * Tenta "develop", fallback para "main", depois "master".
 */
function detectTargetBranch(appRepoPath: string, preferred?: string): string {
  if (preferred) return preferred;

  const candidates = ['develop', 'main', 'master'];
  for (const branch of candidates) {
    try {
      git(appRepoPath, `rev-parse --verify origin/${branch}`);
      return branch;
    } catch {
      // branch não existe, tenta próxima
    }
  }
  return 'main'; // fallback final
}

/**
 * Mapeia status do git diff --name-status para nosso changeType.
 */
function mapChangeType(status: string): PrFileChange['changeType'] {
  switch (status[0]) {
    case 'A': return 'add';
    case 'M': return 'edit';
    case 'D': return 'delete';
    case 'R': return 'rename';
    default: return 'edit';
  }
}

/**
 * Obtém dados de alteração do repositório local via Git.
 * Compara a branch atual (HEAD) com a branch alvo (origin/{target}).
 *
 * @param appRepoPath - Caminho absoluto do repositório da aplicação
 * @param targetBranch - Branch alvo para comparação (default: detect)
 * @returns PrAnalysisResult com dados normalizados
 */
export async function getGitLocalChanges(
  appRepoPath: string,
  targetBranch?: string
): Promise<PrAnalysisResult> {
  // 1. Atualizar refs remotas
  try {
    git(appRepoPath, 'fetch origin --prune');
  } catch {
    console.warn('⚠️  Não foi possível executar git fetch (modo offline?)');
  }

  // 2. Detectar branch alvo
  const target = detectTargetBranch(appRepoPath, targetBranch);

  // 3. Obter branch atual
  const sourceBranch = git(appRepoPath, 'rev-parse --abbrev-ref HEAD');

  // 4. Obter arquivos alterados
  const diffOutput = git(appRepoPath, `diff --name-status origin/${target}...HEAD`);
  const files: PrFileChange[] = diffOutput
    .split('\n')
    .filter(line => line.trim() !== '')
    .map(line => {
      const parts = line.split('\t');
      const status = parts[0];
      // Para rename (R100), o path novo está na posição 2
      const filePath = parts.length >= 3 ? parts[2] : parts[1];
      return {
        changeType: mapChangeType(status),
        path: `/${filePath}`,
      };
    });

  // 4.1. Coletar diffs reais para os arquivos (max 10 arquivos, max 500 linhas/arquivo)
  const MAX_DIFF_FILES = 10;
  const MAX_DIFF_LINES = 500;
  const diffableFiles = files.filter(f => f.changeType !== 'delete').slice(0, MAX_DIFF_FILES);
  for (const file of diffableFiles) {
    try {
      const filePath = file.path.replace(/^\/+/, '');
      const rawDiff = git(appRepoPath, `diff origin/${target}...HEAD -- "${filePath}"`);
      if (rawDiff) {
        const diffLines = rawDiff.split('\n');
        file.diff = diffLines.slice(0, MAX_DIFF_LINES).join('\n');
        const additions = diffLines.filter(l => l.startsWith('+') && !l.startsWith('+++')).length;
        const deletions = diffLines.filter(l => l.startsWith('-') && !l.startsWith('---')).length;
        file.diffStats = { additions, deletions };
      }
    } catch {
      // Diff não disponível para este arquivo — seguir sem
    }
  }

  // 5. Obter metadata do último commit
  const title = git(appRepoPath, 'log -1 --format=%s');
  const author = git(appRepoPath, 'log -1 --format=%an');
  const date = git(appRepoPath, 'log -1 --format=%aI');

  // 6. Gerar ID sintético (hash do branch + timestamp)
  const commitHash = git(appRepoPath, 'rev-parse --short HEAD');
  const syntheticId = parseInt(commitHash, 16) % 100000;

  return {
    pr: {
      id: syntheticId,
      title: `[Git Local] ${title}`,
      source: sourceBranch,
      target: `origin/${target}`,
      author,
      date,
      provider: 'git-local',
    },
    files,
    workItems: [], // Work Items não disponíveis via Git local
  };
}
