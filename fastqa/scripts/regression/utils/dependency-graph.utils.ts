/**
 * ═══════════════════════════════════════════════════════════════════════════
 * FastQA — Dependency Graph Utils
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * Parseia imports/requires dos arquivos da aplicação e monta um grafo
 * de dependências. Usado para:
 *   - Agrupar áreas funcionais acopladas
 *   - Propagar impacto de PRs via dependentes
 *   - Identificar módulos shared (importados por 3+ áreas)
 *   - Refinar escopo de arquivos cross-cutting (*global*)
 *
 * @module dependency-graph-utils
 */

import * as fs from 'fs';
import * as path from 'path';

// ─────────────────────────────────────────────────────────────────────
// Tipos
// ─────────────────────────────────────────────────────────────────────

/** Grafo de dependências: file → set de files que ele importa */
export interface DependencyGraph {
  /** file → arquivos que ele importa (dependências diretas) */
  imports: Map<string, Set<string>>;
  /** file → arquivos que o importam (dependentes diretos) */
  importedBy: Map<string, Set<string>>;
}

/** Resultado da análise de acoplamento entre áreas */
export interface AreaCoupling {
  /** Áreas que esta área depende diretamente */
  dependencies: string[];
  /** Áreas que dependem diretamente desta área */
  dependents: string[];
  /** Módulo é compartilhado (importado por 3+ áreas distintas) */
  shared: boolean;
  /** Se cross-cutting, escopo refinado baseado nos importadores */
  impactScope: 'global' | 'targeted';
  /** Se targeted, lista de áreas impactadas */
  impactedAreas: string[];
}

// ─────────────────────────────────────────────────────────────────────
// Constantes
// ─────────────────────────────────────────────────────────────────────

/** Threshold: se um módulo é importado por N+ áreas distintas, é shared */
const SHARED_THRESHOLD = 3;

/** Extensões tentadas ao resolver imports sem extensão */
const RESOLVE_EXTENSIONS = ['.ts', '.tsx', '.js', '.jsx', '/index.ts', '/index.js'];

// ─────────────────────────────────────────────────────────────────────
// Regex de imports
// ─────────────────────────────────────────────────────────────────────

/** ES Module: import X from './path' | import { X } from './path' | import './path' */
const ES_IMPORT_REGEX = /import\s+(?:[\s\S]*?\s+from\s+)?['"]([^'"]+)['"]/g;

/** Dynamic import: import('./path') | require('./path') */
const DYNAMIC_IMPORT_REGEX = /(?:import|require)\s*\(\s*['"]([^'"]+)['"]\s*\)/g;

/** Re-export: export { X } from './path' | export * from './path' */
const RE_EXPORT_REGEX = /export\s+(?:\{[^}]*\}|\*)\s+from\s+['"]([^'"]+)['"]/g;

// ─────────────────────────────────────────────────────────────────────
// Funções de resolução de path
// ─────────────────────────────────────────────────────────────────────

/**
 * Resolve um import path relativo para um caminho absoluto do sistema de arquivos.
 * Retorna null se não puder ser resolvido (ex: pacote npm, alias).
 */
function resolveImportPath(importPath: string, sourceFile: string, repoRoot: string): string | null {
  // Ignorar pacotes npm e módulos built-in
  if (!importPath.startsWith('.') && !importPath.startsWith('/')) {
    return null;
  }

  const sourceDir = path.dirname(sourceFile);
  const basePath = path.resolve(sourceDir, importPath);

  // Tentar extensões
  for (const ext of RESOLVE_EXTENSIONS) {
    const fullPath = basePath + ext;
    if (fs.existsSync(fullPath)) {
      return path.relative(repoRoot, fullPath).replace(/\\/g, '/');
    }
  }

  // Tentar como path exato (já tem extensão)
  if (fs.existsSync(basePath)) {
    const stat = fs.statSync(basePath);
    if (stat.isFile()) {
      return path.relative(repoRoot, basePath).replace(/\\/g, '/');
    }
    // Se é diretório, tentar index
    if (stat.isDirectory()) {
      for (const idx of ['/index.ts', '/index.js', '/index.tsx', '/index.jsx']) {
        const indexPath = basePath + idx;
        if (fs.existsSync(indexPath)) {
          return path.relative(repoRoot, indexPath).replace(/\\/g, '/');
        }
      }
    }
  }

  return null;
}

