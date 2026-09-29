/**
 * ═══════════════════════════════════════════════════════════════════════════
 * FastQA — Comando: Gerar Regression Map
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * Varre o repositório de testes, infere áreas funcionais a partir dos
 * specs, features e page objects, e gera o regression-map.yaml.
 *
 * Uso:
 *   npx tsx fastqa/scripts/regression/commands/generate-regression-map.command.ts \
 *     [--output <path>] \
 *     [--merge]
 *
 * @module generate-regression-map
 */

import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'js-yaml';

import { deriveAreaName as deriveAppAreaName, isGenericAreaName, detectScope, GLOBAL_SCOPE_DIR_NAMES } from '../utils/area-name.utils';
import { buildDependencyGraph, analyzeAreaCoupling, detectMergeableAreas } from '../utils/dependency-graph.utils';
import { analyzeFileExports, isGenericFileName } from '../utils/export-analyzer.utils';
import type {
  RegressionMapConfig,
  RegressionMapArea,
  GenerateRegressionMapParams,
  EnrichmentContext,
  TestLayer,
} from '../types/regression.types';

// ─────────────────────────────────────────────────────────────────────
// Constantes
// ─────────────────────────────────────────────────────────────────────

const COMMAND_NAME = 'generate-regression-map';
const DEFAULT_OUTPUT = 'fastqa/scripts/regression-map.yaml';
const CONFIG_PATH = 'fastqa/scripts/project_config.json';
const ENRICHMENT_CONTEXT_PATH = 'fastqa/scripts/.enrichment-context.json';
const CACHE_PATH = 'fastqa/scripts/.regression-cache.json';

// ─────────────────────────────────────────────────────────────────────
// Tipos internos
// ─────────────────────────────────────────────────────────────────────

interface InferredArea {
  name: string;
  tests: Set<string>;
  features: Set<string>;
  tags: Set<string>;
  suggestedPatterns: Set<string>;
}

interface ProjectConfig {
  platform?: { type?: string };
  connectors?: { output?: { automation_framework?: string; language?: string } };
  folder_structure?: {
    root?: string;
    custom_paths?: {
      tests?: string;
      pages?: string;
      automation_root?: string;
      additional_test_layers?: Array<{ name: string; path: string }>;
    };
  };
}

// ─────────────────────────────────────────────────────────────────────
// Utilitários de varredura
// ─────────────────────────────────────────────────────────────────────

/** Lista recursivamente todos os arquivos de um diretório com extensão dada */
function walkDir(dir: string, extensions: string[]): string[] {
  const results: string[] = [];
  if (!fs.existsSync(dir)) return results;

  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      // Ignorar node_modules e pastas ocultas
      if (entry.name === 'node_modules' || entry.name.startsWith('.')) continue;
      results.push(...walkDir(fullPath, extensions));
    } else if (extensions.some(ext => entry.name.endsWith(ext))) {
      results.push(fullPath);
    }
  }
  return results;
}

/**
 * Normaliza nome de área funcional:
 * - lowercase
 * - remove extensão e sufixos comuns
 * - remove prefixos de tipo
 * - trata caracteres de URL (/, #, @) para evitar duplicatas
 *   (ex: describe('/#/login') e 'login.spec.ts' → mesma área 'login')
 */
