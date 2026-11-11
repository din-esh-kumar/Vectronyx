// frontend/src/features/data-analyst/ReportCharts.tsx
import React from "react";
import {
  Activity,
  BarChart2,
  BarChartHorizontal,
  GitCommitHorizontal,
  Layers,
  PieChart as PieIcon,
  ScatterChart as ScatterIcon,
  TrendingUp,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ChartSeriesPoint, ChartVisual } from "./types";
import { formatAxisTick, formatMetricValue, truncateLabel } from "./formatters";

const CHART_COLORS = [
  "#9333EA", // Vibrant Royal Violet
  "#C2671A", // Warm Cognac Bronze
  "#A855F7", // Electric Amethyst
  "#8D5C43", // Deep Roasted Chestnut
  "#7E22CE", // Imperial Purple
  "#E08A42", // Golden Amber Bronze
];

function getChartIcon(chartType: string) {
  const ct = (chartType || "").toLowerCase();
  if (ct === "pareto") return <Layers className="w-3.5 h-3.5 text-amber-400" />;
  if (ct === "histogram") return <BarChart2 className="w-3.5 h-3.5 text-violet-400" />;
  if (ct === "horizontal_bar") return <BarChartHorizontal className="w-3.5 h-3.5 text-amber-400" />;
  if (ct === "scatter") return <ScatterIcon className="w-3.5 h-3.5 text-amber-400" />;
  if (ct === "pie") return <PieIcon className="w-3.5 h-3.5 text-violet-400" />;
  if (ct === "area" || ct === "line") return <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />;
  return <BarChart2 className="w-3.5 h-3.5 text-violet-400" />;
}

function formatChartTypeLabel(chartType: string): string {
  const ct = (chartType || "bar").toLowerCase();
  switch (ct) {
    case "horizontal_bar":
      return "Horizontal Rank";
    case "pareto":
      return "Pareto 80/20";
    case "histogram":
      return "Distribution";
    case "scatter":
      return "Correlation Scatter";
    case "area":
      return "Time Series Area";
    case "line":
      return "Time Series Line";
    case "pie":
      return "Composition Donut";
    default:
      return "Cohort Bar";
  }
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ payload?: ChartSeriesPoint; value?: number; name?: string }>;
  vis: ChartVisual;
}