/**
 * Extrai todos os import paths de um arquivo fonte.
 * Retorna apenas imports relativos (começa com ./ ou ../).
 */
function extractImports(filePath: string): string[] {
  let content: string;
  try {
    content = fs.readFileSync(filePath, 'utf-8');
  } catch {
    return [];
  }

  const imports: string[] = [];
  const regexes = [ES_IMPORT_REGEX, DYNAMIC_IMPORT_REGEX, RE_EXPORT_REGEX];

  for (const regex of regexes) {
    regex.lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = regex.exec(content)) !== null) {
      const importPath = match[1];
      if (importPath.startsWith('.')) {
        imports.push(importPath);
      }
    }
  }

  return [...new Set(imports)];
}

// ─────────────────────────────────────────────────────────────────────
// Grafo de dependências
// ─────────────────────────────────────────────────────────────────────

/**
 * Monta o grafo de dependências a partir de uma lista de arquivos da aplicação.
 *
 * @param appFiles   Lista de caminhos absolutos dos arquivos da app
 * @param repoRoot   Caminho absoluto da raiz do repositório da app
 * @returns DependencyGraph com imports e importedBy
 */
export function buildDependencyGraph(appFiles: string[], repoRoot: string): DependencyGraph {
  const imports = new Map<string, Set<string>>();
  const importedBy = new Map<string, Set<string>>();

  for (const absFile of appFiles) {
    const relFile = path.relative(repoRoot, absFile).replace(/\\/g, '/');
    const rawImports = extractImports(absFile);

    const resolvedDeps = new Set<string>();
    for (const importPath of rawImports) {
      const resolved = resolveImportPath(importPath, absFile, repoRoot);
      if (resolved) {
        resolvedDeps.add(resolved);

        // Registrar importedBy reverso
        if (!importedBy.has(resolved)) {
          importedBy.set(resolved, new Set());
        }
        importedBy.get(resolved)!.add(relFile);
      }
    }

    imports.set(relFile, resolvedDeps);
  }

  return { imports, importedBy };
}

/**
 * Retorna dependentes transitivos de um arquivo até maxDepth níveis.
 *
 * @param graph     Grafo de dependências
 * @param filePath  Caminho relativo do arquivo
 * @param maxDepth  Profundidade máxima (default: 3)
 * @returns Set de caminhos relativos de todos os dependentes
 */
export function getTransitiveDependents(
  graph: DependencyGraph,
  filePath: string,
  maxDepth: number = 3
): Set<string> {
  const visited = new Set<string>();
  const queue: Array<{ file: string; depth: number }> = [{ file: filePath, depth: 0 }];

  while (queue.length > 0) {
    const { file, depth } = queue.shift()!;
    if (visited.has(file) || depth > maxDepth) continue;
    visited.add(file);

    const dependents = graph.importedBy.get(file);
    if (dependents) {
      for (const dep of dependents) {
        if (!visited.has(dep)) {
          queue.push({ file: dep, depth: depth + 1 });
        }
      }
    }
  }

  visited.delete(filePath); // não incluir o próprio arquivo
  return visited;
}

/**
 * Analisa o acoplamento de cada área funcional usando o grafo de dependências.
 *
 * @param graph           Grafo de dependências
 * @param fileToArea      Mapa de filePath → areaName
 * @param globalFiles     Lista de arquivos classificados como *global*
 * @returns Mapa de areaName → AreaCoupling
 */
