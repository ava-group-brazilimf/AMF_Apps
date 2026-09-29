#!/usr/bin/env npx tsx
// ==========================================================================
// FastQA — Comando: Criar Test Cases em Lote a partir de .feature
// ==========================================================================
//
// Parseia um arquivo .feature, cria 1 Test Case por Scenario,
// vincula cada TC como child do PBI (parent) e adiciona à suite correspondente.
//
// Uso:
//   npx tsx fastqa/scripts/azure-devops/commands/batch-create-test-cases.command.ts \
//     --feature-file path/to/PBI-45.feature \
//     --parent-id 45 \
//     --plan-id 47 \
//     --suite-id 48 \
//     [--suite-map '{"1-2":49,"3-4":50,"5-7":51,"8-10":52,"11":53,"12":54}'] \
//     [--area-path "Project\\Area"] \
//     [--iteration "Project\\Sprint 1"] \
//     [--tags "pbi-45; fastqa"]
//
// --suite-id:  Adiciona TODOS os TCs a uma única suite (simples)
// --suite-map: JSON mapeando ranges de cenários para suite IDs (avançado)
//              Chaves são ranges "1-3" ou individuais "4", valores são suite IDs
//
// ==========================================================================

import * as fs from 'fs';
import { AzureDevOpsClient, withClient } from '../azure-devops.client';
import { Logger } from '../utils/logger.util';
import type { JsonPatchOperation } from '../types/azure-devops.types';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ParsedScenario {
  number: number;
  name: string;
  steps: string[];
  tags: string[];
  isOutline: boolean;
}

interface SuiteMapping {
  [range: string]: number; // e.g. "1-2": 49, "3": 50
}

interface BatchArgs {
  featureFile: string;
  parentId?: number;
  planId?: number;
  suiteId?: number;
  suiteMap?: SuiteMapping;
  areaPath?: string;
  iteration?: string;
  tags?: string;
}

interface CreatedTestCase {
  scenarioNumber: number;
  scenarioName: string;
  tcId: number;
  suiteId?: number;
  url: string;
}

// ---------------------------------------------------------------------------
// CLI Parsing
// ---------------------------------------------------------------------------

function parseArgs(): BatchArgs {
  const args = process.argv.slice(2);
  const parsed: BatchArgs = { featureFile: '' };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--feature-file': parsed.featureFile = args[++i]; break;
      case '--parent-id': parsed.parentId = parseInt(args[++i], 10); break;
      case '--plan-id': parsed.planId = parseInt(args[++i], 10); break;
      case '--suite-id': parsed.suiteId = parseInt(args[++i], 10); break;
      case '--suite-map': parsed.suiteMap = JSON.parse(args[++i]); break;
      case '--area-path': parsed.areaPath = args[++i]; break;
      case '--iteration': parsed.iteration = args[++i]; break;
      case '--tags': parsed.tags = args[++i]; break;
    }
  }

  if (!parsed.featureFile) {
    console.error('❌ Parâmetro --feature-file é obrigatório');
    process.exit(1);
  }

  if (!fs.existsSync(parsed.featureFile)) {
    console.error(`❌ Arquivo não encontrado: ${parsed.featureFile}`);
    process.exit(1);
  }

  return parsed;
}

// ---------------------------------------------------------------------------
// Feature File Parser
// ---------------------------------------------------------------------------

/**
 * Parseia um arquivo .feature e retorna um array de cenários individuais.
 * Cada cenário contém seus steps (Given/When/Then/And/But) sem o Background.
 * O Background é retornado separadamente para uso na Description.
 */
