# backend/app/modules/data_analyst/schemas.py
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

class ColumnMetric(BaseModel):
    name: str
    dtype: str
    null_count: int = 0
    unique_count: int = 0
    sample_values: List[Any] = []
    min_val: Optional[Any] = None
    max_val: Optional[Any] = None
    mean_val: Optional[float] = None
    skewness: Optional[float] = None
    cv: Optional[float] = None  # Coefficient of Variation (std / mean)

class DatasetProfile(BaseModel):
    row_count: int
    col_count: int
    columns: List[ColumnMetric]
    preview_rows: List[Dict[str, Any]]
    data_integrity_score: float = 100.0

class KPISpec(BaseModel):
    id: str
    title: str
    value: str
    change: Optional[str] = None
    trend: str = "neutral"  # "up", "down", "neutral"
    benchmark: Optional[str] = None
    variance: Optional[str] = None
    executive_takeaway: Optional[str] = None
    formula_dax: str
    formula_tableau: str
    rationale: str

class ChartVisualSpec(BaseModel):
    id: str
    title: str
    chart_type: str  # "bar", "horizontal_bar", "line", "area", "pie", "scatter", "histogram", "pareto"
    x_axis: str
    y_axis: str
    aggregation: str = "sum"  # "sum", "avg", "count", "distribution", "pareto", "raw"
    series_data: List[Dict[str, Any]] = []
    description: str
    selection_reason: Optional[str] = None
    key_insight: Optional[str] = None
    reference_value: Optional[float] = None
    reference_label: Optional[str] = None
    unit_format: Optional[str] = None  # "currency", "percent", "number", "count"
    stat_badge: Optional[str] = None

class AnomalyFinding(BaseModel):
    row_index: int
    score: float
    explanation: str
    root_cause_attribution: Optional[str] = "Multivariate feature variance exceeds threshold"
    business_impact: Optional[str] = "High probability of transaction distortion or reporting leak"
    action_required: Optional[str] = "Audit underlying ledger entry and verify source data"
    features: Dict[str, Any] = {}

class StatisticalDiagnostic(BaseModel):
    metric_name: str
    mean: float
    std: float
    skewness: float
    kurtosis: float
    cv: float  # Coefficient of Variation
    interpretation: str
    median: Optional[float] = None
    p25: Optional[float] = None
    p75: Optional[float] = None
    p95: Optional[float] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    iqr: Optional[float] = None
    outlier_count: Optional[int] = None
    outlier_pct: Optional[float] = None
    normality_verdict: Optional[str] = None
    sample_count: Optional[int] = None
    unit_format: Optional[str] = None

class CorrelationInsight(BaseModel):
    metric_a: str
    metric_b: str
    pearson_r: float
    spearman_rho: Optional[float] = None
    p_value: Optional[float] = None
    strength: str  # "Strong", "Moderate", "Weak", "Negligible"
    direction: str  # "Positive", "Inverse", "Neutral"
    interpretation: str

class CorrelationMatrixData(BaseModel):
    metrics: List[str] = []
    matrix: List[List[float]] = []

class SegmentPerformanceRow(BaseModel):
    dimension: str
    segment: str
    record_count: int
    metric_total: Optional[float] = None
    metric_mean: float
    share_pct: float
    vs_mean_pct: float
    status: str  # "Outperformer", "Baseline", "Underperformer"

class SegmentBenchmark(BaseModel):
    dimension: str
    metric: str
    eta_squared: float
    cohort_count: int
    top_segment: str
    bottom_segment: str
    spread_ratio: Optional[float] = None
    narrative: str
    rows: List[SegmentPerformanceRow] = []

class ColumnAuditItem(BaseModel):
    name: str
    semantic_role: str
    dtype: str
    null_count: int
    null_pct: float
    unique_count: int
    zero_count: int = 0
    recommendation: Optional[str] = None

class DataQualityAudit(BaseModel):
    total_rows: int
    total_columns: int
    duplicate_rows: int
    duplicate_pct: float
    completeness_pct: float
    excluded_id_columns: List[str] = []
    temporal_columns: List[str] = []
    continuous_columns: List[str] = []
    rate_columns: List[str] = []
    categorical_columns: List[str] = []
    column_audit: List[ColumnAuditItem] = []

class ConcentrationAnalysis(BaseModel):
    dimension: str
    metric: str
    top_20_percent_share: float  # E.g., 78.4%
    hhi_index: float  # Herfindahl-Hirschman Index
    market_classification: str  # "Highly Concentrated", "Moderately Concentrated", "Competitive"
    strategic_takeaway: str

