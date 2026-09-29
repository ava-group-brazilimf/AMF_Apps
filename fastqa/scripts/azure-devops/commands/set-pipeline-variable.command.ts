#!/usr/bin/env npx tsx
// ==========================================================================
// FastQA — Comando #23: Criar/Atualizar Variáveis de Pipeline
// ==========================================================================
//
// Cria ou atualiza um Variable Group no Azure DevOps e opcionalmente
// autoriza uma pipeline a utilizá-lo.
//
// Uso:
//   npx tsx fastqa/scripts/azure-devops/commands/set-pipeline-variable.command.ts \
//     --group-name "FastQA Variables" \
//     --variables "AZURE_DEVOPS_PAT=token123,BASE_URL=http://app.com" \
//     [--secret-vars "AZURE_DEVOPS_PAT"] \
//     [--pipeline-id 15] \
//     [--description "Variáveis do projeto FastQA"] \
//     [--update]
//
// ==========================================================================

import { withClient } from '../azure-devops.client';
import { Logger } from '../utils/logger.util';
import type { PipelineVariable, VariableGroup } from '../types/azure-devops.types';

// ---------------------------------------------------------------------------
// CLI Parsing
// ---------------------------------------------------------------------------

interface SetPipelineVariableArgs {
  groupName: string;
  variables: Record<string, PipelineVariable>;
  pipelineId?: number;
  description?: string;
  update: boolean;
}

function parseArgs(): SetPipelineVariableArgs {
  const args = process.argv.slice(2);
  const parsed: SetPipelineVariableArgs = {
    groupName: '',
    variables: {},
    update: false,
  };

  let secretVarNames: string[] = [];

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--group-name': parsed.groupName = args[++i]; break;
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
      case '--secret-vars': secretVarNames = args[++i].split(',').map(s => s.trim()); break;
      case '--pipeline-id': parsed.pipelineId = parseInt(args[++i], 10); break;
      case '--description': parsed.description = args[++i]; break;
      case '--update': parsed.update = true; break;
    }
  }

  // Marcar variáveis secretas
  for (const name of secretVarNames) {
    if (parsed.variables[name]) {
      parsed.variables[name].isSecret = true;
    }
  }

  if (!parsed.groupName) {
    console.error('❌ Parâmetro --group-name é obrigatório');
    process.exit(1);
  }
  if (!Object.keys(parsed.variables).length) {
    console.error('❌ Parâmetro --variables é obrigatório (formato: "KEY1=VALUE1,KEY2=VALUE2")');
    process.exit(1);
  }

  return parsed;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const args = parseArgs();
  const logger = new Logger('set-pipeline-variable');

  logger.info('═══════════════════════════════════════════════════════════');
  logger.info('FastQA — Criar/Atualizar Variáveis de Pipeline');
  logger.info('═══════════════════════════════════════════════════════════');
  logger.info(`Variable Group: ${args.groupName}`);
  logger.info(`Variáveis:`);
  for (const [key, val] of Object.entries(args.variables)) {
    logger.info(`  • ${key} = ${val.isSecret ? '********' : val.value}`);
  }
  if (args.pipelineId) logger.info(`Pipeline ID:    ${args.pipelineId}`);
  if (args.update) logger.info(`Modo:           Atualizar se existir`);

  await withClient(async (client) => {
    let group: VariableGroup | undefined;

    // Step 1: Verificar se já existe
    logger.info('\n🔍 Step 1: Verificando Variable Groups existentes...');
    const existing = await client.getVariableGroups(args.groupName);
    const found = existing.value?.find(g => g.name === args.groupName);

    if (found && args.update) {
      // Step 2a: Atualizar existente
      logger.info(`  📦 Variable Group "${args.groupName}" encontrado (#${found.id}). Atualizando...`);

      // Merge: novas variáveis sobrescrevem, existentes são mantidas
      const mergedVars = { ...found.variables, ...args.variables };

      group = await client.updateVariableGroup(found.id, found, {
        variables: mergedVars,
        description: args.description,
      });
      logger.success(`  ✅ Variable Group atualizado: #${group.id}`);
    } else if (found && !args.update) {
      logger.warn(`  ⚠️ Variable Group "${args.groupName}" já existe (#${found.id}).`);
      logger.warn('  Use --update para atualizar as variáveis existentes.');
      process.exit(1);
    } else {
      // Step 2b: Criar novo
      logger.info('  📦 Variable Group não encontrado. Criando...');
      group = await client.createVariableGroup({
        name: args.groupName,
        description: args.description || `FastQA Variable Group — criado em ${new Date().toISOString()}`,
        variables: args.variables,
      });
      logger.success(`  ✅ Variable Group criado: #${group.id}`);
    }

    // Step 3: Autorizar pipeline (se informado)
    if (args.pipelineId && group) {
      logger.info(`\n🔗 Step 3: Autorizando Pipeline #${args.pipelineId}...`);
      await client.authorizePipelineForVariableGroup(group.id, args.pipelineId);
      logger.success(`  ✅ Pipeline #${args.pipelineId} autorizada para Variable Group #${group.id}`);
    }

    // Step 4: Relatório final
    logger.info('\n═══════════════════════════════════════════════════════════');
    logger.success('📊 RELATÓRIO FINAL');
    logger.info('═══════════════════════════════════════════════════════════');
    if (group) {
      logger.info(`Variable Group ID:   ${group.id}`);
      logger.info(`Variable Group Nome: ${group.name}`);
      logger.info(`Variáveis:`);
      for (const [key, val] of Object.entries(group.variables || args.variables)) {
        logger.info(`  • ${key} = ${val.isSecret ? '******** (secret)' : val.value}`);
      }
      if (args.pipelineId) logger.info(`Pipeline autorizada: #${args.pipelineId}`);
    }
    logger.info('');
    logger.warn('⚠️ Nota: Variáveis secret não podem ser lidas de volta após criação.');
    logger.success('✅ Operação concluída com sucesso');
    logger.info('═══════════════════════════════════════════════════════════');
  }, 'set-pipeline-variable');
}

main().catch((err) => {
  console.error('❌ Erro fatal:', err.message || err);
  process.exit(1);
});