function parseFeatureFile(filePath: string): {
  featureName: string;
  background: string[];
  scenarios: ParsedScenario[];
} {
  const content = fs.readFileSync(filePath, 'utf-8');
  const lines = content.split('\n');

  let featureName = '';
  const background: string[] = [];
  const scenarios: ParsedScenario[] = [];

  let currentSection: 'none' | 'background' | 'scenario' = 'none';
  let currentScenario: ParsedScenario | null = null;
  let scenarioCount = 0;
  let pendingTags: string[] = [];

  for (const rawLine of lines) {
    const line = rawLine.trim();

    // Skip empty lines and comments
    if (!line || line.startsWith('#')) continue;

    // Feature name
    if (line.startsWith('Feature:')) {
      featureName = line.replace('Feature:', '').trim();
      continue;
    }

    // Tags (accumulate for next scenario)
    if (line.startsWith('@')) {
      pendingTags.push(...line.split(/\s+/).filter(t => t.startsWith('@')));
      continue;
    }

    // Background
    if (line.startsWith('Background:')) {
      currentSection = 'background';
      continue;
    }

    // Scenario / Scenario Outline
    if (line.startsWith('Scenario Outline:') || line.startsWith('Scenario:')) {
      // Save previous scenario
      if (currentScenario) {
        scenarios.push(currentScenario);
      }

      scenarioCount++;
      const isOutline = line.startsWith('Scenario Outline:');
      const name = line.replace(/^Scenario( Outline)?:\s*/, '').trim();

      currentScenario = {
        number: scenarioCount,
        name,
        steps: [],
        tags: [...pendingTags],
        isOutline,
      };
      pendingTags = [];
      currentSection = 'scenario';
      continue;
    }

    // Examples table (skip — not needed for TC steps)
    if (line.startsWith('Examples:') || line.startsWith('|')) {
      continue;
    }

    // Step lines
    if (/^(Given|When|Then|And|But)\s/i.test(line)) {
      if (currentSection === 'background') {
        background.push(line);
      } else if (currentSection === 'scenario' && currentScenario) {
        currentScenario.steps.push(line);
      }
    }
  }

  // Push last scenario
  if (currentScenario) {
    scenarios.push(currentScenario);
  }

  return { featureName, background, scenarios };
}

// ---------------------------------------------------------------------------
// Suite Mapping Resolver
// ---------------------------------------------------------------------------

/**
 * Resolve o suite ID para um cenário dado seu número.
 * Suporta ranges ("1-3") e valores individuais ("4").
 */
