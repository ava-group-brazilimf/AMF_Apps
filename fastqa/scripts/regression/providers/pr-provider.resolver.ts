/**
 * ═══════════════════════════════════════════════════════════════════════════
 * FastQA — PR Provider Resolver (Regression Analysis)
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * Parser de URL de PR e dispatcher para o provedor adequado.
 * Detecta Azure DevOps ou Git local a partir da URL/args fornecidos.
 *
 * Uso:
 *   import { resolvePrInput, fetchPrData } from './pr-provider.resolver';
 *   const input = resolvePrInput('https://dev.azure.com/.../pullrequest/123');
 *   const result = await fetchPrData(input);
 *
 * @module pr-provider-resolver
 */

import type { PrInput, PrAnalysisResult, AnalyzePrRegressionParams } from '../types/regression.types';
import { getGitLocalChanges } from './git-local.provider';

// ─────────────────────────────────────────────────────────────────────
// URL Patterns
// ─────────────────────────────────────────────────────────────────────

/** Regex para URL Azure DevOps: dev.azure.com/{org}/{project}/_git/{repo}/pullrequest/{id} */
const AZURE_DEVOPS_URL_REGEX =
  /dev\.azure\.com\/[^/]+\/[^/]+\/_git\/([^/]+)\/pullrequest\/(\d+)/i;

/** Regex alternativa: {org}.visualstudio.com/{project}/_git/{repo}/pullrequest/{id} */
const AZURE_DEVOPS_LEGACY_URL_REGEX =
  /\.visualstudio\.com\/[^/]+\/_git\/([^/]+)\/pullrequest\/(\d+)/i;

// ─────────────────────────────────────────────────────────────────────
// Resolver
// ─────────────────────────────────────────────────────────────────────

/**
 * Resolve o input do usuário (URL ou parâmetros) em um PrInput normalizado.
 *
 * Suporta:
 * - URL Azure DevOps (dev.azure.com ou visualstudio.com)
 * - ID numérico + repo name → Azure DevOps
 * - Flag useGitLocal ou appRepoPath → Git local
 */
export function resolvePrInput(input: string | AnalyzePrRegressionParams): PrInput {
  // Se string, tratar como URL ou ID numérico
  if (typeof input === 'string') {
    return parsePrUrl(input);
  }

  // Se forçar git local ou sem PR URL/ID
  if (input.useGitLocal || (!input.prUrl && !input.prId && input.appRepoPath)) {
    return {
      provider: 'git-local',
      appRepoPath: input.appRepoPath,
      targetBranch: input.targetBranch,
    };
  }

  // Se tem URL, parsear
  if (input.prUrl) {
    const resolved = parsePrUrl(input.prUrl);
    // Enriquecer com dados adicionais
    if (input.appRepoPath) resolved.appRepoPath = input.appRepoPath;
    if (input.targetBranch) resolved.targetBranch = input.targetBranch;
    return resolved;
  }

  // Se tem ID + repo → Azure DevOps
  if (input.prId && input.repo) {
    return {
      provider: 'azure-devops',
      prId: input.prId,
      repoNameOrId: input.repo,
      appRepoPath: input.appRepoPath,
      targetBranch: input.targetBranch,
    };
  }

  // Se tem ID + appRepoPath → git local
  if (input.prId && input.appRepoPath) {
    return {
      provider: 'git-local',
      prId: input.prId,
      appRepoPath: input.appRepoPath,
      targetBranch: input.targetBranch,
    };
  }

  throw new Error(
    'Input insuficiente. Informe --pr-url, ou --pr-id + --repo, ou --app-repo-path.'
  );
}

/**
 * Parseia uma URL de PR e detecta o provedor.
 */
