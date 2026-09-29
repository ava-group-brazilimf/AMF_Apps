/**
 * ============================================================================
 * FastQA — Criar Bug no Azure DevOps
 * ============================================================================
 * Script para criação de bugs com campos especializados QA:
 * - Passos de reprodução estruturados
 * - Resultado esperado vs obtido
 * - Severidade e prioridade
 * - Upload automático de evidências
 * - Vínculo com work items relacionados
 *
 * Uso:
 *   npx tsx create-bug.command.ts \
 *     --title "Erro no login" \
 *     --repro-steps "1. Acessar /login\n2. Preencher credenciais" \
 *     --expected "Login com sucesso" \
 *     --actual "Erro 500" \
 *     --severity "2 - High" \
 *     --evidence-path "manual_test/evidence/TS-001"
 * ============================================================================
 */

import * as path from 'path';
import * as fs from 'fs';
import { AzureDevOpsClient } from '../azure-devops.client';
import { config } from '../azure-devops.config';
import type { JsonPatchOperation, WorkItem } from '../types/azure-devops.types';

// ═══════════════════════════════════════════════════════════════════════════
// Interface de Parâmetros
// ═══════════════════════════════════════════════════════════════════════════

interface CreateBugParams {
  title: string;
  reproSteps: string;
  expected: string;
  actual: string;
  severity: '1 - Critical' | '2 - High' | '3 - Medium' | '4 - Low';
  priority?: '1' | '2' | '3' | '4';
  evidencePath?: string;
  parentId?: number;
  tags?: string;
  areaPath?: string;
  iterationPath?: string;
  systemInfo?: string;
  assignedTo?: string;
}

// ═══════════════════════════════════════════════════════════════════════════
// Funções Auxiliares
// ═══════════════════════════════════════════════════════════════════════════

/** Formata passos de reprodução em HTML estruturado */
function formatReproSteps(steps: string, expected: string, actual: string, systemInfo?: string): string {
  // Dividir steps por quebra de linha e criar lista numerada
  const stepLines = steps.split('\n').filter(s => s.trim() !== '');
  const stepsHtml = stepLines
    .map((step, index) => {
      // Remover numeração existente se houver
      const cleanStep = step.replace(/^(Step )?\d+[.:)\s]+/i, '').trim();
      return `  <li>${cleanStep}</li>`;
    })
    .join('\n');

  return `
<div style="font-family: Segoe UI, Tahoma, Geneva, Verdana, sans-serif;">
  <h3 style="color: #0078d4;">🔄 Passos de Reprodução</h3>
  <ol style="line-height: 1.6;">
${stepsHtml}
  </ol>

  <h3 style="color: #107c10; margin-top: 20px;">✅ Resultado Esperado</h3>
  <p style="padding: 10px; background-color: #f0f9f0; border-left: 4px solid #107c10;">
    ${expected}
  </p>

  <h3 style="color: #d13438; margin-top: 20px;">❌ Resultado Obtido</h3>
  <p style="padding: 10px; background-color: #fff4f4; border-left: 4px solid #d13438;">
    ${actual}
  </p>

  ${systemInfo ? `
  <h3 style="color: #505050; margin-top: 20px;">🖥️ Informações do Sistema</h3>
  <p style="padding: 10px; background-color: #f5f5f5; border-left: 4px solid #505050;">
    ${systemInfo}
  </p>
  ` : ''}
</div>
`.trim();
}

