/**
 * ═══════════════════════════════════════════════════════════════════════════
 * FastQA — Comando: Análise de Regressão por PR
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * Recebe um PR da aplicação (Azure DevOps ou Git local), identifica
 * áreas funcionais impactadas, cruza com testes existentes via
 * regression-map.yaml + heurística em cascata, classifica por risco
 * e gera plano de regressão priorizado.
 *
 * Uso:
 *   npx tsx fastqa/scripts/regression/commands/analyze-pr-regression.command.ts \
 *     --pr-url <url> \
 *     [--app-repo-path <path>] \
 *     [--target-branch <branch>] \
 *     [--output <path>] \
 *     [--use-git-local] \
 *     [--dry-run]
 *
 * @module analyze-pr-regression
 */

import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'js-yaml';
import { minimatch } from 'minimatch';

import { resolvePrInput, fetchPrData } from '../providers/pr-provider.resolver';
import { deriveAreaName, detectScope, SCOPE_PATTERNS, AREA_SUFFIXES } from '../utils/area-name.utils';
import type {
  PrAnalysisResult,
  PrFileChange,
  PrWorkItem,
  FunctionalArea,
  FunctionalAreaScope,
  RegressionMapConfig,
  RegressionMapArea,
  RegressionTestEntry,
  RegressionPlan,
  RiskLevel,
  AnalyzePrRegressionParams,
  RegressionAnalysisJson,
  GlobalAlert,
  TestLayer,
} from '../types/regression.types';

// ─────────────────────────────────────────────────────────────────────
// Constantes
// ─────────────────────────────────────────────────────────────────────

const COMMAND_NAME = 'analyze-pr-regression';
const DEFAULT_MAP_PATH = 'fastqa/scripts/regression-map.yaml';
const CONFIG_PATH = 'fastqa/scripts/project_config.json';
const DEFAULT_OUTPUT_DIR = 'fastqa/manual_test/regression_analysis';

// ─────────────────────────────────────────────────────────────────────
// Tipos internos
// ─────────────────────────────────────────────────────────────────────

interface ProjectConfig {
  platform?: { type?: string };
  connectors?: { output?: { automation_framework?: string; language?: string } };
  folder_structure?: {
    root?: string;
    custom_paths?: {
      tests?: string;
      pages?: string;
      automation_root?: string;
      results?: string;
      additional_test_layers?: Array<{ name: string; path: string }>;
    };
  };
}

interface TestMatch {
  test: string;
  area: string;
  confidence: 'high' | 'medium-high' | 'medium' | 'low';
  strategy: string;
  /** Área funcional de origem (para estratégias indiretas como dependency-graph) */
  sourceArea?: string;
  /** Detalhe descritivo para compor o motivo no relatório */
  detail?: string;
  /** Camada de teste: e2e, api, unit, manual */
  layer?: string;
  /** Chave da área no regression-map que originou o match (pode diferir de area) */
  mapAreaKey?: string;
}

// ─────────────────────────────────────────────────────────────────────
// Utilitários
// ─────────────────────────────────────────────────────────────────────

function walkDir(dir: string, extensions: string[]): string[] {
  const results: string[] = [];
  if (!fs.existsSync(dir)) return results;
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === 'node_modules' || entry.name.startsWith('.')) continue;
      results.push(...walkDir(fullPath, extensions));
    } else if (extensions.some(ext => entry.name.endsWith(ext))) {
      results.push(fullPath);
    }
  }
  return results;
}

function padRight(text: string, length: number): string {
  return text.length >= length ? text.substring(0, length) : text + ' '.repeat(length - text.length);
}

function truncate(text: string, maxLength: number): string {
  return text.length > maxLength ? text.substring(0, maxLength - 2) + '..' : text;
}

// ─────────────────────────────────────────────────────────────────────
// Parsing de .feature para seção de testes manuais
// ─────────────────────────────────────────────────────────────────────

interface ParsedFeature {
  fileName: string;
  filePath: string;
  title: string;
  tags: string[];
  scenarios: Array<{ name: string; tags: string[]; isOutline: boolean }>;
  background?: string;
}

interface ParsedUS {
  title: string;
  priority?: string;
  browsers?: string[];
  devices?: string[];
  url?: string;
  checklist: string[];
}

function parseFeatureFile(featurePath: string): ParsedFeature | null {
  if (!fs.existsSync(featurePath)) return null;
  const content = fs.readFileSync(featurePath, 'utf-8');
  const fileLines = content.split('\n');

  let title = '';
  const fileTags: string[] = [];
  const scenarios: Array<{ name: string; tags: string[]; isOutline: boolean }> = [];
  let background = '';
  let pendingTags: string[] = [];

  for (let i = 0; i < fileLines.length; i++) {
    const line = fileLines[i].trim();

    if (line.startsWith('@')) {
      const tags = line.match(/@[\w-]+/g) || [];
      if (!title) {
        fileTags.push(...tags);
      } else {
        pendingTags = tags;
      }
      continue;
    }

    if (line.startsWith('Feature:')) {
      title = line.replace('Feature:', '').trim();
      continue;
    }

    if (line.startsWith('Background:')) {
      const bgLines: string[] = [];
      for (let j = i + 1; j < fileLines.length; j++) {
        const bgLine = fileLines[j].trim();
        if (bgLine.startsWith('Scenario') || bgLine.startsWith('@') || bgLine === '') break;
        bgLines.push(bgLine);
      }
      background = bgLines.join(' | ');
      continue;
    }

    if (line.startsWith('Scenario Outline:') || line.startsWith('Scenario:')) {
      const isOutline = line.startsWith('Scenario Outline:');
      const name = line.replace(/Scenario( Outline)?:/, '').trim();
      scenarios.push({ name, tags: [...pendingTags], isOutline });
      pendingTags = [];
    }
  }

  return {
    fileName: path.basename(featurePath),
    filePath: featurePath,
    title: title || path.basename(featurePath, '.feature'),
    tags: fileTags,
    scenarios,
    background,
  };
}

