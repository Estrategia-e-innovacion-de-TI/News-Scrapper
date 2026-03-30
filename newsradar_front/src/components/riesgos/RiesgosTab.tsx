/**
 * RiesgosTab — Container for the Riesgos tab with sub-tabs for ARAS
 * and Riesgos Emergentes, sharing a single ResultsTable.
 *
 * Manages: active sub-tab, search results, error messages, loading state.
 *
 * Validates: Req 2.1-2.6, 3.1-3.5
 */
import React, { useState, useCallback } from "react";
import ArasSearchForm from "./ArasSearchForm";
import RiesgosSearchForm from "./RiesgosSearchForm";
import ResultsTable from "../results/ResultsTable";
import type { DocumentResult, ArasSearchResponse, RiesgosSearchResponse } from "@/lib/api";
import styles from "./RiesgosTab.module.css";

type SubTab = "aras" | "riesgos";

export default function RiesgosTab() {
  const [activeSubTab, setActiveSubTab] = useState<SubTab>("aras");
  const [results, setResults] = useState<DocumentResult[]>([]);
  const [excelUrl, setExcelUrl] = useState<string | null>(null);
  const [totalDocuments, setTotalDocuments] = useState(0);
  const [totalClassified, setTotalClassified] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleArasResults = useCallback((response: ArasSearchResponse) => {
    setResults(response.results);
    setExcelUrl(response.excel_url);
    setTotalDocuments(response.total_documents);
    setTotalClassified(response.total_classified);
    setError(null);
  }, []);

  const handleRiesgosResults = useCallback((response: RiesgosSearchResponse) => {
    setResults(response.results);
    setExcelUrl(response.excel_url);
    setTotalDocuments(response.total_documents);
    setTotalClassified(response.total_classified);
    setError(null);
  }, []);

  const handleError = useCallback((message: string) => {
    setError(message);
  }, []);

  const handleLoadingChange = useCallback((isLoading: boolean) => {
    setLoading(isLoading);
  }, []);

  return (
    <div className={styles.container} data-testid="content-riesgos">
      <div className={styles.subTabList} role="tablist" aria-label="Sub-secciones de Riesgos">
        <button
          role="tab"
          id="subtab-aras"
          aria-selected={activeSubTab === "aras"}
          aria-controls="subtabpanel-aras"
          className={`${styles.subTab} ${activeSubTab === "aras" ? styles.subTabActive : ""}`}
          onClick={() => setActiveSubTab("aras")}
        >
          ARAS
        </button>
        <button
          role="tab"
          id="subtab-riesgos"
          aria-selected={activeSubTab === "riesgos"}
          aria-controls="subtabpanel-riesgos"
          className={`${styles.subTab} ${activeSubTab === "riesgos" ? styles.subTabActive : ""}`}
          onClick={() => setActiveSubTab("riesgos")}
        >
          Riesgos Emergentes
        </button>
      </div>

      <div
        role="tabpanel"
        id={`subtabpanel-${activeSubTab}`}
        aria-labelledby={`subtab-${activeSubTab}`}
      >
        {activeSubTab === "aras" && (
          <ArasSearchForm
            onResults={handleArasResults}
            onError={handleError}
            onLoadingChange={handleLoadingChange}
          />
        )}
        {activeSubTab === "riesgos" && (
          <RiesgosSearchForm
            onResults={handleRiesgosResults}
            onError={handleError}
            onLoadingChange={handleLoadingChange}
          />
        )}
      </div>

      {error && (
        <p className={styles.errorMessage} role="alert" data-testid="riesgos-error">
          {error}
        </p>
      )}

      <div className={styles.resultsSection}>
        <ResultsTable
          results={results}
          excelUrl={excelUrl}
          totalDocuments={totalDocuments}
          totalClassified={totalClassified}
        />
      </div>
    </div>
  );
}