/** Coleta arquivos de evidência de uma pasta ou arquivo */
function collectEvidenceFiles(evidencePath: string): string[] {
  console.log(`🔍 [DEBUG] Caminho original recebido: "${evidencePath}"`);
  
  // Normalizar path do Windows (converter barras)
  const normalizedPath = evidencePath.replace(/\\/g, '/');
  console.log(`🔍 [DEBUG] Caminho normalizado: "${normalizedPath}"`);
  
  const resolvedPath = path.resolve(normalizedPath);
  console.log(`🔍 [DEBUG] Caminho resolvido: "${resolvedPath}"`);

  if (!fs.existsSync(resolvedPath)) {
    console.warn(`⚠️  Caminho de evidência não encontrado: ${resolvedPath}`);
    return [];
  }

  const stat = fs.statSync(resolvedPath);
  console.log(`🔍 [DEBUG] Tipo: ${stat.isFile() ? 'arquivo' : stat.isDirectory() ? 'diretório' : 'outro'}`);

  if (stat.isFile()) {
    console.log(`🔍 [DEBUG] Retornando arquivo único`);
    return [resolvedPath];
  }

  if (stat.isDirectory()) {
    const files = fs.readdirSync(resolvedPath);
    console.log(`🔍 [DEBUG] Arquivos na pasta: ${files.join(', ')}`);
    
    const allowedExts = config.allowedExtensions;
    const evidenceFiles = files
      .filter(f => {
        const ext = path.extname(f).toLowerCase();
        const isAllowed = allowedExts.includes(ext);
        console.log(`🔍 [DEBUG]   ${f} (${ext}) -> ${isAllowed ? '✅' : '❌'}`);
        return isAllowed;
      })
      .map(f => path.join(resolvedPath, f));
    
    console.log(`🔍 [DEBUG] Total de arquivos filtrados: ${evidenceFiles.length}`);
    return evidenceFiles;
  }

  return [];
}

// ═══════════════════════════════════════════════════════════════════════════
// Função Principal de Criação de Bug
// ═══════════════════════════════════════════════════════════════════════════

