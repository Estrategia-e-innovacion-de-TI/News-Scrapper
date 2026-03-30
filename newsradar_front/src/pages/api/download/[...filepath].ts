import type { NextApiRequest, NextApiResponse } from 'next';
import { existsSync, readFileSync, statSync } from 'fs';
import path from 'path';

/** Absolute path to the pipeline root (news_radar_mvp/). */
const PIPELINE_ROOT = path.resolve(process.cwd(), '..');

/**
 * GET /api/download/:runId/:filename
 *
 * Serves files from the pipeline output directory (out/) for Excel downloads.
 * Only allows .xlsx and .jsonl files to prevent directory traversal attacks.
 */
export default function handler(
  req: NextApiRequest,
  res: NextApiResponse,
) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { filepath } = req.query;

  if (!Array.isArray(filepath) || filepath.length < 2) {
    return res.status(400).json({ error: 'Ruta inválida: se espera /api/download/:runId/:filename' });
  }

  const [runId, filename] = filepath;

  // Security: only allow safe characters in runId and filename
  if (!/^[a-zA-Z0-9_-]+$/.test(runId)) {
    return res.status(400).json({ error: 'runId inválido' });
  }
  if (!/^[a-zA-Z0-9_.-]+$/.test(filename)) {
    return res.status(400).json({ error: 'Nombre de archivo inválido' });
  }

  // Only allow specific file extensions
  const ext = path.extname(filename).toLowerCase();
  const ALLOWED_EXTENSIONS = new Set(['.xlsx', '.jsonl', '.json']);
  if (!ALLOWED_EXTENSIONS.has(ext)) {
    return res.status(403).json({ error: 'Tipo de archivo no permitido' });
  }

  const filePath = path.join(PIPELINE_ROOT, 'out', runId, filename);

  // Ensure resolved path stays within the out/ directory (prevent traversal)
  const resolvedPath = path.resolve(filePath);
  const allowedBase = path.resolve(PIPELINE_ROOT, 'out');
  if (!resolvedPath.startsWith(allowedBase + path.sep)) {
    return res.status(403).json({ error: 'Acceso denegado' });
  }

  if (!existsSync(resolvedPath)) {
    return res.status(404).json({ error: 'Archivo no encontrado' });
  }

  const stat = statSync(resolvedPath);
  const content = readFileSync(resolvedPath);

  // Set appropriate content type
  const CONTENT_TYPES: Record<string, string> = {
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.jsonl': 'application/x-ndjson',
    '.json': 'application/json',
  };

  res.setHeader('Content-Type', CONTENT_TYPES[ext] ?? 'application/octet-stream');
  res.setHeader('Content-Length', stat.size);
  res.setHeader(
    'Content-Disposition',
    `attachment; filename="${filename}"`,
  );

  return res.status(200).send(content);
}
