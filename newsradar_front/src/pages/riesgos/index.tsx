/**
 * Riesgos Emergentes search page — Form with terms/preset, date range.
 * Submits to POST /api/riesgos/search and displays results + Excel download.
 */
import React, { useState, FormEvent } from "react";
import {
  searchRiesgos,
  type RiesgosSearchRequest,
  type RiesgosSearchResponse,
} from "@/lib/api";
import ResultsTable from "@/components/results/ResultsTable";

const PRESETS = [
  { value: "", label: "— Sin preset —" },
  { value: "ciber", label: "Cibernético" },
  { value: "fraude", label: "Fraude" },
  { value: "operacional", label: "Operacional" },
  { value: "ambiental_social", label: "Ambiental / Social" },
  { value: "all", label: "Todos" },
] as const;

export default function RiesgosPage() {
  const [terms, setTerms] = useState("");
  const [preset, setPreset] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<RiesgosSearchResponse | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const termsList = terms
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    const req: RiesgosSearchRequest = {
      terms: termsList.length > 0 ? termsList : undefined,
      terms_preset: (preset as RiesgosSearchRequest["terms_preset"]) || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    };

    try {
      const data = await searchRiesgos(req);
      setResponse(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: 32 }}>
      <h1>Riesgos Emergentes — Búsqueda Ad-hoc</h1>

      <form onSubmit={handleSubmit}>
        <fieldset>
          <legend>Parámetros de búsqueda</legend>

          <div className="form-grid">
            <div className="form-grid-full">
              <label htmlFor="terms">Términos (separados por coma)</label>
              <input
                id="terms"
                value={terms}
                onChange={(e) => setTerms(e.target.value)}
                placeholder="ransomware, phishing, breach"
              />
            </div>

            <div>
              <label htmlFor="preset">Preset</label>
              <select
                id="preset"
                value={preset}
                onChange={(e) => setPreset(e.target.value)}
              >
                {PRESETS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="date-from">Desde</label>
              <input
                id="date-from"
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
              />
            </div>

            <div>
              <label htmlFor="date-to">Hasta</label>
              <input
                id="date-to"
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
              />
            </div>
          </div>
        </fieldset>

        <button type="submit" disabled={loading} style={{ marginTop: 12 }}>
          {loading ? "Buscando..." : "Buscar"}
        </button>
      </form>

      {error && <p style={{ color: "red" }}>{error}</p>}

      {response && (
        <ResultsTable
          results={response.results}
          excelUrl={response.excel_url}
          totalDocuments={response.total_documents}
          totalClassified={response.total_classified}
        />
      )}
    </main>
  );
}