async function createBug(params: CreateBugParams): Promise<WorkItem> {
  const client = new AzureDevOpsClient('CreateBug');

  console.log('\n🐛 ═══════════════════════════════════════════════════════════════');
  console.log('   FastQA — Criação de Bug no Azure DevOps');
  console.log('═══════════════════════════════════════════════════════════════\n');

  // ─────────────────────────────────────────────────────────────────────────
  // Preparar campos do bug
  // ─────────────────────────────────────────────────────────────────────────

  const reproStepsHtml = formatReproSteps(
    params.reproSteps,
    params.expected,
    params.actual,
    params.systemInfo
  );

  const priority = params.priority || params.severity.charAt(0); // Usar primeiro dígito da severidade

  const operations: JsonPatchOperation[] = [
    { op: 'add', path: '/fields/System.Title', value: params.title },
    { op: 'add', path: '/fields/Microsoft.VSTS.TCM.ReproSteps', value: reproStepsHtml },
    { op: 'add', path: '/fields/Microsoft.VSTS.Common.Severity', value: params.severity },
    { op: 'add', path: '/fields/Microsoft.VSTS.Common.Priority', value: parseInt(priority) },
  ];

  if (params.areaPath) {
    operations.push({ op: 'add', path: '/fields/System.AreaPath', value: params.areaPath });
  }

  if (params.iterationPath) {
    operations.push({ op: 'add', path: '/fields/System.IterationPath', value: params.iterationPath });
  }

  if (params.systemInfo) {
    operations.push({ op: 'add', path: '/fields/Microsoft.VSTS.TCM.SystemInfo', value: params.systemInfo });
  }

  if (params.assignedTo) {
    operations.push({ op: 'add', path: '/fields/System.AssignedTo', value: params.assignedTo });
  }

  if (params.tags) {
    operations.push({ op: 'add', path: '/fields/System.Tags', value: params.tags });
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Criar o bug
  // ─────────────────────────────────────────────────────────────────────────

  console.log(`📝 Criando bug: "${params.title}"\n`);
  console.log(`   Severidade: ${params.severity}`);
  console.log(`   Prioridade: ${priority}`);
  if (params.tags) console.log(`   Tags: ${params.tags}`);
  console.log('');

  const bug = await client.createWorkItem('Bug', operations);
  const bugId = bug.id!;
  const bugUrl = `${config.orgUrl}/${encodeURIComponent(config.project)}/_workitems/edit/${bugId}`;

  console.log(`✅ Bug #${bugId} criado com sucesso!\n`);
  console.log(`🔗 URL: ${bugUrl}\n`);

  // ─────────────────────────────────────────────────────────────────────────
  // Upload de evidências
  // ─────────────────────────────────────────────────────────────────────────

  let evidenceFiles: string[] = [];
  let uploadedCount = 0;
  let failedCount = 0;
  
  if (params.evidencePath) {
    try {
      console.log('\n📎 ═══════════════════════════════════════════════════════════════');
      console.log('   Processando Evidências');
      console.log('═══════════════════════════════════════════════════════════════\n');
      
      evidenceFiles = collectEvidenceFiles(params.evidencePath);

      if (evidenceFiles.length === 0) {
        console.warn(`⚠️  Nenhum arquivo de evidência encontrado em: ${params.evidencePath}\n`);
      } else {
        console.log(`\n📂 Encontrados ${evidenceFiles.length} arquivo(s) de evidência:\n`);

        for (const filePath of evidenceFiles) {
          try {
            const fileName = path.basename(filePath);
            const fileSize = fs.statSync(filePath).size;
            const fileSizeMB = (fileSize / (1024 * 1024)).toFixed(2);
            
            console.log(`📤 Uploading: ${fileName} (${fileSizeMB} MB)...`);

            const attachment = await client.uploadAttachment(filePath, fileName);
            console.log(`   ⏳ Attachment URL: ${attachment.url}`);
            
            await client.attachToWorkItem(bugId, attachment.url, `Evidência: ${fileName}`);

            console.log(`   ✅ Anexado com sucesso!\n`);
            uploadedCount++;
          } catch (error) {
            console.error(`   ❌ Erro ao anexar ${path.basename(filePath)}:`);
            console.error(`      ${error}\n`);
            failedCount++;
          }
        }

        console.log('═══════════════════════════════════════════════════════════════');
        console.log(`✅ Upload concluído: ${uploadedCount} sucesso | ${failedCount} falhas`);
        console.log('═══════════════════════════════════════════════════════════════\n');
      }
    } catch (error) {
      console.error(`\n❌ Erro ao processar evidências: ${error}\n`);
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Vincular ao work item pai
  // ─────────────────────────────────────────────────────────────────────────

  if (params.parentId) {
    console.log(`🔗 Vinculando Bug #${bugId} ao work item #${params.parentId}...\n`);
    try {
      await client.linkWorkItems(bugId, params.parentId, 'Child');
      console.log(`✅ Bug vinculado ao work item #${params.parentId}\n`);
    } catch (error) {
      console.error(`❌ Erro ao vincular: ${error}\n`);
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Resumo final
  // ─────────────────────────────────────────────────────────────────────────

  console.log('\n═══════════════════════════════════════════════════════════════');
  console.log('✅ RESUMO FINAL');
  console.log('═══════════════════════════════════════════════════════════════\n');
  console.log(`   📋 Bug ID: #${bugId}`);
  console.log(`   📝 Título: ${params.title}`);
  console.log(`   ⚠️  Severidade: ${params.severity}`);
  console.log(`   📊 Prioridade: ${priority}`);
  if (params.evidencePath) {
    if (uploadedCount > 0 || failedCount > 0) {
      console.log(`   📎 Evidências: ${uploadedCount} anexadas | ${failedCount} falhas`);
    } else {
      console.log(`   📎 Evidências: Nenhuma encontrada`);
    }
  }
  if (params.parentId) {
    console.log(`   🔗 Vinculado a: #${params.parentId}`);
  }
  console.log(`\n   🌐 Ver no Azure DevOps: ${bugUrl}\n`);

  return bug;
}

// ═══════════════════════════════════════════════════════════════════════════
// CLI Entry Point
// ═══════════════════════════════════════════════════════════════════════════

async function main() {
  const args = process.argv.slice(2);

  // Parse argumentos
  const getArg = (flag: string): string | undefined => {
    const index = args.indexOf(flag);
    return index >= 0 && index + 1 < args.length ? args[index + 1] : undefined;
  };

  const params: CreateBugParams = {
    title: getArg('--title') || 'Bug sem título',
    reproSteps: getArg('--repro-steps') || 'Não informado',
    expected: getArg('--expected') || 'Não informado',
    actual: getArg('--actual') || 'Não informado',
    severity: (getArg('--severity') as any) || '3 - Medium',
    priority: getArg('--priority') as any,
    evidencePath: getArg('--evidence-path'),
    parentId: getArg('--parent-id') ? parseInt(getArg('--parent-id')!) : undefined,
    tags: getArg('--tags'),
    areaPath: getArg('--area-path'),
    iterationPath: getArg('--iteration-path'),
    systemInfo: getArg('--system-info'),
    assignedTo: getArg('--assigned-to'),
  };

  try {
    await createBug(params);
    process.exit(0);
  } catch (error) {
    console.error('\n❌ Erro ao criar bug:');
    console.error(error);
    process.exit(1);
  }
}

// Executar apenas se chamado diretamente
if (require.main === module) {
  main();
}

export { createBug, CreateBugParams };
