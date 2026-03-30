/**
 * RiesgosSearchForm — Search form for Riesgos Emergentes.
 *
 * Extracted from pages/riesgos/index.tsx into a reusable component.
 * Fields: términos (comma-separated), preset de riesgo, rango de fechas.
 * Validates that at least one criterion (terms or preset) is present.
 * Communicates results, errors, and loading state via callback props.
 *
 * Validates: Req 3.1, 3.2, 3.3, 3.5
 */
import React, { useState, FormEvent } from "react";
import {
  searchRiesgos,
  type RiesgosSearchRequest,
  type RiesgosSearchResponse,
} from "@/lib/api";

export const PRESETS = [
  { value: "", label: "— Sin preset —" },
  { value: "ciber", label: "Cibernético" },
  { value: "fraude", label: "Fraude" },
  { value: "operacional", label: "Operacional" },
  { value: "ambiental_social", label: "Ambiental / Social" },
  { value: "all", label: "Todos" },
] as const;

export interface RiesgosSearchFormProps {
  onResults: (response: RiesgosSearchResponse) => void;
  onError: (message: string) => void;
  onLoadingChange: (loading: boolean) => void;
}

export default function RiesgosSearchForm({
  onResults,
  onError,
  onLoadingChange,
}: RiesgosSearchFormProps) {
  const [terms, setTerms] = useState("");
  const [preset, setPreset] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [loading, setLoading] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setValidationError(null);

    const termsList = terms
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    if (termsList.length === 0 && !preset) {
      setValidationError(
        "Seleccione un preset o ingrese términos de búsqueda."
      );
      return;
    }

    setLoading(true);
    onLoadingChange(true);

    const req: RiesgosSearchRequest = {
      terms: termsList.length > 0 ? termsList : undefined,
      terms_preset:
        (preset as RiesgosSearchRequest["terms_preset"]) || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    };

    try {
      const data = await searchRiesgos(req);
      onResults(data);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Error desconocido");
    } finally {
      setLoading(false);
      onLoadingChange(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} aria-label="Búsqueda Riesgos Emergentes">
      <fieldset>
        <legend>Parámetros de búsqueda</legend>

        <div className="form-grid">
          <div className="form-grid-full">
            <label htmlFor="riesgos-terms">Términos (separados por coma)</label>
            <input
              id="riesgos-terms"
              value={terms}
              onChange={(e) => {
                setTerms(e.target.value);
                setValidationError(null);
              }}
              placeholder="ransomware, phishing, breach"
            />
          </div>

          <div>
            <label htmlFor="riesgos-preset">Preset</label>
            <select
              id="riesgos-preset"
              value={preset}
              onChange={(e) => {
                setPreset(e.target.value);
                setValidationError(null);
              }}
            >
              {PRESETS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="riesgos-date-from">Desde</label>
            <input
              id="riesgos-date-from"
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
            />
          </div>

          <div>
            <label htmlFor="riesgos-date-to">Hasta</label>
            <input
              id="riesgos-date-to"
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
            />
          </div>
        </div>
      </fieldset>

      {validationError && (
        <p role="alert" style={{ color: "var(--color-error, red)" }}>
          {validationError}
        </p>
      )}

      <button
        type="submit"
        disabled={loading}
        style={{ marginTop: "var(--spacing-md, 12px)" }}
      >
        {loading ? "Buscando..." : "Buscar"}
      </button>
    </form>
  );
}
