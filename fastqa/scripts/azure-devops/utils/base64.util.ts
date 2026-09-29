/**
 * ============================================================================
 * FastQA — Base64 Utility
 * ============================================================================
 * Utilitários para encoding/decoding de arquivos em Base64.
 * Usado para upload de evidências ao Azure DevOps Test Results.
 * ============================================================================
 */

import * as fs from 'fs';
import * as path from 'path';

/**
 * Converte arquivo para string Base64.
 * @param filePath Caminho absoluto ou relativo do arquivo
 * @returns String Base64 do conteúdo
 */
export function fileToBase64(filePath: string): string {
  const resolvedPath = path.resolve(filePath);
  if (!fs.existsSync(resolvedPath)) {
    throw new Error(`Arquivo não encontrado: ${resolvedPath}`);
  }
  const buffer = fs.readFileSync(resolvedPath);
  return buffer.toString('base64');
}

/**
 * Retorna o tamanho do arquivo em bytes.
 * @param filePath Caminho absoluto ou relativo do arquivo
 * @returns Tamanho em bytes
 */
export function getFileSizeBytes(filePath: string): number {
  const resolvedPath = path.resolve(filePath);
  if (!fs.existsSync(resolvedPath)) {
    throw new Error(`Arquivo não encontrado: ${resolvedPath}`);
  }
  return fs.statSync(resolvedPath).size;
}

/**
 * Retorna o tamanho formatado (KB, MB, GB).
 * @param bytes Tamanho em bytes
 * @returns String formatada (ex: "15.3 MB")
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const size = bytes / Math.pow(1024, i);
  return `${size.toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
}

/**
 * Lista todos os arquivos de um diretório (recursivo opcional).
 * @param dirPath Caminho do diretório
 * @param recursive Se deve buscar em subpastas (default: true)
 * @param allowedExtensions Extensões permitidas (ex: ['.png', '.mp4'])
 * @returns Lista de caminhos absolutos dos arquivos
 */
export function listFiles(
  dirPath: string,
  recursive: boolean = true,
  allowedExtensions?: string[]
): string[] {
  const resolvedPath = path.resolve(dirPath);
  if (!fs.existsSync(resolvedPath)) {
    throw new Error(`Diretório não encontrado: ${resolvedPath}`);
  }

  const stat = fs.statSync(resolvedPath);
  if (!stat.isDirectory()) {
    throw new Error(`Caminho não é um diretório: ${resolvedPath}`);
  }

  const files: string[] = [];

  function scan(dir: string): void {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory() && recursive) {
        scan(fullPath);
      } else if (entry.isFile()) {
        if (allowedExtensions) {
          const ext = path.extname(entry.name).toLowerCase();
          if (allowedExtensions.includes(ext)) {
            files.push(fullPath);
          }
        } else {
          files.push(fullPath);
        }
      }
    }
  }

  scan(resolvedPath);
  return files.sort();
}

/**
 * Verifica se a extensão do arquivo é permitida.
 * @param filePath Caminho do arquivo
 * @param allowedExtensions Lista de extensões permitidas
 * @returns true se permitido
 */
export function isAllowedExtension(
  filePath: string,
  allowedExtensions: string[]
): boolean {
  const ext = path.extname(filePath).toLowerCase();
  return allowedExtensions.includes(ext);
}