function parseUSFile(usPath: string): ParsedUS | null {
  if (!fs.existsSync(usPath)) return null;
  const content = fs.readFileSync(usPath, 'utf-8');

  const titleMatch = content.match(/^#\s+.*?:\s*(.+)/m);
  const priorityMatch = content.match(/\*\*Prioridade:\*\*\s*(.+)/);
  const urlMatch = content.match(/\*\*URL.*?\*\*:\s*(https?:\/\/\S+)/);
  const browserMatch = content.match(/\*\*Navegadores?\*\*:\s*(.+)/i);
  const deviceMatch = content.match(/\*\*Dispositivos?\*\*:\s*\n([\s\S]*?)(?:\n\n|\n###|\n---)/); 

  const checklist: string[] = [];
  const checklistRegex = /- \[[ x]\]\s*(.+)/g;
  let cm;
  while ((cm = checklistRegex.exec(content)) !== null) {
    checklist.push(cm[1].trim());
  }

  let browsers: string[] = [];
  if (browserMatch) {
    browsers = browserMatch[1].split(/,\s*/).map(b => b.trim()).filter(Boolean);
  }

  let devices: string[] = [];
  if (deviceMatch) {
    devices = deviceMatch[1].split('\n')
      .map(l => l.replace(/^\s*-\s*/, '').trim())
      .filter(Boolean);
  }

  return {
    title: titleMatch ? titleMatch[1].trim() : '',
    priority: priorityMatch ? priorityMatch[1].trim() : undefined,
    browsers: browsers.length > 0 ? browsers : undefined,
    devices: devices.length > 0 ? devices : undefined,
    url: urlMatch ? urlMatch[1] : undefined,
    checklist,
  };
}

// ─────────────────────────────────────────────────────────────────────
// Step 7.3 — Extrair áreas funcionais dos arquivos do PR
// ─────────────────────────────────────────────────────────────────────

function extractFunctionalAreas(files: PrFileChange[]): FunctionalArea[] {
  const areasMap = new Map<string, FunctionalArea>();

  for (const file of files) {
    const filePath = file.path;

    // Determinar scope
    const scope = detectScope(filePath);

    // Extrair nome da área a partir do path
    const areaName = deriveAreaName(filePath);

    if (!areasMap.has(areaName)) {
      areasMap.set(areaName, { name: areaName, scope, sourceFiles: [] });
    }
    const area = areasMap.get(areaName)!;
    area.sourceFiles.push(filePath);
    // Se algum arquivo marca global, a área inteira é global
    if (scope === 'global') area.scope = 'global';
  }

  return [...areasMap.values()];
}

// ─────────────────────────────────────────────────────────────────────
// Extrair layer do prefixo [layerName] em nome de teste do regression-map
// ─────────────────────────────────────────────────────────────────────

function extractLayerPrefix(testName: string): { layer: string | undefined; cleanName: string } {
  const match = testName.match(/^\[(\w+)\]\s*(.+)$/);
  if (match) return { layer: match[1], cleanName: match[2] };
  return { layer: undefined, cleanName: testName };
}

/** Inferir layer a partir do caminho do diretório de testes */
function inferLayerFromDir(dir: string, resolvedLayers: Array<{ name: string; path: string }>): string | undefined {
  for (const layer of resolvedLayers) {
    if (dir.includes(layer.path) || layer.path.includes(dir)) return layer.name;
  }
  const dirLower = dir.toLowerCase();
  if (dirLower.includes('/api/') || dirLower.includes('\\api\\')) return 'api';
  if (dirLower.includes('/unit/') || dirLower.includes('\\unit\\') || dirLower.includes('__tests__')) return 'unit';
  if (dirLower.includes('/integration/') || dirLower.includes('\\integration\\')) return 'integration';
  return 'e2e';
}

// ─────────────────────────────────────────────────────────────────────
// Step 7.4 — Mapear áreas → testes (estratégias em cascata)
// ─────────────────────────────────────────────────────────────────────

function mapAreasToTests(
  areas: FunctionalArea[],
  regMap: RegressionMapConfig | null,
  testsDirs: string[],
  featureDir: string,
  resolvedLayers: Array<{ name: string; path: string }>,
  regMapLayersUsed?: Array<{ name: string; path: string }>
): { matches: TestMatch[]; globalAlerts: GlobalAlert[] } {
  const matches: TestMatch[] = [];
  const globalAlerts: GlobalAlert[] = [];
  const matchedTests = new Set<string>();

  for (const area of areas) {
    // Estratégia 1: regression-map.yaml (confiança ALTA)
    if (regMap) {
      for (const [areaKey, mapArea] of Object.entries(regMap.areas)) {
        for (const sourceFile of area.sourceFiles) {
          const normalizedFile = sourceFile.replace(/^\/+/, '');
          const isMatch = (mapArea.app_patterns ?? []).some(pattern =>
            minimatch(normalizedFile, pattern, { dot: true }) || minimatch(sourceFile, pattern, { dot: true })
          );
          if (isMatch) {
            for (const test of (mapArea.tests ?? [])) {
              const { layer: extractedLayer, cleanName } = extractLayerPrefix(test);
              // Se layer não veio do prefixo [layer] e layers_used tem exatamente 1 camada, usar essa
              const layer = extractedLayer ?? (regMapLayersUsed?.length === 1 ? regMapLayersUsed[0].name : undefined);
              if (!matchedTests.has(`${area.name}:${cleanName}`)) {
                matches.push({ test: cleanName, area: area.name, confidence: 'high', strategy: 'regression-map', sourceArea: area.name, detail: `pattern matched: ${sourceFile}`, layer, mapAreaKey: areaKey });
                matchedTests.add(`${area.name}:${cleanName}`);
              }
            }
            for (const feature of (mapArea.features ?? [])) {
              if (!matchedTests.has(`${area.name}:${feature}`)) {
                matches.push({ test: feature, area: area.name, confidence: 'high', strategy: 'regression-map', sourceArea: area.name, detail: `pattern matched: ${sourceFile}`, layer: 'manual', mapAreaKey: areaKey });
                matchedTests.add(`${area.name}:${feature}`);
              }
            }
          }
        }
      }
    }

    // Estratégia 1.5: Propagação via grafo de dependências (confiança MÉDIA)
    if (regMap) {
      for (const [areaKey, mapArea] of Object.entries(regMap.areas)) {
        if (mapArea.dependencies && mapArea.dependencies.includes(area.name)) {
          for (const test of (mapArea.tests ?? [])) {
            const { layer, cleanName } = extractLayerPrefix(test);
            if (!matchedTests.has(`${areaKey}:${cleanName}`)) {
              matches.push({ test: cleanName, area: areaKey, confidence: 'medium', strategy: 'dependency-graph', sourceArea: area.name, detail: `${areaKey} depende de ${area.name}`, layer });
              matchedTests.add(`${areaKey}:${cleanName}`);
            }
          }
        }
        if (area.name === '*global*' && mapArea.impact_scope === 'targeted' && mapArea.impacted_areas) {
          if (mapArea.impacted_areas.includes(areaKey)) {
            for (const test of (mapArea.tests ?? [])) {
              const { layer, cleanName } = extractLayerPrefix(test);
              if (!matchedTests.has(`${areaKey}:${cleanName}`)) {
                matches.push({ test: cleanName, area: areaKey, confidence: 'medium', strategy: 'targeted-impact', sourceArea: area.name, detail: `global impacta ${areaKey} via targeted scope`, layer });
                matchedTests.add(`${areaKey}:${cleanName}`);
              }
            }
          }
        }
      }
    }

    // Estratégia 2: Tags em .feature files (confiança MÉDIA-ALTA)
    if (fs.existsSync(featureDir)) {
      const featureFiles = walkDir(featureDir, ['.feature']);
      for (const ff of featureFiles) {
        const content = fs.readFileSync(ff, 'utf-8');
        const areaTag = `@${area.name}`;
        if (content.includes(areaTag)) {
          const basename = path.basename(ff);
          if (!matchedTests.has(`${area.name}:${basename}`)) {
            matches.push({ test: basename, area: area.name, confidence: 'medium-high', strategy: 'feature-tag', sourceArea: area.name, detail: `tag ${areaTag} em ${basename}`, layer: 'manual' });
            matchedTests.add(`${area.name}:${basename}`);
          }
        }
      }
    }

    // Estratégia 3: Nome de arquivo por convenção (confiança MÉDIA)
    for (const dir of testsDirs) {
      if (!fs.existsSync(dir)) continue;
      const specFiles = walkDir(dir, ['.spec.ts', '.spec.js', '.test.ts', '.test.js', '.spec.py', '.test.py']);
      for (const sf of specFiles) {
        const basename = path.basename(sf).toLowerCase();
        if (basename.includes(area.name) && area.name !== '*global*') {
          if (!matchedTests.has(`${area.name}:${path.basename(sf)}`)) {
            const layerName = inferLayerFromDir(dir, resolvedLayers);
            matches.push({ test: path.basename(sf), area: area.name, confidence: 'medium', strategy: 'name-convention', sourceArea: area.name, detail: `nome contém "${area.name}"`, layer: layerName });
            matchedTests.add(`${area.name}:${path.basename(sf)}`);
          }
        }
      }
    }

    // Estratégia 4: Busca textual no conteúdo (confiança BAIXA)
    // Pular se a área já tem matches de estratégias mais confiáveis
    const areaHasStrongMatches = matches.some(m => m.area === area.name && (m.strategy === 'regression-map' || m.strategy === 'dependency-graph' || m.strategy === 'name-convention' || m.strategy === 'feature-tag'));
    const MAX_TEXT_SEARCH_PER_AREA = 5;

    if (area.name !== '*global*' && !areaHasStrongMatches) {
      let textSearchCount = 0;
      let textSearchSkipped = 0;
      for (const dir of testsDirs) {
        if (!fs.existsSync(dir)) continue;
        const allTestFiles = walkDir(dir, ['.spec.ts', '.spec.js', '.test.ts', '.test.js', '.ts', '.js', '.py']);
        for (const tf of allTestFiles) {
          if (matchedTests.has(`${area.name}:${path.basename(tf)}`)) continue;
          try {
            const content = fs.readFileSync(tf, 'utf-8');
            // Buscar referências significativas (exclui URL paths genéricas como /login que casam com endpoints de autenticação)
            const searchTerms = [
              `"${area.name}"`, `'${area.name}'`,
              `[data-testid*="${area.name}"]`,
            ];
            if (searchTerms.some(term => content.toLowerCase().includes(term.toLowerCase()))) {
              if (textSearchCount < MAX_TEXT_SEARCH_PER_AREA) {
                const layerName = inferLayerFromDir(dir, resolvedLayers);
                matches.push({ test: path.basename(tf), area: area.name, confidence: 'low', strategy: 'text-search', sourceArea: area.name, detail: `referência textual a "${area.name}"`, layer: layerName });
                matchedTests.add(`${area.name}:${path.basename(tf)}`);
                textSearchCount++;
              } else {
                textSearchSkipped++;
              }
            }
          } catch {
            // Arquivo ilegível, ignorar
          }
        }
      }
      // Resumo para testes excedentes
      if (textSearchSkipped > 0) {
        matches.push({
          test: `(+${textSearchSkipped} outros testes referenciam "${area.name}")`,
          area: area.name,
          confidence: 'low',
          strategy: 'text-search',
          sourceArea: area.name,
          detail: `${textSearchSkipped} testes adicionais omitidos — provavelmente usam "${area.name}" como pré-requisito`,
        });
      }
    }

    // Estratégia 5: Impacto global → gera ALERTA (não teste fantasma)
    if (area.scope === 'global' || area.name === '*global*') {
      globalAlerts.push({
        message: `Arquivo global alterado: ${area.sourceFiles[0] || area.name} — executar suite de sanidade completa`,
        strategy: 'global-impact',
        sourceFile: area.sourceFiles[0] || area.name,
      });
    }
  }

  // Verificar global_triggers do mapa → também gera ALERTA
  if (regMap?.global_triggers) {
    for (const area of areas) {
      for (const sourceFile of area.sourceFiles) {
        const normalizedFile = sourceFile.replace(/^\/+/, '');
        if (regMap.global_triggers.some(trigger => minimatch(normalizedFile, trigger, { dot: true }) || minimatch(sourceFile, trigger, { dot: true }))) {
          const alreadyAlerted = globalAlerts.some(a => a.strategy === 'global-trigger');
          if (!alreadyAlerted) {
            globalAlerts.push({
              message: `Arquivo em global_triggers: ${sourceFile} — executar suite de sanidade completa`,
              strategy: 'global-trigger',
              sourceFile,
            });
          }
          break;
        }
      }
    }
  }

  return { matches, globalAlerts };
}

// ─────────────────────────────────────────────────────────────────────
// Step 7.5 — Classificar risco
// ─────────────────────────────────────────────────────────────────────

function classifyRisk(
  match: TestMatch,
  allMatches: TestMatch[],
  workItems: PrWorkItem[],
  areas: FunctionalArea[]
): RiskLevel {
  // Work Items com prioridade alta
  const maxPriority = workItems.reduce((max, wi) => {
    if (wi.priority && (max === 0 || wi.priority < max)) return wi.priority;
    return max;
  }, 0);

  // Convergência: mesmo teste impactado por múltiplas áreas
  const convergenceCount = allMatches.filter(m => m.test === match.test).length;

  // Tags indicam criticidade (no nome do arquivo/teste)
  const testLower = match.test.toLowerCase();
  const hasCriticalTag = testLower.includes('critical');
  const hasE2ETag = testLower.includes('e2e') || testLower.includes('jornada') || testLower.includes('journey');

  // Área da fonte
  const sourceArea = areas.find(a => a.name === match.area);
  const isMainPage = sourceArea?.scope === 'page' || sourceArea?.scope === 'api';

  // Classificação
  if (maxPriority === 1 || hasCriticalTag || (convergenceCount >= 3 && isMainPage)) {
    return 'critical';
  }
  if (maxPriority === 2 || hasE2ETag || (isMainPage && convergenceCount >= 2) || match.confidence === 'high') {
    return 'high';
  }
  if (match.confidence === 'medium-high' || match.confidence === 'medium' || convergenceCount >= 2) {
    return 'medium';
  }
  return 'low';
}

// ─────────────────────────────────────────────────────────────────────
// Step 7.6 — Gerar relatório Markdown
// ─────────────────────────────────────────────────────────────────────

function generateMarkdownReport(plan: RegressionPlan, framework: string, featureDir?: string, usDir?: string, regMapLayersUsed?: Array<{ name: string; path: string }>): string {
  const riskOrder: RiskLevel[] = ['critical', 'high', 'medium', 'low', 'gap'];
  const lines: string[] = [];

  // Header
  lines.push(`# 📋 Plano de Regressão — PR #${plan.pr.id}`);
  lines.push('');
  lines.push(`> Gerado automaticamente por **FastQA Regression Analysis** (template do script)`);
  lines.push(`> ⚠️ Para relatório enriquecido com análise semântica de diffs, use \`@fastqa:regression_analyze\` (modo \`--json\`)`);
  lines.push(`> Data: ${new Date().toLocaleString('pt-BR')}`);
  lines.push('');
  lines.push('## 📌 Dados do PR');
  lines.push('');
  lines.push(`| Campo | Valor |`);
  lines.push(`|-------|-------|`);
  lines.push(`| **Título** | ${plan.pr.title} |`);
  lines.push(`| **Branch** | \`${plan.pr.source}\` → \`${plan.pr.target}\` |`);
  lines.push(`| **Autor** | ${plan.pr.author} |`);
  lines.push(`| **Data** | ${new Date(plan.pr.date).toLocaleString('pt-BR')} |`);
  lines.push(`| **Provider** | ${plan.pr.provider} |`);
  lines.push('');

  // Resumo executivo
  lines.push('## 📊 Resumo Executivo');
  lines.push('');
  lines.push(`| Métrica | Valor |`);
  lines.push(`|---------|-------|`);
  lines.push(`| Arquivos alterados | ${plan.summary.filesChanged} |`);
  lines.push(`| Áreas impactadas | ${plan.summary.areasImpacted} |`);
  lines.push(`| Testes impactados | ${plan.summary.testsImpacted} |`);
  lines.push(`| Gaps de cobertura | ${plan.summary.gapsFound} |`);
  lines.push(`| Confiança média | ${plan.summary.avgConfidence} |`);
  lines.push('');

  // ── ANÁLISE FUNCIONAL ──────────────────────────────────────────────

  lines.push('## 🔍 Análise Funcional');
  lines.push('');
  lines.push('> Visão orientada a negócio: o que foi alterado, por que testar e o que validar.');
  lines.push('');

  // Scope labels descritivos
  const scopeDescriptions: Record<string, string> = {
    page: 'Interface do usuário (tela/página)',
    api: 'Endpoint de API / rota de serviço',
    service: 'Lógica de negócio / serviço interno',
    component: 'Componente reutilizável',
    model: 'Modelo de dados / entidade',
    global: 'Configuração / infraestrutura global',
  };

  for (const area of plan.areas) {
    const areaTests = plan.tests.filter(t => (t.coveredAreas || []).includes(area.name));
    const areaGaps = plan.gaps.filter(g => g.area === area.name);
    const hasTests = areaTests.length > 0;
    const hasGaps = areaGaps.length > 0;

    const scopeDesc = scopeDescriptions[area.scope] || area.scope;
    const changeTypes = new Set<string>();
    // Inferir tipo de mudança a partir dos arquivos
    for (const f of area.sourceFiles) {
      const ext = f.split('.').pop()?.toLowerCase() || '';
      if (['yml', 'yaml', 'json', 'env', 'config'].includes(ext)) changeTypes.add('configuração');
      else if (['ts', 'js', 'py', 'java', 'cs', 'go'].includes(ext)) changeTypes.add('lógica');
      else if (['html', 'tsx', 'jsx', 'vue', 'svelte'].includes(ext)) changeTypes.add('interface');
      else if (['css', 'scss', 'less'].includes(ext)) changeTypes.add('estilo');
      else if (['sql', 'prisma', 'graphql'].includes(ext)) changeTypes.add('schema/dados');
      else changeTypes.add('código');
    }

    // Layers envolvidas
    const layersInvolved = [...new Set(areaTests.map(t => t.layer).filter(Boolean))];
    const defaultLayerName = regMapLayersUsed?.length === 1 ? regMapLayersUsed[0].name : undefined;
    const layerLabel = layersInvolved.length > 0 ? layersInvolved.join(', ') : (defaultLayerName || '—');

    // Risco mais alto
    const maxRisk = areaTests.length > 0
      ? areaTests.reduce((best, t) => riskOrder.indexOf(t.risk) < riskOrder.indexOf(best) ? t.risk : best, 'low' as RiskLevel)
      : 'gap';
    const riskIcon = maxRisk === 'critical' ? '🔴' : maxRisk === 'high' ? '🟠' : maxRisk === 'medium' ? '🟡' : maxRisk === 'low' ? '🟢' : '⚪';

    lines.push(`### ${riskIcon} ${area.name}`);
    lines.push('');
    lines.push(`| Aspecto | Detalhe |`);
    lines.push(`|---------|---------|`);
    lines.push(`| **Tipo** | ${scopeDesc} |`);
    lines.push(`| **O que mudou** | Alteração de ${[...changeTypes].join(' + ')} em ${area.sourceFiles.length} arquivo(s): ${area.sourceFiles.map(f => `\`${f}\``).join(', ')} |`);
    lines.push(`| **Risco** | ${riskIcon} ${maxRisk} |`);
    lines.push(`| **Cobertura** | ${hasTests ? `${areaTests.length} teste(s) mapeado(s) (${layerLabel})` : '⚪ Sem cobertura'}${hasGaps ? ` + ${areaGaps.length} gap(s)` : ''} |`);
    lines.push('');

    // O que validar — recomendações funcionais baseadas no scope
    lines.push('**O que validar:**');
    lines.push('');
    if (area.scope === 'page') {
      lines.push(`- Verificar se a tela **${area.name}** renderiza corretamente após a alteração`);
      lines.push(`- Validar comportamento de formulários, navegação e interações do usuário`);
      lines.push(`- Testar responsividade e acessibilidade se aplicável`);
    } else if (area.scope === 'api') {
      lines.push(`- Validar que o endpoint **${area.name}** responde com status e payload esperados`);
      lines.push(`- Verificar autenticação/autorização (tokens, permissões)`);
      lines.push(`- Testar cenários de erro (404, 401, 422, 500)`);
      lines.push(`- Validar contrato de API (schema de request/response)`);
    } else if (area.scope === 'service') {
      lines.push(`- Verificar lógica de negócio do serviço **${area.name}**`);
      lines.push(`- Validar integrações downstream que consomem este serviço`);
      lines.push(`- Testar cenários de borda e tratamento de exceções`);
    } else if (area.scope === 'model') {
      lines.push(`- Validar integridade do modelo **${area.name}** (campos, tipos, validações)`);
      lines.push(`- Verificar impacto em telas e APIs que consomem este modelo`);
      lines.push(`- Testar serialização/deserialização se aplicável`);
    } else if (area.scope === 'global') {
      lines.push(`- ⚠️ **Impacto amplo:** configuração global alterada afeta múltiplas áreas`);
      lines.push(`- Executar suite de sanidade completa`);
      lines.push(`- Validar que valores de configuração estão corretos em todos os ambientes`);
    } else {
      lines.push(`- Verificar funcionalidade do componente **${area.name}**`);
      lines.push(`- Validar todas as áreas que reutilizam este componente`);
    }
    lines.push('');
  }

  // Alertas de impacto global
  if (plan.globalAlerts.length > 0) {
    lines.push('## ⚠️ Alertas de Impacto Global');
    lines.push('');
    lines.push('> 🔴 **Arquivos de configuração ou infraestrutura foram alterados. Recomenda-se executar TODOS os testes (e2e + api + unit).**');
    lines.push('>');
    lines.push('> Motivo: alterações em configuração global podem afetar qualquer parte do sistema. Uma execução parcial pode não detectar regressões indiretas.');
    lines.push('');
    for (const alert of plan.globalAlerts) {
      lines.push(`- 🔴 **${alert.strategy}**: \`${alert.sourceFile}\` — ${alert.message}`);
    }
    lines.push('');
  }

  // ── SEÇÃO PRINCIPAL: Áreas Funcionais Impactadas ──────────────────

  lines.push('## 🧠 Áreas Funcionais Impactadas');
  lines.push('');

  // Agrupar testes por área (usando coveredAreas para multi-área)
  const testsByArea = new Map<string, RegressionTestEntry[]>();
  for (const t of plan.tests) {
    const areas = t.coveredAreas || [t.reason.split(' ')[0] || '—'];
    for (const area of areas) {
      if (!testsByArea.has(area)) testsByArea.set(area, []);
      testsByArea.get(area)!.push(t);
    }
  }

  // Agrupar gaps por área
  const gapsByArea = new Map<string, Array<{ file: string; note: string }>>();
  for (const g of plan.gaps) {
    if (!gapsByArea.has(g.area)) gapsByArea.set(g.area, []);
    gapsByArea.get(g.area)!.push({ file: g.file, note: g.note });
  }

  // Coletar todas as áreas (incluindo as que só têm gaps), filtrar por áreas do PR
  const prAreaNames = new Set(plan.areas.map(a => a.name));
  const allAreaNames = new Set([
    ...[...testsByArea.keys()].filter(a => prAreaNames.has(a)),
    ...gapsByArea.keys(),
  ]);

  // Ordenar áreas por risco mais alto
  const sortedAreas = [...allAreaNames].sort((a, b) => {
    const aTests = testsByArea.get(a) || [];
    const bTests = testsByArea.get(b) || [];
    const aMaxRisk = aTests.length > 0 ? Math.min(...aTests.map(t => riskOrder.indexOf(t.risk))) : 99;
    const bMaxRisk = bTests.length > 0 ? Math.min(...bTests.map(t => riskOrder.indexOf(t.risk))) : 99;
    return aMaxRisk - bMaxRisk;
  });

  for (const areaName of sortedAreas) {
    const areaObj = plan.areas.find(a => a.name === areaName);
    const areaTests = testsByArea.get(areaName) || [];
    const areaGaps = gapsByArea.get(areaName) || [];
    const scopeLabel = areaObj?.scope || 'unknown';
    const maxRisk = areaTests.length > 0 ? areaTests.reduce((best, t) => riskOrder.indexOf(t.risk) < riskOrder.indexOf(best) ? t.risk : best, 'low' as RiskLevel) : 'gap';
    const riskIcon = maxRisk === 'critical' ? '🔴' : maxRisk === 'high' ? '🟠' : maxRisk === 'medium' ? '🟡' : maxRisk === 'low' ? '🟢' : '⚪';

    lines.push(`### ${riskIcon} ${areaName} (${scopeLabel})`);
    lines.push('');

    // Arquivos da app alterados
    if (areaObj) {
      lines.push(`**Arquivos alterados:** ${areaObj.sourceFiles.map(f => `\`${f}\``).join(', ')}`);
      lines.push('');
    }

    // Motivo do impacto (extrair do reason do primeiro teste)
    if (areaTests.length > 0) {
      const strategies = [...new Set(areaTests.map(t => { const m = t.reason.match(/\(([^)]+)\)$/); return m ? m[1] : '—'; }))];
      lines.push(`**Detectado por:** ${strategies.join(', ')}`);
      lines.push('');
    }

    // Testes agrupados por layer
    if (areaTests.length > 0) {
      const byLayer = new Map<string, RegressionTestEntry[]>();
      for (const t of areaTests) {
        const layer = t.layer || 'outros';
        if (!byLayer.has(layer)) byLayer.set(layer, []);
        byLayer.get(layer)!.push(t);
      }

      lines.push('| Layer | Teste | Risco | Confiança | Motivo |');
      lines.push('|-------|-------|-------|-----------|--------|');
      for (const [layer, tests] of byLayer) {
        for (const t of tests) {
          const ri = t.risk === 'critical' ? '🔴' : t.risk === 'high' ? '🟠' : t.risk === 'medium' ? '🟡' : '🟢';
          lines.push(`| ${layer} | ${t.test} | ${ri} ${t.risk} | ${t.confidence} | ${t.reason} |`);
        }
      }
      lines.push('');
    }

    // Gaps desta área
    if (areaGaps.length > 0) {
      lines.push(`> ⚪ **Gap:** ${areaGaps.length} arquivo(s) sem teste mapeado`);
      for (const g of areaGaps) {
        lines.push(`>  - \`${g.file}\` — ${g.note}`);
      }
      lines.push('');
    }
  }

  // ── SEÇÃO: Testes Funcionais Manuais ──────────────────────────────

  const manualTests = plan.tests.filter(t => t.layer === 'manual');
  if (manualTests.length > 0 && featureDir) {
    lines.push('## 🧪 Testes Funcionais Manuais');
    lines.push('');
    lines.push('> Testes manuais impactados que requerem validação humana via `@fastqa:run_manual_test`.');
    lines.push('');

    // Agrupar por feature file
    const featureMap = new Map<string, RegressionTestEntry[]>();
    for (const t of manualTests) {
      if (!featureMap.has(t.test)) featureMap.set(t.test, []);
      featureMap.get(t.test)!.push(t);
    }

    // Tabela resumo
    lines.push('| Feature | Área | Cenários | Tags | Prioridade | Esforço |');
    lines.push('|---------|------|----------|------|------------|---------|');

    const parsedFeatures: Array<{ entry: RegressionTestEntry; feature: ParsedFeature | null; us: ParsedUS | null }> = [];

    for (const [featureName, entries] of featureMap) {
      const entry = entries[0];
      const area = (entry.coveredAreas || [])[0] || entry.reason.split(' ')[0] || '—';

      // Tentar localizar o .feature
      let feature: ParsedFeature | null = null;
      if (featureDir) {
        const featureFiles = walkDir(featureDir, ['.feature']);
        const found = featureFiles.find(f => path.basename(f) === featureName);
        if (found) feature = parseFeatureFile(found);
      }

      // Tentar localizar a US
      let us: ParsedUS | null = null;
      if (usDir) {
        const usId = featureName.replace('.feature', '');
        const usFilePath = path.join(usDir, `${usId}.md`);
        us = parseUSFile(usFilePath);
      }

      parsedFeatures.push({ entry, feature, us });

      const scenarioCount = feature ? feature.scenarios.length : '?';
      const tags = feature ? feature.tags.slice(0, 4).join(' ') : '—';
      const riskIcon = entry.risk === 'critical' ? '🔴' : entry.risk === 'high' ? '🟠' : entry.risk === 'medium' ? '🟡' : '🟢';
      const effort = feature ? `~${Math.max(1, Math.ceil(feature.scenarios.length * 0.4))}h` : '—';

      lines.push(`| ${featureName} | ${area} | ${scenarioCount} | ${tags} | ${riskIcon} ${entry.risk} | ${effort} |`);
    }
    lines.push('');

    // Detalhes por feature
    for (const { entry, feature, us } of parsedFeatures) {
      const area = (entry.coveredAreas || [])[0] || entry.reason.split(' ')[0] || '—';

      lines.push(`### 📄 ${entry.test}${feature ? ` — ${feature.title}` : ''}`);
      lines.push('');

      // Metadados
      lines.push(`- **Área impactada:** ${area} (arquivo: \`${entry.sourceFile}\`)`);
      if (feature) {
        lines.push(`- **Tags:** ${feature.tags.join(' ')}`);
        lines.push(`- **Cenários:** ${feature.scenarios.length}`);
      }
      if (us?.url) lines.push(`- **URL de teste:** ${us.url}`);
      if (us?.browsers) lines.push(`- **Navegadores:** ${us.browsers.join(', ')}`);
      if (us?.devices) lines.push(`- **Dispositivos:** ${us.devices.join(', ')}`);
      lines.push('');

      // Lista de cenários
      if (feature && feature.scenarios.length > 0) {
        lines.push('**Cenários a validar:**');
        lines.push('');
        for (const sc of feature.scenarios) {
          const scTags = sc.tags.length > 0 ? ` ${sc.tags.join(' ')}` : '';
          const outlineLabel = sc.isOutline ? ' *(parametrizado)*' : '';
          lines.push(`- [ ] ${sc.name}${outlineLabel}${scTags}`);
        }
        lines.push('');
      }

      // Checklist de AC da US
      if (us && us.checklist.length > 0) {
        lines.push('**Checklist de Aceite:**');
        lines.push('');
        for (const item of us.checklist) {
          lines.push(`- [ ] ${item}`);
        }
        lines.push('');
      }

      // Como executar
      lines.push('**Como executar:**');
      lines.push('');
      lines.push(`1. Execute: \`@fastqa:run_manual_test\``);
      lines.push(`2. Informe o test case: ${entry.test.replace('.feature', '')}`);
      lines.push(`3. Selecione modo de evidência: 📷 Screenshot ou 🎥 Vídeo`);
      lines.push(`4. Siga os steps Gherkin e capture as evidências`);
      if (us) {
        const usId = entry.test.replace('.feature', '');
        lines.push(`5. Valide contra AC: \`fastqa/manual_test/US/${usId}.md\``);
      }
      lines.push('');
    }

    // Ordem de execução por prioridade
    const sortedByRisk = [...parsedFeatures].sort((a, b) => {
      return riskOrder.indexOf(a.entry.risk) - riskOrder.indexOf(b.entry.risk);
    });

    lines.push('**📋 Ordem de Execução Recomendada:**');
    lines.push('');
    let order = 1;
    for (const { entry, feature } of sortedByRisk) {
      const ri = entry.risk === 'critical' ? '🔴' : entry.risk === 'high' ? '🟠' : entry.risk === 'medium' ? '🟡' : '🟢';
      const title = feature ? feature.title : entry.test;
      lines.push(`${order}. ${ri} **${entry.test}** — ${title}`);
      order++;
    }
    lines.push('');
  }

  // ── SEÇÃO SECUNDÁRIA: Resumo de Testes por Risco ──────────────────

  const riskLevels: Array<{ level: RiskLevel; icon: string; label: string }> = [
    { level: 'critical', icon: '🔴', label: 'Crítico' },
    { level: 'high', icon: '🟠', label: 'Alta Prioridade' },
    { level: 'medium', icon: '🟡', label: 'Média Prioridade' },
    { level: 'low', icon: '🟢', label: 'Baixa Prioridade' },
  ];

  lines.push('## 📊 Resumo de Testes por Risco');
  lines.push('');

  for (const { level, icon, label } of riskLevels) {
    const testsAtLevel = plan.tests.filter(t => t.risk === level);
    if (testsAtLevel.length === 0) continue;

    lines.push(`### ${icon} ${label} (${testsAtLevel.length})`);
    lines.push('');
    lines.push(`| Layer | Teste | Área | Arquivo da App |`);
    lines.push(`|-------|-------|------|----------------|`);
    for (const t of testsAtLevel) {
      const area = (t.coveredAreas || [])[0] || t.reason.split(' ')[0] || '—';
      lines.push(`| ${t.layer || '—'} | ${t.test} | ${area} | ${t.sourceFile} |`);
    }
    lines.push('');
  }

  // Gaps
  if (plan.gaps.length > 0) {
    const knownGaps = plan.gaps.filter(g => g.note.includes('PRÉ-EXISTENTE'));
    const newGaps = plan.gaps.filter(g => !g.note.includes('PRÉ-EXISTENTE'));

    lines.push('## ⚪ Gaps de Cobertura');
    lines.push('');
    lines.push(`> **${plan.gaps.length} arquivo(s)** da aplicação alterado(s) sem nenhum teste mapeado.`);
    if (knownGaps.length > 0) {
      lines.push(`> ⚠️ **${knownGaps.length}** são gaps pré-existentes (já sem cobertura no regression-map).`);
    }
    if (newGaps.length > 0) {
      lines.push(`> 🆕 **${newGaps.length}** são gaps novos detectados neste PR.`);
    }
    lines.push('');
    lines.push(`| Status | Arquivo da App | Área | Ação Recomendada |`);
    lines.push(`|--------|----------------|------|-----------------|`);
    for (const gap of plan.gaps) {
      const status = gap.note.includes('PRÉ-EXISTENTE') ? '⚠️ Pré-existente' : '🆕 Novo';
      lines.push(`| ${status} | ${gap.file} | ${gap.area} | ${gap.note} |`);
    }
    lines.push('');

    lines.push('### 💡 Recomendações para Gaps');
    lines.push('');
    const highRiskGaps = plan.gaps.filter(g => g.note.includes('alto risco'));
    const medRiskGaps = plan.gaps.filter(g => g.note.includes('médio risco'));
    if (highRiskGaps.length > 0) {
      lines.push(`- 🔴 **Prioridade alta:** ${highRiskGaps.length} arquivo(s) em áreas críticas (page/api) sem testes`);
      for (const g of highRiskGaps.slice(0, 5)) {
        lines.push(`  - \`${g.file}\` (área: ${g.area})`);
      }
    }
    if (medRiskGaps.length > 0) {
      lines.push(`- 🟠 **Prioridade média:** ${medRiskGaps.length} arquivo(s) em serviços sem testes`);
    }
    lines.push(`- 💡 Use \`@fastqa:test_case_with_fastqa\` para gerar testes para estes gaps`);
    lines.push('');
  }

  // Comandos de Execução
  lines.push('## 🏷️ Comandos de Execução');
  lines.push('');
  for (const cmd of plan.commands) {
    lines.push(`### ${cmd.label}`);
    lines.push('```bash');
    lines.push(cmd.command);
    lines.push('```');
    lines.push('');
  }

  // Rastreabilidade
  lines.push('## 📋 Rastreabilidade');
  lines.push('');
  lines.push(`| Arquivo da App | Área | Layer | Estratégia | Teste | Confiança |`);
  lines.push(`|----------------|------|-------|------------|-------|-----------|`);
  for (const t of plan.tests) {
    const strategyMatch = t.reason.match(/\(([^)]+)\)$/);
    const strategy = strategyMatch ? strategyMatch[1] : '—';
    const area = (t.coveredAreas || [])[0] || t.reason.split(' ')[0] || '—';
    lines.push(`| ${t.sourceFile} | ${area} | ${t.layer || '—'} | ${strategy} | ${t.test} | ${t.confidence} |`);
  }
  lines.push('');

  return lines.join('\n');
}

