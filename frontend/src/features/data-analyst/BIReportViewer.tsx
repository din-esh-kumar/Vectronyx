// frontend/src/features/data-analyst/BIReportViewer.tsx
import React, { useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  FileArchive,
  FileCode2,
  FolderOpen,
  Layers,
  LayoutDashboard,
  SlidersHorizontal,
  Table2,
  X,
} from "lucide-react";
import type { DashboardPlan, PowerBiPageBlueprint } from "./types";
import { ReportCharts } from "./ReportCharts";
import { parseBIUploadFile, type ParsedBIFile } from "./biArchiveParser";

interface BIReportViewerProps {
  dashboard?: DashboardPlan | null;
}

const DEFAULT_PBI_PAGES: PowerBiPageBlueprint[] = [
  {
    page_number: 1,
    name: "Executive Overview",
    dimensions: "1280x720",
    purpose: "Top-line KPI scorecards and primary distribution & ranking visuals.",
  },
  {
    page_number: 2,
    name: "Diagnostic Breakdown",
    dimensions: "1280x720",
    purpose: "Cohort comparisons, correlation drivers, and trend trajectories.",
  },
  {
    page_number: 3,
    name: "Risk & Anomaly Matrix",
    dimensions: "1280x720",
    purpose: "Outlier forensics, severity flags, and strategic action items.",
  },
];

