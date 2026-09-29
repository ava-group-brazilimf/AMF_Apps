/**
 * ═══════════════════════════════════════════════════════════════════════════
 * FastQA — Export Analyzer Utils
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * Extrai nomes de exports de arquivos fonte e infere a área funcional
 * quando o nome do arquivo é genérico (helpers, utils, common, etc.).
 *
 * Usado para reclassificar módulos cujo path não revela a área funcional.
 *
 * @module export-analyzer-utils
 */

import * as fs from 'fs';

// ─────────────────────────────────────────────────────────────────────
// Tipos
// ─────────────────────────────────────────────────────────────────────

/** Resultado da análise de exports de um arquivo */
export interface ExportAnalysis {
  /** Nomes exportados encontrados (funções, classes, constantes) */
  exportNames: string[];
  /** Área funcional inferida a partir dos exports (ou null se inconclusivo) */
  inferredArea: string | null;
  /** Confiança na inferência */
  confidence: 'high' | 'medium' | 'low';
}

// ─────────────────────────────────────────────────────────────────────
// Constantes
// ─────────────────────────────────────────────────────────────────────

/** Nomes de arquivo que disparam reclassificação por exports */
export const GENERIC_FILE_NAMES = new Set([
  'helpers', 'utils', 'common', 'shared', 'index', 'lib',
  'misc', 'functions', 'base', 'core', 'general', 'tools',
  'support', 'auxiliary', 'constants', 'types', 'main', 'app',
]);

/**
 * Mapa de keywords → área funcional.
 * Quando um export contém uma dessas keywords, é associado à área.
 */
const KEYWORD_TO_AREA: Array<{ keywords: RegExp; area: string }> = [
  { keywords: /shipping|freight|delivery|postage/i, area: 'shipping' },
  { keywords: /payment|pay|charge|billing|invoice|stripe|paypal/i, area: 'payment' },
  { keywords: /cart|basket|bag/i, area: 'cart' },
  { keywords: /checkout|purchase|order|buy/i, area: 'checkout' },
  { keywords: /auth|login|logout|session|token|credential|password|signin|signup/i, area: 'auth' },
  { keywords: /user|account|profile|registration|member/i, area: 'user' },
  { keywords: /product|catalog|item|sku|inventory|stock/i, area: 'product' },
  { keywords: /search|filter|query|find|lookup/i, area: 'search' },
  { keywords: /notification|notify|alert|email|sms|push/i, area: 'notification' },
  { keywords: /report|analytics|metric|dashboard|statistic/i, area: 'analytics' },
  { keywords: /upload|download|file|attachment|media|image/i, area: 'media' },
  { keywords: /permission|role|access|policy|rbac|acl/i, area: 'permission' },
  { keywords: /config|setting|preference|option|env/i, area: 'config' },
  { keywords: /validate|validation|sanitize|check|verify/i, area: 'validation' },
  { keywords: /format|parse|transform|convert|serialize|deserialize/i, area: 'transform' },
  { keywords: /cache|redis|memcache/i, area: 'cache' },
  { keywords: /log|logger|logging|audit|trace/i, area: 'logging' },
  { keywords: /database|db|repository|query|migration|seed/i, area: 'database' },
  { keywords: /api|request|response|endpoint|route|http|fetch/i, area: 'api' },
  { keywords: /schedule|cron|job|task|queue|worker/i, area: 'scheduler' },
  { keywords: /navigation|nav|menu|sidebar|breadcrumb|tab/i, area: 'navigation' },
  { keywords: /form|input|field|select|textarea|checkbox/i, area: 'form' },
  { keywords: /table|list|grid|pagination|sort/i, area: 'listing' },
  { keywords: /modal|dialog|popup|toast|snackbar/i, area: 'modal' },
  { keywords: /theme|style|color|font|layout|css/i, area: 'theme' },
  { keywords: /i18n|locale|translation|language|l10n/i, area: 'i18n' },
  { keywords: /test|mock|stub|fake|fixture/i, area: 'testing' },
  { keywords: /error|exception|fault|failure/i, area: 'error-handling' },
  { keywords: /encrypt|decrypt|hash|cipher|security|sanitize/i, area: 'security' },
  { keywords: /socket|websocket|realtime|sse|event/i, area: 'realtime' },
  { keywords: /map|geo|location|address|coordinate/i, area: 'geolocation' },
  { keywords: /chat|message|conversation|comment/i, area: 'messaging' },
  { keywords: /tax|discount|coupon|promo|price|pricing|cost/i, area: 'pricing' },
];