function normalizeAreaName(raw: string): string {
  return raw
    .toLowerCase()
    .replace(/\.(spec|test|page|screen|steps|feature|e2e|integration)?(\.ts|\.tsx|\.js|\.jsx|\.py|\.java|\.cs|\.robot|\.feature)?$/i, '')
    // Sufixos compostos usados em specs de API/Unit (ex: loginApiSpec, insecuritySpec)
    .replace(/(api)?spec$/i, '')
    .replace(/(page|screen|controller|service|component|steps)$/i, '')
    .replace(/^(test_|spec_|e2e_)/i, '')
    // Inclui /, #, @ para tratar nomes derivados de URLs Angular (ex: /#/login → login)
    .replace(/[_.\/#@-]/g, '-')
    .trim()
    .replace(/-+/g, '-')
    .replace(/-+$/, '')
    .replace(/^-+/, '');
}

/** Extrai tags de um arquivo .feature */
function extractFeatureTags(filePath: string): string[] {
  const content = fs.readFileSync(filePath, 'utf-8');
  const tagRegex = /@[\w-]+/g;
  const matches = content.match(tagRegex);
  return matches ? [...new Set(matches)] : [];
}

/** Extrai nome do describe/test.describe de um spec file */
function extractSpecDescribe(filePath: string): string | null {
  const content = fs.readFileSync(filePath, 'utf-8');
  // Playwright/Jest: test.describe('Name', ...) ou describe('Name', ...)
  const match = content.match(/(?:test\.)?describe\s*\(\s*['"`]([^'"`]+)['"`]/);
  return match ? match[1] : null;
}

// ─────────────────────────────────────────────────────────────────────
// Varredura da Aplicação (App-Aware Patterns)
// ─────────────────────────────────────────────────────────────────────

/** Diretórios excluídos da varredura da aplicação */
const APP_EXCLUDE_DIRS = new Set([
  'node_modules', 'dist', 'build', '.git', 'coverage',
  '__mocks__', '__tests__', '.nyc_output', '.next', '.nuxt',
  'out', 'tmp', '.tmp', '.cache', '.vscode', '.idea',
]);

/** Extensões de código-fonte da aplicação */
const APP_SOURCE_EXTENSIONS = ['.ts', '.js', '.tsx', '.jsx', '.py', '.java', '.cs', '.go', '.rb'];

/**
 * Varre o repositório da aplicação e agrupa arquivos por área funcional.
 * Reutiliza a mesma lógica de `deriveAreaName` usada no analyze-pr-regression.
 * Quando o nome é genérico, tenta reclassificar via análise de exports.
 *
 * @returns objeto com appAreas, allAbsFiles (para grafo), fileToArea e globalFiles
 */
function scanAppStructure(
  appRepoPath: string,
  srcDirs?: string[]
): {
  appAreas: Map<string, Set<string>>;
  allAbsFiles: string[];
  fileToArea: Map<string, string>;
  globalFiles: string[];
} {
  const appAreas = new Map<string, Set<string>>();
  const fileToArea = new Map<string, string>();
  const globalFiles: string[] = [];

  // Determinar diretórios a varrer
  let dirsToScan: string[];
  if (srcDirs && srcDirs.length > 0) {
    dirsToScan = srcDirs.map(d => path.join(appRepoPath, d));
  } else {
    // Auto-detect: varrer raiz excluindo dirs de teste/build
    dirsToScan = [appRepoPath];
  }

  function walkAppDir(dir: string): string[] {
    const results: string[] = [];
    if (!fs.existsSync(dir)) return results;
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        const lower = entry.name.toLowerCase();
        // Excluir diretórios irrelevantes
        if (APP_EXCLUDE_DIRS.has(entry.name) || lower.startsWith('test') || lower.startsWith('.')) continue;
        results.push(...walkAppDir(fullPath));
      } else if (APP_SOURCE_EXTENSIONS.some(ext => entry.name.endsWith(ext))) {
        // Excluir arquivos de teste/spec dentro do código-fonte
        if (/\.(spec|test|e2e)\./i.test(entry.name)) continue;
        results.push(fullPath);
      }
    }
    return results;
  }

  const allAbsFiles: string[] = [];

  for (const dir of dirsToScan) {
    const files = walkAppDir(dir);
    allAbsFiles.push(...files);

    for (const absFilePath of files) {
      const relativePath = path.relative(appRepoPath, absFilePath).replace(/\\/g, '/');
      let areaName = deriveAppAreaName(relativePath);

      // Coletar arquivos globais para análise de cross-cutting posterior
      if (areaName === '*global*') {
        globalFiles.push(relativePath);
        fileToArea.set(relativePath, '*global*');
        continue;
      }

      if (!areaName) continue;

      // Fase 2: Se o nome derivado é genérico, tentar reclassificar via exports
      if (isGenericAreaName(areaName) || isGenericFileName(path.basename(absFilePath))) {
        const exportAnalysis = analyzeFileExports(absFilePath);
        if (exportAnalysis.inferredArea && exportAnalysis.confidence !== 'low') {
          areaName = exportAnalysis.inferredArea;
        }
      }

      fileToArea.set(relativePath, areaName);

      if (!appAreas.has(areaName)) {
        appAreas.set(areaName, new Set());
      }
      appAreas.get(areaName)!.add(relativePath);
    }
  }

  return { appAreas, allAbsFiles, fileToArea, globalFiles };
}

/**
 * Gera app_patterns precisos a partir dos caminhos reais da aplicação.
 *
 * Estratégia:
 * - Se há um subdiretório nomeado como a área, usa pattern de diretório
 * - Se múltiplos arquivos no mesmo diretório, padrão de dir
 * - Arquivos individuais, padrão por arquivo
 * - Sempre inclui genérico como fallback
 */
function generateSmartPatterns(appFiles: Set<string>, areaName: string): string[] {
  const patterns: string[] = [];
  const dirCounts = new Map<string, number>();

  for (const filePath of appFiles) {
    const dir = path.dirname(filePath);
    dirCounts.set(dir, (dirCounts.get(dir) || 0) + 1);

    // Verificar se há um diretório com o nome da área
    const segments = filePath.split('/');
    for (const seg of segments.slice(0, -1)) {
      if (seg.toLowerCase() === areaName.toLowerCase() ||
          seg.toLowerCase().replace(/[_-]/g, '') === areaName.replace(/[_-]/g, '')) {
        const dirPattern = `**/${seg}/**`;
        if (!patterns.includes(dirPattern)) {
          patterns.push(dirPattern);
        }
      }
    }
  }

  // Agrupar por diretório: se 2+ arquivos no mesmo dir, sugerir padrão de dir
  for (const [dir, count] of dirCounts) {
    if (count >= 2) {
      const dirPattern = `${dir}/**`;
      if (!patterns.includes(dirPattern)) {
        patterns.push(dirPattern);
      }
    } else {
      // Arquivo individual
      for (const filePath of appFiles) {
        if (path.dirname(filePath) === dir) {
          if (!patterns.includes(filePath)) {
            patterns.push(filePath);
          }
        }
      }
    }
  }

  // Fallback genérico (menor prioridade)
  const generic = `**/${areaName}*`;
  if (!patterns.includes(generic)) {
    patterns.push(generic);
  }

  return patterns;
}

/**
 * Deriva global_triggers dinamicamente a partir dos arquivos globais
 * detectados no repositório da aplicação.
 *
 * Quando `appRepoPath` é fornecido:
 *   1. Extrai diretórios-pai dos `globalFiles` já classificados como *global*
 *   2. Varre a raiz do repo buscando arquivos de infra (.env, Dockerfile, etc.)
 *   3. Detecta diretórios de 1º nível que casam com GLOBAL_SCOPE_DIR_NAMES
 *
 * Sem `appRepoPath`, retorna fallback mínimo universal.
 */
function deriveGlobalTriggers(globalFiles: string[], appRepoPath?: string): string[] {
  const triggers = new Set<string>();

  if (appRepoPath && globalFiles.length > 0) {
    // 1. Extrair diretórios dos arquivos já classificados como *global*
    for (const filePath of globalFiles) {
      const segments = filePath.split('/');
      // Pegar o diretório de 1º ou 2º nível significativo
      for (const seg of segments.slice(0, -1)) {
        const lower = seg.toLowerCase();
        if (GLOBAL_SCOPE_DIR_NAMES.has(lower) || /^(config|middleware|database|migration)/i.test(lower)) {
          triggers.add(`**/${seg}/**`);
        }
      }
    }

    // 2. Varrer diretórios de 1º nível contra GLOBAL_SCOPE_DIR_NAMES
    if (fs.existsSync(appRepoPath)) {
      const rootEntries = fs.readdirSync(appRepoPath, { withFileTypes: true });
      for (const entry of rootEntries) {
        if (entry.isDirectory() && GLOBAL_SCOPE_DIR_NAMES.has(entry.name.toLowerCase())) {
          triggers.add(`**/${entry.name}/**`);
        }
      }

      // 3. Detectar arquivos de infra na raiz
      for (const entry of rootEntries) {
        if (!entry.isFile()) continue;
        const name = entry.name;
        if (/^Dockerfile/i.test(name)) triggers.add('**/Dockerfile*');
        if (/^docker-compose/i.test(name)) triggers.add('**/docker-compose*');
        if (/^\.env/i.test(name)) triggers.add('**/.env*');
        if (/\.(tf|tfvars)$/i.test(name)) triggers.add('**/*.tf');
        if (/^Jenkinsfile/i.test(name)) triggers.add('**/Jenkinsfile*');
        if (/^azure-pipelines/i.test(name)) triggers.add('**/azure-pipelines*');
        if (/^\.gitlab-ci/i.test(name)) triggers.add('**/.gitlab-ci*');
      }

      // 4. Detectar diretórios CI/CD ocultos
      if (fs.existsSync(path.join(appRepoPath, '.github', 'workflows'))) {
        triggers.add('.github/workflows/**');
      }
      if (fs.existsSync(path.join(appRepoPath, '.gitlab'))) {
        triggers.add('.gitlab/**');
      }
    }
  }

  // Fallback mínimo: sempre incluir os 3 patterns mais universais
  triggers.add('**/.env*');
  triggers.add('**/Dockerfile*');
  triggers.add('**/docker-compose*');

  return [...triggers].sort();
}

// ─────────────────────────────────────────────────────────────────────
// Lógica Principal
// ─────────────────────────────────────────────────────────────────────

async function generateRegressionMap(params: GenerateRegressionMapParams): Promise<void> {
  console.log('\n🗺️  ═══════════════════════════════════════════════════════════════');
  console.log('   FastQA — Geração de Regression Map');
  console.log('═══════════════════════════════════════════════════════════════\n');

  const outputPath = params.output || DEFAULT_OUTPUT;

  // ── 1. Ler project_config.json ──────────────────────────────────────

  console.log('📋 Etapa 1: Lendo configuração do projeto...\n');

  let projectConfig: ProjectConfig = {};
  if (fs.existsSync(CONFIG_PATH)) {
    projectConfig = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf-8'));
    const framework = projectConfig.connectors?.output?.automation_framework || 'N/A';
    const platform = projectConfig.platform?.type || 'N/A';
    console.log(`   Framework:  ${framework}`);
    console.log(`   Plataforma: ${platform}`);
  } else {
    console.warn('   ⚠️  project_config.json não encontrado. Usando padrões.');
  }

  // Resolver caminhos
  const root = projectConfig.folder_structure?.root || 'fastqa';
  const customPaths = projectConfig.folder_structure?.custom_paths || {};

  // Diretórios de busca
  const testsDirs: string[] = [];
  const pagesDirs: string[] = [];

  if (customPaths.tests) testsDirs.push(customPaths.tests);
  if (customPaths.pages) pagesDirs.push(customPaths.pages);

  // Fallback: buscar nos diretórios padrão do FastQA
  const platformType = (projectConfig.platform?.type || 'web').toLowerCase();
  const autoRoot = customPaths.automation_root || `${root}/automated_test`;

  if (testsDirs.length === 0) {
    testsDirs.push(`${autoRoot}/${platformType}/tests`);
    testsDirs.push(`${autoRoot}/api/tests`);
  }
  if (pagesDirs.length === 0) {
    pagesDirs.push(`${autoRoot}/${platformType}/pages`);
    pagesDirs.push(`${autoRoot}/${platformType}/screens`);
  }

  const featureDir = `${root}/manual_test/test_cases`;

  console.log(`\n   Diretórios de testes:   ${testsDirs.filter(d => fs.existsSync(d)).join(', ') || '(nenhum encontrado)'}`);
  console.log(`   Diretórios de pages:    ${pagesDirs.filter(d => fs.existsSync(d)).join(', ') || '(nenhum encontrado)'}`);
  console.log(`   Diretório de features:  ${fs.existsSync(featureDir) ? featureDir : '(não encontrado)'}`);
  console.log('');

  // ── 2. Varrer diretórios ──────────────────────────────────────────

  console.log('🔍 Etapa 2: Varrendo repositório de testes...\n');

  const specExtensions = [
    '.spec.ts', '.spec.js', '.test.ts', '.test.js',
    '.spec.py', '.test.py', '.spec.java', '.spec.cs',
    // Padrão usado por frameworks como Frisby/Jest/Mocha (ex: loginApiSpec.ts)
    'Spec.ts', 'Spec.js',
  ];
  const pageExtensions = ['.page.ts', '.page.js', '.screen.ts', '.screen.js', '.page.py', '.screen.py', '.page.java', '.page.cs'];
  const featureExtensions = ['.feature'];

  const specFiles: string[] = [];
  /** Mapa layer → lista de spec files (para prefixo) */
  const layerSpecFiles = new Map<string, string[]>();

  // Camadas explícitas (CLI ou agent) têm prioridade sobre config
  const resolvedLayers: TestLayer[] = params.layers ?? [];

  // Se nenhuma camada explícita, montar a partir do config
  if (resolvedLayers.length === 0) {
    // Camada principal (e2e) vem dos diretórios já resolvidos
    resolvedLayers.push({ name: 'e2e', path: '__resolved_tests_dirs__' });

    // Camadas adicionais do project_config.json
    const additionalLayers = customPaths.additional_test_layers || [];
    for (const layer of additionalLayers) {
      if (layer.name && layer.path) {
        resolvedLayers.push({ name: layer.name, path: layer.path });
      }
    }
  }

  // Flag para identificar se há mais de uma camada (ativa prefixos)
  const multiLayer = resolvedLayers.length > 1;

  for (const layer of resolvedLayers) {
    let dirs: string[];
    if (layer.path === '__resolved_tests_dirs__') {
      // Camada principal usa os testsDirs já resolvidos do config
      dirs = testsDirs;
    } else {
      dirs = [layer.path];
    }

    const layerFiles: string[] = [];
    for (const dir of dirs) {
      layerFiles.push(...walkDir(dir, specExtensions));
    }
    layerSpecFiles.set(layer.name, layerFiles);
    specFiles.push(...layerFiles);

    if (layerFiles.length > 0) {
      console.log(`   📄 [${layer.name}] Specs encontrados: ${layerFiles.length} (${dirs.filter(d => fs.existsSync(d)).join(', ')})`);
    }
  }

  const pageFiles: string[] = [];
  for (const dir of pagesDirs) {
    pageFiles.push(...walkDir(dir, pageExtensions));
  }

  const featureFiles = walkDir(featureDir, featureExtensions);

  console.log(`   📄 Specs total:          ${specFiles.length}`);
  console.log(`   📄 Pages encontrados:    ${pageFiles.length}`);
  console.log(`   📄 Features encontrados: ${featureFiles.length}`);
  console.log('');

  if (specFiles.length === 0 && pageFiles.length === 0 && featureFiles.length === 0) {
    console.warn('⚠️  Nenhum arquivo de teste encontrado.');
    console.warn('   Verifique se os diretórios de testes estão corretos em project_config.json');
    console.warn('   ou se o projeto já possui testes automatizados/manuais.\n');
    return;
  }

  // ── 3. Inferir áreas funcionais ─────────────────────────────────────

  console.log('🧠 Etapa 3: Inferindo áreas funcionais...\n');

  const areasMap = new Map<string, InferredArea>();

  function getOrCreateArea(name: string): InferredArea {
    const normalized = normalizeAreaName(name);
    if (!normalized) return getOrCreateArea('general');
    if (!areasMap.has(normalized)) {
      areasMap.set(normalized, {
        name: normalized,
        tests: new Set(),
        features: new Set(),
        tags: new Set(),
        suggestedPatterns: new Set(),
      });
    }
    return areasMap.get(normalized)!;
  }

  // 3.1 — Specs: nome do arquivo → área (com prefixo de camada se multi-layer)
  for (const [layerName, files] of layerSpecFiles) {
    for (const specFile of files) {
      const basename = path.basename(specFile);
      const areaName = normalizeAreaName(basename);
      if (!areaName) continue;

      const area = getOrCreateArea(areaName);
      const testLabel = multiLayer ? `[${layerName}] ${basename}` : basename;
      area.tests.add(testLabel);
      area.suggestedPatterns.add(`**/${areaName}*`);

      // Tentar extrair describe para nome mais rico
      const describe = extractSpecDescribe(specFile);
      if (describe) {
        const descArea = normalizeAreaName(describe);
        if (descArea && descArea !== areaName) {
          // Se o describe contém o nome do arquivo ou vice-versa, mesclar na área do arquivo
          // Ex: 'changepassword' ⊂ 'privacy-security-change-password' → mesma área 'changepassword'
          const descNoDash = descArea.replace(/-/g, '');
          const areaNoDash = areaName.replace(/-/g, '');
          if (descNoDash.includes(areaNoDash) || areaNoDash.includes(descNoDash)) {
            // Mesclar: adicionar patterns do describe na área do arquivo
            area.suggestedPatterns.add(`**/${descArea}*`);
          } else {
            const da = getOrCreateArea(descArea);
            da.tests.add(testLabel);
            da.suggestedPatterns.add(`**/${descArea}*`);
          }
        }
      }
    }
  }

  // 3.2 — Page Objects: nome do page → área
  for (const pageFile of pageFiles) {
    const basename = path.basename(pageFile);
    const areaName = normalizeAreaName(basename);
    if (!areaName) continue;

    const area = getOrCreateArea(areaName);
    area.suggestedPatterns.add(`**/${areaName}*`);
    area.suggestedPatterns.add(`**/pages/${areaName}*`);
  }

  // 3.3 — Features: tags → áreas
  for (const featureFile of featureFiles) {
    const basename = path.basename(featureFile);
    const tags = extractFeatureTags(featureFile);

    for (const tag of tags) {
      // Ignorar tags genéricas
      if (['@smoke', '@regression', '@critical', '@e2e', '@wip', '@skip', '@ignore'].includes(tag.toLowerCase())) {
        continue;
      }

      const areaName = normalizeAreaName(tag.replace('@', ''));
      if (!areaName) continue;

      const area = getOrCreateArea(areaName);
      area.features.add(basename);
      area.tags.add(tag);
      area.suggestedPatterns.add(`**/${areaName}*`);
    }

    // Também inferir área pelo nome do feature file
    const featureArea = normalizeAreaName(basename);
    if (featureArea) {
      const area = getOrCreateArea(featureArea);
      area.features.add(basename);
    }
  }

  console.log(`   🗂️  Áreas funcionais detectadas: ${areasMap.size}`);
  for (const [name, area] of areasMap) {
    console.log(`      • ${name}: ${area.tests.size} tests, ${area.features.size} features, ${area.tags.size} tags`);
  }
  console.log('');

  // ── 3.5. Varrer aplicação para app_patterns precisos ────────────────

  let appAreasMap: Map<string, Set<string>> | null = null;
  let fileToArea: Map<string, string> | null = null;
  let areaCouplingMap: Map<string, import('../utils/dependency-graph.utils').AreaCoupling> | null = null;
  let mergeableAreas: Map<string, string> | null = null;
  let depGraphRef: import('../utils/dependency-graph.utils').DependencyGraph | null = null;
  let globalFilesRef: string[] = [];
  const uncoveredAppAreas: string[] = [];

  if (params.appRepoPath && fs.existsSync(params.appRepoPath)) {
    console.log('🏗️  Etapa 3.5: Varrendo repositório da aplicação...\n');
    console.log(`   📂 App repo: ${params.appRepoPath}`);
    if (params.appSrcDirs?.length) {
      console.log(`   📁 Diretórios fonte: ${params.appSrcDirs.join(', ')}`);
    } else {
      console.log('   📁 Diretórios fonte: auto-detect (excluindo node_modules, dist, test*, etc.)');
    }

    const scanResult = scanAppStructure(params.appRepoPath, params.appSrcDirs);
    appAreasMap = scanResult.appAreas;
    fileToArea = scanResult.fileToArea;
    console.log(`\n   🗂️  Áreas da aplicação detectadas: ${appAreasMap.size}`);

    // ── 3.6. Grafo de dependências ──────────────────────────────────────

    console.log('\n🔗 Etapa 3.6: Analisando dependências entre módulos...\n');

    const depGraph = buildDependencyGraph(scanResult.allAbsFiles, params.appRepoPath);
    depGraphRef = depGraph;
    globalFilesRef = scanResult.globalFiles;
    const edgeCount = [...depGraph.imports.values()].reduce((sum, deps) => sum + deps.size, 0);
    console.log(`   📊 Grafo: ${depGraph.imports.size} módulos, ${edgeCount} dependências`);

    // Analisar acoplamento entre áreas
    areaCouplingMap = analyzeAreaCoupling(depGraph, fileToArea, scanResult.globalFiles);

    // Contar shared modules
    const sharedCount = [...areaCouplingMap.values()].filter(c => c.shared).length;
    if (sharedCount > 0) {
      console.log(`   📦 Módulos shared (importados por 3+ áreas): ${sharedCount}`);
    }

    // Refinar cross-cutting: verificar quais *global* são realmente targeted
    const globalCoupling = areaCouplingMap.get('*global*');
    if (globalCoupling && globalCoupling.impactScope === 'targeted') {
      console.log(`   🎯 Cross-cutting refinado: ${scanResult.globalFiles.length} arquivo(s) globais → impacto em ${globalCoupling.impactedAreas.length} área(s) específica(s)`);
      for (const area of globalCoupling.impactedAreas) {
        console.log(`      • ${area}`);
      }
    }

    // ── 3.7. Fusão de áreas acopladas ───────────────────────────────────

    mergeableAreas = detectMergeableAreas(areaCouplingMap);

    if (mergeableAreas.size > 0) {
      console.log(`\n🔄 Etapa 3.7: Fusão de áreas acopladas (${mergeableAreas.size} merge(s))...\n`);

      for (const [secondary, primary] of mergeableAreas) {
        console.log(`   🔗 "${secondary}" → fundida em "${primary}"`);

        // Mover arquivos da área secundária para a primária
        const secondaryFiles = appAreasMap.get(secondary);
        if (secondaryFiles) {
          if (!appAreasMap.has(primary)) {
            appAreasMap.set(primary, new Set());
          }
          for (const f of secondaryFiles) {
            appAreasMap.get(primary)!.add(f);
            fileToArea.set(f, primary);
          }
          appAreasMap.delete(secondary);
        }

        // Se a área secundária também estava nos testes, migrar pro primary
        if (areasMap.has(secondary)) {
          const secondaryArea = areasMap.get(secondary)!;
          const primaryArea = getOrCreateArea(primary);
          for (const t of secondaryArea.tests) primaryArea.tests.add(t);
          for (const f of secondaryArea.features) primaryArea.features.add(f);
          for (const t of secondaryArea.tags) primaryArea.tags.add(t);
          for (const p of secondaryArea.suggestedPatterns) primaryArea.suggestedPatterns.add(p);
          areasMap.delete(secondary);
        }
      }
    }

    // Cruzar áreas da app com áreas de teste
    let matchedCount = 0;
    for (const [appArea, files] of appAreasMap) {
      if (areasMap.has(appArea)) {
        matchedCount++;
        // Substituir suggestedPatterns genéricos por smart patterns reais
        const area = areasMap.get(appArea)!;
        const smartPatterns = generateSmartPatterns(files, appArea);
        area.suggestedPatterns = new Set(smartPatterns);
      } else {
        uncoveredAppAreas.push(appArea);
      }
    }

    console.log(`\n   ✅ Áreas cruzadas (app ↔ testes): ${matchedCount}`);
    if (uncoveredAppAreas.length > 0) {
      console.log(`   ⚠️  Áreas da app sem testes: ${uncoveredAppAreas.length}`);
    }
    console.log('');
  } else if (params.appRepoPath) {
    console.warn(`   ⚠️  Caminho da aplicação não encontrado: ${params.appRepoPath}\n`);
  }

  // ── 4. Gerar regression-map.yaml ─────────────────────────────────────

  console.log('📝 Etapa 4: Gerando regression-map.yaml...\n');

  // Se --merge e mapa existente, preservar app_patterns customizados
  let existingMap: RegressionMapConfig | null = null;
  if (params.merge && fs.existsSync(outputPath)) {
    const content = fs.readFileSync(outputPath, 'utf-8');
    existingMap = yaml.load(content) as RegressionMapConfig;
    console.log('   📂 Mapa existente detectado — modo merge ativado');
    console.log(`      Áreas existentes: ${Object.keys(existingMap.areas || {}).length}`);
    console.log('');
  }

  const newAreas: Record<string, RegressionMapArea> = {};

  for (const [name, area] of areasMap) {
    const existingArea = existingMap?.areas?.[name];
    const coupling = areaCouplingMap?.get(name);

    newAreas[name] = {
      description: existingArea?.description || `# TODO: descrever a área "${name}"`,
      app_patterns: existingArea?.app_patterns || [...area.suggestedPatterns],
      tests: [...new Set([...(existingArea?.tests || []), ...area.tests])],
      features: [...new Set([...(existingArea?.features || []), ...area.features])],
      tags: [...new Set([...(existingArea?.tags || []), ...area.tags])],
      coverage: area.tests.size > 0 && area.features.size > 0 ? 'full' : (area.tests.size > 0 || area.features.size > 0 ? 'partial' : 'none'),
      // Campos do grafo de dependências (Fase 1)
      ...(coupling?.dependencies?.length ? { dependencies: coupling.dependencies } : {}),
      ...(coupling?.dependents?.length ? { dependents: coupling.dependents } : {}),
      ...(coupling?.shared ? { shared: true } : {}),
      ...(coupling?.impactScope === 'targeted' ? {
        impact_scope: 'targeted' as const,
        impacted_areas: coupling.impactedAreas,
      } : {}),
    };
  }

  // Se merge, manter áreas existentes que não foram re-detectadas
  if (existingMap?.areas) {
    for (const [name, existingArea] of Object.entries(existingMap.areas)) {
      if (!newAreas[name]) {
        newAreas[name] = existingArea;
      }
    }
  }

  // ── 4.1. Incluir áreas gap (--include-gaps) ──────────────────────────

  /** Escopos relevantes para gaps (exclui componentes visuais puros) */
  const GAP_RELEVANT_SCOPES = new Set(['page', 'api', 'service', 'model', 'global']);

  let gapAreasIncluded = 0;
  let gapAreasFiltered = 0;

  if (params.includeGaps && appAreasMap && uncoveredAppAreas.length > 0) {
    console.log('   📋 Incluindo áreas gap relevantes no mapa...\n');

    for (const gapAreaName of uncoveredAppAreas) {
      // Já existe no mapa (ex: via merge)
      if (newAreas[gapAreaName]) continue;

      const files = appAreasMap.get(gapAreaName);
      if (!files || files.size === 0) continue;

      // Detectar scope da área via seus arquivos
      const sampleFile = [...files][0];
      const scope = detectScope(sampleFile);

      // Filtrar por relevância: apenas page, api, service, model, global
      if (!GAP_RELEVANT_SCOPES.has(scope)) {
        gapAreasFiltered++;
        continue;
      }

      const coupling = areaCouplingMap?.get(gapAreaName);
      const smartPatterns = generateSmartPatterns(files, gapAreaName);

      newAreas[gapAreaName] = {
        description: `# GAP: área detectada na aplicação sem testes (scope: ${scope})`,
        app_patterns: smartPatterns,
        tests: [],
        features: [],
        tags: [],
        coverage: 'none',
        ...(coupling?.dependencies?.length ? { dependencies: coupling.dependencies } : {}),
        ...(coupling?.dependents?.length ? { dependents: coupling.dependents } : {}),
        ...(coupling?.shared ? { shared: true } : {}),
      };
      gapAreasIncluded++;
    }

    console.log(`      ✅ ${gapAreasIncluded} áreas gap incluídas (relevantes: page/api/service/model/global)`);
    if (gapAreasFiltered > 0) {
      console.log(`      ⏭️  ${gapAreasFiltered} áreas visuais/componentes omitidas (baixo risco isolado)`);
    }
    console.log('');
  }

  const derivedTriggers = existingMap?.global_triggers || deriveGlobalTriggers(globalFilesRef, params.appRepoPath);

  console.log(`   🌐 Global triggers: ${derivedTriggers.length} patterns`);
  for (const t of derivedTriggers) {
    console.log(`      • ${t}`);
  }
  console.log('');

  // Separar áreas cobertas e gaps para geração YAML com seções visuais
  const coveredAreaNames = new Set<string>();
  const gapAreaNames = new Set<string>();

  for (const [name, area] of Object.entries(newAreas)) {
    if (area.coverage === 'none') {
      gapAreaNames.add(name);
    } else {
      coveredAreaNames.add(name);
    }
  }

  // Ordenar: áreas cobertas primeiro, gaps depois
  const orderedAreas: Record<string, RegressionMapArea> = {};
  for (const name of [...coveredAreaNames].sort()) {
    orderedAreas[name] = newAreas[name];
  }
  for (const name of [...gapAreaNames].sort()) {
    orderedAreas[name] = newAreas[name];
  }

  const mapConfig: RegressionMapConfig = {
    version: '1.0',
    layers_used: resolvedLayers.map(l => ({
      name: l.name,
      path: l.path === '__resolved_tests_dirs__' ? (testsDirs[0] || l.path) : l.path,
    })),
    areas: orderedAreas,
    global_triggers: derivedTriggers,
  };

  const yamlOpts = {
    indent: 2,
    lineWidth: 120,
    noRefs: true,
    quotingType: '"' as const,
    forceQuotes: false,
  };

  let yamlBody = yaml.dump(mapConfig, yamlOpts);

  // Injetar comentário de seção GAP antes da primeira área gap no YAML
  if (gapAreaNames.size > 0) {
    const firstGap = [...gapAreaNames].sort()[0];
    const gapMarker = `  ${firstGap}:`;
    const gapComment = [
      `  # ═══════════════════════════════════════════════════════════════════════`,
      `  # GAPS — Áreas da aplicação sem cobertura de teste (${gapAreaNames.size} áreas)`,
      `  # Filtradas por relevância: page, api, service, model, global`,
      `  # Use @fastqa:test_case_with_fastqa para criar testes para estas áreas.`,
      `  # ─────────────────────────────────────────────────────────────────────`,
    ].join('\n');
    yamlBody = yamlBody.replace(gapMarker, gapComment + '\n' + gapMarker);
  }

  // Gerar YAML com comentários de cabeçalho
  const yamlContent = [
    '# ═══════════════════════════════════════════════════════════════════════════',
    '# FastQA — Regression Map',
    '# ═══════════════════════════════════════════════════════════════════════════',
    '# Conecta áreas funcionais da aplicação aos testes existentes.',
    `# Gerado por: @fastqa:generate_regression_map`,
    `# Última atualização: ${new Date().toISOString()}`,
    '#',
    '# IMPORTANTE: Revise os app_patterns de cada área.',
    '# Padrões marcados com "# TODO" foram sugeridos automaticamente.',
    '# ───────────────────────────────────────────────────────────────────────────',
    '',
    yamlBody,
  ].join('\n');

  // Garantir diretório de output
  const outDir = path.dirname(outputPath);
  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }

  fs.writeFileSync(outputPath, yamlContent, 'utf-8');

  // ── 4.5. Gerar enrichment context (--enrich) ─────────────────────────

  if (params.enrich && params.appRepoPath && fileToArea) {
    console.log('🤖 Etapa 4.5: Gerando contexto de enriquecimento para IA...\n');

    const enrichment: EnrichmentContext = {
      ambiguous_files: [],
      cross_cutting: [],
      uncovered_app_areas: uncoveredAppAreas,
      low_confidence_areas: [],
    };

    // Coletar arquivos com nomes genéricos que foram reclassificados (ou não)
    for (const [relPath, area] of fileToArea) {
      const fileName = path.basename(relPath);
      if (isGenericFileName(fileName) || isGenericAreaName(area)) {
        const absPath = path.join(params.appRepoPath, relPath);
        const analysis = analyzeFileExports(absPath);
        enrichment.ambiguous_files.push({
          path: relPath,
          exports: analysis.exportNames.slice(0, 15), // limitar para IA
          current_area: area,
          inferred_area: analysis.inferredArea,
          confidence: analysis.confidence,
        });
      }
    }

    // Coletar cross-cutting files para revisão de escopo
    if (areaCouplingMap && depGraphRef) {
      for (const globalFile of globalFilesRef) {
        const importers = [...(depGraphRef.importedBy.get(globalFile) || [])];
        const importerAreas = [...new Set(importers.map(f => fileToArea?.get(f)).filter(Boolean))] as string[];

        enrichment.cross_cutting.push({
          path: globalFile,
          importedBy: importers.slice(0, 10),
          current_scope: 'global',
          suggested_scope: importerAreas.length <= 2 && importerAreas.length > 0 ? 'targeted' : 'global',
          impacted_areas: importerAreas,
        });
      }
    }

    // Coletar áreas com nomes de ticket (baixa confiança)
    for (const [areaName, area] of areasMap) {
      if (/^(pbi|us|bug|task|issue|story|feat|fix)[-_]?\d+$/i.test(areaName)) {
        enrichment.low_confidence_areas.push({
          area: areaName,
          tests: [...area.tests],
          reason: 'area-name-from-ticket-id',
        });
      }
    }

    // Salvar
    const enrichDir = path.dirname(ENRICHMENT_CONTEXT_PATH);
    if (!fs.existsSync(enrichDir)) {
      fs.mkdirSync(enrichDir, { recursive: true });
    }
    fs.writeFileSync(ENRICHMENT_CONTEXT_PATH, JSON.stringify(enrichment, null, 2), 'utf-8');

    console.log(`   📄 Enrichment context: ${ENRICHMENT_CONTEXT_PATH}`);
    console.log(`      Arquivos ambíguos:       ${enrichment.ambiguous_files.length}`);
    console.log(`      Cross-cutting a revisar: ${enrichment.cross_cutting.length}`);
    console.log(`      Áreas sem cobertura:     ${enrichment.uncovered_app_areas.length}`);
    console.log(`      Áreas baixa confiança:   ${enrichment.low_confidence_areas.length}`);
    console.log('');
  }

  // ── 5. Resumo ─────────────────────────────────────────────────────────

  console.log('✅ ═══════════════════════════════════════════════════════════════');
  console.log('   Regression Map Gerado');
  console.log('═══════════════════════════════════════════════════════════════\n');
  console.log(`   📄 Arquivo:         ${outputPath}`);
  const coveredCount = coveredAreaNames.size;
  const gapCount = gapAreaNames.size;
  console.log(`   🗂️  Áreas:           ${Object.keys(newAreas).length}${gapCount > 0 ? ` (${coveredCount} cobertas + ${gapCount} gaps)` : ''}`);
  const allMappedTests = [...new Set(Object.values(newAreas).flatMap(a => a.tests))];
  const specsFoundTotal = specFiles.length;
  const unmapped = specsFoundTotal - allMappedTests.length;
  console.log(`   📄 Testes mapeados: ${allMappedTests.length} / ${specsFoundTotal} specs encontrados${unmapped > 0 ? ` (⚠️ ${unmapped} não classificados)` : ''}`);
  console.log(`   📋 Features:        ${[...new Set(Object.values(newAreas).flatMap(a => a.features))].length}`);
  console.log(`   🏷️  Tags:            ${[...new Set(Object.values(newAreas).flatMap(a => a.tags))].length}`);

  // Contagem por camada (sempre mostrar)
  if (layerSpecFiles.size > 0) {
    console.log('');
    console.log('   📊 Testes por camada:');
    for (const [layerName, files] of layerSpecFiles) {
      // Contar specs desta camada que estão no mapa
      const layerMapped = allMappedTests.filter(t => {
        const cleanName = multiLayer ? t.replace(`[${layerName}] `, '') : t;
        return files.some(f => path.basename(f) === cleanName);
      }).length;
      console.log(`      [${layerName}]: ${layerMapped} mapeados / ${files.length} encontrados`);
    }
  }
  console.log('');

  // Listar app_patterns que precisam de revisão
  const needsReview = Object.entries(newAreas)
    .filter(([, a]) => typeof a.description === 'string' && a.description.startsWith('# TODO'));

  if (appAreasMap) {
    // App-aware mode: mostrar qualidade dos patterns
    const smartCount = Object.values(newAreas).filter(a =>
      a.app_patterns.some(p => !p.startsWith('**/') || p.includes('/'))
    ).length;
    console.log(`   🏗️  App-aware patterns: ${smartCount} áreas com patterns precisos`);

    // Mostrar stats do grafo de dependências
    if (areaCouplingMap) {
      const withDeps = Object.values(newAreas).filter(a => a.dependencies && a.dependencies.length > 0).length;
      const sharedAreas = Object.values(newAreas).filter(a => a.shared).length;
      const targetedAreas = Object.values(newAreas).filter(a => a.impact_scope === 'targeted').length;
      console.log(`   🔗 Grafo de dependências: ${withDeps} áreas com dependências mapeadas`);
      if (sharedAreas > 0) console.log(`   📦 Módulos shared: ${sharedAreas}`);
      if (targetedAreas > 0) console.log(`   🎯 Cross-cutting refinados: ${targetedAreas} (targeted em vez de global)`);
    }

    if (mergeableAreas && mergeableAreas.size > 0) {
      console.log(`   🔄 Áreas fundidas: ${mergeableAreas.size} (por dependência bidirecional)`);
    }

    if (needsReview.length > 0) {
      console.log(`   ⚠️  ${needsReview.length} área(s) com patterns genéricos (sem match na app)`);
    }
    if (uncoveredAppAreas.length > 0) {
      if (gapAreasIncluded > 0) {
        console.log(`   📋 Gaps incluídos:    ${gapAreasIncluded} áreas relevantes (--include-gaps)`);
        if (gapAreasFiltered > 0) {
          console.log(`   ⏭️  Gaps omitidos:    ${gapAreasFiltered} componentes visuais (baixo risco)`);
        }
      } else {
        console.log(`\n   ⚠️  Áreas da app sem cobertura: ${uncoveredAppAreas.length}`);
        console.log(`      Use --include-gaps para inclui-las no mapa (filtradas por relevância)`);
        for (const area of uncoveredAppAreas.slice(0, 10)) {
          console.log(`      • ${area}`);
        }
        if (uncoveredAppAreas.length > 10) {
          console.log(`      ... e mais ${uncoveredAppAreas.length - 10} áreas`);
        }
      }
    }
  } else if (needsReview.length > 0) {
    console.log('   ⚠️  Áreas que precisam de revisão manual (app_patterns):');
    for (const [name] of needsReview) {
      console.log(`      • ${name}`);
    }
    console.log('\n   Edite o arquivo e ajuste os app_patterns para refletir os paths do código da aplicação.');
    console.log('   💡 Use --app-repo-path para gerar patterns precisos automaticamente.');
  }

  console.log('');
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

  const output = getArg('--output');
  const merge = hasFlag('--merge');
  const enrich = hasFlag('--enrich');
  const cache = !hasFlag('--no-cache');
  const includeGaps = hasFlag('--include-gaps');
  const appRepoPath = getArg('--app-repo-path');
  const appSrcDirsRaw = getArg('--app-src-dirs');
  const appSrcDirs = appSrcDirsRaw ? appSrcDirsRaw.split(',').map(d => d.trim()).filter(Boolean) : undefined;

  // --layers: formato "name:path,name:path" (ex: "e2e:test/e2e,api:test/api,unit:server/test")
  const layersRaw = getArg('--layers');
  let layers: TestLayer[] | undefined;
  if (layersRaw) {
    layers = layersRaw.split(',').map(entry => {
      const [name, ...pathParts] = entry.split(':');
      return { name: name.trim(), path: pathParts.join(':').trim() };
    }).filter(l => l.name && l.path);
  }

  if (hasFlag('--help')) {
    console.log('');
    console.log('Uso:');
    console.log('  npx tsx fastqa/scripts/regression/commands/generate-regression-map.command.ts [opções]');
    console.log('');
    console.log('Opções:');
    console.log('  --output <path>          Caminho de saída do regression-map.yaml');
    console.log(`                           (padrão: ${DEFAULT_OUTPUT})`);
    console.log('  --merge                  Preserva app_patterns customizados de mapa existente');
    console.log('  --layers <name:path,...>  Camadas de teste a varrer (ex: e2e:test/e2e,api:test/api)');
    console.log('                           Se omitido, usa paths do project_config.json');
    console.log('  --app-repo-path <path>   Caminho do repositório da aplicação para gerar');
    console.log('                           app_patterns precisos baseados na estrutura real');
    console.log('  --app-src-dirs <dirs>    Diretórios fonte da app (vírgula-separado)');
    console.log('                           Ex: src,lib,routes (default: auto-detect)');
    console.log('  --enrich                 Gera .enrichment-context.json para enriquecimento via IA');
    console.log('  --include-gaps           Inclui áreas da app sem testes no mapa (filtradas por relevância)');
    console.log('  --no-cache               Ignora cache de classificações anteriores');
    console.log('  --help                   Exibe esta ajuda');
    console.log('');
    console.log('Exemplos:');
    console.log('  npx tsx fastqa/scripts/regression/commands/generate-regression-map.command.ts');
    console.log('  npx tsx fastqa/scripts/regression/commands/generate-regression-map.command.ts --merge');
    console.log('  npx tsx fastqa/scripts/regression/commands/generate-regression-map.command.ts --layers e2e:test/e2e,api:test/api');
    console.log('  npx tsx fastqa/scripts/regression/commands/generate-regression-map.command.ts --app-repo-path ../my-app');
    console.log('  npx tsx fastqa/scripts/regression/commands/generate-regression-map.command.ts --app-repo-path ../my-app --app-src-dirs src,lib,routes');
    console.log('');
    process.exit(0);
  }

  try {
    await generateRegressionMap({ output, merge, layers, appRepoPath, appSrcDirs, enrich, cache, includeGaps });
    process.exit(0);
  } catch (error) {
    console.error('\n❌ Erro na geração do regression map:');
    console.error(error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

export { generateRegressionMap };