export function analyzeAreaCoupling(
  graph: DependencyGraph,
  fileToArea: Map<string, string>,
  globalFiles: string[] = []
): Map<string, AreaCoupling> {
  const coupling = new Map<string, AreaCoupling>();

  // Agrupar arquivos por área
  const areaFiles = new Map<string, Set<string>>();
  for (const [file, area] of fileToArea) {
    if (!areaFiles.has(area)) {
      areaFiles.set(area, new Set());
    }
    areaFiles.get(area)!.add(file);
  }

  // Para cada área, computar dependências e dependentes por área
  for (const [areaName, files] of areaFiles) {
    const depAreas = new Set<string>();
    const dependentAreas = new Set<string>();

    for (const file of files) {
      // Dependências (o que este arquivo importa)
      const deps = graph.imports.get(file);
      if (deps) {
        for (const dep of deps) {
          const depArea = fileToArea.get(dep);
          if (depArea && depArea !== areaName && depArea !== '*global*') {
            depAreas.add(depArea);
          }
        }
      }

      // Dependentes (quem importa este arquivo)
      const importers = graph.importedBy.get(file);
      if (importers) {
        for (const imp of importers) {
          const impArea = fileToArea.get(imp);
          if (impArea && impArea !== areaName && impArea !== '*global*') {
            dependentAreas.add(impArea);
          }
        }
      }
    }

    const shared = dependentAreas.size >= SHARED_THRESHOLD;

    coupling.set(areaName, {
      dependencies: [...depAreas],
      dependents: [...dependentAreas],
      shared,
      impactScope: 'global',
      impactedAreas: [],
    });
  }

  // Refinar escopo de arquivos cross-cutting (*global*)
  for (const globalFile of globalFiles) {
    const importers = graph.importedBy.get(globalFile);
    if (!importers || importers.size === 0) continue;

    const importerAreas = new Set<string>();
    for (const imp of importers) {
      const area = fileToArea.get(imp);
      if (area && area !== '*global*') {
        importerAreas.add(area);
      }
    }

    // Se importado por poucas áreas, não é realmente global
    const isTargeted = importerAreas.size > 0 && importerAreas.size <= 2;

    if (!coupling.has('*global*')) {
      coupling.set('*global*', {
        dependencies: [],
        dependents: [],
        shared: false,
        impactScope: 'global',
        impactedAreas: [],
      });
    }

    const globalCoupling = coupling.get('*global*')!;
    if (isTargeted) {
      globalCoupling.impactScope = 'targeted';
      for (const area of importerAreas) {
        if (!globalCoupling.impactedAreas.includes(area)) {
          globalCoupling.impactedAreas.push(area);
        }
      }
    }
  }

  return coupling;
}

/**
 * Identifica e funde áreas fortemente acopladas.
 *
 * Quando duas áreas têm dependência bidirecional (A importa B e B importa A),
 * elas representam provavelmente a mesma área funcional e devem ser fundidas.
 *
 * @param coupling    Mapa de acoplamento por área 
 * @returns Mapa de areaName → mergedAreaName (para áreas que devem ser fundidas)
 */
export function detectMergeableAreas(
  coupling: Map<string, AreaCoupling>
): Map<string, string> {
  const mergeMap = new Map<string, string>();
  const processed = new Set<string>();

  for (const [areaA, couplingA] of coupling) {
    if (processed.has(areaA) || areaA === '*global*') continue;

    for (const depArea of couplingA.dependencies) {
      if (processed.has(depArea) || depArea === '*global*') continue;

      const couplingB = coupling.get(depArea);
      if (!couplingB) continue;

      // Verificar dependência bidirecional
      if (couplingB.dependencies.includes(areaA)) {
        // Merge: o nome mais curto vence (mais provável de ser o nome "principal")
        const primary = areaA.length <= depArea.length ? areaA : depArea;
        const secondary = primary === areaA ? depArea : areaA;

        mergeMap.set(secondary, primary);
        processed.add(secondary);
      }
    }
  }

  return mergeMap;
}