const ExpertChartTooltip: React.FC<CustomTooltipProps> = ({ active, payload, vis }) => {
  if (!active || !payload || payload.length === 0 || !payload[0]?.payload) {
    return null;
  }
  const pt = payload[0].payload;
  const ct = (vis.chart_type || "bar").toLowerCase();
  const isHistogram = ct === "histogram";

  return (
    <div
      style={{
        backgroundColor: "var(--bg-card)",
        color: "var(--text-primary)",
        border: "1px solid var(--border-subtle)",
        boxShadow: "0 12px 30px rgba(0, 0, 0, 0.35)",
      }}
      className="rounded-xl px-3.5 py-2.5 text-xs space-y-1 max-w-[260px]"
    >
      <div className="font-bold leading-snug break-words" style={{ color: "var(--text-primary)" }}>
        {pt.name}
      </div>

      {ct === "scatter" ? (
        <div className="space-y-0.5 font-mono text-[11px]">
          <div>
            <span style={{ color: "var(--text-muted)" }}>{vis.x_axis}: </span>
            <strong>{formatMetricValue(pt.x, null)}</strong>
          </div>
          <div>
            <span style={{ color: "var(--text-muted)" }}>{vis.y_axis}: </span>
            <strong>{formatMetricValue(pt.value, vis.unit_format)}</strong>
          </div>
          {pt.isOutlier && (
            <div className="mt-1 px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-500 font-semibold text-[10px]">
              IsolationForest Anomaly Outlier
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-0.5 font-mono text-[11px]">
          <div>
            <span style={{ color: "var(--text-muted)" }}>
              {isHistogram ? "Records in Bin" : `${vis.y_axis} (${vis.aggregation.toUpperCase()})`}:{" "}
            </span>
            <strong>{formatMetricValue(pt.value, isHistogram ? "count" : vis.unit_format)}</strong>
          </div>
          {pt.pct !== undefined && (
            <div>
              <span style={{ color: "var(--text-muted)" }}>Sample Share: </span>
              <strong>{pt.pct.toFixed(1)}%</strong>
            </div>
          )}
          {pt.count !== undefined && !isHistogram && (
            <div>
              <span style={{ color: "var(--text-muted)" }}>Cohort Size (n): </span>
              <strong>{pt.count.toLocaleString()}</strong>
            </div>
          )}
          {pt.sharePct !== undefined && (
            <div>
              <span style={{ color: "var(--text-muted)" }}>Portfolio Share: </span>
              <strong>{pt.sharePct.toFixed(1)}%</strong>
            </div>
          )}
          {pt.cumulativePct !== undefined && (
            <div>
              <span style={{ color: "var(--text-muted)" }}>Cumulative %: </span>
              <strong>{pt.cumulativePct.toFixed(1)}%</strong>
            </div>
          )}
          {pt.vsMeanPct !== undefined && (
            <div>
              <span style={{ color: "var(--text-muted)" }}>vs Cohort Mean: </span>
              <strong>
                {pt.vsMeanPct >= 0 ? "+" : ""}
                {pt.vsMeanPct.toFixed(1)}%
              </strong>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

interface ReportChartsProps {
  visuals: ChartVisual[];
  sectionTitle?: string;
  sectionSubtitle?: string;
}

export const ReportCharts: React.FC<ReportChartsProps> = ({
  visuals,
  sectionTitle,
  sectionSubtitle,
}) => {
  if (!visuals || visuals.length === 0) return null;

  return (
    <div className="space-y-4">
      {(sectionTitle || sectionSubtitle) && (
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2">
          <div>
            {sectionTitle && (
              <h3 className="text-base sm:text-lg font-bold text-white font-display flex items-center gap-2">
                <Activity className="w-5 h-5 text-amber-400 shrink-0" />
                <span>{sectionTitle}</span>
              </h3>
            )}
            {sectionSubtitle && (
              <p className="text-xs text-violet-300/70 mt-0.5">{sectionSubtitle}</p>
            )}
          </div>
          <span className="text-[11px] font-mono text-amber-300/80 self-start sm:self-auto">
            {visuals.length} Shape-Selected Visualizations
          </span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {visuals.map((vis, idx) => {
          const color = CHART_COLORS[idx % CHART_COLORS.length];
          const ct = (vis.chart_type || "bar").toLowerCase().trim();
          const data = vis.series_data || [];
          const hasManyBars = data.length > 6;
          const gradId = `area-grad-${vis.id || idx}-${idx}`;

          const normalScatter = ct === "scatter" ? data.filter((d) => !d.isOutlier) : [];
          const outlierScatter = ct === "scatter" ? data.filter((d) => d.isOutlier) : [];

          return (
            <div
              key={vis.id || idx}
              className="p-5 sm:p-6 rounded-3xl glass-card border border-violet-500/20 flex flex-col justify-between gap-3 print-break-avoid"
            >
              {/* Card Header */}
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-1.5 mb-1">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-mono font-semibold uppercase bg-amber-950/50 text-amber-300 border border-amber-500/30">
                        {getChartIcon(ct)}
                        <span>{formatChartTypeLabel(ct)}</span>
                      </span>
                      {vis.stat_badge && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-mono font-semibold bg-violet-950/60 text-violet-200 border border-violet-500/30">
                          {vis.stat_badge}
                        </span>
                      )}
                    </div>
                    <h4 className="text-sm sm:text-base font-bold text-white font-display leading-snug">
                      {vis.title}
                    </h4>
                  </div>

                  <div className="text-[10px] font-mono text-violet-300/70 shrink-0 text-right hidden sm:block">
                    <div>{vis.x_axis} → {vis.y_axis}</div>
                    <div className="uppercase text-amber-400/80">{vis.aggregation}</div>
                  </div>
                </div>

                {/* Why Selected Rationale */}
                {vis.selection_reason ? (
                  <div className="text-[11px] text-violet-200/85 bg-violet-950/40 border border-violet-500/20 rounded-xl px-3 py-1.5 leading-relaxed">
                    <span className="font-mono font-semibold text-violet-300 uppercase text-[10px] mr-1.5">
                      Why Chosen:
                    </span>
                    {vis.selection_reason}
                  </div>
                ) : (
                  <p className="text-xs text-violet-300/70 leading-relaxed">{vis.description}</p>
                )}
              </div>

              {/* Chart Canvas */}
              <div className="h-64 sm:h-72 w-full">
                {data.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    {ct === "horizontal_bar" ? (
                      <BarChart
                        data={data}
                        layout="vertical"
                        margin={{ top: 8, right: 20, left: 6, bottom: 8 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(139, 92, 246, 0.14)" horizontal={false} />
                        <XAxis
                          type="number"
                          stroke="#8B5CF6"
                          fontSize={11}
                          tickFormatter={(v) => formatAxisTick(v, vis.unit_format)}
                        />
                        <YAxis
                          type="category"
                          dataKey="name"
                          stroke="#8B5CF6"
                          fontSize={11}
                          width={122}
                          tickFormatter={(v) => truncateLabel(String(v), 17)}
                        />
                        <Tooltip content={<ExpertChartTooltip vis={vis} />} />
                        {vis.reference_value != null && (
                          <ReferenceLine
                            x={vis.reference_value}
                            stroke="#F59E0B"
                            strokeDasharray="4 4"
                            strokeWidth={1.5}
                          />
                        )}
                        <Bar dataKey="value" fill={color} radius={[0, 6, 6, 0]} maxBarSize={24} />
                      </BarChart>
                    ) : ct === "pareto" ? (
                      <ComposedChart data={data} margin={{ top: 10, right: 12, left: 4, bottom: hasManyBars ? 18 : 6 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(139, 92, 246, 0.14)" />
                        <XAxis
                          dataKey="name"
                          stroke="#8B5CF6"
                          fontSize={10.5}
                          interval={0}
                          angle={hasManyBars ? -20 : 0}
                          textAnchor={hasManyBars ? "end" : "middle"}
                          height={hasManyBars ? 48 : 30}
                          tickFormatter={(v) => truncateLabel(String(v), 12)}
                        />
                        <YAxis
                          yAxisId="left"
                          stroke="#8B5CF6"
                          fontSize={11}
                          width={56}
                          tickFormatter={(v) => formatAxisTick(v, vis.unit_format)}
                        />
                        <YAxis
                          yAxisId="right"
                          orientation="right"
                          domain={[0, 100]}
                          stroke="#F59E0B"
                          fontSize={10.5}
                          width={38}
                          tickFormatter={(v) => `${v}%`}
                        />
                        <Tooltip content={<ExpertChartTooltip vis={vis} />} />
                        <ReferenceLine
                          yAxisId="right"
                          y={80}
                          stroke="#F59E0B"
                          strokeDasharray="4 4"
                          label={{ value: "80%", position: "insideTopRight", fill: "#F59E0B", fontSize: 10 }}
                        />
                        <Bar yAxisId="left" dataKey="value" fill={color} radius={[5, 5, 0, 0]} maxBarSize={38} />
                        <Line
                          yAxisId="right"
                          type="monotone"
                          dataKey="cumulativePct"
                          name="Cumulative %"
                          stroke="#F59E0B"
                          strokeWidth={2.5}
                          dot={{ r: 3.5, fill: "#F59E0B" }}
                        />
                      </ComposedChart>
                    ) : ct === "histogram" ? (
                      <BarChart
                        data={data}
                        barCategoryGap="6%"
                        margin={{ top: 10, right: 10, left: 0, bottom: 20 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(139, 92, 246, 0.14)" vertical={false} />
                        <XAxis
                          dataKey="name"
                          stroke="#8B5CF6"
                          fontSize={10}
                          interval={0}
                          angle={-22}
                          textAnchor="end"
                          height={50}
                          tickFormatter={(v) => truncateLabel(String(v), 15)}
                        />
                        <YAxis
                          stroke="#8B5CF6"
                          fontSize={11}
                          width={46}
                          tickFormatter={(v) => formatAxisTick(v, "count")}
                        />
                        <Tooltip content={<ExpertChartTooltip vis={vis} />} />
                        <Bar dataKey="value" fill="#9333EA" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    ) : ct === "scatter" ? (
                      <ScatterChart margin={{ top: 12, right: 16, left: 4, bottom: 8 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(139, 92, 246, 0.14)" />
                        <XAxis
                          type="number"
                          dataKey="x"
                          name={vis.x_axis}
                          stroke="#8B5CF6"
                          fontSize={11}
                          tickFormatter={(v) => formatAxisTick(v, null)}
                        />
                        <YAxis
                          type="number"
                          dataKey="value"
                          name={vis.y_axis}
                          stroke="#8B5CF6"
                          fontSize={11}
                          width={54}
                          tickFormatter={(v) => formatAxisTick(v, vis.unit_format)}
                        />
                        <Tooltip content={<ExpertChartTooltip vis={vis} />} />
                        <Legend wrapperStyle={{ fontSize: "11px" }} />
                        <Scatter
                          name="Typical Cohort"
                          data={normalScatter}
                          fill="#A855F7"
                          fillOpacity={0.82}
                        />
                        {outlierScatter.length > 0 && (
                          <Scatter
                            name="Outliers (Anomaly)"
                            data={outlierScatter}
                            fill="#F59E0B"
                            shape="diamond"
                          />
                        )}
                      </ScatterChart>
                    ) : ct === "line" ? (
                      <LineChart data={data} margin={{ top: 10, right: 16, left: 4, bottom: 6 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(139, 92, 246, 0.14)" />
                        <XAxis dataKey="name" stroke="#8B5CF6" fontSize={11} />
                        <YAxis
                          stroke="#8B5CF6"
                          fontSize={11}
                          width={56}
                          tickFormatter={(v) => formatAxisTick(v, vis.unit_format)}
                        />
                        <Tooltip content={<ExpertChartTooltip vis={vis} />} />
                        {vis.reference_value != null && (
                          <ReferenceLine y={vis.reference_value} stroke="#F59E0B" strokeDasharray="4 4" />
                        )}
                        <Line
                          type="monotone"
                          dataKey="value"
                          stroke={color}
                          strokeWidth={2.5}
                          dot={{ r: 3.5, fill: color }}
                          activeDot={{ r: 5.5 }}
                        />
                      </LineChart>
                    ) : ct === "area" ? (
                      <AreaChart data={data} margin={{ top: 10, right: 16, left: 4, bottom: 6 }}>
                        <defs>
                          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={color} stopOpacity={0.45} />
                            <stop offset="95%" stopColor={color} stopOpacity={0.03} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(139, 92, 246, 0.14)" />
                        <XAxis dataKey="name" stroke="#8B5CF6" fontSize={11} />
                        <YAxis
                          stroke="#8B5CF6"
                          fontSize={11}
                          width={56}
                          tickFormatter={(v) => formatAxisTick(v, vis.unit_format)}
                        />
                        <Tooltip content={<ExpertChartTooltip vis={vis} />} />
                        {vis.reference_value != null && (
                          <ReferenceLine y={vis.reference_value} stroke="#F59E0B" strokeDasharray="4 4" />
                        )}
                        <Area
                          type="monotone"
                          dataKey="value"
                          stroke={color}
                          strokeWidth={2.25}
                          fillOpacity={1}
                          fill={`url(#${gradId})`}
                        />
                      </AreaChart>
                    ) : ct === "pie" ? (
                      <PieChart>
                        <Tooltip content={<ExpertChartTooltip vis={vis} />} />
                        <Pie
                          data={data}
                          dataKey="value"
                          nameKey="name"
                          cx="50%"
                          cy="48%"
                          outerRadius={78}
                          innerRadius={44}
                          paddingAngle={2}
                        >
                          {data.map((_, i) => (
                            <Cell key={`cell-${i}`} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                          ))}
                        </Pie>
                        <Legend wrapperStyle={{ fontSize: "11px" }} />
                      </PieChart>
                    ) : (
                      <BarChart data={data} margin={{ top: 10, right: 12, left: 4, bottom: hasManyBars ? 16 : 6 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(139, 92, 246, 0.14)" vertical={false} />
                        <XAxis
                          dataKey="name"
                          stroke="#8B5CF6"
                          fontSize={11}
                          interval={0}
                          angle={hasManyBars ? -18 : 0}
                          textAnchor={hasManyBars ? "end" : "middle"}
                          height={hasManyBars ? 46 : 30}
                          tickFormatter={(v) => truncateLabel(String(v), 14)}
                        />
                        <YAxis
                          stroke="#8B5CF6"
                          fontSize={11}
                          width={56}
                          tickFormatter={(v) => formatAxisTick(v, vis.unit_format)}
                        />
                        <Tooltip content={<ExpertChartTooltip vis={vis} />} />
                        {vis.reference_value != null && (
                          <ReferenceLine
                            y={vis.reference_value}
                            stroke="#F59E0B"
                            strokeDasharray="4 4"
                            strokeWidth={1.5}
                          />
                        )}
                        <Bar dataKey="value" fill={color} radius={[6, 6, 0, 0]} maxBarSize={44} />
                      </BarChart>
                    )}
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-xs text-violet-400/60">
                    No empirical series points available for {vis.title}
                  </div>
                )}
              </div>

              {/* Analytical Finding Footer */}
              <div className="pt-2 border-t border-violet-500/15 space-y-1">
                {vis.reference_label && (
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-amber-400/90">
                    <GitCommitHorizontal className="w-3.5 h-3.5 shrink-0" />
                    <span>Dashed Reference Benchmark: {vis.reference_label}</span>
                  </div>
                )}
                <div className="text-xs text-amber-200/90 bg-amber-950/30 border border-amber-500/20 rounded-xl px-3 py-2 leading-relaxed">
                  <strong className="text-amber-300 font-semibold">Finding: </strong>
                  {vis.key_insight || vis.description}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
