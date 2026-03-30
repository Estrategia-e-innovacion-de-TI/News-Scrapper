/**
 * ResultsTable — Displays search results in a table with CSV download button.
 *
 * Shared by ARAS and Riesgos pages. Generates CSV client-side for download.
 */
import React, { useCallback } from "react";
import type { DocumentResult } from "@/lib/api";

interface ResultsTableProps {
  results: DocumentResult[];
  excelUrl: string | null;
  totalDocuments: number;
  totalClassified: number;
}

/** Escape a value for CSV (wrap in quotes if it contains comma, newline, or quote). */
function csvEscape(val: string): string {
  if (val.includes(",") || val.includes("\n") || val.includes('"')) {
    return '"' + val.replace(/"/g, '""') + '"';
  }
  return val;
}

export default function ResultsTable({
  results,
  excelUrl,
  totalDocuments,
  totalClassified,
}: ResultsTableProps) {
  const handleDownload = useCallback(() => {
    const headers = [
      "Título",
      "Medio",
      "Fecha",
      "URL",
      "Resumen",
      "Categoría",
      "Severidad",
      "Evidencia",
    ];

    const rows = results.map((doc) => [
      csvEscape(doc.title),
      csvEscape(doc.source),
      csvEscape(doc.published_at ?? ""),
      csvEscape(doc.url ?? ""),
      csvEscape(doc.summary),
      csvEscape(doc.category ?? ""),
      csvEscape(doc.severity ?? ""),
      csvEscape(doc.evidence.slice(0, 3).join(" | ")),
    ]);

    const csv =
      "\uFEFF" + // BOM for Excel UTF-8
      headers.join(",") +
      "\n" +
      rows.map((r) => r.join(",")).join("\n");

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `resultados_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [results]);

  if (results.length === 0) {
    return <p>Sin resultados para los criterios especificados.</p>;
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--spacing-md, 16px)" }}>
        <p style={{ margin: 0 }}>
          {totalDocuments} documentos encontrados, {totalClassified} clasificados.
        </p>
        <button
          type="button"
          onClick={handleDownload}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            padding: "8px 16px",
            backgroundColor: "#3fb950",
            color: "#fff",
            border: "none",
            borderRadius: "6px",
            cursor: "pointer",
            fontWeight: 500,
            fontSize: "14px",
          }}
        >
          📥 Descargar CSV
        </button>
      </div>

      {excelUrl && (
        <a
          href={excelUrl}
          download
          style={{
            display: "inline-block",
            marginBottom: "var(--spacing-sm, 8px)",
            color: "var(--blue, #3B82F6)",
          }}
        >
          📊 Descargar Excel (.xlsx)
        </a>
      )}

      <div style={{ maxHeight: "600px", overflowY: "auto", borderRadius: "8px", boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Título</th>
              <th>Medio</th>
              <th>Fecha</th>
              <th>Categoría</th>
              <th>Severidad</th>
              <th>Evidencia</th>
              <th>URL</th>
            </tr>
          </thead>
          <tbody>
            {results.map((doc, idx) => (
              <tr key={idx}>
                <td>{idx + 1}</td>
                <td>{doc.title}</td>
                <td>{doc.source}</td>
                <td>{doc.published_at ?? "—"}</td>
                <td>{doc.category ?? "—"}</td>
                <td>
                  <span
                    style={{
                      fontWeight: 600,
                      color:
                        doc.severity === "H"
                          ? "#e53e3e"
                          : doc.severity === "M"
                            ? "#d69e2e"
                            : "#a0aec0",
                    }}
                  >
                    {doc.severity ?? "—"}
                  </span>
                </td>
                <td style={{ maxWidth: "300px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {doc.evidence.slice(0, 3).join(" | ") || "—"}
                </td>
                <td>
                  {doc.url ? (
                    <a href={doc.url} target="_blank" rel="noopener noreferrer">
                      Ver
                    </a>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
