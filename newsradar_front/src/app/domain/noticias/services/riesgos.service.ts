import { Injectable } from '@angular/core';
import { ArasSearchRequest } from '../models/aras.model';
import { RiesgosSearchRequest } from '../models/riesgos.model';
import { DocumentResult } from '../models/document-result.model';

@Injectable({ providedIn: 'root' })
export class RiesgosService {
  validateArasSearch(req: ArasSearchRequest): boolean {
    const hasCompany = !!req.company?.trim();
    const hasNit = !!req.nit?.trim();
    return hasCompany || hasNit;
  }

  validateRiesgosSearch(req: RiesgosSearchRequest): boolean {
    const hasTerms = !!req.terms && req.terms.length > 0;
    const hasPreset = !!req.terms_preset;
    return hasTerms || hasPreset;
  }

  formatResults(results: DocumentResult[]): DocumentResult[] {
    return results.map((r) => ({
      ...r,
      title: r.title?.trim() || 'Sin título',
      source: r.source?.trim() || 'Desconocido',
      evidence: r.evidence ?? [],
    }));
  }
}