class StrategicInitiative(BaseModel):
    priority: str  # "P0 - Immediate", "P1 - 30-60 Days", "P2 - 90 Days+"
    time_horizon: str
    title: str
    rationale: str
    expected_financial_impact: str
    operational_owner: str
    risk_level: str  # "Low", "Medium", "High"

class RiskAssessment(BaseModel):
    risk_title: str
    severity: str  # "Critical", "High", "Moderate"
    probability: str  # "High", "Medium", "Low"
    business_exposure: str
    mitigation_protocol: str

class ExecutiveDossier(BaseModel):
    executive_verdict: str
    situation: str  # Current operating baseline
    complication: str  # Latent risks, structural vulnerabilities
    resolution: str  # Strategic roadmap and recommendations
    data_integrity_score: float
    statistical_diagnostics: List[StatisticalDiagnostic] = []
    concentration_risk: Optional[ConcentrationAnalysis] = None
    strategic_initiatives: List[StrategicInitiative] = []
    risk_matrix: List[RiskAssessment] = []
    methodological_notes: List[str] = []
    data_quality_audit: Optional[DataQualityAudit] = None
    correlation_insights: List[CorrelationInsight] = []
    correlation_matrix: Optional[CorrelationMatrixData] = None
    segment_benchmarks: List[SegmentBenchmark] = []

class RefinementIterationRecord(BaseModel):
    iteration: int
    score: float
    rubric_scores: Dict[str, float] = {}
    critiques_found: List[str] = []
    improvements_applied: List[str] = []
    verdict: str = "needs_refinement"  # "needs_refinement" | "expert_certified"


class ReportCritique(BaseModel):
    overall_score: float = Field(..., ge=0.0, le=100.0)
    empirical_grounding: float = Field(..., ge=0.0, le=100.0)
    executive_depth: float = Field(..., ge=0.0, le=100.0)
    statistical_rigor: float = Field(..., ge=0.0, le=100.0)
    visual_storytelling: float = Field(..., ge=0.0, le=100.0)
    powerbi_dax_readiness: float = Field(..., ge=0.0, le=100.0)
    actionability_roi: float = Field(..., ge=0.0, le=100.0)
    critical_defects: List[str] = []
    concrete_upgrade_directives: List[str] = []
    dax_and_powerbi_upgrades: List[str] = []
    passes_principal_bar: bool = False


class LLMChartVisualDraft(BaseModel):
    """Lean chart schema for LLM generation (series_data is computed deterministically by Pandas)."""
    id: str
    title: str
    chart_type: str
    x_axis: str
    y_axis: str
    aggregation: str = "sum"
    description: str
    selection_reason: Optional[str] = None
    key_insight: Optional[str] = None


class LLMExecutiveDossierDraft(BaseModel):
    """Lean executive narrative schema for LLM generation (quantitative matrices computed deterministically)."""
    executive_verdict: str
    situation: str
    complication: str
    resolution: str
    data_integrity_score: float = 100.0
    strategic_initiatives: List[StrategicInitiative] = []
    risk_matrix: List[RiskAssessment] = []
    methodological_notes: List[str] = []


class LLMDashboardDraft(BaseModel):
    """Token-efficient structured output schema for LLM planning & N-iteration refinement."""
    title: str
    summary: str
    dataset_name: str = "Dataset"
    kpis: List[KPISpec]
    visuals: List[LLMChartVisualDraft]
    dossier: Optional[LLMExecutiveDossierDraft] = None
    dax_script: str = ""
    powerquery_m: str = ""
    tableau_calculated_fields: List[Dict[str, str]] = []

    def to_dashboard_plan(self) -> "DashboardPlan":
        return DashboardPlan(
            title=self.title,
            summary=self.summary,
            dataset_name=self.dataset_name,
            kpis=self.kpis,
            visuals=[ChartVisualSpec(**v.model_dump()) for v in self.visuals],
            dossier=ExecutiveDossier(**self.dossier.model_dump()) if self.dossier else None,
            dax_script=self.dax_script,
            powerquery_m=self.powerquery_m,
            tableau_calculated_fields=self.tableau_calculated_fields,
        )


class CleansingAction(BaseModel):
    stage: str
    target: str
    action: str
    count: int = 0
    detail: str


class DataCleansingReport(BaseModel):
    raw_rows: int
    cleaned_rows: int
    rows_removed: int = 0
    duplicates_removed: int = 0
    raw_columns: int
    cleaned_columns: int
    columns_dropped: int = 0
    dropped_column_names: List[str] = []
    redundant_columns_removed: List[str] = []
    collinear_features_pruned: List[str] = []
    type_coercions: List[str] = []
    missing_values_imputed: int = 0
    whitespace_and_case_normalized: int = 0
    outliers_winsorized: int = 0
    integrity_before: float = 100.0
    integrity_after: float = 100.0
    actions: List[CleansingAction] = []