function parsePrUrl(url: string): PrInput {
  // Azure DevOps (moderno)
  const azdoMatch = url.match(AZURE_DEVOPS_URL_REGEX);
  if (azdoMatch) {
    return {
      provider: 'azure-devops',
      repoNameOrId: decodeURIComponent(azdoMatch[1]),
      prId: parseInt(azdoMatch[2], 10),
    };
  }

  // Azure DevOps (legado)
  const azdoLegacyMatch = url.match(AZURE_DEVOPS_LEGACY_URL_REGEX);
  if (azdoLegacyMatch) {
    return {
      provider: 'azure-devops',
      repoNameOrId: decodeURIComponent(azdoLegacyMatch[1]),
      prId: parseInt(azdoLegacyMatch[2], 10),
    };
  }

  // URL não reconhecida
  throw new Error(
    `URL não reconhecida: "${url}".\n` +
    'Formatos suportados:\n' +
    '  - Azure DevOps: https://dev.azure.com/{org}/{project}/_git/{repo}/pullrequest/{id}\n' +
    '  - Git local: use --app-repo-path com --use-git-local'
  );
}

// ─────────────────────────────────────────────────────────────────────
// Dispatcher
// ─────────────────────────────────────────────────────────────────────

/**
 * Busca dados do PR usando o provedor adequado.
 * Implementa fallback automático para git-local se Azure DevOps falhar
 * e appRepoPath estiver disponível.
 */
export async function fetchPrData(input: PrInput): Promise<PrAnalysisResult> {
  if (input.provider === 'git-local') {
    if (!input.appRepoPath) {
      throw new Error('Para provider git-local, --app-repo-path é obrigatório.');
    }
    return getGitLocalChanges(input.appRepoPath, input.targetBranch);
  }

  if (input.provider === 'azure-devops') {
    return fetchFromAzureDevOps(input);
  }

  throw new Error(`Provider desconhecido: ${input.provider}`);
}

/**
 * Busca dados do PR via Azure DevOps REST API.
 * Se falhar e appRepoPath estiver disponível, faz fallback para git-local.
 */
async function fetchFromAzureDevOps(input: PrInput): Promise<PrAnalysisResult> {
  // Import dinâmico para não forçar dependência de config do Azure DevOps
  // quando usando apenas git-local
  const { default: AzureDevOpsClient } = await import('../../azure-devops/azure-devops.client');

  const client = new AzureDevOpsClient('RegressionAnalysis');
  const repoName = input.repoNameOrId!;
  const prId = input.prId!;

  try {
    // 1. Obter PR metadata
    const pr = await client.getPullRequest(repoName, prId);

    // 2. Obter iterações para pegar o diff completo
    const iterations = await client.getPullRequestIterations(repoName, prId);
    const lastIterationId = iterations.length > 0
      ? iterations[iterations.length - 1].id
      : 1;

    // 3. Obter arquivos alterados (da última iteração = diff completo)
    const changes = await client.getPullRequestChanges(repoName, prId, lastIterationId);

    // 4. Obter Work Items associados
    const workItemRefs = await client.getPullRequestWorkItems(repoName, prId);

    // 5. Enriquecer Work Items com dados básicos (título, prioridade)
    const workItems = await Promise.all(
      workItemRefs.map(async (ref) => {
        try {
          const wi = await client.getWorkItem(parseInt(ref.id), 'fields');
          return {
            id: ref.id,
            title: wi.fields?.['System.Title'] as string | undefined,
            priority: wi.fields?.['Microsoft.VSTS.Common.Priority'] as number | undefined,
          };
        } catch {
          return { id: ref.id };
        }
      })
    );

    return {
      pr: {
        id: pr.pullRequestId,
        title: pr.title,
        source: pr.sourceRefName.replace('refs/heads/', ''),
        target: pr.targetRefName.replace('refs/heads/', ''),
        author: pr.createdBy.displayName,
        date: pr.creationDate,
        provider: 'azure-devops',
      },
      files: changes
        .filter(c => c.item?.path && !c.item.path.endsWith('/'))
        .map(c => ({
          changeType: c.changeType,
          path: c.item.path,
        })),
      workItems,
    };
  } catch (error) {
    // Fallback para git-local se disponível
    if (input.appRepoPath) {
      console.warn(
        `⚠️  Azure DevOps falhou: ${error instanceof Error ? error.message : error}\n` +
        `   Fallback para Git local: ${input.appRepoPath}`
      );
      return getGitLocalChanges(input.appRepoPath, input.targetBranch);
    }
    throw error;
  }
}