function resolveSuiteId(
  scenarioNumber: number,
  suiteMap?: SuiteMapping,
  defaultSuiteId?: number
): number | undefined {
  if (!suiteMap) return defaultSuiteId;

  for (const [range, suiteId] of Object.entries(suiteMap)) {
    if (range.includes('-')) {
      const [start, end] = range.split('-').map(Number);
      if (scenarioNumber >= start && scenarioNumber <= end) {
        return suiteId;
      }
    } else {
      if (scenarioNumber === Number(range)) {
        return suiteId;
      }
    }
  }

  // Fallback to default suite
  return defaultSuiteId;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const args = parseArgs();
  const logger = new Logger('batch-create-test-cases');

  logger.info('═══════════════════════════════════════════════════════════');
  logger.info('FastQA — Criar Test Cases em Lote');
  logger.info('═══════════════════════════════════════════════════════════');
  logger.info(`Feature file: ${args.featureFile}`);

  // Parse feature file
  const { featureName, background, scenarios } = parseFeatureFile(args.featureFile);

  logger.info(`Feature: ${featureName}`);
  logger.info(`Background steps: ${background.length}`);
  logger.info(`Cenários encontrados: ${scenarios.length}`);

  if (scenarios.length === 0) {
    logger.info('⚠️ Nenhum cenário encontrado no arquivo .feature');
    process.exit(0);
  }

  // Build background description if present
  const backgroundDescription = background.length > 0
    ? `<strong>Background (Contexto):</strong><br>${background.map(s => s).join('<br>')}`
    : '';

  const results: CreatedTestCase[] = [];
  const errors: { scenarioNumber: number; name: string; error: string }[] = [];

  await withClient(async (client) => {
    for (const scenario of scenarios) {
      const title = `${scenario.number} - ${scenario.name}`;
      logger.info(`\n──────────────────────────────────────────────`);
      logger.info(`📝 Criando TC: ${title}`);

      try {
        // Build operations
        const operations: JsonPatchOperation[] = [
          { op: 'add', path: '/fields/System.Title', value: title },
          { op: 'add', path: '/fields/Microsoft.VSTS.TCM.AutomationStatus', value: 'Not Automated' },
        ];

        if (backgroundDescription) {
          operations.push({ op: 'add', path: '/fields/System.Description', value: backgroundDescription });
        }
        if (args.areaPath) {
          operations.push({ op: 'add', path: '/fields/System.AreaPath', value: args.areaPath });
        }
        if (args.iteration) {
          operations.push({ op: 'add', path: '/fields/System.IterationPath', value: args.iteration });
        }

        // Build tags
        const tagParts: string[] = [];
        if (args.tags) tagParts.push(args.tags);
        if (scenario.tags.length) tagParts.push(scenario.tags.map(t => t.replace('@', '')).join('; '));
        if (tagParts.length) {
          operations.push({ op: 'add', path: '/fields/System.Tags', value: tagParts.join('; ') });
        }

        // Add steps XML
        if (scenario.steps.length) {
          const stepsXml = AzureDevOpsClient.buildTestCaseStepsXmlFromFeatureLines(scenario.steps);
          operations.push({ op: 'add', path: '/fields/Microsoft.VSTS.TCM.Steps', value: stepsXml });
        }

        // Create TC
        const wi = await client.createWorkItem('Test Case', operations);
        logger.success(`  ✅ TC #${wi.id} criado`);

        // Link as child of parent PBI
        if (args.parentId) {
          await client.linkWorkItems(wi.id, args.parentId, 'Parent');
          logger.success(`  🔗 Vinculado como child de #${args.parentId}`);
        }

        // Add to suite
        const suiteId = resolveSuiteId(scenario.number, args.suiteMap, args.suiteId);
        if (args.planId && suiteId) {
          await client.addTestCaseToSuite(args.planId, suiteId, [wi.id]);
          logger.success(`  📋 Adicionado à Suite #${suiteId}`);
        }

        results.push({
          scenarioNumber: scenario.number,
          scenarioName: scenario.name,
          tcId: wi.id,
          suiteId,
          url: wi.url,
        });
      } catch (err: any) {
        const errMsg = err.message || String(err);
        logger.info(`  ❌ Erro: ${errMsg}`);
        errors.push({
          scenarioNumber: scenario.number,
          name: scenario.name,
          error: errMsg,
        });
      }
    }

    // Report
    logger.info('\n═══════════════════════════════════════════════════════════');
    logger.info('📊 Resultado da criação em lote');
    logger.info('═══════════════════════════════════════════════════════════');
    logger.info(`✅ Criados: ${results.length}/${scenarios.length}`);
    if (errors.length) {
      logger.info(`❌ Erros: ${errors.length}`);
    }

    logger.info('\n📋 Test Cases criados:');
    for (const r of results) {
      logger.info(`  #${r.tcId} — ${r.scenarioNumber} - ${r.scenarioName}${r.suiteId ? ` (Suite #${r.suiteId})` : ''}`);
    }

    if (errors.length) {
      logger.info('\n⚠️ Erros:');
      for (const e of errors) {
        logger.info(`  Cenário ${e.scenarioNumber} (${e.name}): ${e.error}`);
      }
    }

    // Output JSON for automation
    const output = {
      feature: featureName,
      parentId: args.parentId,
      planId: args.planId,
      created: results,
      errors,
    };
    console.log('\n__BATCH_RESULT_JSON__');
    console.log(JSON.stringify(output, null, 2));
    console.log('__BATCH_RESULT_JSON_END__');

    logger.success('\n✅ Criação em lote concluída');
    logger.info('═══════════════════════════════════════════════════════════');
  }, 'batch-create-test-cases');
}

main().catch((err) => {
  console.error('❌ Erro fatal:', err.message || err);
  process.exit(1);
});