class ClusterProfile(BaseModel):
    cluster_id: int
    label: str
    size: int
    share_pct: float
    centroid_summary: Dict[str, float] = {}


class FeatureImportanceItem(BaseModel):
    feature: str
    importance_pct: float
    direction: str = "positive"


class DataScienceSummary(BaseModel):
    target_metric: Optional[str] = None
    model_type: str = "Unsupervised + Predictive Feature Importance"
    r2_score: Optional[float] = None
    rmse: Optional[float] = None
    optimal_clusters: int = 0
    silhouette_score: Optional[float] = None
    pca_variance_explained_pct: List[float] = []
    top_feature_importances: List[FeatureImportanceItem] = []
    clusters: List[ClusterProfile] = []
    ai_data_science_verdict: str = ""
    models_participated: List[str] = []


class LLMDataScienceSynthesis(BaseModel):
    """Structured output returned by Groq/Gemini for the Data Science & Cleansing audit."""
    cleansing_assessment: str
    feature_engineering_recommendations: List[str] = []
    cluster_interpretations: List[str] = []
    predictive_driver_takeaway: str


class DatasetVerificationCheck(BaseModel):
    name: str
    status: Literal["pass", "warn", "fail"]
    detail: str


class DatasetVerificationResult(BaseModel):
    status: Literal["perfect", "good_with_warnings", "unusable"]
    is_good_dataset: bool
    readiness_score: float = Field(..., ge=0.0, le=100.0)
    summary: str
    row_count: int = 0
    column_count: int = 0
    cleaned_row_count: int = 0
    cleaned_column_count: int = 0
    completeness_pct: float = 0.0
    duplicate_rows: int = 0
    numeric_metrics: List[str] = []
    categorical_dimensions: List[str] = []
    temporal_dimensions: List[str] = []
    excluded_id_columns: List[str] = []
    checks: List[DatasetVerificationCheck] = []
    warnings: List[str] = []
    blocking_issues: List[str] = []


class AlignedMetricSpec(BaseModel):
    metric_name: str
    role: Literal["North Star", "Guardrail", "Driver", "Segment Dimension"] = "Driver"
    aggregation: str
    stakeholder_alignment: str


class StakeholderAlignment(BaseModel):
    stakeholder_role: str
    primary_concern: str
    target_metrics: List[str] = []


class ProblemDefinitionResult(BaseModel):
    core_question: str
    business_goal: str
    decision_needed: str
    stakeholders: List[StakeholderAlignment] = []
    aligned_metrics: List[AlignedMetricSpec] = []
    clarifying_questions: List[str] = []
    recommended_analysis_prompt: str
    static_signals: List[str] = []
    synthesis_mode: str = "static_only"  # "static_and_ai" | "static_only"
    ai_provider_used: str = "deterministic"


class DatasetIntakeResponse(BaseModel):
    dataset_name: str = "dataset.csv"
    verification: DatasetVerificationResult
    problem_definition: Optional[ProblemDefinitionResult] = None


class DashboardPlan(BaseModel):
    title: str
    summary: str
    dataset_name: str = "Dataset"
    kpis: List[KPISpec]
    visuals: List[ChartVisualSpec]
    anomalies: List[AnomalyFinding] = []
    dossier: Optional[ExecutiveDossier] = None
    dax_script: str = ""
    powerquery_m: str = ""
    tableau_calculated_fields: List[Dict[str, str]] = []
    focused_metrics: List[str] = []
    focused_dimensions: List[str] = []
    analytical_intent: Optional[str] = None
    quality_score: Optional[float] = None
    refinement_iterations_run: int = 0
    refinement_history: List[RefinementIterationRecord] = []
    powerbi_pages: List[Dict[str, Any]] = []
    cleansing_report: Optional[DataCleansingReport] = None
    data_science_summary: Optional[DataScienceSummary] = None
    models_used: List[str] = []
    dataset_verification: Optional[DatasetVerificationResult] = None
    problem_definition: Optional[ProblemDefinitionResult] = None


class DashboardGenerateRequest(BaseModel):
    prompt: str = Field(..., description="User prompt describing analysis or dashboard requirements")
    csv_data: str = Field(..., description="Raw CSV string content")
    dataset_name: Optional[str] = "dataset.csv"
    refinement_iterations: int = Field(3, ge=1, le=8, description="Number of iterative peer-review & refinement passes")
    target_quality_score: float = Field(92.0, ge=75.0, le=99.0, description="Target Principal Analyst rubric score")
