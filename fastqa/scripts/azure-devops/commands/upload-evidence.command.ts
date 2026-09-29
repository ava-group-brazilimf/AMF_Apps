/**
 * ============================================================================
 * FastQA — Upload de Evidências para Work Item
 * ============================================================================
 * Script para fazer upload de evidências (screenshots, vídeos) para um
 * work item do Azure DevOps.
 *
 * Uso:
 *   npx tsx upload-evidence.command.ts \
 *     --work-item-id 6 \
 *     --evidence-path "manual_test/evidence/TS-001" \
 *     --comment "Evidências da execução"
 * ============================================================================
 */

import * as path from 'path';
import * as fs from 'fs';
import { AzureDevOpsClient } from '../azure-devops.client';
import { config } from '../azure-devops.config';

function collectEvidenceFiles(evidencePath: string): string[] {
  const resolvedPath = path.resolve(evidencePath);

  if (!fs.existsSync(resolvedPath)) {
    console.warn(`⚠️  Caminho não encontrado: ${resolvedPath}`);
    return [];
  }

  const stat = fs.statSync(resolvedPath);

  if (stat.isFile()) {
    return [resolvedPath];
  }

  if (stat.isDirectory()) {
    const files = fs.readdirSync(resolvedPath);
    const allowedExts = config.allowedExtensions;
    const evidenceFiles = files
      .filter(f => {
        const ext = path.extname(f).toLowerCase();
        return allowedExts.includes(ext);
      })
      .map(f => path.join(resolvedPath, f));
    return evidenceFiles;
  }

  return [];
}

async function uploadEvidence(workItemId: number, evidencePath: string, comment?: string) {
  const client = new AzureDevOpsClient('UploadEvidence');

  console.log('\n📎 ═══════════════════════════════════════════════════════════════');
  console.log('   FastQA — Upload de Evidências para Azure DevOps');
  console.log('═══════════════════════════════════════════════════════════════\n');

  const evidenceFiles = collectEvidenceFiles(evidencePath);

  if (evidenceFiles.length === 0) {
    console.warn(`⚠️  Nenhum arquivo de evidência encontrado em: ${evidencePath}\n`);
    return;
  }

  console.log(`📂 Encontrados ${evidenceFiles.length} arquivo(s) de evidência:\n`);

  let uploadedCount = 0;
  let failedCount = 0;

  for (const filePath of evidenceFiles) {
    try {
      const fileName = path.basename(filePath);
      const fileSize = fs.statSync(filePath).size;
      const fileSizeMB = (fileSize / (1024 * 1024)).toFixed(2);

      console.log(`📤 Uploading: ${fileName} (${fileSizeMB} MB)...`);

      const attachment = await client.uploadAttachment(filePath, fileName);
      const attachmentComment = comment?.trim()
        ? `${comment.trim()} | ${fileName}`
        : `Evidência: ${fileName}`;
      await client.attachToWorkItem(workItemId, attachment.url, attachmentComment);

      console.log(`✅ Anexado com sucesso!\n`);
      uploadedCount++;
    } catch (error) {
      console.error(`❌ Erro ao anexar ${path.basename(filePath)}: ${error}\n`);
      failedCount++;
    }
  }

  if (comment?.trim() && uploadedCount > 0) {
    const discussionComment =
      `FastQA - Upload de evidências concluído. ` +
      `Comentário: ${comment.trim()}. Arquivos enviados: ${uploadedCount}/${evidenceFiles.length}.`;
    await client.addWorkItemDiscussionComment(workItemId, discussionComment);
  }

  const bugUrl = `${config.orgUrl}/${encodeURIComponent(config.project)}/_workitems/edit/${workItemId}`;

  console.log('═══════════════════════════════════════════════════════════════');
  console.log('✅ Upload de evidências concluído!');
  console.log('═══════════════════════════════════════════════════════════════\n');
  console.log(`   Work Item: #${workItemId}`);
  console.log(`   ✅ Sucesso: ${uploadedCount} arquivo(s)`);
  if (failedCount > 0) {
    console.log(`   ❌ Falhas: ${failedCount} arquivo(s)`);
  }
  console.log(`\n   🔗 ${bugUrl}\n`);
}

async function main() {
  const args = process.argv.slice(2);
  const getArg = (flag: string): string | undefined => {
    const index = args.indexOf(flag);
    return index >= 0 && index + 1 < args.length ? args[index + 1] : undefined;
  };

  const workItemId = getArg('--work-item-id');
  const evidencePath = getArg('--evidence-path');
  const comment = getArg('--comment');

  if (!workItemId || !evidencePath) {
    console.error('❌ Uso: npx tsx upload-evidence.command.ts --work-item-id <id> --evidence-path <path> [--comment <texto>]');
    process.exit(1);
  }

  try {
    await uploadEvidence(parseInt(workItemId, 10), evidencePath, comment);
    process.exit(0);
  } catch (error) {
    console.error('\n❌ Erro ao fazer upload de evidências:');
    console.error(error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

export { uploadEvidence };
