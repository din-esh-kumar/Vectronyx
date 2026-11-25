// frontend/src/features/data-analyst/types.ts

export interface KPISpec {
  id: string;
  title: string;
  value: string;
  change?: string;
  trend: string;
  benchmark?: string;
  variance?: string;
  executive_takeaway?: string;
  formula_dax: string;
  formula_tableau: string;
  rationale: string;
}

export interface ChartSeriesPoint {
  name: string;
  value: number;
  x?: number;
  count?: number;
  pct?: number;
  sharePct?: number;
  cumulativePct?: number;
  vsMeanPct?: number;
  binMin?: number;
  binMax?: number;
  isOutlier?: boolean;
}

export interface ChartVisual {
  id: string;
  title: string;
  chart_type: string;
  x_axis: string;
  y_axis: string;
  aggregation: string;
  description: string;
  selection_reason?: string;
  key_insight?: string;
  reference_value?: number | null;
  reference_label?: string | null;
  unit_format?: string | null;
  stat_badge?: string | null;
  series_data: ChartSeriesPoint[];
}

export interface AnomalyFinding {
  row_index: number;
  score: number;
  explanation: string;
  root_cause_attribution?: string;
  business_impact?: string;
  action_required?: string;
  features: Record<string, any>;
}

export interface StatisticalDiagnostic {
  metric_name: string;
  mean: number;
  std: number;
  median?: number | null;
  p25?: number | null;
  p75?: number | null;
  p95?: number | null;
  min_val?: number | null;
  max_val?: number | null;
  iqr?: number | null;
  outlier_count?: number | null;
  outlier_pct?: number | null;
  normality_verdict?: string | null;
  sample_count?: number | null;
  unit_format?: string | null;
  skewness: number;
  kurtosis: number;
  cv: number;
  interpretation: string;
}

export interface CorrelationInsight {
  metric_a: string;
  metric_b: string;
  pearson_r: number;
  spearman_rho: number;
  p_value: number;
  strength: string;
  direction: string;
  interpretation: string;
}

export interface CorrelationMatrixData {
  metrics: string[];
  matrix: number[][];
}

export interface SegmentPerformanceRow {
  dimension: string;
  segment: string;
  record_count: number;
  metric_total?: number | null;
  metric_mean: number;
  share_pct: number;
  vs_mean_pct: number;
  status: string;
}

export interface SegmentBenchmark {
  dimension: string;
  metric: string;
  eta_squared: number;
  cohort_count: number;
  top_segment: string;
  bottom_segment: string;
  spread_ratio?: number | null;
  narrative: string;
  rows: SegmentPerformanceRow[];
}

export interface ColumnAuditItem {
  name: string;
  semantic_role: string;
  dtype: string;
  null_count: number;
  null_pct: number;
  unique_count: number;
  zero_count: number;
  recommendation: string;
}

export interface DataQualityAudit {
  total_rows: number;
  total_columns: number;
  duplicate_rows: number;
  duplicate_pct: number;
  completeness_pct: number;
  excluded_id_columns: string[];
  temporal_columns: string[];
  continuous_columns: string[];
  rate_columns: string[];
  categorical_columns: string[];
  column_audit: ColumnAuditItem[];
}

export interface ConcentrationAnalysis {
  dimension: string;
  metric: string;
  top_20_percent_share: number;
  hhi_index: number;
  market_classification: string;
  strategic_takeaway: string;
}

export interface StrategicInitiative {
  priority: string;
  time_horizon: string;
  title: string;
  rationale: string;
  expected_financial_impact: string;
  operational_owner: string;
  risk_level: string;
}

export interface RiskAssessment {
  risk_title: string;
  severity: string;
  probability: string;
  business_exposure: string;
  mitigation_protocol: string;
}

export interface ExecutiveDossier {
  executive_verdict: string;
  situation: string;
  complication: string;
  resolution: string;
  data_integrity_score: number;
  statistical_diagnostics: StatisticalDiagnostic[];
  concentration_risk?: ConcentrationAnalysis | null;
  data_quality_audit?: DataQualityAudit | null;
  correlation_insights?: CorrelationInsight[];
  correlation_matrix?: CorrelationMatrixData | null;
  segment_benchmarks?: SegmentBenchmark[];
  strategic_initiatives: StrategicInitiative[];
  risk_matrix: RiskAssessment[];
  methodological_notes: string[];
}

export interface RefinementIterationRecord {
  iteration: number;
  score: number;
  rubric_scores?: Record<string, number>;
  critiques_found?: string[];
  improvements_applied?: string[];
  verdict: string;
}

export interface PowerBiPageBlueprint {
  page_number: number;
  name: string;
  dimensions: string;
  purpose: string;
  slicers?: string[];
  kpis?: string[];
  visuals?: string[];
}

export interface CleansingAction {
  stage: string;
  target: string;
  action: string;
  count: number;
  detail: string;
}

export interface DataCleansingReport {
  raw_rows: number;
  cleaned_rows: number;
  rows_removed: number;
  duplicates_removed: number;
  raw_columns: number;
  cleaned_columns: number;
  columns_dropped: number;
  dropped_column_names: string[];
  redundant_columns_removed: string[];
  collinear_features_pruned: string[];
  type_coercions: string[];
  missing_values_imputed: number;
  whitespace_and_case_normalized: number;
  outliers_winsorized: number;
  integrity_before: number;
  integrity_after: number;
  actions: CleansingAction[];
}

export interface ClusterProfile {
  cluster_id: number;
  label: string;
  size: number;
  share_pct: number;
  centroid_summary: Record<string, number>;
}

export interface FeatureImportanceItem {
  feature: string;
  importance_pct: number;
  direction: string;
}

export interface DataScienceSummary {
  target_metric?: string | null;
  model_type: string;
  r2_score?: number | null;
  rmse?: number | null;
  optimal_clusters: number;
  silhouette_score?: number | null;
  pca_variance_explained_pct: number[];
  top_feature_importances: FeatureImportanceItem[];
  clusters: ClusterProfile[];
  ai_data_science_verdict: string;
  models_participated: string[];
}

export interface DashboardPlan {
  title: string;
  summary: string;
  dataset_name: string;
  kpis: KPISpec[];
  visuals: ChartVisual[];
  anomalies: AnomalyFinding[];
  dossier?: ExecutiveDossier | null;
  dax_script: string;
  powerquery_m: string;
  tableau_calculated_fields: Array<{ caption: string; formula: string }>;
  focused_metrics?: string[];
  focused_dimensions?: string[];
  analytical_intent?: string;
  quality_score?: number | null;
  refinement_iterations_run?: number;
  refinement_history?: RefinementIterationRecord[];
  powerbi_pages?: PowerBiPageBlueprint[];
  cleansing_report?: DataCleansingReport | null;
  data_science_summary?: DataScienceSummary | null;
  models_used?: string[];
}