// ─────────────────────────────────────────────────────────────────────
// Gerar comandos de execução
// ─────────────────────────────────────────────────────────────────────

function generateExecutionCommands(
  tests: RegressionTestEntry[],
  areas: FunctionalArea[],
  framework: string,
  regMap: RegressionMapConfig | null,
  globalAlerts: GlobalAlert[]
): Array<{ label: string; command: string }> {
  const commands: Array<{ label: string; command: string }> = [];
  const fw = framework.toLowerCase();

  // Coletar tags REAIS do regression-map (não inventar)
  const realTags = new Set<string>();
  if (regMap) {
    for (const [, mapArea] of Object.entries(regMap.areas)) {
      for (const tag of (mapArea.tags ?? [])) {
        realTags.add(tag.toLowerCase());
      }
    }
  }

  const hasSmokeTag = realTags.has('@smoke');
  const hasRegressionTag = realTags.has('@regression');

  // Coletar specs por layer — aceita qualquer teste real (não resumos)
  const specsByLayer = new Map<string, string[]>();
  for (const t of tests) {
    const layer = t.layer || 'e2e';
    // Incluir qualquer teste que seja um arquivo real (tem extensão), exceto resumos como "(+N outros...)"
    if (t.test.startsWith('(')) continue;
    if (!specsByLayer.has(layer)) specsByLayer.set(layer, []);
    specsByLayer.get(layer)!.push(t.test);
  }

  // Coletar tags de área para grep
  const areaTags = [...new Set(areas.map(a => `@${a.name}`).filter(t => t !== '@*global*'))];

  // Se há alertas globais, recomendar execução de TODOS os testes
  if (globalAlerts.length > 0) {
    if (fw.includes('playwright')) {
      commands.push({ label: '🔴 Executar TODOS os testes (impacto global)', command: 'npx playwright test' });
    } else if (fw.includes('cypress')) {
      commands.push({ label: '🔴 Executar TODOS os testes (impacto global)', command: 'npx cypress run' });
    } else if (fw.includes('robot')) {
      commands.push({ label: '🔴 Executar TODOS os testes (impacto global)', command: 'robot .' });
    } else {
      commands.push({ label: '🔴 Executar TODOS os testes (impacto global)', command: 'npm test' });
    }
    // Opcionalmente, sugerir smoke como fallback rápido
    if (hasSmokeTag) {
      if (fw.includes('playwright')) {
        commands.push({ label: '⚡ Smoke rápido (fallback)', command: 'npx playwright test --grep "@smoke"' });
      } else if (fw.includes('cypress')) {
        commands.push({ label: '⚡ Smoke rápido (fallback)', command: 'npx cypress run --env grepTags="@smoke"' });
      } else if (fw.includes('robot')) {
        commands.push({ label: '⚡ Smoke rápido (fallback)', command: 'robot --include smoke .' });
      }
    }
  }

  // Gerar comandos por layer
  if (fw.includes('playwright')) {
    const e2eSpecs = specsByLayer.get('e2e') || [];
    if (e2eSpecs.length > 0) {
      commands.push({ label: '🎯 E2E — Specs Impactados', command: `npx playwright test ${[...new Set(e2eSpecs)].join(' ')}` });
    }
    if (areaTags.length > 0) {
      commands.push({ label: '🎯 E2E — Áreas Impactadas', command: `npx playwright test --grep "${areaTags.join('|')}"` });
    }
    if (hasRegressionTag) {
      commands.push({ label: '🔄 Regressão Completa', command: 'npx playwright test --grep "@regression"' });
    }
  } else if (fw.includes('cypress')) {
    const e2eSpecs = specsByLayer.get('e2e') || [];
    if (e2eSpecs.length > 0) {
      commands.push({ label: '🎯 E2E — Specs Impactados', command: `npx cypress run --spec "${[...new Set(e2eSpecs)].join(',')}"` });
    }
    if (hasRegressionTag) {
      commands.push({ label: '🔄 Regressão Completa', command: 'npx cypress run --env grepTags="@regression"' });
    }
  } else if (fw.includes('robot')) {
    if (areaTags.length > 0) {
      const robotTags = areaTags.map(t => t.replace('@', '')).join('OR');
      commands.push({ label: '🎯 Áreas Impactadas', command: `robot --include ${robotTags} .` });
    }
    if (hasRegressionTag) {
      commands.push({ label: '🔄 Regressão Completa', command: 'robot --include regression .' });
    }
  } else {
    // Fallback genérico
    const allSpecs = [...specsByLayer.values()].flat();
    if (allSpecs.length > 0) {
      commands.push({ label: '🎯 Specs Impactados', command: `npm test -- ${[...new Set(allSpecs)].join(' ')}` });
    }
  }

  // Comandos para layers adicionais (api, unit)
  for (const [layer, specs] of specsByLayer) {
    if (layer === 'e2e') continue;
    const uniqueSpecs = [...new Set(specs)];
    if (layer === 'unit') {
      commands.push({ label: `🧪 Unit — Specs Impactados`, command: `npm test -- ${uniqueSpecs.join(' ')}` });
    } else if (layer === 'api') {
      commands.push({ label: `🔌 API — Specs Impactados`, command: `npm test -- ${uniqueSpecs.join(' ')}` });
    } else {
      commands.push({ label: `📦 ${layer} — Specs Impactados`, command: `npm test -- ${uniqueSpecs.join(' ')}` });
    }
  }

  return commands;
}

