/**
 * ARAS search page — Form with company/NIT, risk category, date range.
 * Submits to POST /api/aras/search and displays results + Excel download.
 */
import React, { useState, FormEvent } from "react";
import {
  searchAras,
  type ArasSearchRequest,
  type ArasSearchResponse,
} from "@/lib/api";
import ResultsTable from "@/components/results/ResultsTable";

export default function ArasPage() {
  const [company, setCompany] = useState("");
  const [nit, setNit] = useState("");
  const [riskCategory, setRiskCategory] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ArasSearchResponse | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const req: ArasSearchRequest = {
      company: company || undefined,
      nit: nit || undefined,
      risk_category: riskCategory || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    };

    try {
      const data = await searchAras(req);
      setResponse(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: 32 }}>
      <h1>ARAS — Búsqueda Ad-hoc</h1>

      <form onSubmit={handleSubmit}>
        <fieldset>
          <legend>Parámetros de búsqueda</legend>

          <div className="form-grid">
            <div>
              <label htmlFor="company">Empresa</label>
              <input
                id="company"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="Nombre de la empresa"
              />
            </div>

            <div>
              <label htmlFor="nit">NIT</label>
              <input
                id="nit"
                value={nit}
                onChange={(e) => setNit(e.target.value)}
                placeholder="900123456-7"
              />
            </div>

            <div>
              <label htmlFor="risk-category">Tipo de riesgo</label>
              <select
                id="risk-category"
                value={riskCategory}
                onChange={(e) => setRiskCategory(e.target.value)}
              >
                <option value="">— Todos —</option>
                <option value="lavado_activos">Lavado de activos</option>
                <option value="financiamiento_terrorismo">Financiamiento del terrorismo</option>
                <option value="fraude">Fraude</option>
                <option value="corrupcion">Corrupción</option>
                <option value="sanciones">Sanciones</option>
                <option value="pep">PEP</option>
                <option value="ambiental">Ambiental</option>
                <option value="social">Social</option>
                {/* TODO: Load categories dynamically from YAML */}
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