export const BIReportViewer: React.FC<BIReportViewerProps> = ({ dashboard }) => {
  const [viewerMode, setViewerMode] = useState<"powerbi" | "tableau">("powerbi");
  const [pbiPageIndex, setPbiPageIndex] = useState(0);
  const [tableauSheetIndex, setTableauSheetIndex] = useState(0);
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [chartTypeFilter, setChartTypeFilter] = useState<string>("all");

  const [uploadedFile, setUploadedFile] = useState<ParsedBIFile | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isParsing, setIsParsing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const pbiPages = useMemo(() => {
    if (dashboard?.powerbi_pages && dashboard.powerbi_pages.length > 0) {
      return dashboard.powerbi_pages;
    }
    return DEFAULT_PBI_PAGES;
  }, [dashboard]);

  const filteredVisuals = useMemo(() => {
    if (!dashboard?.visuals) return [];
    if (chartTypeFilter === "all") return dashboard.visuals;
    return dashboard.visuals.filter((v) => v.chart_type === chartTypeFilter);
  }, [dashboard, chartTypeFilter]);

  const pageVisuals = useMemo(() => {
    if (filteredVisuals.length === 0) return [];
    if (pbiPageIndex === 0) return filteredVisuals.slice(0, Math.max(2, Math.ceil(filteredVisuals.length / 2)));
    if (pbiPageIndex === 1) return filteredVisuals.slice(Math.ceil(filteredVisuals.length / 2));
    return filteredVisuals;
  }, [filteredVisuals, pbiPageIndex]);

  const getAnomalySeverity = (score: number): "high" | "medium" | "low" => {
    if (score >= 0.75) return "high";
    if (score >= 0.45) return "medium";
    return "low";
  };

  const filteredAnomalies = useMemo(() => {
    if (!dashboard?.anomalies) return [];
    if (severityFilter === "all") return dashboard.anomalies;
    return dashboard.anomalies.filter(
      (a) => getAnomalySeverity(a.score) === severityFilter.toLowerCase()
    );
  }, [dashboard, severityFilter]);

  const uniqueChartTypes = useMemo(() => {
    if (!dashboard?.visuals) return [];
    return Array.from(new Set(dashboard.visuals.map((v) => v.chart_type).filter(Boolean)));
  }, [dashboard]);

  const handleOpenBIFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsParsing(true);
    setUploadError(null);
    try {
      const parsed = await parseBIUploadFile(file);
      setUploadedFile(parsed);
      setViewerMode(parsed.kind);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Failed to parse BI file.");
    } finally {
      setIsParsing(false);
      e.target.value = "";
    }
  };

  const activeTableauVisual = dashboard?.visuals?.[tableauSheetIndex] || dashboard?.visuals?.[0];

  return (
    <div className="p-5 sm:p-6 rounded-3xl glass-card border border-violet-500/25 space-y-5">
      {/* Top Toolbar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-violet-500/15 pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <LayoutDashboard className="w-5 h-5 text-amber-400" />
            <h3 className="text-lg font-bold text-white font-display">
              Interactive Power BI & Tableau Viewer
            </h3>
          </div>
          <p className="text-xs text-violet-300/75">
            Preview the generated 3-page Power BI (.pbip) & Tableau (.twbx) report in-browser, or open any exported .pbip / .twbx / .twb file from disk.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Mode Toggle */}
          <div className="inline-flex p-1 rounded-xl bg-black/40 border border-violet-500/25">
            <button
              type="button"
              onClick={() => setViewerMode("powerbi")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
                viewerMode === "powerbi"
                  ? "bg-amber-500/25 text-amber-200 border border-amber-500/40"
                  : "text-violet-300/70 hover:text-white"
              }`}
            >
              Power BI (.pbip)
            </button>
            <button
              type="button"
              onClick={() => setViewerMode("tableau")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
                viewerMode === "tableau"
                  ? "bg-violet-600/35 text-violet-100 border border-violet-400/40"
                  : "text-violet-300/70 hover:text-white"
              }`}
            >
              Tableau (.twbx)
            </button>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept=".twbx,.twb,.pbip,.zip"
            onChange={handleOpenBIFile}
            className="hidden"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isParsing}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-violet-900/50 hover:bg-violet-800/60 text-violet-100 text-xs font-medium border border-violet-500/30 transition cursor-pointer"
          >
            <FolderOpen className="w-3.5 h-3.5 text-amber-400" />
            <span>{isParsing ? "Opening..." : "Open .pbip / .twbx File"}</span>
          </button>
        </div>
      </div>

      {uploadError && (
        <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-500/30 text-xs text-rose-200 flex items-center justify-between">
          <span>{uploadError}</span>
          <button onClick={() => setUploadError(null)} className="cursor-pointer">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Uploaded Archive Inspector */}
      {uploadedFile && (
        <div className="p-4 rounded-2xl bg-black/45 border border-emerald-500/30 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-emerald-500/20 pb-3">
            <div className="flex items-center gap-2">
              <FileArchive className="w-4 h-4 text-emerald-400" />
              <span className="text-sm font-bold text-white font-display">
                Opened File: {uploadedFile.fileName}
              </span>
              <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono text-[10px] uppercase">
                {uploadedFile.kind}
              </span>
            </div>
            <button
              type="button"
              onClick={() => setUploadedFile(null)}
              className="text-xs text-violet-300 hover:text-white inline-flex items-center gap-1 cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
              <span>Close File</span>
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 text-xs">
            {/* Package Tree */}
            <div className="p-3 rounded-xl bg-violet-950/35 border border-violet-500/20 space-y-2">
              <div className="font-mono font-bold text-amber-300 uppercase text-[11px]">
                Archive Contents ({uploadedFile.files.length})
              </div>
              <div className="max-h-44 overflow-y-auto space-y-1 font-mono text-[11px] text-violet-200/80">
                {uploadedFile.files.map((f) => (
                  <div key={f.name} className="flex justify-between gap-2 truncate">
                    <span className="truncate">{f.name}</span>
                    <span className="text-violet-400 shrink-0">{f.size}B</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Pages or Worksheets */}
            <div className="p-3 rounded-xl bg-violet-950/35 border border-violet-500/20 space-y-2">
              <div className="font-mono font-bold text-amber-300 uppercase text-[11px]">
                {uploadedFile.kind === "powerbi"
                  ? `Report Pages (${uploadedFile.pages.length})`
                  : `Worksheets (${uploadedFile.worksheets.length})`}
              </div>
              <div className="max-h-44 overflow-y-auto space-y-1.5">
                {uploadedFile.kind === "powerbi"
                  ? uploadedFile.pages.map((p, idx) => (
                      <div key={idx} className="p-2 rounded-lg bg-black/35 border border-violet-500/15">
                        <div className="font-semibold text-white">{p.name}</div>
                        <div className="text-[10px] font-mono text-violet-300/80">
                          {p.visualsCount} visuals {p.visualTypes.length > 0 ? `(${p.visualTypes.join(", ")})` : ""}
                        </div>
                      </div>
                    ))
                  : uploadedFile.worksheets.map((ws, idx) => (
                      <div key={idx} className="p-2 rounded-lg bg-black/35 border border-violet-500/15">
                        <div className="font-semibold text-white">{ws.name}</div>
                        <div className="text-[10px] font-mono text-violet-300/80">
                          Mark: {ws.markType} · Cols: {ws.cols || "—"} · Rows: {ws.rows || "—"}
                        </div>
                      </div>
                    ))}
              </div>
            </div>

            {/* Calculated Fields / DAX */}
            <div className="p-3 rounded-xl bg-violet-950/35 border border-violet-500/20 space-y-2">
              <div className="font-mono font-bold text-amber-300 uppercase text-[11px]">
                {uploadedFile.kind === "powerbi"
                  ? `DAX Measures (${uploadedFile.daxMeasures.length})`
                  : `Calculated Fields (${uploadedFile.calculatedFields.length})`}
              </div>
              <div className="max-h-44 overflow-y-auto space-y-1.5 font-mono text-[11px]">
                {uploadedFile.kind === "powerbi"
                  ? uploadedFile.daxMeasures.map((m, i) => (
                      <div key={i} className="p-2 rounded-lg bg-black/35 border border-violet-500/15">
                        <div className="text-amber-200 font-bold">{m.name}</div>
                        <div className="text-violet-200/80 truncate">{m.expression}</div>
                      </div>
                    ))
                  : uploadedFile.calculatedFields.map((c, i) => (
                      <div key={i} className="p-2 rounded-lg bg-black/35 border border-violet-500/15">
                        <div className="text-amber-200 font-bold">{c.caption}</div>
                        <div className="text-violet-200/80 truncate">{c.formula}</div>
                      </div>
                    ))}
              </div>
            </div>
          </div>

          {/* Embedded CSV Data Preview */}
          {uploadedFile.csvPreview && (
            <div className="space-y-2">
              <div className="text-[11px] font-mono font-bold text-emerald-300 uppercase flex items-center gap-1.5">
                <Table2 className="w-3.5 h-3.5" />
                <span>Embedded Dataset Preview (First {uploadedFile.csvPreview.rows.length} rows)</span>
              </div>
              <div className="overflow-x-auto rounded-xl border border-violet-500/20">
                <table className="w-full text-left text-[11px] font-mono">
                  <thead className="bg-violet-950/60 text-amber-200">
                    <tr>
                      {uploadedFile.csvPreview.headers.map((h, i) => (
                        <th key={i} className="px-2.5 py-1.5 border-b border-violet-500/20 whitespace-nowrap">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-violet-500/10 text-violet-100/85">
                    {uploadedFile.csvPreview.rows.map((row, rIdx) => (
                      <tr key={rIdx} className="hover:bg-violet-900/20">
                        {row.map((cell, cIdx) => (
                          <td key={cIdx} className="px-2.5 py-1 whitespace-nowrap">
                            {cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Live Generated Report Canvas */}
      {!dashboard ? (
        <div className="p-8 rounded-2xl bg-black/30 border border-dashed border-violet-500/25 text-center space-y-2">
          <FileCode2 className="w-8 h-8 text-amber-400/80 mx-auto" />
          <div className="text-sm font-semibold text-white">
            No live analysis report loaded yet
          </div>
          <p className="text-xs text-violet-300/70 max-w-md mx-auto">
            Upload a CSV/TSV above to generate an Executive Report, or click{" "}
            <span className="text-amber-300 font-mono">Open .pbip / .twbx File</span> to inspect an existing Power BI or Tableau file.
          </p>
        </div>
      ) : viewerMode === "powerbi" ? (
        <div className="space-y-4 rounded-2xl bg-[#110c1d]/90 border border-amber-500/25 p-4 sm:p-5">
          {/* Power BI Canvas Header + Slicers */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-amber-500/15 pb-3">
            <div>
              <div className="text-[11px] font-mono uppercase tracking-wider text-amber-400">
                Power BI Canvas · Page {pbiPageIndex + 1} of {pbiPages.length}:{" "}
                {pbiPages[pbiPageIndex]?.name}
              </div>
              <div className="text-xs text-violet-300/75 mt-0.5">
                {pbiPages[pbiPageIndex]?.purpose}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="inline-flex items-center gap-1 text-violet-300 font-mono text-[11px]">
                <SlidersHorizontal className="w-3.5 h-3.5 text-amber-400" />
                Slicer:
              </span>
              <select
                value={chartTypeFilter}
                onChange={(e) => setChartTypeFilter(e.target.value)}
                className="px-2.5 py-1 rounded-lg bg-violet-950/70 border border-violet-500/30 text-violet-100 text-xs font-mono"
              >
                <option value="all">All Visuals ({dashboard.visuals.length})</option>
                {uniqueChartTypes.map((ct) => (
                  <option key={ct} value={ct}>
                    {ct}
                  </option>
                ))}
              </select>

              {pbiPageIndex === 2 && (
                <select
                  value={severityFilter}
                  onChange={(e) => setSeverityFilter(e.target.value)}
                  className="px-2.5 py-1 rounded-lg bg-violet-950/70 border border-amber-500/30 text-amber-200 text-xs font-mono"
                >
                  <option value="all">All Severities</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              )}
            </div>
          </div>

          {/* KPI Strip */}
          {dashboard.kpis.length > 0 && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              {dashboard.kpis.slice(0, 4).map((kpi, idx) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-xl bg-violet-950/50 border border-amber-500/20 space-y-1"
                >
                  <div className="text-[11px] font-mono text-violet-300/75 truncate">
                    {kpi.title}
                  </div>
                  <div className="text-lg font-extrabold text-white font-display">
                    {kpi.value}
                  </div>
                  <div className="text-[10px] font-mono text-amber-300/80 truncate">
                    DAX: {kpi.formula_dax}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Page Content */}
          {pbiPageIndex < 2 ? (
            pageVisuals.length > 0 ? (
              <ReportCharts visuals={pageVisuals} />
            ) : (
              <div className="p-6 text-center text-xs text-violet-300/70">
                No visuals match the active slicer filter.
              </div>
            )
          ) : (
            <div className="space-y-4">
              {filteredAnomalies.length > 0 ? (
                <div className="overflow-x-auto rounded-xl border border-amber-500/25">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-amber-950/40 text-amber-200 font-mono text-[11px]">
                      <tr>
                        <th className="px-3 py-2">Row</th>
                        <th className="px-3 py-2">Severity (Score)</th>
                        <th className="px-3 py-2">Explanation</th>
                        <th className="px-3 py-2">Action Required</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-violet-500/15 text-violet-100/85">
                      {filteredAnomalies.map((a, idx) => {
                        const sev = getAnomalySeverity(a.score);
                        return (
                          <tr key={idx} className="hover:bg-violet-900/20">
                            <td className="px-3 py-2 font-mono font-semibold text-white">
                              #{a.row_index}
                            </td>
                            <td className="px-3 py-2 font-mono uppercase text-[11px] text-amber-300">
                              {sev} ({a.score.toFixed(2)})
                            </td>
                            <td className="px-3 py-2 text-violet-100">{a.explanation}</td>
                            <td className="px-3 py-2 text-violet-200/80">
                              {a.action_required || a.business_impact || "Inspect outlier"}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-5 rounded-xl bg-violet-950/40 border border-violet-500/20 text-xs text-violet-300/80 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  <span>No anomalies matched the current severity slicer.</span>
                </div>
              )}
            </div>
          )}

          {/* Power BI Bottom Page Tabs */}
          <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-violet-500/15">
            {pbiPages.map((pg, idx) => (
              <button
                key={pg.page_number}
                type="button"
                onClick={() => setPbiPageIndex(idx)}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono transition cursor-pointer ${
                  pbiPageIndex === idx
                    ? "bg-amber-500/25 text-amber-200 border border-amber-500/40 font-bold"
                    : "bg-violet-950/40 text-violet-300/70 hover:text-white border border-violet-500/15"
                }`}
              >
                Page {pg.page_number}: {pg.name}
              </button>
            ))}
          </div>
        </div>
      ) : (
        /* TABLEAU (.twbx) WORKBOOK VIEW */
        <div className="space-y-4 rounded-2xl bg-[#110c1d]/90 border border-violet-500/25 p-4 sm:p-5">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-violet-500/15 pb-3">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-violet-400" />
              <span className="text-xs font-mono uppercase tracking-wider text-violet-200 font-bold">
                Tableau Workbook (.twbx) · {dashboard.visuals.length} Worksheets
              </span>
            </div>
            <span className="text-[11px] font-mono text-amber-300">
              {dashboard.tableau_calculated_fields.length} Calculated Fields
            </span>
          </div>

          {activeTableauVisual ? (
            <div className="space-y-4">
              {/* Tableau Shelves */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 text-xs font-mono">
                <div className="p-2.5 rounded-xl bg-black/40 border border-violet-500/20">
                  <span className="text-violet-400">Columns: </span>
                  <span className="px-2 py-0.5 rounded bg-violet-700/40 text-violet-100 border border-violet-500/30">
                    [{activeTableauVisual.x_axis}]
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-black/40 border border-violet-500/20">
                  <span className="text-violet-400">Rows: </span>
                  <span className="px-2 py-0.5 rounded bg-emerald-700/35 text-emerald-200 border border-emerald-500/30">
                    {activeTableauVisual.aggregation.toUpperCase()}([{activeTableauVisual.y_axis}])
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-black/40 border border-violet-500/20">
                  <span className="text-violet-400">Marks: </span>
                  <span className="px-2 py-0.5 rounded bg-amber-700/35 text-amber-200 border border-amber-500/30">
                    {activeTableauVisual.chart_type}
                  </span>
                </div>
              </div>

              <ReportCharts visuals={[activeTableauVisual]} />
            </div>
          ) : (
            <div className="p-6 text-center text-xs text-violet-300/70">
              No worksheets available in this report.
            </div>
          )}

          {/* Tableau Bottom Worksheet Tabs */}
          <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-violet-500/15">
            {dashboard.visuals.map((v, idx) => (
              <button
                key={v.id || idx}
                type="button"
                onClick={() => setTableauSheetIndex(idx)}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono transition cursor-pointer inline-flex items-center gap-1.5 ${
                  tableauSheetIndex === idx
                    ? "bg-violet-600/35 text-white border border-violet-400/50 font-bold"
                    : "bg-violet-950/40 text-violet-300/70 hover:text-white border border-violet-500/15"
                }`}
              >
                <BarChart3 className="w-3 h-3 text-amber-400" />
                <span>Sheet {idx + 1}: {v.title}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