// ─────────────────────────────────────────────────────────────────────
// Função Principal
// ─────────────────────────────────────────────────────────────────────

async function analyzePrRegression(params: AnalyzePrRegressionParams): Promise<RegressionPlan> {
  console.log('\n🔬 ═══════════════════════════════════════════════════════════════');
  console.log('   FastQA — Análise de Regressão por PR');
  console.log('═══════════════════════════════════════════════════════════════\n');

  // ── 7.1 Carregar contexto ──────────────────────────────────────────

  console.log('📋 Etapa 1: Carregando contexto...\n');

  let projectConfig: ProjectConfig = {};
  const basePath = params.appRepoPath || process.cwd();
  const configPath = path.resolve(basePath, CONFIG_PATH);
  const mapPath = path.resolve(basePath, DEFAULT_MAP_PATH);
  if (fs.existsSync(configPath)) {
    projectConfig = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
  } else {
    console.warn('   ⚠️  project_config.json não encontrado. Usando padrões.');
  }

  const framework = projectConfig.connectors?.output?.automation_framework || 'Playwright';
  const root = projectConfig.folder_structure?.root || 'fastqa';
  const customPaths = projectConfig.folder_structure?.custom_paths || {};
  const platformType = (projectConfig.platform?.type || 'web').toLowerCase();
  const autoRoot = customPaths.automation_root || `${root}/automated_test`;

  // Diretórios de teste — resolver layers
  // Preferir layers_used do regression-map.yaml (será carregado abaixo)
  // Fallback: project_config.json (compatibilidade com mapas antigos)
  let resolvedLayers: Array<{ name: string; path: string }> = [];
  const testsDirs: string[] = [];

  // Tentar carregar regression-map.yaml antecipadamente para ler layers_used
  let regMapLayersUsed: Array<{ name: string; path: string }> | undefined;
  if (fs.existsSync(mapPath)) {
    try {
      const rawMap = yaml.load(fs.readFileSync(mapPath, 'utf-8')) as RegressionMapConfig;
      regMapLayersUsed = rawMap.layers_used;
    } catch { /* ignorar erro de parse — será tratado abaixo */ }
  }

  if (regMapLayersUsed?.length) {
    // Usar EXATAMENTE as camadas que foram usadas para gerar o mapa
    resolvedLayers = regMapLayersUsed;
    for (const layer of resolvedLayers) {
      if (!testsDirs.includes(layer.path)) {
        testsDirs.push(layer.path);
      }
    }
  } else {
    // Fallback: project_config.json (mapas antigos sem layers_used)
    if (customPaths.tests) {
      testsDirs.push(customPaths.tests);
      resolvedLayers.push({ name: 'e2e', path: customPaths.tests });
    }
    if (testsDirs.length === 0) {
      const e2eDir = `${autoRoot}/${platformType}/tests`;
      const apiDir = `${autoRoot}/api/tests`;
      testsDirs.push(e2eDir, apiDir);
      resolvedLayers.push({ name: 'e2e', path: e2eDir });
      resolvedLayers.push({ name: 'api', path: apiDir });
    }
    const additionalLayers = customPaths.additional_test_layers || [];
    for (const layer of additionalLayers) {
      if (layer.name && layer.path) {
        resolvedLayers.push({ name: layer.name, path: layer.path });
        if (!testsDirs.includes(layer.path)) {
          testsDirs.push(layer.path);
        }
      }
    }
  }
  const featureDir = path.resolve(basePath, `${root}/manual_test/test_cases`);

  console.log(`   Framework:       ${framework}`);
  console.log(`   Plataforma:      ${projectConfig.platform?.type || 'Web'}`);
  console.log(`   Layers:          ${resolvedLayers.map(l => `${l.name}(${l.path})`).join(', ') || 'default'}`);
  console.log(`   Tests dirs:      ${testsDirs.join(', ')}`);

  // Carregar regression-map.yaml
  let regMap: RegressionMapConfig | null = null;
  if (fs.existsSync(mapPath)) {
    regMap = yaml.load(fs.readFileSync(mapPath, 'utf-8')) as RegressionMapConfig;
    console.log(`   Regression Map:  ✅ ${Object.keys(regMap.areas || {}).length} áreas`);
  } else {
    console.warn(`   Regression Map:  ⚠️  Não encontrado em ${mapPath} (operando apenas com heurística)`);
    console.warn('   Dica: Execute @fastqa:generate_regression_map para gerar o mapa.');
  }
  console.log('');

  // ── 7.2 Obter dados do PR ──────────────────────────────────────────

  console.log('🔍 Etapa 2: Obtendo dados do PR...\n');

  const prInput = resolvePrInput(params);
  console.log(`   Provider:  ${prInput.provider}`);

  const prResult: PrAnalysisResult = await fetchPrData(prInput);

  console.log(`   PR:        #${prResult.pr.id} — ${prResult.pr.title}`);
  console.log(`   Branch:    ${prResult.pr.source} → ${prResult.pr.target}`);
  console.log(`   Autor:     ${prResult.pr.author}`);
  console.log(`   Arquivos:  ${prResult.files.length}`);
  console.log(`   Work Items: ${prResult.workItems.length}`);
  console.log('');

  // Listar arquivos
  for (const f of prResult.files) {
    const typeIcon = f.changeType === 'add' ? '➕' : f.changeType === 'delete' ? '🗑️' : f.changeType === 'rename' ? '📝' : '✏️';
    console.log(`   ${typeIcon} [${f.changeType}] ${f.path}`);
  }
  console.log('');

  // ── 7.3 Extrair áreas funcionais ──────────────────────────────────

  console.log('🧠 Etapa 3: Extraindo áreas funcionais...\n');

  const areas = extractFunctionalAreas(prResult.files);

  for (const area of areas) {
    console.log(`   📂 ${area.name} (${area.scope}) — ${area.sourceFiles.length} arquivo(s)`);
  }
  console.log('');

  // ── 7.4 Mapear áreas → testes ─────────────────────────────────────

  console.log('🔗 Etapa 4: Mapeando áreas → testes...\n');

  const { matches: testMatches, globalAlerts } = mapAreasToTests(areas, regMap, testsDirs, featureDir, resolvedLayers, regMapLayersUsed);

  console.log(`   📊 ${testMatches.length} mapeamento(s) encontrado(s)`);
  for (const m of testMatches) {
    const confIcon = m.confidence === 'high' ? '🟢' : m.confidence === 'medium-high' ? '🔵' : m.confidence === 'medium' ? '🟡' : '🟠';
    const layerTag = m.layer ? ` [${m.layer}]` : '';
    console.log(`   ${confIcon} [${m.strategy}]${layerTag} ${m.area} → ${m.test}`);
  }
  if (globalAlerts.length > 0) {
    console.log(`   ⚠️  ${globalAlerts.length} alerta(s) de impacto global`);
    for (const alert of globalAlerts) {
      console.log(`      🔴 ${alert.message}`);
    }
  }
  console.log('');

  // ── 7.5 Classificar risco ──────────────────────────────────────────

  console.log('⚖️  Etapa 5: Classificando risco...\n');

  const regressionTests: RegressionTestEntry[] = testMatches.map(match => {
    const risk = classifyRisk(match, testMatches, prResult.workItems, areas);
    const area = areas.find(a => a.name === match.area);

    // Coletar tags do regression-map para este teste
    let tags: string[] = [];
    if (regMap) {
      for (const [, mapArea] of Object.entries(regMap.areas)) {
        if ((mapArea.tests ?? []).includes(match.test) || (mapArea.features ?? []).includes(match.test)) {
          tags = [...tags, ...(mapArea.tags ?? [])];
        }
      }
    }
    tags = [...new Set(tags)];

    // Resolver sourceFile: para estratégias indiretas, buscar da área de origem
    let resolvedSourceFile = area?.sourceFiles[0] || '—';
    if (match.sourceArea && match.sourceArea !== match.area) {
      const originArea = areas.find(a => a.name === match.sourceArea);
      if (originArea) {
        resolvedSourceFile = originArea.sourceFiles[0] || resolvedSourceFile;
      }
    }

    // Compor reason descritivo
    const reason = match.detail
      ? `${match.area} ← ${match.detail} (${match.strategy})`
      : `${match.area} (${match.strategy})`;

    // Coletar todas as áreas que este match cobre (área do PR + área do mapa se diferente)
    const matchCoveredAreas = [match.area];
    if (match.mapAreaKey && match.mapAreaKey !== match.area) {
      matchCoveredAreas.push(match.mapAreaKey);
    }

    return {
      test: match.test,
      tags,
      risk,
      reason,
      confidence: match.confidence,
      sourceFile: resolvedSourceFile,
      layer: match.layer,
      coveredAreas: [...new Set(matchCoveredAreas)],
    };
  });

  // Deduplicar (mesmo teste pode aparecer de múltiplas áreas — manter o de maior risco, acumular coveredAreas)
  const deduped = new Map<string, RegressionTestEntry>();
  const riskOrder: RiskLevel[] = ['critical', 'high', 'medium', 'low', 'gap'];
  for (const entry of regressionTests) {
    const existing = deduped.get(entry.test);
    if (!existing) {
      deduped.set(entry.test, entry);
    } else {
      // Merge coveredAreas de todas as entradas
      const mergedAreas = new Set([...(existing.coveredAreas || []), ...(entry.coveredAreas || [])]);
      if (riskOrder.indexOf(entry.risk) < riskOrder.indexOf(existing.risk)) {
        deduped.set(entry.test, { ...entry, coveredAreas: [...mergedAreas] });
      } else {
        existing.coveredAreas = [...mergedAreas];
      }
    }
  }
  const finalTests = [...deduped.values()];

  // Contar por nível
  const countByRisk = (level: RiskLevel) => finalTests.filter(t => t.risk === level).length;
  console.log(`   🔴 Crítico:   ${countByRisk('critical')}`);
  console.log(`   🟠 Alto:      ${countByRisk('high')}`);
  console.log(`   🟡 Médio:     ${countByRisk('medium')}`);
  console.log(`   🟢 Baixo:     ${countByRisk('low')}`);
  console.log('');

  // ── Detectar gaps ──────────────────────────────────────────────────

  const coveredAreas = new Set(finalTests.flatMap(t => t.coveredAreas || []));

  // Consultar coverage do regression-map para enriquecer gaps
  const mapCoverage = new Map<string, string>();
  if (regMap) {
    for (const [areaKey, mapArea] of Object.entries(regMap.areas)) {
      if (mapArea.coverage) {
        mapCoverage.set(areaKey, mapArea.coverage);
      }
    }
  }

  // Contexto de camadas ativas para gaps
  const activeLayerNames = regMapLayersUsed?.map(l => l.name.toUpperCase()).join(', ') || '';
  const scopeDescForGaps: Record<string, string> = {
    page: 'interface de usuário',
    api: 'endpoint de API',
    service: 'serviço interno',
    component: 'componente',
    model: 'modelo de dados',
    global: 'configuração global',
  };

  const gaps = areas
    .filter(a => !coveredAreas.has(a.name) && a.name !== '*global*')
    .flatMap(a => {
      const existingCoverage = mapCoverage.get(a.name);
      const isKnownGap = existingCoverage === 'none';
      const riskLabel = a.scope === 'page' || a.scope === 'api' ? '🔴 alto risco' : a.scope === 'service' ? '🟠 médio risco' : '🟡 baixo risco';
      const scopeDesc = scopeDescForGaps[a.scope] || a.scope;
      const layerCtx = activeLayerNames ? ` ${activeLayerNames}` : '';

      let note: string;
      if (isKnownGap) {
        note = `⚠️ GAP PRÉ-EXISTENTE — sem cobertura${layerCtx} para "${a.name}" (${scopeDesc}). ${riskLabel}`;
      } else {
        note = `Criar testes${layerCtx} para "${a.name}" (${scopeDesc}). ${riskLabel}`;
      }

      return a.sourceFiles.map(f => ({
        file: f,
        area: a.name,
        note,
      }));
    });

  if (gaps.length > 0) {
    console.log(`   ⚪ Gaps:      ${gaps.length}`);
    const knownGapCount = gaps.filter(g => g.note.includes('PRÉ-EXISTENTE')).length;
    const newGapCount = gaps.length - knownGapCount;
    if (knownGapCount > 0) {
      console.log(`      ⚠️  ${knownGapCount} gap(s) pré-existente(s) no regression-map`);
    }
    if (newGapCount > 0) {
      console.log(`      🆕 ${newGapCount} gap(s) novo(s) detectado(s) neste PR`);
    }
    for (const gap of gaps) {
      console.log(`      • ${gap.file} → ${gap.area}`);
    }
    console.log('');
  }

  // ── 7.6 Gerar relatório ──────────────────────────────────────────

  const commands = generateExecutionCommands(finalTests, areas, framework, regMap, globalAlerts);

  // Calcular confiança média
  const confValues: Record<string, number> = { 'high': 4, 'medium-high': 3, 'medium': 2, 'low': 1 };
  const avgConf = finalTests.length > 0
    ? (finalTests.reduce((sum, t) => sum + (confValues[t.confidence] || 1), 0) / finalTests.length).toFixed(1)
    : '0';
  const avgConfLabel = parseFloat(avgConf) >= 3.5 ? 'Alta' : parseFloat(avgConf) >= 2.5 ? 'Média-Alta' : parseFloat(avgConf) >= 1.5 ? 'Média' : 'Baixa';

  const plan: RegressionPlan = {
    pr: prResult.pr,
    areas,
    tests: finalTests,
    gaps,
    commands,
    globalAlerts,
    summary: {
      filesChanged: prResult.files.length,
      areasImpacted: areas.length,
      testsImpacted: finalTests.length,
      gapsFound: gaps.length,
      avgConfidence: avgConfLabel,
    },
  };

  if (!params.dryRun) {
    const outputPath = params.output || path.resolve(basePath, DEFAULT_OUTPUT_DIR, `PR-${prResult.pr.id}_regression_plan.md`);
    const outDir = path.dirname(outputPath);
    if (!fs.existsSync(outDir)) {
      fs.mkdirSync(outDir, { recursive: true });
    }

    const skipMd = params.json && !params.mdOnly;
    if (!skipMd) {
      const usDir = path.resolve(basePath, `${root}/manual_test/US`);
      const markdown = generateMarkdownReport(plan, framework, featureDir, usDir, regMapLayersUsed);
      fs.writeFileSync(outputPath, markdown, 'utf-8');
      console.log(`📄 Relatório salvo em: ${outputPath}`);
    } else {
      console.log(`📄 MD não gerado (--json sem --md-only). O agente IA compõe o relatório.`);
    }

    // ── Saída JSON estruturada para o agente IA ───────────────────────
    if (params.json) {
      const coveredAreaNames = new Set(finalTests.flatMap(t => t.coveredAreas || []));

      // Top impact: arquivos com mais testes mapeados e maior risco
      const fileImpact = new Map<string, { area: string; scope: FunctionalAreaScope; testCount: number; risk: RiskLevel }>();
      for (const t of finalTests) {
        const existing = fileImpact.get(t.sourceFile);
        const currentRiskIdx = riskOrder.indexOf(t.risk);
        if (!existing || currentRiskIdx < riskOrder.indexOf(existing.risk)) {
          const area = areas.find(a => a.sourceFiles.includes(t.sourceFile));
          fileImpact.set(t.sourceFile, {
            area: area?.name || '—',
            scope: area?.scope || 'global',
            testCount: (existing?.testCount || 0) + 1,
            risk: t.risk,
          });
        } else {
          existing.testCount++;
        }
      }
      const topImpactFiles = [...fileImpact.entries()]
        .sort((a, b) => riskOrder.indexOf(a[1].risk) - riskOrder.indexOf(b[1].risk) || b[1].testCount - a[1].testCount)
        .slice(0, 5)
        .map(([filePath, info]) => ({
          path: filePath,
          area: info.area,
          scope: info.scope,
          test_count: info.testCount,
          risk: info.risk,
        }));

      // Áreas sem cobertura para a IA analisar
      const uncoveredAreas = areas
        .filter(a => !coveredAreaNames.has(a.name) && a.name !== '*global*')
        .map(a => ({ name: a.name, scope: a.scope, files: a.sourceFiles }));

      const jsonOutput: RegressionAnalysisJson = {
        pr: prResult.pr,
        files: prResult.files,
        areas,
        tests: finalTests,
        gaps,
        commands,
        summary: plan.summary,
        top_impact_files: topImpactFiles,
        uncovered_areas: uncoveredAreas,
      };

      const jsonPath = outputPath.replace(/\.md$/, '.json');
      fs.writeFileSync(jsonPath, JSON.stringify(jsonOutput, null, 2), 'utf-8');
      console.log(`📊 JSON para agente salvo em: ${jsonPath}`);
    }
  } else {
    console.log('📄 Dry-run: relatório não salvo (use sem --dry-run para salvar).');
  }

  // ── 7.7 Resumo no terminal ──────────────────────────────────────────

  console.log('\n✅ ═══════════════════════════════════════════════════════════════');
  console.log('   Análise de Regressão Concluída');
  console.log('═══════════════════════════════════════════════════════════════\n');

  console.log(`   PR:              #${plan.pr.id} — ${truncate(plan.pr.title, 50)}`);
  console.log(`   Arquivos:        ${plan.summary.filesChanged}`);
  console.log(`   Áreas:           ${plan.summary.areasImpacted}`);
  console.log(`   Testes:          ${plan.summary.testsImpacted}`);
  console.log(`   Gaps:            ${plan.summary.gapsFound}`);
  console.log(`   Confiança:       ${plan.summary.avgConfidence}`);
  console.log('');

  // Alertas globais
  if (globalAlerts.length > 0) {
    console.log('⚠️  Alertas de Impacto Global:');
    for (const alert of globalAlerts) {
      console.log(`   🔴 [${alert.strategy}] ${alert.sourceFile}`);
    }
    console.log('');
  }

  // Tabela de testes
  if (finalTests.length > 0) {
    console.log('📋 Testes Impactados:');
    console.log('─'.repeat(105));
    console.log(
      padRight('Layer', 10) +
      padRight('Teste', 30) +
      padRight('Risco', 10) +
      padRight('Confiança', 14) +
      padRight('Área', 18) +
      padRight('Estratégia', 18) +
      padRight('Arquivo', 15)
    );
    console.log('─'.repeat(105));
    for (const t of finalTests) {
      const riskIcon = t.risk === 'critical' ? '🔴' : t.risk === 'high' ? '🟠' : t.risk === 'medium' ? '🟡' : '🟢';
      const area = (t.coveredAreas || [])[0] || t.reason.split(' ')[0] || '—';
      console.log(
        padRight(t.layer || '—', 10) +
        padRight(truncate(t.test, 28), 30) +
        padRight(`${riskIcon} ${t.risk}`, 10) +
        padRight(t.confidence, 14) +
        padRight(truncate(area, 16), 18) +
        padRight(t.reason.split('(')[1]?.replace(')', '') || '—', 18) +
        padRight(truncate(path.basename(t.sourceFile), 13), 15)
      );
    }
    console.log('─'.repeat(105));
  }

  // Comandos sugeridos
  console.log('\n🏷️ Comandos Sugeridos:');
  for (const cmd of plan.commands) {
    console.log(`   ${cmd.label}: ${cmd.command}`);
  }

  // Tabela de gaps no terminal
  if (gaps.length > 0) {
    console.log('');
    console.log('⚪ Gaps de Cobertura:');
    console.log('─'.repeat(95));
    console.log(
      padRight('Status', 16) +
      padRight('Arquivo', 40) +
      padRight('Área', 20) +
      padRight('Risco', 19)
    );
    console.log('─'.repeat(95));
    for (const gap of gaps) {
      const status = gap.note.includes('PRÉ-EXISTENTE') ? '⚠️  Existente' : '🆕 Novo';
      const riskMatch = gap.note.match(/(🔴 alto risco|🟠 médio risco|🟡 baixo risco)/);
      const risk = riskMatch ? riskMatch[1] : '—';
      console.log(
        padRight(status, 16) +
        padRight(truncate(gap.file, 38), 40) +
        padRight(truncate(gap.area, 18), 20) +
        padRight(risk, 19)
      );
    }
    console.log('─'.repeat(95));
    console.log('   💡 Use @fastqa:test_case_with_fastqa para criar testes para estes gaps');
  }
  console.log('');

  return plan;
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
  const hasFlag = (flag: string): boolean => args.includes(flag);

  const prUrl = getArg('--pr-url');
  const prIdStr = getArg('--pr-id');
  const repo = getArg('--repo');
  const appRepoPath = getArg('--app-repo-path');
  const targetBranch = getArg('--target-branch');
  const output = getArg('--output');
  const useGitLocal = hasFlag('--use-git-local');
  const dryRun = hasFlag('--dry-run');
  const json = hasFlag('--json');
  const mdOnly = hasFlag('--md-only');

  if (hasFlag('--help') || (!prUrl && !prIdStr && !appRepoPath)) {
    console.log('');
    console.log('Uso:');
    console.log('  npx tsx fastqa/scripts/regression/commands/analyze-pr-regression.command.ts [opções]');
    console.log('');
    console.log('Opções obrigatórias (uma das opções):');
    console.log('  --pr-url <url>            URL do PR (Azure DevOps)');
    console.log('  --pr-id <id> --repo <name> ID do PR + nome do repositório (Azure DevOps)');
    console.log('  --app-repo-path <path>    Caminho local do repo da aplicação (Git local)');
    console.log('');
    console.log('Opções adicionais:');
    console.log('  --target-branch <branch>  Branch alvo para comparação (padrão: develop)');
    console.log('  --output <path>           Caminho de saída do relatório');
    console.log('  --use-git-local           Forçar provedor Git local');
    console.log('  --dry-run                 Simular sem salvar relatório');
    console.log('  --json                    Gera saída JSON estruturada (pula MD, agente IA compõe relatório)');
    console.log('  --md-only                 Força geração do MD mesmo com --json (backward compat)');
    console.log('  --help                    Exibe esta ajuda');
    console.log('');
    console.log('Exemplos:');
    console.log('  # Via URL do Azure DevOps');
    console.log('  npx tsx analyze-pr-regression.command.ts \\');
    console.log('    --pr-url https://dev.azure.com/org/project/_git/repo/pullrequest/123');
    console.log('');
    console.log('  # Via ID + repo');
    console.log('  npx tsx analyze-pr-regression.command.ts --pr-id 123 --repo MyApp');
    console.log('');
    console.log('  # Via Git local');
    console.log('  npx tsx analyze-pr-regression.command.ts \\');
    console.log('    --app-repo-path C:\\Repos\\my-app --target-branch develop');
    console.log('');
    process.exit(hasFlag('--help') ? 0 : 1);
  }

  try {
    await analyzePrRegression({
      prUrl,
      prId: prIdStr ? parseInt(prIdStr, 10) : undefined,
      repo,
      appRepoPath,
      targetBranch,
      output,
      useGitLocal,
      dryRun,
      json,
      mdOnly,
    });
    process.exit(0);
  } catch (error) {
    console.error('\n❌ Erro na análise de regressão:');
    console.error(error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

export { analyzePrRegression };