// ─────────────────────────────────────────────────────────────────────
// Regex de exports
// ─────────────────────────────────────────────────────────────────────

/** Named export: export function X, export const X, export class X, export enum X */
const NAMED_EXPORT_REGEX = /export\s+(?:async\s+)?(?:function|const|let|var|class|interface|type|enum)\s+(\w+)/g;

/** Export default: export default function X, export default class X */
const DEFAULT_EXPORT_REGEX = /export\s+default\s+(?:async\s+)?(?:function|class)\s+(\w+)/g;

/** module.exports = { X, Y, Z } */
const CJS_EXPORTS_REGEX = /module\.exports\s*=\s*\{([^}]+)\}/g;

/** exports.X = ... */
const CJS_NAMED_REGEX = /exports\.(\w+)\s*=/g;

// ─────────────────────────────────────────────────────────────────────
// Funções
// ─────────────────────────────────────────────────────────────────────

/**
 * Extrai os nomes de todos os exports de um arquivo fonte.
 */
export function extractExportNames(filePath: string): string[] {
  let content: string;
  try {
    content = fs.readFileSync(filePath, 'utf-8');
  } catch {
    return [];
  }

  const names: string[] = [];

  // ES Modules
  for (const regex of [NAMED_EXPORT_REGEX, DEFAULT_EXPORT_REGEX]) {
    regex.lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = regex.exec(content)) !== null) {
      names.push(match[1]);
    }
  }

  // CommonJS: module.exports = { X, Y, Z }
  CJS_EXPORTS_REGEX.lastIndex = 0;
  let cjsMatch: RegExpExecArray | null;
  while ((cjsMatch = CJS_EXPORTS_REGEX.exec(content)) !== null) {
    const inner = cjsMatch[1];
    const keys = inner.split(',').map(k => k.trim().split(':')[0].trim()).filter(Boolean);
    names.push(...keys);
  }

  // CommonJS: exports.X = ...
  CJS_NAMED_REGEX.lastIndex = 0;
  let namedMatch: RegExpExecArray | null;
  while ((namedMatch = CJS_NAMED_REGEX.exec(content)) !== null) {
    names.push(namedMatch[1]);
  }

  return [...new Set(names)];
}

/**
 * Infere a área funcional de um arquivo a partir dos nomes dos seus exports.
 *
 * Estratégia:
 * 1. Conta quantos exports batem com cada keyword/area
 * 2. A área com mais matches vence
 * 3. Se empate ou nenhum match, retorna null
 */
export function inferAreaFromExports(exportNames: string[]): ExportAnalysis {
  if (exportNames.length === 0) {
    return { exportNames, inferredArea: null, confidence: 'low' };
  }

  // Contar matches por área
  const areaCounts = new Map<string, number>();

  for (const exportName of exportNames) {
    for (const { keywords, area } of KEYWORD_TO_AREA) {
      if (keywords.test(exportName)) {
        areaCounts.set(area, (areaCounts.get(area) || 0) + 1);
      }
    }
  }

  if (areaCounts.size === 0) {
    return { exportNames, inferredArea: null, confidence: 'low' };
  }

  // Encontrar área dominante
  const sorted = [...areaCounts.entries()].sort((a, b) => b[1] - a[1]);
  const [topArea, topCount] = sorted[0];
  const secondCount = sorted.length > 1 ? sorted[1][1] : 0;

  // Determinar confiança
  let confidence: 'high' | 'medium' | 'low';
  const ratio = topCount / exportNames.length;

  if (topCount >= 3 && ratio >= 0.5 && topCount > secondCount * 2) {
    confidence = 'high';
  } else if (topCount >= 2 && topCount > secondCount) {
    confidence = 'medium';
  } else {
    confidence = 'low';
  }

  return {
    exportNames,
    inferredArea: topArea,
    confidence,
  };
}

/**
 * Analisa um arquivo e retorna a área funcional inferida pelos exports.
 * Combina extração + inferência em um passo.
 */
export function analyzeFileExports(filePath: string): ExportAnalysis {
  const exportNames = extractExportNames(filePath);
  return inferAreaFromExports(exportNames);
}

/**
 * Verifica se o nome de um arquivo é genérico (requer análise de exports).
 */
export function isGenericFileName(fileName: string): boolean {
  const baseName = fileName
    .replace(/\.[^.]+$/, '')     // remover extensão
    .replace(/([a-z])([A-Z])/g, '$1-$2')
    .toLowerCase()
    .replace(/[_.-]/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');

  return GENERIC_FILE_NAMES.has(baseName);
}
