#!/usr/bin/env npx tsx
// ==========================================================================
// FastQA — Comando #21: Criar Pipeline no Azure DevOps
// ==========================================================================
//
// Cria uma definição de pipeline (build definition) no Azure DevOps
// apontando para um arquivo YAML em um repositório existente.
//
// Uso:
//   npx tsx fastqa/scripts/azure-devops/commands/create-pipeline.command.ts \
//     --name "FastQA CI - Playwright" \
//     --repo "meu-repo-automacao" \
//     --yaml-path "azure-pipelines.yml" \
//     [--branch main] \
//     [--folder "\\FastQA"] \
//     [--dry-run]
//
// ==========================================================================

import { withClient } from '../azure-devops.client';
import { Logger } from '../utils/logger.util';

// ---------------------------------------------------------------------------
// CLI Parsing
// ---------------------------------------------------------------------------

interface CreatePipelineArgs {
  name: string;
  repo: string;
  yamlPath: string;
  branch: string;
  folder: string;
  dryRun: boolean;
}

function parseArgs(): CreatePipelineArgs {
  const args = process.argv.slice(2);
  const parsed: CreatePipelineArgs = {
    name: '',
    repo: '',
    yamlPath: 'azure-pipelines.yml',
    branch: 'main',
    folder: '\\',
    dryRun: false,
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--name': parsed.name = args[++i]; break;
      case '--repo': parsed.repo = args[++i]; break;
      case '--yaml-path': parsed.yamlPath = args[++i]; break;
      case '--branch': parsed.branch = args[++i]; break;
      case '--folder': parsed.folder = args[++i]; break;
      case '--dry-run': parsed.dryRun = true; break;
    }
  }

  if (!parsed.name) {
    console.error('❌ Parâmetro --name é obrigatório');
    process.exit(1);
  }
  if (!parsed.repo) {
    console.error('❌ Parâmetro --repo é obrigatório');
    process.exit(1);
  }

  return parsed;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const args = parseArgs();
  const logger = new Logger('create-pipeline');

  logger.info('═══════════════════════════════════════════════════════════');
  logger.info('FastQA — Criar Pipeline no Azure DevOps');
  logger.info('═══════════════════════════════════════════════════════════');
  logger.info(`Nome:        ${args.name}`);
  logger.info(`Repositório: ${args.repo}`);
  logger.info(`YAML Path:   ${args.yamlPath}`);
  logger.info(`Branch:      ${args.branch}`);
  logger.info(`Folder:      ${args.folder}`);

  if (args.dryRun) {
    logger.warn('🔍 Modo DRY-RUN — nenhuma alteração será feita');
    logger.info('\n📋 Pipeline que seria criada:');
    logger.info(`  Nome: "${args.name}"`);
    logger.info(`  Repositório: "${args.repo}"`);
    logger.info(`  YAML: "${args.yamlPath}"`);
    logger.info(`  Branch padrão: "${args.branch}"`);
    logger.success('✅ Dry-run concluído');
    return;
  }

  await withClient(async (client) => {
    // Step 1: Resolver repositório
    logger.info('\n🔍 Step 1: Resolvendo repositório...');
    const repo = await client.getRepository(args.repo);
    logger.success(`  ✅ Repositório encontrado: ${repo.name} (${repo.id})`);

    // Step 2: Criar pipeline definition
    logger.info('\n📝 Step 2: Criando pipeline definition...');
    const definition = await client.createPipelineDefinition({
      name: args.name,
      repoId: repo.id,
      yamlPath: args.yamlPath,
      branchName: args.branch,
      folder: args.folder,
    });

    // Step 3: Relatório final
    logger.info('\n═══════════════════════════════════════════════════════════');
    logger.success('📊 RELATÓRIO FINAL');
    logger.info('═══════════════════════════════════════════════════════════');
    logger.info(`Pipeline ID:     ${definition.id}`);
    logger.info(`Pipeline Nome:   ${definition.name}`);
    logger.info(`Folder:          ${definition.path}`);
    logger.info(`Repositório:     ${repo.name}`);
    logger.info(`YAML:            ${args.yamlPath}`);
    logger.info(`Branch padrão:   ${args.branch}`);
    if (definition.url) logger.info(`URL:             ${definition.url}`);
    logger.success('✅ Pipeline criada com sucesso');
    logger.info('═══════════════════════════════════════════════════════════');
  }, 'create-pipeline');
}

main().catch((err) => {
  console.error('❌ Erro fatal:', err.message || err);
  process.exit(1);
});
