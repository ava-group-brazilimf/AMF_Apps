/**
 * ============================================================================
 * FastQA — Upload de Pasta de Evidências para Work Item
 * ============================================================================
 * Script para fazer upload de todos os arquivos válidos de uma pasta e
 * anexar ao Work Item informado no Azure DevOps.
 *
 * Uso:
 *   npx tsx upload-folder-evidence.command.ts \
 *     --work-item-id 6 \
 *     --folder-path "manual_test/evidence/TS-001" \
 *     --comment "Evidências da execução manual"
 * ============================================================================
 */

import * as path from 'path';
import * as fs from 'fs';
import { AzureDevOpsClient } from '../azure-devops.client';
import { config } from '../azure-devops.config';

// ─────────────────────────────────────────────────────────────────────
// Utilitários
// ─────────────────────────────────────────────────────────────────────

function collectFolderFiles(
  folderPath: string,
  recursive: boolean = true,
  extensionsFilter?: string[]
): string[] {
  const resolved = path.resolve(folderPath);

  if (!fs.existsSync(resolved)) {
    throw new Error(`Pasta não encontrada: ${resolved}`);
  }

  if (!fs.statSync(resolved).isDirectory()) {
    throw new Error(`Caminho não é um diretório: ${resolved}`);
  }

  const allowedExts = extensionsFilter || config.allowedExtensions;
  const results: string[] = [];

  function walk(dir: string) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isFile()) {
        const ext = path.extname(entry.name).toLowerCase();
        if (allowedExts.includes(ext)) {
          results.push(fullPath);
        }
      } else if (entry.isDirectory() && recursive) {
        walk(fullPath);
      }
    }
  }

  walk(resolved);
  return results.sort();
}

async function uploadFolderEvidence(params: {
  workItemId: number;
  folderPath: string;
  comment?: string;
  recursive?: boolean;
  extensions?: string[];
}) {
  const client = new AzureDevOpsClient('UploadFolderEvidenceWorkItem');

  console.log('\n📁 ═══════════════════════════════════════════════════════════════');
  console.log('   FastQA — Upload de Pasta para Work Item');
  console.log('═══════════════════════════════════════════════════════════════\n');

  console.log(`   Work Item ID:  ${params.workItemId}`);
  console.log(`   Pasta:         ${params.folderPath}`);
  console.log(`   Recursivo:     ${params.recursive !== false ? 'Sim' : 'Não'}`);
  console.log('');

  // ── 1. Coletar arquivos ───────────────────────────────────────────

  const files = collectFolderFiles(
    params.folderPath,
    params.recursive !== false,
    params.extensions
  );

  if (files.length === 0) {
    console.error('❌ Nenhum arquivo válido encontrado na pasta.');
    console.error(`   Extensões permitidas: ${config.allowedExtensions.join(', ')}`);
    process.exit(1);
  }

  let totalSize = 0;
  console.log(`📂 ${files.length} arquivo(s) encontrados:\n`);
  for (const f of files) {
    const size = fs.statSync(f).size;
    totalSize += size;
    const sizeMB = (size / (1024 * 1024)).toFixed(2);
    console.log(`   📄 ${path.basename(f)} (${sizeMB} MB)`);
  }
  const totalMB = (totalSize / (1024 * 1024)).toFixed(2);
  console.log(`\n   Total: ${totalMB} MB\n`);

  // ── 2. Anexar ao Work Item ────────────────────────────────────────

  console.log(`🔄 Anexando evidências ao Work Item #${params.workItemId}...\n`);

  const baseComment = params.comment?.trim();
  let uploadedCount = 0;
  let failedCount = 0;

  for (const filePath of files) {
    try {
      const fileName = path.basename(filePath);
      const attachment = await client.uploadAttachment(filePath, fileName);
      const attachmentComment = baseComment
        ? `${baseComment} | ${fileName}`
        : `Evidência: ${fileName}`;

      await client.attachToWorkItem(
        params.workItemId,
        attachment.url,
        attachmentComment
      );
      console.log(`   ✅ ${fileName}`);
      uploadedCount++;
    } catch (error) {
      console.error(`   ❌ ${path.basename(filePath)}: ${error}`);
      failedCount++;
    }
  }

  if (baseComment && uploadedCount > 0) {
    const discussionComment =
      `FastQA - Upload de pasta de evidências concluído. ` +
      `Comentário: ${baseComment}. Arquivos enviados: ${uploadedCount}/${files.length}.`;
    await client.addWorkItemDiscussionComment(params.workItemId, discussionComment);
  }

  // ── 3. Resumo ─────────────────────────────────────────────────────

  const workItemUrl = `${config.orgUrl}/${encodeURIComponent(config.project)}/_workitems/edit/${params.workItemId}`;

  console.log('\n═══════════════════════════════════════════════════════════════');
  console.log('✅ Upload de pasta para Work Item concluído!');
  console.log('═══════════════════════════════════════════════════════════════\n');
  console.log(`   Work Item:    #${params.workItemId}`);
  console.log(`   Arquivos:     ${uploadedCount}/${files.length} enviados`);
  if (failedCount > 0) {
    console.log(`   Falhas:       ${failedCount}`);
  }
  console.log(`   Tamanho:      ${totalMB} MB`);
  console.log(`\n   🔗 ${workItemUrl}\n`);

  // ── 4. Log ────────────────────────────────────────────────────────

  const logsDir = config.logsDir;
  if (!fs.existsSync(logsDir)) {
    fs.mkdirSync(logsDir, { recursive: true });
  }
  const logPath = path.join(logsDir, `folder-evidence-work-item-${params.workItemId}-${Date.now()}.json`);
  fs.writeFileSync(logPath, JSON.stringify({
    timestamp: new Date().toISOString(),
    command: 'upload-folder-evidence',
    workItemId: params.workItemId,
    totalFiles: files.length,
    uploadedFiles: uploadedCount,
    failedFiles: failedCount,
    totalSizeMB: totalMB,
    files: files.map(f => path.basename(f)),
  }, null, 2), 'utf-8');
  console.log(`   📝 Log: ${logPath}\n`);
}

// ─────────────────────────────────────────────────────────────────────
// CLI
// ─────────────────────────────────────────────────────────────────────

async function main() {
  const args = process.argv.slice(2);
  const getArg = (flag: string): string | undefined => {
    const index = args.indexOf(flag);
    return index >= 0 && index + 1 < args.length ? args[index + 1] : undefined;
  };

  const workItemId = getArg('--work-item-id');
  const folderPath = getArg('--folder-path');
  const comment = getArg('--comment');
  const recursive = getArg('--recursive');
  const extensions = getArg('--extensions');

  if (!workItemId || !folderPath) {
    console.error('\n❌ Parâmetros obrigatórios faltando.\n');
    console.error('Uso:');
    console.error('  npx tsx upload-folder-evidence.command.ts \\');
    console.error('    --work-item-id <id> \\');
    console.error('    --folder-path <caminho>\n');
    console.error('Opcionais:');
    console.error('    --comment <texto>');
    console.error('    --recursive <true|false>');
    console.error('    --extensions ".png,.mp4,.pdf"\n');
    process.exit(1);
  }

  try {
    await uploadFolderEvidence({
      workItemId: parseInt(workItemId, 10),
      folderPath,
      comment,
      recursive: recursive !== 'false',
      extensions: extensions ? extensions.split(',').map(e => e.trim()) : undefined,
    });

    process.exit(0);
  } catch (error) {
    console.error('\n❌ Erro:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

export { uploadFolderEvidence, collectFolderFiles };
