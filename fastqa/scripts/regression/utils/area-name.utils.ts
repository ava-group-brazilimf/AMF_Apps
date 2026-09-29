/**
 * ═══════════════════════════════════════════════════════════════════════════
 * FastQA — Area Name Utils (Shared)
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * Funções compartilhadas para derivar nomes de áreas funcionais a partir
 * de caminhos de arquivo. Usado por:
 *   - analyze-pr-regression.command.ts (análise de PR)
 *   - generate-regression-map.command.ts (varredura da app)
 *
 * @module area-name-utils
 */

import type { FunctionalAreaScope } from '../types/regression.types';

// ─────────────────────────────────────────────────────────────────────
// Constantes exportadas
// ─────────────────────────────────────────────────────────────────────

/** Nomes de arquivo genéricos que sinalizam necessidade de reclassificação */
export const GENERIC_AREA_NAMES = new Set([
  'helpers', 'utils', 'common', 'shared', 'index', 'lib',
  'misc', 'functions', 'base', 'core', 'general', 'tools',
  'support', 'auxiliary', 'constants', 'types', 'main', 'app',
]);

/** Nomes de diretórios que indicam escopo global / infraestrutura */
export const GLOBAL_SCOPE_DIR_NAMES = new Set([
  // Core infra (já classificados como global por SCOPE_PATTERNS)
  'config', 'middleware', 'database', 'migrations', 'migration',
  // IaC / deploy
  'infra', 'infrastructure', 'deploy', 'deployment', 'devops',
  'terraform', 'bicep', 'pulumi', 'cdk',
  'k8s', 'kubernetes', 'helm', 'charts',
  // CI/CD
  'pipelines', 'ci', 'cd', '.github', '.gitlab',
  // Prisma / ORM
  'prisma', 'drizzle', 'typeorm',
  // Segurança / auth global
  'security', 'auth', 'iam',
  // Seed / fixtures de dados
  'seeds', 'seed', 'fixtures',
]);

/** Padrões de path que identificam o escopo de uma área */
export const SCOPE_PATTERNS: Array<{ pattern: RegExp; scope: FunctionalAreaScope }> = [
  { pattern: /\/pages?\//i, scope: 'page' },
  { pattern: /\/views?\//i, scope: 'page' },
  { pattern: /\/screens?\//i, scope: 'page' },
  { pattern: /\/api\//i, scope: 'api' },
  { pattern: /\/controllers?\//i, scope: 'api' },
  { pattern: /\/routes?\//i, scope: 'api' },
  { pattern: /\/endpoints?\//i, scope: 'api' },
  { pattern: /\/services?\//i, scope: 'service' },
  { pattern: /\/providers?\//i, scope: 'service' },
  { pattern: /\/components?\//i, scope: 'component' },
  { pattern: /\/widgets?\//i, scope: 'component' },
  { pattern: /\/models?\//i, scope: 'model' },
  { pattern: /\/entities?\//i, scope: 'model' },
  { pattern: /\/schemas?\//i, scope: 'model' },
  { pattern: /\/middleware\//i, scope: 'global' },
  { pattern: /\/config\//i, scope: 'global' },
  { pattern: /\/database\//i, scope: 'global' },
  { pattern: /\/migrations?\//i, scope: 'global' },
  { pattern: /\.env/i, scope: 'global' },
];

/** Sufixos a remover do nome de área */
export const AREA_SUFFIXES = /\.(controller|service|page|screen|component|module|model|entity|repository|handler|middleware|guard|interceptor|pipe|filter|resolver|dto|util|helper|spec|test)$/i;

/** Segmentos de path que indicam a área funcional está no próximo segmento */
export const KNOWN_SEGMENTS = [
  'pages', 'api', 'controllers', 'services', 'components',
  'views', 'screens', 'routes', 'modules',
];

// ─────────────────────────────────────────────────────────────────────
// Funções
// ─────────────────────────────────────────────────────────────────────

/**
 * Deriva o nome da área funcional a partir de um caminho de arquivo.
 *
 * Estratégia:
 * 1. Se o path contém um segmento conhecido (pages, routes, etc.),
 *    usa o próximo segmento como área.
 * 2. Caso contrário, usa o nome do arquivo sem extensão/sufixos.
 * 3. Arquivos transversais (middleware, config, etc.) retornam '*global*'.
 * 4. Normaliza para kebab-case.
 */
export function deriveAreaName(filePath: string): string {
  const segments = filePath.split(/[/\\]/).filter(Boolean);
  const fileName = segments[segments.length - 1] || '';

  // Remover extensão e sufixos
  let name = fileName
    .replace(/\.[^.]+$/, '')     // extensão
    .replace(AREA_SUFFIXES, ''); // sufixos

  // Tentar extrair do path por segmentos conhecidos
  for (let i = 0; i < segments.length - 1; i++) {
    if (KNOWN_SEGMENTS.includes(segments[i].toLowerCase()) && segments[i + 1]) {
      name = segments[i + 1].replace(/\.[^.]+$/, '').replace(AREA_SUFFIXES, '');
      break;
    }
  }

  // Transversais → *global*
  if (/^(middleware|config|database|migration|docker|env)/i.test(name)) {
    return '*global*';
  }

  // Normalizar
  return name
    .replace(/([a-z])([A-Z])/g, '$1-$2') // camelCase → kebab
    .toLowerCase()
    .replace(/[_. ]/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
}

/**
 * Verifica se um nome de área derivado é genérico e precisa de reclassificação
 * (por export analysis ou IA).
 */
export function isGenericAreaName(areaName: string): boolean {
  return GENERIC_AREA_NAMES.has(areaName.toLowerCase());
}

/**
 * Detecta o scope funcional de um arquivo a partir do seu path.
 */
export function detectScope(filePath: string): FunctionalAreaScope {
  for (const { pattern, scope } of SCOPE_PATTERNS) {
    if (pattern.test(filePath)) {
      return scope;
    }
  }
  return 'component';
}
