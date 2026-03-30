/**
 * ArasSearchForm — Search form for ARAS risk analysis.
 *
 * Extracted from pages/aras/index.tsx into a reusable component.
 * Fields: empresa, NIT, categoría de riesgo, rango de fechas.
 * Communicates results, errors, and loading state via callback props.
 *
 * Validates: Req 2.1, 2.2, 2.5, 2.6
 */
import React, { useState, FormEvent } from "react";
import {
  searchAras,
  type ArasSearchRequest,
  type ArasSearchResponse,
} from "@/lib/api";

export interface ArasSearchFormProps {
  onResults: (response: ArasSearchResponse) => void;
  onError: (message: string) => void;
  onLoadingChange: (loading: boolean) => void;
}

export default function ArasSearchForm({
  onResults,
  onError,
  onLoadingChange,
}: ArasSearchFormProps) {
  const [company, setCompany] = useState("");
  const [nit, setNit] = useState("");
  const [riskCategory, setRiskCategory] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();

    setLoading(true);
    onLoadingChange(true);

    const req: ArasSearchRequest = {
      company: company || undefined,
      nit: nit || undefined,
      risk_category: riskCategory || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    };

    try {
      const data = await searchAras(req);
      onResults(data);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Error desconocido");
    } finally {
      setLoading(false);
      onLoadingChange(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} aria-label="Búsqueda ARAS">
      <fieldset>
        <legend>Parámetros de búsqueda</legend>

        <div className="form-grid">
          <div>
            <label htmlFor="aras-company">Empresa</label>
            <input
              id="aras-company"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="Nombre de la empresa"
            />
          </div>

          <div>
            <label htmlFor="aras-nit">NIT</label>
            <input
              id="aras-nit"
              value={nit}
              onChange={(e) => setNit(e.target.value)}
              placeholder="900123456-7"
            />
          </div>

          <div>
            <label htmlFor="aras-risk-category">Tipo de riesgo</label>
            <select
              id="aras-risk-category"
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
            </select>
          </div>

          <div>
            <label htmlFor="aras-date-from">Desde</label>
            <input
              id="aras-date-from"
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
            />
          </div>

          <div>
            <label htmlFor="aras-date-to">Hasta</label>
            <input
              id="aras-date-to"
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
            />
          </div>
        </div>
      </fieldset>

      <button type="submit" disabled={loading} style={{ marginTop: "var(--spacing-md, 12px)" }}>
        {loading ? "Buscando..." : "Buscar"}
      </button>
    </form>
  );
}
