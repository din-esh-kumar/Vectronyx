# backend/app/modules/data_analyst/schemas.py
from typing import List, Dict, Any, Optional
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
    chart_type: str  # "bar", "line", "area", "pie", "scatter"
    x_axis: str
    y_axis: str
    aggregation: str = "sum"  # "sum", "avg", "count"
    series_data: List[Dict[str, Any]] = []
    description: str

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

class DashboardGenerateRequest(BaseModel):
    prompt: str = Field(..., description="User prompt describing analysis or dashboard requirements")
    csv_data: str = Field(..., description="Raw CSV string content")
    dataset_name: Optional[str] = "dataset.csv"
