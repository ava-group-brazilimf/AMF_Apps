#!/usr/bin/env npx tsx
// ==========================================================================
// FastQA — Comando #22: Executar Pipeline no Azure DevOps
// ==========================================================================
//
// Dispara uma pipeline run e opcionalmente aguarda sua conclusão com polling.
//
// Uso:
//   npx tsx fastqa/scripts/azure-devops/commands/run-pipeline.command.ts \
//     --pipeline-id 15 \
//     [--branch main] \
//     [--variables "KEY1=VALUE1,KEY2=VALUE2"] \
//     [--wait] \
//     [--timeout 600000] \
//     [--poll-interval 15000]
//
// ==========================================================================

import { withClient } from '../azure-devops.client';
import { Logger } from '../utils/logger.util';
import type { PipelineRun, Build } from '../types/azure-devops.types';

// ---------------------------------------------------------------------------
// CLI Parsing
// ---------------------------------------------------------------------------

interface RunPipelineArgs {
  pipelineId: number;
  branch?: string;
  variables: Record<string, { value: string; isSecret?: boolean }>;
  wait: boolean;
  timeoutMs: number;
  pollIntervalMs: number;
}

function parseArgs(): RunPipelineArgs {
  const args = process.argv.slice(2);
  const parsed: RunPipelineArgs = {
    pipelineId: 0,
    variables: {},
    wait: false,
    timeoutMs: 600_000,
    pollIntervalMs: 15_000,
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--pipeline-id': parsed.pipelineId = parseInt(args[++i], 10); break;
      case '--branch': parsed.branch = args[++i]; break;
      case '--variables': {
        const pairs = args[++i].split(',');
        for (const pair of pairs) {
          const eqIdx = pair.indexOf('=');
          if (eqIdx > 0) {
            const key = pair.substring(0, eqIdx).trim();
            const value = pair.substring(eqIdx + 1).trim();
            parsed.variables[key] = { value };
          }
        }
        break;
      }
      case '--wait': parsed.wait = true; break;
      case '--timeout': parsed.timeoutMs = parseInt(args[++i], 10); break;
      case '--poll-interval': parsed.pollIntervalMs = parseInt(args[++i], 10); break;
    }
  }

  if (!parsed.pipelineId) {
    console.error('❌ Parâmetro --pipeline-id é obrigatório');
    process.exit(1);
  }

  return parsed;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const remainingSecs = seconds % 60;
  if (minutes > 0) return `${minutes}m ${remainingSecs}s`;
  return `${seconds}s`;
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const args = parseArgs();
  const logger = new Logger('run-pipeline');

  logger.info('═══════════════════════════════════════════════════════════');
  logger.info('FastQA — Executar Pipeline no Azure DevOps');
  logger.info('═══════════════════════════════════════════════════════════');
  logger.info(`Pipeline ID:    ${args.pipelineId}`);
  if (args.branch) logger.info(`Branch:         ${args.branch}`);
  const varKeys = Object.keys(args.variables);
  if (varKeys.length) logger.info(`Variáveis:      ${varKeys.join(', ')}`);
  if (args.wait) logger.info(`Modo:           Aguardar conclusão (timeout: ${formatDuration(args.timeoutMs)})`);

  await withClient(async (client) => {
    // Step 1: Disparar pipeline
    logger.info('\n🚀 Step 1: Disparando pipeline...');
    const run: PipelineRun = await client.runPipeline(args.pipelineId, {
      branchName: args.branch,
      variables: varKeys.length ? args.variables : undefined,
    });
    logger.success(`✅ Pipeline Run disparada: #${run.id}`);
    logger.info(`  Estado: ${run.state}`);
    logger.info(`  URL: ${run.url}`);

    // Step 2: Aguardar conclusão (se --wait)
    if (args.wait) {
      logger.info('\n⏳ Step 2: Aguardando conclusão da pipeline...');
      const startTime = Date.now();

      // Extract build ID from the pipeline run
      // Pipeline runs and builds share the same ID in Azure DevOps
      const buildId = run.id;

      let lastStatus = '';
      while (true) {
        const elapsed = Date.now() - startTime;
        if (elapsed > args.timeoutMs) {
          logger.error(`⏱️ Timeout atingido (${formatDuration(args.timeoutMs)}). Pipeline ainda em execução.`);
          logger.info(`Verifique manualmente: Build #${buildId}`);
          process.exit(2);
        }

        const build: Build = await client.getBuild(buildId);

        if (build.status !== lastStatus) {
          lastStatus = build.status;
          logger.info(`  ⏳ Build #${buildId} — status: ${build.status} (${formatDuration(elapsed)})`);
        }

        if (build.status === 'completed') {
          logger.info('');
          const resultIcon = build.result === 'succeeded' ? '✅' : build.result === 'failed' ? '❌' : '⚠️';
          logger.info(`${resultIcon} Pipeline concluída: ${build.result}`);

          // Step 3: Relatório final
          logger.info('\n═══════════════════════════════════════════════════════════');
          logger.success('📊 RELATÓRIO FINAL');
          logger.info('═══════════════════════════════════════════════════════════');
          logger.info(`Pipeline ID:     ${args.pipelineId}`);
          logger.info(`Build ID:        ${build.id}`);
          logger.info(`Build Number:    ${build.buildNumber}`);
          logger.info(`Resultado:       ${build.result}`);
          logger.info(`Branch:          ${build.sourceBranch}`);
          logger.info(`Duração:         ${formatDuration(elapsed)}`);
          if (build.startTime) logger.info(`Início:          ${build.startTime}`);
          if (build.finishTime) logger.info(`Fim:             ${build.finishTime}`);
          logger.info('═══════════════════════════════════════════════════════════');

          if (build.result === 'failed') {
            process.exit(2);
          }
          return;
        }

        await sleep(args.pollIntervalMs);
      }
    } else {
      // Sem --wait: apenas reportar o disparo
      logger.info('\n═══════════════════════════════════════════════════════════');
      logger.success('📊 RELATÓRIO FINAL');
      logger.info('═══════════════════════════════════════════════════════════');
      logger.info(`Pipeline ID:     ${args.pipelineId}`);
      logger.info(`Run ID:          ${run.id}`);
      logger.info(`Estado:          ${run.state}`);
      logger.info('');
      logger.info('💡 Para aguardar a conclusão, use: --wait');
      logger.info(`💡 Para sincronizar resultados: npx tsx sync-pipeline-results.command.ts --build-id ${run.id} --test-plan-id <ID> --test-suite-id <ID>`);
      logger.info('═══════════════════════════════════════════════════════════');
    }
  }, 'run-pipeline');
}

main().catch((err) => {
  console.error('❌ Erro fatal:', err.message || err);
  process.exit(1);
});
