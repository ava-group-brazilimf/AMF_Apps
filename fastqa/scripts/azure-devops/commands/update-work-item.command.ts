/**
 * ============================================================================
 * FastQA — Atualizar Work Item no Azure DevOps
 * ============================================================================
 * Script para atualizar campos de um work item existente.
 *
 * Uso:
 *   npx tsx update-work-item.command.ts \
 *     --id 6 \
 *     --field "Microsoft.VSTS.Common.Severity" \
 *     --value "2 - High"
 * ============================================================================
 */

import { AzureDevOpsClient } from '../azure-devops.client';
import { config } from '../azure-devops.config';
import type { JsonPatchOperation } from '../types/azure-devops.types';

async function updateWorkItem(id: number, field: string, value: any) {
  const client = new AzureDevOpsClient('UpdateWorkItem');

  console.log(`\n📝 Atualizando work item #${id}...`);
  console.log(`   Campo: ${field}`);
  console.log(`   Valor: ${value}\n`);

  const operations: JsonPatchOperation[] = [
    { op: 'add', path: `/fields/${field}`, value }
  ];

  const result = await client.updateWorkItem(id, operations);
  const bugUrl = `${config.orgUrl}/${encodeURIComponent(config.project)}/_workitems/edit/${id}`;

  console.log(`✅ Work item #${id} atualizado com sucesso!`);
  console.log(`🔗 ${bugUrl}\n`);

  return result;
}

async function main() {
  const args = process.argv.slice(2);
  const getArg = (flag: string): string | undefined => {
    const index = args.indexOf(flag);
    return index >= 0 && index + 1 < args.length ? args[index + 1] : undefined;
  };

  const id = getArg('--id');
  const field = getArg('--field');
  const value = getArg('--value');

  if (!id || !field || !value) {
    console.error('❌ Uso: npx tsx update-work-item.command.ts --id <id> --field <field> --value <value>');
    process.exit(1);
  }

  try {
    await updateWorkItem(parseInt(id), field, value);
    process.exit(0);
  } catch (error) {
    console.error('\n❌ Erro ao atualizar work item:');
    console.error(error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

export { updateWorkItem };
