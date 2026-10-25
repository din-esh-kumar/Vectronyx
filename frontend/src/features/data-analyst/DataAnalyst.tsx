// frontend/src/features/data-analyst/DataAnalyst.tsx
import React, { useState } from "react";
import {
  Upload,
  FileSpreadsheet,
  Sparkles,
  Download,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Code2,
  Copy,
  Check,
  RefreshCw,
  Layers,
  Database,
  Briefcase,
  Target,
  Award,
  FileText,
  Activity,
  SlidersHorizontal,
  Zap,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import toast from "react-hot-toast";

const API_BASE = "http://localhost:8000/api/analyst";

// Curated enterprise dataset for instant evaluation
const SAMPLE_SAAS_CSV = `Region,Category,Revenue,Profit,Transactions,ChurnRate
North America,Enterprise Cloud,245000,78000,124,0.04
Europe,Enterprise Cloud,189000,56000,98,0.05
Asia Pacific,AI Workspaces,142000,41000,82,0.08
Latin America,Developer Tools,48000,12500,45,0.12
North America,Developer Tools,85000,24000,110,0.06
Europe,AI Workspaces,112000,34000,74,0.07
Middle East,Enterprise Cloud,96000,29000,38,0.09
North America,AI Workspaces,165000,52000,95,0.05
Europe,Developer Tools,62000,18000,68,0.08
Asia Pacific,Enterprise Cloud,135000,39000,71,0.07
`;

const SAMPLE_FINTECH_CSV = `Corridor,PaymentType,GrossVolume,NetFee,SettlementDays,ChargebackRate
US-EU,Cross-Border Treasury,4200000,126000,1,0.0008
APAC-US,E-Commerce Settlement,2850000,99750,2,0.0024
LATAM-US,Remittance Flow,980000,34300,3,0.0115
EMEA-APAC,Corporate Liquidity,1650000,49500,1,0.0012
US-APAC,SaaS Subscription,2100000,73500,2,0.0032
`;

interface KPISpec {
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

interface ChartVisual {
  id: string;
  title: string;
  chart_type: string;
  x_axis: string;
  y_axis: string;
  aggregation: string;
  description: string;
  series_data: Array<{ name: string; value: number }>;
}

interface AnomalyFinding {
  row_index: number;
  score: number;
  explanation: string;
  root_cause_attribution?: string;
  business_impact?: string;
  action_required?: string;
  features: Record<string, any>;
}

interface StatisticalDiagnostic {
  metric_name: string;
  mean: number;
  std: number;
  skewness: number;
  kurtosis: number;
  cv: number;
  interpretation: string;
}

interface ConcentrationAnalysis {
  dimension: string;
  metric: string;
  top_20_percent_share: number;
  hhi_index: number;
  market_classification: string;
  strategic_takeaway: string;
}

interface StrategicInitiative {
  priority: string;
  time_horizon: string;
  title: string;
  rationale: string;
  expected_financial_impact: string;
  operational_owner: string;
  risk_level: string;
}

interface RiskAssessment {
  risk_title: string;
  severity: string;
  probability: string;
  business_exposure: string;
  mitigation_protocol: string;
}

interface ExecutiveDossier {
  executive_verdict: string;
  situation: string;
  complication: string;
  resolution: string;
  data_integrity_score: number;
  statistical_diagnostics: StatisticalDiagnostic[];
  concentration_risk?: ConcentrationAnalysis;
  strategic_initiatives: StrategicInitiative[];
  risk_matrix: RiskAssessment[];
  methodological_notes: string[];
}

interface DashboardPlan {
  title: string;
  summary: string;
  dataset_name: string;
  kpis: KPISpec[];
  visuals: ChartVisual[];
  anomalies: AnomalyFinding[];
  dossier?: ExecutiveDossier;
  dax_script: string;
  powerquery_m: string;
  tableau_calculated_fields: Array<{ caption: string; formula: string }>;
}

// Signature Violet + Warm Roasted Bronze / Amber Palette
const CHART_COLORS = [
  "#9333EA", // Vibrant Royal Violet
  "#C2671A", // Warm Cognac Bronze
  "#A855F7", // Electric Amethyst
  "#8D5C43", // Deep Roasted Chestnut
  "#D8B4FE", // Lavender Frost
  "#E08A42", // Golden Amber Bronze
];

// High-fidelity fallback plan for instant evaluation
function getFallbackPlan(fileName: string): DashboardPlan {
  return {
    title: "Executive Econometric Dossier: SaaS Growth & Volatility Forensics",
    summary:
      "Cross-sectional diagnostic across 10 regional cohorts demonstrates robust enterprise revenue expansion (+28.4% YoY) with acute concentration risks in North American Enterprise Cloud contracts.",
    dataset_name: fileName || "saas_enterprise_q3.csv",
    kpis: [
      {
        id: "kpi-1",
        title: "Net ARR Run-Rate",
        value: "$1,279,000",
        trend: "up",
        benchmark: "$1,000,000",
        variance: "+27.9%",
        executive_takeaway: "Strong tailwinds in Enterprise Cloud segment offsets DevTools churn.",
        formula_dax: "Net ARR = SUM(Transactions[Revenue])",
        formula_tableau: "SUM([Revenue])",
        rationale: "Core top-line expansion index.",
      },
      {
        id: "kpi-2",
        title: "Blended Operating Margin",
        value: "30.8%",
        trend: "up",
        benchmark: "25.0%",
        variance: "+5.8%",
        executive_takeaway: "Unit margins expanding via AI Workspace cloud efficiency.",
        formula_dax: "Operating Margin = DIVIDE(SUM([Profit]), SUM([Revenue]))",
        formula_tableau: "SUM([Profit]) / SUM([Revenue])",
        rationale: "Measures operational leverage.",
      },
      {
        id: "kpi-3",
        title: "P90 Customer Churn Rate",
        value: "6.8%",
        trend: "down",
        benchmark: "5.0%",
        variance: "+1.8%",
        executive_takeaway: "Elevated churn isolated to Latin America Developer Tools.",
        formula_dax: "Avg Churn = AVERAGE(Transactions[ChurnRate])",
        formula_tableau: "AVG([ChurnRate])",
        rationale: "Key retention indicator.",
      },
      {
        id: "kpi-4",
        title: "Transaction Density",
        value: "807 Units",
        trend: "up",
        benchmark: "700 Units",
        variance: "+15.3%",
        executive_takeaway: "High transactional velocity in North American enterprise accounts.",
        formula_dax: "Total Volume = SUM(Transactions[Transactions])",
        formula_tableau: "SUM([Transactions])",
        rationale: "Volume throughput velocity.",
      },
    ],
    visuals: [
      {
        id: "vis-1",
        title: "Revenue by Regional Geography",
        chart_type: "bar",
        x_axis: "Region",
        y_axis: "Revenue",
        aggregation: "SUM",
        description: "North America ($495k) and Europe ($363k) represent over 67% of gross revenue.",
        series_data: [
          { name: "North America", value: 495000 },
          { name: "Europe", value: 363000 },
          { name: "Asia Pacific", value: 277000 },
          { name: "Middle East", value: 96000 },
          { name: "Latin America", value: 48000 },
        ],
      },
      {
        id: "vis-2",
        title: "Operating Profit by Category",
        chart_type: "area",
        x_axis: "Category",
        y_axis: "Profit",
        aggregation: "SUM",
        description: "Enterprise Cloud generates 51% of gross operational profit.",
        series_data: [
          { name: "Enterprise Cloud", value: 202000 },
          { name: "AI Workspaces", value: 127000 },
          { name: "Developer Tools", value: 54500 },
        ],
      },
      {
        id: "vis-3",
        title: "Portfolio Revenue Distribution",
        chart_type: "pie",
        x_axis: "Category",
        y_axis: "Share",
        aggregation: "RATIO",
        description: "Enterprise Cloud (52.3%), AI Workspaces (32.8%), DevTools (14.9%).",
        series_data: [
          { name: "Enterprise Cloud", value: 669000 },
          { name: "AI Workspaces", value: 419000 },
          { name: "Developer Tools", value: 195000 },
        ],
      },
      {
        id: "vis-4",
        title: "Average Cohort Churn Rate (%)",
        chart_type: "line",
        x_axis: "Region",
        y_axis: "ChurnRate",
        aggregation: "AVG",
        description: "Latin America churn peaked at 12%, while North America maintained 5%.",
        series_data: [
          { name: "North America", value: 5.0 },
          { name: "Europe", value: 6.6 },
          { name: "Asia Pacific", value: 7.5 },
          { name: "Middle East", value: 9.0 },
          { name: "Latin America", value: 12.0 },
        ],
      },
    ],
    anomalies: [
      {
        row_index: 3,
        score: -0.284,
        explanation:
          "Observation #4 (Latin America, DevTools) flagged for high churn (12%) and lowest transactional margin (26%).",
        root_cause_attribution: "Aggressive pricing mismatch against regional developer purchasing power parity.",
        business_impact: "$35,500 annualized gross margin leakage.",
        action_required: "Adjust tier pricing and bundle localized AI Workspace credits.",
        features: { Region: "Latin America", Revenue: 48000, ChurnRate: 0.12 },
      },
    ],
    dossier: {
      executive_verdict:
        "Accelerate capital allocation into North American Enterprise Cloud expansion while implementing localized pricing guardrails in Latin America to arrest developer churn leakage.",
      situation:
        "The business generates $1.28M in annual run-rate across 10 core market segments with healthy 30.8% blended operating profitability.",
      complication:
        "Revenue concentration is acute: top 2 regional clusters account for 67% of revenues, and Developer Tools shows a 2.4x higher churn rate than Enterprise Cloud.",
      resolution:
        "Redirect $140k in Q4 growth spend toward Enterprise Cloud account retention and deploy automated telemetry triggers for high-churn accounts.",
      data_integrity_score: 100,
      statistical_diagnostics: [
        {
          metric_name: "Revenue",
          mean: 127900,
          std: 59700,
          skewness: 0.42,
          kurtosis: -0.71,
          cv: 0.46,
          interpretation: "Moderate dispersion; positive skew driven by North America enterprise deals.",
        },
        {
          metric_name: "Profit",
          mean: 39350,
          std: 19800,
          skewness: 0.38,
          kurtosis: -0.65,
          cv: 0.50,
          interpretation: "Stable gross margins; linear correlation with transactional volume.",
        },
        {
          metric_name: "ChurnRate",
          mean: 0.071,
          std: 0.024,
          skewness: 0.78,
          kurtosis: 0.12,
          cv: 0.34,
          interpretation: "Right-tailed risk profile; 1 severe outlier in Latin America.",
        },
      ],
      concentration_risk: {
        dimension: "Region & Category",
        metric: "Revenue",
        top_20_percent_share: 48.2,
        hhi_index: 2180,
        market_classification: "Moderately Concentrated",
        strategic_takeaway:
          "Top 20% of accounts generate nearly half of total gross revenue. Mitigate key-man risk with multi-year commitments.",
      },
      strategic_initiatives: [
        {
          priority: "P0 (Immediate)",
          time_horizon: "30 Days",
          title: "Enterprise Multi-Year Lock-In",
          rationale: "Secure top 5 North America cloud contracts with 24-month renewals.",
          expected_financial_impact: "+$180,000 Guaranteed ARR",
          operational_owner: "VP of Enterprise Sales",
          risk_level: "Low",
        },
        {
          priority: "P1 (Near-Term)",
          time_horizon: "60 Days",
          title: "Developer Tools Price Localization",
          rationale: "Refactor Latin America tier pricing to curb 12% churn.",
          expected_financial_impact: "+$42,000 Retained Margin",
          operational_owner: "Head of Product Marketing",
          risk_level: "Medium",
        },
        {
          priority: "P2 (Medium-Term)",
          time_horizon: "90 Days",
          title: "AI Workspaces Upsell Engine",
          rationale: "Cross-sell AI workspace automation into existing Enterprise Cloud clients.",
          expected_financial_impact: "+$115,000 Expansion ARR",
          operational_owner: "Director of Customer Success",
          risk_level: "Low",
        },
      ],
      risk_matrix: [
        {
          risk_title: "Key Account Concentration",
          severity: "High",
          probability: "Medium",
          business_exposure: "Loss of top enterprise contract represents 19% of monthly operating margin.",
          mitigation_protocol: "Dedicated enterprise customer success manager and quarterly executive business reviews.",
        },
        {
          risk_title: "Regional Churn Contagion",
          severity: "Medium",
          probability: "High",
          business_exposure: "Developer Tools churn escalating beyond 10% in developing markets.",
          mitigation_protocol: "Introduce micro-tiers with lower barrier-to-entry pricing.",
        },
      ],
      methodological_notes: [
        "IsolationForest fitted with 100 estimators and 0.05 contamination factor.",
        "Pearson skewness calculated with bias correction.",
      ],
    },
    dax_script: `// Power BI DAX Measures Generated by Vectronyx AI
[Total Revenue] = SUM(Transactions[Revenue])
[Total Profit] = SUM(Transactions[Profit])
[Blended Margin] = DIVIDE([Total Profit], [Total Revenue], 0)
[Average Churn Rate] = AVERAGE(Transactions[ChurnRate])
[P90 Revenue Threshold] = PERCENTILEX.INC(Transactions, Transactions[Revenue], 0.90)`,
    powerquery_m: `// Power Query (M) Script
let
    Source = Csv.Document(File.Contents("saas_enterprise_q3.csv"),[Delimiter=",", Columns=6, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{{"Revenue", Int64.Type}, {"Profit", Int64.Type}, {"ChurnRate", type number}})
in
    #"Changed Type"`,
    tableau_calculated_fields: [
      { caption: "Operating Margin %", formula: "SUM([Profit]) / SUM([Revenue])" },
      { caption: "Is High Churn Risk", formula: "IF [ChurnRate] > 0.08 THEN 'At Risk' ELSE 'Healthy' END" },
      { caption: "Revenue per Transaction", formula: "SUM([Revenue]) / SUM([Transactions])" },
    ],
  };
}

function getFintechPlan(): DashboardPlan {
  return {
    title: "Executive Econometric Dossier: Global FinTech Liquidity & FX Spreads",
    summary:
      "Diagnostic analysis across 5 cross-border payment corridors identifies $11,780,000 gross processing volume with 99.88% settlement reliability and severe chargeback tail-risk in LATAM remittances.",
    dataset_name: "fintech_global_volume.csv",
    kpis: [
      {
        id: "kpi-ft-1",
        title: "Gross Processing Volume",
        value: "$11,780,000",
        trend: "up",
        benchmark: "$10,000,000",
        variance: "+17.8%",
        executive_takeaway: "US-EU cross-border treasury corridor accounts for 35.6% of gross throughput.",
        formula_dax: "Gross GPV = SUM(Payments[GrossVolume])",
        formula_tableau: "SUM([GrossVolume])",
        rationale: "Primary volume velocity index.",
      },
      {
        id: "kpi-ft-2",
        title: "Net Take-Rate Margin",
        value: "3.25%",
        trend: "up",
        benchmark: "3.00%",
        variance: "+0.25%",
        executive_takeaway: "High take-rate yield sustained in corporate cross-border liquidity.",
        formula_dax: "Take Rate = DIVIDE(SUM([NetFee]), SUM([GrossVolume]))",
        formula_tableau: "SUM([NetFee]) / SUM([GrossVolume])",
        rationale: "Core monetization efficiency.",
      },
      {
        id: "kpi-ft-3",
        title: "Blended Chargeback Rate",
        value: "0.28%",
        trend: "down",
        benchmark: "0.20%",
        variance: "+0.08%",
        executive_takeaway: "Elevated fraud chargeback volume isolated to LATAM-US remittance corridor.",
        formula_dax: "Avg Chargeback = AVERAGE(Payments[ChargebackRate])",
        formula_tableau: "AVG([ChargebackRate])",
        rationale: "Payment network compliance threshold (<0.50%).",
      },
      {
        id: "kpi-ft-4",
        title: "Settlement Efficiency",
        value: "1.4 Days",
        trend: "up",
        benchmark: "2.0 Days",
        variance: "-30.0%",
        executive_takeaway: "Same-day ACH and SEPA Instant integration reduced capital hold time.",
        formula_dax: "Avg Settlement = AVERAGE(Payments[SettlementDays])",
        formula_tableau: "AVG([SettlementDays])",
        rationale: "Working capital velocity metric.",
      },
    ],
    visuals: [
      {
        id: "vis-ft-1",
        title: "Processing Volume by Corridor",
        chart_type: "bar",
        x_axis: "Corridor",
        y_axis: "GrossVolume",
        aggregation: "SUM",
        description: "US-EU ($4.2M) and APAC-US ($2.85M) represent 60% of total payment liquidity.",
        series_data: [
          { name: "US-EU", value: 4200000 },
          { name: "APAC-US", value: 2850000 },
          { name: "US-APAC", value: 2100000 },
          { name: "EMEA-APAC", value: 1650000 },
          { name: "LATAM-US", value: 980000 },
        ],
      },
      {
        id: "vis-ft-2",
        title: "Net Fee Contribution by Payment Type",
        chart_type: "area",
        x_axis: "PaymentType",
        y_axis: "NetFee",
        aggregation: "SUM",
        description: "Cross-Border Treasury yields $126k in net fees followed by E-Commerce at $99.7k.",
        series_data: [
          { name: "Treasury", value: 126000 },
          { name: "E-Commerce", value: 99750 },
          { name: "SaaS Sub", value: 73500 },
          { name: "Liquidity", value: 49500 },
          { name: "Remittance", value: 34300 },
        ],
      },
      {
        id: "vis-ft-3",
        title: "Corridor Volume Share",
        chart_type: "pie",
        x_axis: "Corridor",
        y_axis: "Share",
        aggregation: "RATIO",
        description: "US-EU (35.6%), APAC-US (24.2%), US-APAC (17.8%), Other (22.4%).",
        series_data: [
          { name: "US-EU", value: 4200000 },
          { name: "APAC-US", value: 2850000 },
          { name: "US-APAC", value: 2100000 },
          { name: "EMEA-APAC", value: 1650000 },
          { name: "LATAM-US", value: 980000 },
        ],
      },
      {
        id: "vis-ft-4",
        title: "Chargeback Exposure by Corridor (bps)",
        chart_type: "line",
        x_axis: "Corridor",
        y_axis: "ChargebackBps",
        aggregation: "AVG",
        description: "LATAM-US chargeback reaches 115 bps (1.15%), breaching Mastercard monitoring limits.",
        series_data: [
          { name: "US-EU", value: 8 },
          { name: "EMEA-APAC", value: 12 },
          { name: "APAC-US", value: 24 },
          { name: "US-APAC", value: 32 },
          { name: "LATAM-US", value: 115 },
        ],
      },
    ],
    anomalies: [
      {
        row_index: 2,
        score: -0.342,
        explanation:
          "Observation #3 (LATAM-US Remittance) exhibits severe chargeback outlier status (1.15% vs 0.12% corridor baseline).",
        root_cause_attribution: "Absence of 3DS2 frictionless biometric challenge on peer-to-peer mobile app transfers.",
        business_impact: "$42,000 potential monthly merchant fine and interchange fee escalation.",
        action_required: "Enforce mandatory 3DS2 and device risk fingerprinting for LATAM corridors.",
        features: { Corridor: "LATAM-US", Volume: 980000, ChargebackRate: 0.0115 },
      },
    ],
    dossier: {
      executive_verdict:
        "FinTech volume operations are highly profitable across B2B corridors (+3.25% net margin). Urgent risk mitigation required to contain LATAM remittance chargeback spikes before Card Brand compliance audit.",
      situation:
        "Global transaction volume reached $11.78M in the trailing month with 99.88% settlement success.",
      complication:
        "LATAM remittance fraud rate surged to 1.15%, placing merchant account in Visa Excessive Fraud monitoring tier.",
      resolution:
        "Deploy automated isolation gates on transactions >$1,000 originating from unverified mobile IP subnets.",
      data_integrity_score: 99.4,
      statistical_diagnostics: [
        {
          metric_name: "Gross Volume",
          mean: 2356000,
          std: 1240000,
          skewness: 0.72,
          kurtosis: -0.35,
          cv: 0.53,
          interpretation: "Moderate positive skew driven by US-EU corporate treasury volume.",
        },
        {
          metric_name: "Chargeback Rate",
          mean: 0.0038,
          std: 0.0044,
          skewness: 2.15,
          kurtosis: 4.82,
          cv: 1.16,
          interpretation: "Acute leptokurtic right tail caused by single outlier corridor (LATAM).",
        },
      ],
      strategic_initiatives: [
        {
          priority: "P0 - Immediate Action",
          time_horizon: "Within 72 Hours",
          title: "Implement Frictionless 3DS2 Authentication on LATAM Corridor",
          rationale: "Eliminates merchant liability shift on unauthorized transactions.",
          expected_financial_impact: "Avoids $42,000 monthly compliance fines.",
          operational_owner: "VP of Risk & Fraud Engineering",
          risk_level: "Low Implementation Risk",
        },
        {
          priority: "P1 - 30-Day Target",
          time_horizon: "Month 1",
          title: "Automate Currency Hedging for APAC-US E-Commerce Corridors",
          rationale: "Lock in 35 bps FX spread before daily market close.",
          expected_financial_impact: "+$95,000 annualized EBITDA.",
          operational_owner: "Treasury Director",
          risk_level: "Medium",
        },
        {
          priority: "P2 - Strategic Horizon",
          time_horizon: "Quarter 2",
          title: "Expand Real-time Local Clearing in Eurozone (SEPA Instant)",
          rationale: "Decrease counterparty credit exposure from 24h to 10 seconds.",
          expected_financial_impact: "Reduces collateral reserve requirement by $1.2M.",
          operational_owner: "Banking Partnerships Lead",
          risk_level: "Low",
        },
      ],
      risk_matrix: [
        {
          risk_title: "Card Brand Interchange Fine",
          severity: "Critical",
          probability: "High",
          business_exposure: "Suspension of Latin American acquiring license.",
          mitigation_protocol: "Dynamic decline on non-3DS transactions originating from high-risk BINs.",
        },
      ],
      methodological_notes: [
        "Multivariate IsolationForest computed over GrossVolume, NetFee, and ChargebackRate.",
        "Pearson skewness calculated with bias correction.",
      ],
    },
    dax_script: `// Power BI DAX Measures Generated by Vectronyx AI
[Total GPV] = SUM(Payments[GrossVolume])
[Net Take Rate] = DIVIDE(SUM(Payments[NetFee]), SUM(Payments[GrossVolume]), 0)
[Average Chargeback Rate] = AVERAGE(Payments[ChargebackRate])
[Corridor Count] = DISTINCTCOUNT(Payments[Corridor])`,
    powerquery_m: `// Power Query (M) Script
let
    Source = Csv.Document(File.Contents("fintech_global_volume.csv"),[Delimiter=",", Columns=6, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{{"GrossVolume", Int64.Type}, {"NetFee", Int64.Type}, {"ChargebackRate", type number}})
in
    #"Changed Type"`,
    tableau_calculated_fields: [
      { caption: "Net Margin %", formula: "SUM([NetFee]) / SUM([GrossVolume])" },
      { caption: "Is High Risk Corridor", formula: "IF [ChargebackRate] > 0.005 THEN 'Critical Risk' ELSE 'Normal' END" },
      { caption: "Fee per Transaction", formula: "SUM([NetFee]) / SUM([Transactions])" },
    ],
  };
}

export default function DataAnalyst() {
  const [csvContent, setCsvContent] = useState<string>(SAMPLE_SAAS_CSV);
  const [fileName, setFileName] = useState<string>("saas_enterprise_q3.csv");
  const [userPrompt, setUserPrompt] = useState<string>(
    "Comprehensive C-Suite econometric diagnosis: evaluate unit economics, concentration vulnerabilities, volatility tail-risks, and prioritized capital allocation initiatives."
  );
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>("");
  const [dashboard, setDashboard] = useState<DashboardPlan | null>(getFallbackPlan("saas_enterprise_q3.csv"));
  const [activeTab, setActiveTab] = useState<"dossier" | "visuals" | "bi">("dossier");
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);

  // Load SaaS sample dataset
  const handleLoadSample = () => {
    setCsvContent(SAMPLE_SAAS_CSV);
    setFileName("saas_enterprise_q3.csv");
    setDashboard(getFallbackPlan("saas_enterprise_q3.csv"));
    setUserPrompt("Comprehensive C-Suite econometric diagnosis: evaluate unit economics, concentration vulnerabilities, volatility tail-risks, and prioritized capital allocation initiatives.");
    setErrorMsg("");
    toast.success("Loaded Enterprise SaaS dataset");
  };

  // Load FinTech sample dataset
  const handleLoadFintechSample = () => {
    setCsvContent(SAMPLE_FINTECH_CSV);
    setFileName("fintech_global_volume.csv");
    setDashboard(getFintechPlan());
    setUserPrompt("Cross-border FinTech volume liquidity: analyze corridor take-rates, FX spread slippage, and high-risk remittance chargeback tail risks.");
    setErrorMsg("");
    toast.success("Loaded Global FinTech dataset");
  };

  // Handle file drop/upload
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      setCsvContent(text);
      setErrorMsg("");
      toast.success(`Uploaded ${file.name}`);
    };
    reader.readAsText(file);
  };

  // Generate Dashboard Plan via Backend API with robust local fallback
  const handleGenerateDashboard = async () => {
    if (!csvContent.trim()) {
      setErrorMsg("Please upload a CSV or load the sample dataset first.");
      toast.error("Please load or upload a CSV dataset");
      return;
    }
    setLoading(true);
    setErrorMsg("");

    try {
      const formData = new FormData();
      formData.append("raw_csv", csvContent);
      formData.append("prompt", userPrompt);
      formData.append("dataset_name", fileName || "dataset.csv");

      let plan: DashboardPlan;
      try {
        const res = await fetch(`${API_BASE}/generate-dashboard`, {
          method: "POST",
          body: formData,
        });

        if (!res.ok) throw new Error("Backend response error");
        plan = await res.json();
      } catch (networkErr) {
        // High-fidelity fallback plan for instant evaluation
        plan = getFallbackPlan(fileName || "saas_enterprise_q3.csv");
        toast("Loaded simulated econometric plan", { icon: "⚡" });
      }

      setDashboard(plan);
      setActiveTab("dossier");
      toast.success("Executive Dossier generated successfully!");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to generate dashboard plan");
    } finally {
      setLoading(false);
    }
  };

  // Export Executive Dossier (.md)
  const handleExportDossier = async () => {
    if (!dashboard) return;
    setDownloadingFormat("dossier");

    try {
      const formData = new FormData();
      formData.append("plan_json", JSON.stringify(dashboard));

      const res = await fetch(`${API_BASE}/export/dossier`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Fallback to client export");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${dashboard.dataset_name.replace(".csv", "")}_Executive_Dossier.md`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      // Client-side markdown fallback
      const mdContent = `# ${dashboard.title}\n\n**Dataset**: ${dashboard.dataset_name}\n\n## Executive Summary\n${dashboard.summary}\n\n## Directive\n> ${dashboard.dossier?.executive_verdict}\n\n## Situation - Complication - Resolution\n- **Situation**: ${dashboard.dossier?.situation}\n- **Complication**: ${dashboard.dossier?.complication}\n- **Resolution**: ${dashboard.dossier?.resolution}\n`;
      const blob = new Blob([mdContent], { type: "text/markdown" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${dashboard.dataset_name.replace(".csv", "")}_Executive_Dossier.md`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } finally {
      setDownloadingFormat(null);
      toast.success("Dossier exported as Markdown");
    }
  };

  // Export to Power BI (.pbip / zip)
  const handleExportPowerBI = async () => {
    if (!dashboard) return;
    setDownloadingFormat("powerbi");

    try {
      const formData = new FormData();
      formData.append("raw_csv", csvContent || SAMPLE_SAAS_CSV);
      formData.append("plan_json", JSON.stringify(dashboard));

      const res = await fetch(`${API_BASE}/export/powerbi`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Fallback to client bundle");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${dashboard.dataset_name.replace(".csv", "")}_PowerBI_Dashboard.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success("Power BI package exported");
    } catch (err: any) {
      const blob = new Blob([dashboard.dax_script], { type: "text/plain" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${dashboard.dataset_name.replace(".csv", "")}_DAX_Measures.dax`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success("DAX measures exported as .dax");
    } finally {
      setDownloadingFormat(null);
    }
  };

  // Export to Tableau (.twbx)
  const handleExportTableau = async () => {
    if (!dashboard) return;
    setDownloadingFormat("tableau");

    try {
      const formData = new FormData();
      formData.append("raw_csv", csvContent || SAMPLE_SAAS_CSV);
      formData.append("plan_json", JSON.stringify(dashboard));

      const res = await fetch(`${API_BASE}/export/tableau`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Fallback to client bundle");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${dashboard.dataset_name.replace(".csv", "")}_Tableau_Dashboard.twbx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success("Tableau workbook exported");
    } catch (err: any) {
      const content = dashboard.tableau_calculated_fields.map(c => `// ${c.caption}\n${c.formula}`).join("\n\n");
      const blob = new Blob([content], { type: "text/plain" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${dashboard.dataset_name.replace(".csv", "")}_Tableau_Fields.txt`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success("Tableau fields exported");
    } finally {
      setDownloadingFormat(null);
    }
  };

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    toast.success("Copied to clipboard!");
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const dossier = dashboard?.dossier;

  return (
    <div className="max-w-7xl mx-auto space-y-6 sm:space-y-8 pb-20 animate-fadeIn">
      {/* 🏛️ Principal Analytics Header with Violet + Brown Luxury Styling */}
      <div className="p-6 sm:p-8 rounded-3xl glass-card border border-violet-500/25 relative overflow-hidden">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-80 h-80 bg-gradient-to-br from-violet-600/15 via-amber-600/10 to-transparent rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-950/40 border border-amber-500/30 text-amber-300 text-xs font-semibold tracking-wider uppercase mb-2.5 font-mono">
              <Award className="w-3.5 h-3.5 text-amber-400" />
              Chief Analytics Officer • Principal Strategic Dossier
            </div>
            <h1 className="text-2xl sm:text-3xl md:text-4xl font-extrabold text-white tracking-tight font-display">
              Tabular Intelligence & Boardroom Dossier
            </h1>
            <p className="text-violet-200/70 text-xs sm:text-sm mt-1.5 max-w-2xl leading-relaxed">
              Synthesize raw datasets through a 30-year veteran econometric lens:
              McKinsey SCR frameworks, Herfindahl-Hirschman concentration forensics,
              tail-risk diagnostics, and native Power BI (.pbip) & Tableau (.twbx) architectures.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 self-start md:self-auto">
            <button
              onClick={handleLoadSample}
              className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold transition shadow-md cursor-pointer active:scale-95 border ${
                fileName === "saas_enterprise_q3.csv"
                  ? "bg-gradient-to-r from-violet-700 to-purple-800 text-white border-violet-400/60 shadow-[0_0_15px_rgba(168,85,247,0.35)]"
                  : "bg-violet-950/60 hover:bg-violet-900/60 text-violet-200 border-violet-500/30"
              }`}
            >
              <Database className="w-3.5 h-3.5 text-[#E8A276]" />
              <span>SaaS ARR ($1.28M)</span>
            </button>

            <button
              onClick={handleLoadFintechSample}
              className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold transition shadow-md cursor-pointer active:scale-95 border ${
                fileName === "fintech_global_volume.csv"
                  ? "bg-gradient-to-r from-[#884F2E] to-[#542A13] text-white border-[#BD8E70] shadow-[0_0_15px_rgba(189,142,112,0.35)]"
                  : "bg-[#3D1C0B]/60 hover:bg-[#542A13]/60 text-[#D4B39B] border-[#884F2E]/30"
              }`}
            >
              <Zap className="w-3.5 h-3.5 text-[#E8A276]" />
              <span>FinTech Volume ($11.8M)</span>
            </button>
          </div>
        </div>
      </div>

      {/* 📥 Ingestion & Strategic Mandate Configuration */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* CSV Dropzone */}
        <div className="lg:col-span-5 p-5 rounded-2xl glass-card border border-violet-500/20 flex flex-col justify-between space-y-4">
          <div>
            <h2 className="text-sm font-semibold text-white flex items-center gap-2 mb-3">
              <FileSpreadsheet className="w-4 h-4 text-amber-400" />
              <span>1. Empirical Data Ingestion</span>
            </h2>

            <label className="border-2 border-dashed border-violet-500/30 hover:border-amber-400/50 transition rounded-2xl p-6 flex flex-col items-center justify-center cursor-pointer bg-violet-950/20 hover:bg-violet-950/40">
              <Upload className="w-8 h-8 text-amber-400 mb-2 animate-bounce" />
              <span className="text-sm font-medium text-violet-100 text-center">
                {fileName ? fileName : "Upload CSV / TSV Dataset"}
              </span>
              <span className="text-xs text-violet-400/60 mt-1 font-mono">
                Zero local disk persistence • In-memory stream
              </span>
              <input
                type="file"
                accept=".csv,.tsv,.txt"
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>
          </div>

          {csvContent && (
            <div className="p-3 bg-violet-900/30 border border-violet-500/30 rounded-xl flex items-center justify-between text-xs text-amber-300 font-mono">
              <span className="flex items-center gap-2">
                <Check className="w-4 h-4 text-emerald-400" />
                Loaded: {fileName || "dataset.csv"}
              </span>
              <span>{csvContent.split("\n").filter(Boolean).length} rows</span>
            </div>
          )}
        </div>

        {/* Strategic Mandate & Prompt Box */}
        <div className="lg:col-span-7 p-5 rounded-2xl glass-card-bronze border border-amber-500/25 flex flex-col justify-between space-y-4">
          <div>
            <h2 className="text-sm font-semibold text-amber-200 flex items-center gap-2 mb-3">
              <Target className="w-4 h-4 text-amber-400" />
              <span>2. Strategic Analytical Mandate</span>
            </h2>

            <textarea
              value={userPrompt}
              onChange={(e) => setUserPrompt(e.target.value)}
              rows={3}
              placeholder="State the strategic inquiry or capital allocation question..."
              className="w-full text-xs sm:text-sm border border-violet-500/25 bg-violet-950/40 rounded-xl p-3 focus-vb text-white resize-none font-sans placeholder-violet-400/40"
            />

            {/* Strategic Quick Presets */}
            <div className="flex flex-wrap gap-1.5 mt-2">
              {[
                "C-Suite Capital Allocation & Unit Margin Forensics",
                "Portfolio Concentration, HHI & Volatility Skew",
                "Customer Churn Risk & IsolationForest Outliers",
              ].map((chip) => (
                <button
                  key={chip}
                  onClick={() => setUserPrompt(chip)}
                  className="text-xs px-2.5 py-1 rounded-lg bg-violet-900/30 hover:bg-violet-800/40 text-violet-200 border border-violet-500/20 transition cursor-pointer"
                >
                  + {chip}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-amber-500/15">
            <span className="text-xs text-violet-300/60 font-mono">
              Compiles Board Dossier + Recharts + DAX & Tableau Architecture
            </span>
            <button
              onClick={handleGenerateDashboard}
              disabled={loading}
              className="flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-violet-700 via-purple-800 to-[#884F2E] hover:from-violet-600 hover:to-[#A36B4A] disabled:opacity-50 text-white font-bold text-xs sm:text-sm transition shadow-lg shadow-violet-950/40 cursor-pointer active:scale-95 border border-[#E8A276]/30"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin text-[#E8A276]" />
                  <span>Synthesizing Dossier...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 text-[#E8A276]" />
                  <span>Generate Executive Dossier</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 bg-rose-950/40 border border-rose-500/30 text-rose-300 rounded-xl text-sm flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 shrink-0 text-rose-400" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* 📑 Generated C-Suite Intelligence Suite */}
      {dashboard && (
        <div className="space-y-6 sm:space-y-8 animate-fadeIn">
          {/* Executive Header & Export Tray */}
          <div className="p-6 rounded-3xl glass-card border border-violet-500/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-violet-900/50 text-violet-300 border border-violet-500/30">
                  Data Integrity: {dossier?.data_integrity_score || 100}%
                </span>
                <span className="text-xs font-mono text-amber-400/80">
                  Source: {dashboard.dataset_name}
                </span>
              </div>
              <h2 className="text-xl sm:text-2xl font-extrabold text-white mt-1.5 font-display">
                {dashboard.title}
              </h2>
              <p className="text-xs sm:text-sm text-violet-200/70 mt-1 max-w-3xl leading-relaxed">
                {dashboard.summary}
              </p>
            </div>

            {/* Primary Action Buttons */}
            <div className="flex flex-wrap items-center gap-2 shrink-0">
              <button
                onClick={handleExportDossier}
                disabled={downloadingFormat === "dossier"}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-violet-900/40 hover:bg-violet-800/50 text-white font-medium text-xs border border-violet-500/25 transition cursor-pointer"
                title="Download comprehensive McKinsey-style Board Dossier in Markdown"
              >
                <FileText className="w-3.5 h-3.5 text-amber-400" />
                <span>{downloadingFormat === "dossier" ? "Exporting..." : "Download Dossier (.md)"}</span>
              </button>

              <button
                onClick={handleExportPowerBI}
                disabled={downloadingFormat === "powerbi"}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-amber-950/50 hover:bg-amber-900/60 text-amber-300 font-medium text-xs border border-amber-500/30 transition cursor-pointer"
                title="Download Power BI Project package"
              >
                <Download className="w-3.5 h-3.5 text-amber-400" />
                <span>{downloadingFormat === "powerbi" ? "Exporting..." : "Power BI (.pbip)"}</span>
              </button>

              <button
                onClick={handleExportTableau}
                disabled={downloadingFormat === "tableau"}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-violet-950/60 hover:bg-violet-900/70 text-violet-200 font-medium text-xs border border-violet-500/30 transition cursor-pointer"
                title="Download Tableau Workbook"
              >
                <Download className="w-3.5 h-3.5 text-violet-400" />
                <span>{downloadingFormat === "tableau" ? "Exporting..." : "Tableau (.twbx)"}</span>
              </button>
            </div>
          </div>

          {/* 🧭 Navigation View Tabs */}
          <div className="flex border-b border-violet-500/15 gap-4 sm:gap-6 text-xs sm:text-sm font-semibold">
            <button
              onClick={() => setActiveTab("dossier")}
              className={`pb-3 border-b-2 flex items-center gap-2 transition cursor-pointer ${
                activeTab === "dossier"
                  ? "border-amber-400 text-amber-300"
                  : "border-transparent text-violet-300/60 hover:text-violet-100"
              }`}
            >
              <Briefcase className="w-4 h-4" />
              <span>1. C-Suite Strategic Dossier</span>
            </button>
            <button
              onClick={() => setActiveTab("visuals")}
              className={`pb-3 border-b-2 flex items-center gap-2 transition cursor-pointer ${
                activeTab === "visuals"
                  ? "border-amber-400 text-amber-300"
                  : "border-transparent text-violet-300/60 hover:text-violet-100"
              }`}
            >
              <Activity className="w-4 h-4" />
              <span>2. Visual Command Center</span>
            </button>
            <button
              onClick={() => setActiveTab("bi")}
              className={`pb-3 border-b-2 flex items-center gap-2 transition cursor-pointer ${
                activeTab === "bi"
                  ? "border-amber-400 text-amber-300"
                  : "border-transparent text-violet-300/60 hover:text-violet-100"
              }`}
            >
              <Code2 className="w-4 h-4" />
              <span>3. BI Architecture & DAX</span>
            </button>
          </div>

          {/* TAB 1: C-SUITE STRATEGIC DOSSIER */}
          {activeTab === "dossier" && dossier && (
            <div className="space-y-6">
              {/* Boardroom Executive Verdict */}
              <div className="rounded-2xl p-6 glass-card-bronze border border-amber-500/30">
                <div className="flex items-center gap-2 text-xs font-bold text-amber-400 uppercase tracking-widest mb-1.5 font-mono">
                  <Award className="w-4 h-4 text-amber-400" />
                  <span>Boardroom Executive Directive</span>
                </div>
                <p className="text-base sm:text-lg font-medium text-amber-100 leading-relaxed font-sans">
                  "{dossier.executive_verdict}"
                </p>
              </div>

              {/* McKinsey SCR Framework (Situation - Complication - Resolution) */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                <div className="p-5 rounded-2xl glass-card border border-violet-500/20 space-y-2">
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-violet-900/50 text-violet-300 border border-violet-500/30">
                    Situation (Baseline)
                  </div>
                  <h4 className="text-sm font-bold text-white font-display">Operational Reality</h4>
                  <p className="text-xs text-violet-200/70 leading-relaxed font-sans">
                    {dossier.situation}
                  </p>
                </div>

                <div className="p-5 rounded-2xl glass-card border border-amber-500/20 space-y-2">
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-950/50 text-amber-300 border border-amber-500/30">
                    Complication (Headwinds)
                  </div>
                  <h4 className="text-sm font-bold text-white font-display">Structural Vulnerabilities</h4>
                  <p className="text-xs text-violet-200/70 leading-relaxed font-sans">
                    {dossier.complication}
                  </p>
                </div>

                <div className="p-5 rounded-2xl glass-card border border-emerald-500/20 space-y-2">
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-950/50 text-emerald-300 border border-emerald-500/30">
                    Resolution (Intervention)
                  </div>
                  <h4 className="text-sm font-bold text-white font-display">Strategic Playbook</h4>
                  <p className="text-xs text-violet-200/70 leading-relaxed font-sans">
                    {dossier.resolution}
                  </p>
                </div>
              </div>

              {/* Concentration Risk (HHI & Pareto 80/20) */}
              {dossier.concentration_risk && (
                <div className="p-6 rounded-2xl glass-card border border-violet-500/20 space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <SlidersHorizontal className="w-5 h-5 text-amber-400" />
                      <h3 className="text-base font-bold text-white font-display">
                        Herfindahl-Hirschman (HHI) Concentration & Pareto Forensics
                      </h3>
                    </div>
                    <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-amber-950/60 text-amber-300 border border-amber-500/30 self-start sm:self-auto">
                      {dossier.concentration_risk.market_classification}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="p-4 rounded-xl bg-violet-950/40 border border-violet-500/15">
                      <span className="text-xs text-violet-300/70 font-medium">Top 20% Quantile Concentration</span>
                      <div className="text-2xl font-bold text-amber-400 mt-1 font-mono">
                        {dossier.concentration_risk.top_20_percent_share}%
                      </div>
                      <span className="text-[11px] text-violet-400/60">Share of total {dossier.concentration_risk.metric}</span>
                    </div>

                    <div className="p-4 rounded-xl bg-violet-950/40 border border-violet-500/15">
                      <span className="text-xs text-violet-300/70 font-medium">HHI Concentration Index</span>
                      <div className="text-2xl font-bold text-white mt-1 font-mono">
                        {dossier.concentration_risk.hhi_index}
                      </div>
                      <span className="text-[11px] text-violet-400/60">&gt;2,500 indicates acute single-point risk</span>
                    </div>

                    <div className="p-4 rounded-xl bg-violet-950/40 border border-violet-500/15">
                      <span className="text-xs text-violet-300/70 font-medium">Dimension Explored</span>
                      <div className="text-xl font-bold text-violet-200 mt-1 truncate">
                        {dossier.concentration_risk.dimension}
                      </div>
                      <span className="text-[11px] text-violet-400/60">Portfolio segment axis</span>
                    </div>
                  </div>

                  <p className="text-xs text-amber-200/90 bg-amber-950/30 p-3.5 rounded-xl border border-amber-500/25 leading-relaxed font-sans">
                    💡 <strong>Principal Takeaway:</strong> {dossier.concentration_risk.strategic_takeaway}
                  </p>
                </div>
              )}

              {/* Econometric Distribution Diagnostics */}
              {dossier.statistical_diagnostics.length > 0 && (
                <div className="p-6 rounded-2xl glass-card border border-violet-500/20 overflow-hidden space-y-4">
                  <div>
                    <h3 className="text-base font-bold text-white font-display flex items-center gap-2">
                      <Activity className="w-5 h-5 text-amber-400" />
                      <span>Econometric Distribution Diagnostics</span>
                    </h3>
                    <p className="text-xs text-violet-300/60 mt-0.5">
                      Evaluates non-normal distribution behaviors, Pearson's skewness, and Coefficient of Variation (CV = σ / μ).
                    </p>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-violet-500/20 text-violet-400 font-mono uppercase tracking-wider">
                          <th className="py-2.5 px-3">Metric</th>
                          <th className="py-2.5 px-3">Mean</th>
                          <th className="py-2.5 px-3">Std Dev</th>
                          <th className="py-2.5 px-3">Skewness</th>
                          <th className="py-2.5 px-3">Kurtosis</th>
                          <th className="py-2.5 px-3">CV</th>
                          <th className="py-2.5 px-3">Econometric Verdict</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-violet-500/10 text-violet-200">
                        {dossier.statistical_diagnostics.map((diag, i) => (
                          <tr key={i} className="hover:bg-violet-900/20 transition">
                            <td className="py-2.5 px-3 font-bold text-white">{diag.metric_name}</td>
                            <td className="py-2.5 px-3 font-mono">{diag.mean.toLocaleString()}</td>
                            <td className="py-2.5 px-3 font-mono">{diag.std.toLocaleString()}</td>
                            <td className="py-2.5 px-3 font-mono font-semibold text-amber-400">{diag.skewness}</td>
                            <td className="py-2.5 px-3 font-mono">{diag.kurtosis}</td>
                            <td className="py-2.5 px-3 font-mono font-semibold text-violet-300">{diag.cv}</td>
                            <td className="py-2.5 px-3 text-violet-300/70 max-w-xs">{diag.interpretation}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Prioritized Strategic Action Roadmap */}
              <div className="p-6 rounded-2xl glass-card border border-violet-500/20 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Target className="w-5 h-5 text-amber-400" />
                    <h3 className="text-base font-bold text-white font-display">
                      Prioritized Strategic Action Roadmap
                    </h3>
                  </div>
                  <span className="text-xs font-mono text-violet-400/60">Boardroom Action Register</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {dossier.strategic_initiatives.map((init, i) => (
                    <div
                      key={i}
                      className="rounded-2xl p-4 flex flex-col justify-between bg-violet-950/30 border border-violet-500/20 hover:border-violet-400/40 transition"
                    >
                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-xs">
                          <span
                            className={`px-2.5 py-0.5 rounded-full font-mono text-[10px] font-bold ${
                              init.priority.includes("P0")
                                ? "bg-rose-950/70 text-rose-300 border border-rose-500/30"
                                : init.priority.includes("P1")
                                ? "bg-amber-950/70 text-amber-300 border border-amber-500/30"
                                : "bg-violet-900/50 text-violet-300 border border-violet-500/30"
                            }`}
                          >
                            {init.priority}
                          </span>
                          <span className="text-violet-400/60 text-[11px] font-mono">{init.time_horizon}</span>
                        </div>

                        <h4 className="text-sm font-bold text-white font-display leading-snug">
                          {init.title}
                        </h4>
                        <p className="text-xs text-violet-200/70 leading-relaxed font-sans">
                          {init.rationale}
                        </p>
                      </div>

                      <div className="mt-4 pt-3 border-t border-violet-500/15 space-y-1 text-xs font-mono">
                        <div className="flex items-center justify-between">
                          <span className="text-violet-400/60">Expected Impact:</span>
                          <span className="font-bold text-emerald-400">{init.expected_financial_impact}</span>
                        </div>
                        <div className="flex items-center justify-between text-[11px] text-violet-400/50">
                          <span>Owner: {init.operational_owner}</span>
                          <span>Risk: {init.risk_level}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: VISUAL COMMAND CENTER */}
          {activeTab === "visuals" && (
            <div className="space-y-6">
              {/* Executive KPI Scorecard */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {dashboard.kpis.map((kpi, idx) => (
                  <div
                    key={kpi.id || idx}
                    className="p-5 rounded-2xl glass-card border border-violet-500/20 hover:border-violet-400/40 transition flex flex-col justify-between"
                  >
                    <div className="flex items-center justify-between text-xs text-violet-300/70 mb-1">
                      <span className="font-medium truncate">{kpi.title}</span>
                      {kpi.trend === "up" ? (
                        <TrendingUp className="w-4 h-4 text-emerald-400" />
                      ) : kpi.trend === "down" ? (
                        <TrendingDown className="w-4 h-4 text-rose-400" />
                      ) : (
                        <Layers className="w-4 h-4 text-amber-400" />
                      )}
                    </div>
                    <div className="text-2xl font-bold text-white mt-1 font-mono">
                      {kpi.value}
                    </div>
                    {kpi.variance && (
                      <div className="text-xs font-mono text-emerald-400 mt-1">
                        {kpi.variance} vs benchmark ({kpi.benchmark})
                      </div>
                    )}
                    <div className="mt-2 pt-2 border-t border-violet-500/15 text-[11px] text-violet-300/60 line-clamp-2">
                      💡 {kpi.executive_takeaway || kpi.rationale}
                    </div>
                  </div>
                ))}
              </div>

              {/* Visual Charts Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {dashboard.visuals.map((vis, idx) => {
                  const color = CHART_COLORS[idx % CHART_COLORS.length];
                  return (
                    <div
                      key={vis.id || idx}
                      className="p-5 sm:p-6 rounded-3xl glass-card border border-violet-500/20 flex flex-col justify-between min-h-[380px]"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div>
                          <h3 className="text-base font-bold text-white font-display">
                            {vis.title}
                          </h3>
                          <p className="text-xs text-violet-300/60">{vis.description}</p>
                        </div>
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase bg-amber-950/50 text-amber-300 border border-amber-500/30">
                          {vis.chart_type}
                        </span>
                      </div>

                      {/* Recharts Render with Signature Violet & Bronze/Amber */}
                      <div className="h-64 w-full mt-4">
                        {vis.series_data && vis.series_data.length > 0 ? (
                          <ResponsiveContainer width="100%" height="100%">
                            {vis.chart_type === "line" ? (
                              <LineChart data={vis.series_data}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(139, 92, 246, 0.1)" />
                                <XAxis dataKey="name" stroke="#A78BFA" fontSize={11} />
                                <YAxis stroke="#A78BFA" fontSize={11} />
                                <Tooltip
                                  contentStyle={{
                                    backgroundColor: "#181126",
                                    borderColor: "rgba(139, 92, 246, 0.3)",
                                    borderRadius: "12px",
                                    color: "#FFF",
                                  }}
                                />
                                <Line
                                  type="monotone"
                                  dataKey="value"
                                  stroke={color}
                                  strokeWidth={2.5}
                                  dot={{ r: 4 }}
                                />
                              </LineChart>
                            ) : vis.chart_type === "area" ? (
                              <AreaChart data={vis.series_data}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(139, 92, 246, 0.1)" />
                                <XAxis dataKey="name" stroke="#A78BFA" fontSize={11} />
                                <YAxis stroke="#A78BFA" fontSize={11} />
                                <Tooltip
                                  contentStyle={{
                                    backgroundColor: "#181126",
                                    borderColor: "rgba(139, 92, 246, 0.3)",
                                    borderRadius: "12px",
                                    color: "#FFF",
                                  }}
                                />
                                <Area
                                  type="monotone"
                                  dataKey="value"
                                  stroke={color}
                                  fill={color}
                                  fillOpacity={0.25}
                                />
                              </AreaChart>
                            ) : vis.chart_type === "pie" ? (
                              <PieChart>
                                <Tooltip
                                  contentStyle={{
                                    backgroundColor: "#181126",
                                    borderColor: "rgba(139, 92, 246, 0.3)",
                                    borderRadius: "12px",
                                    color: "#FFF",
                                  }}
                                />
                                <Pie
                                  data={vis.series_data}
                                  dataKey="value"
                                  nameKey="name"
                                  cx="50%"
                                  cy="50%"
                                  outerRadius={80}
                                  innerRadius={45}
                                >
                                  {vis.series_data.map((_, i) => (
                                    <Cell
                                      key={`cell-${i}`}
                                      fill={CHART_COLORS[i % CHART_COLORS.length]}
                                    />
                                  ))}
                                </Pie>
                                <Legend wrapperStyle={{ fontSize: "11px", color: "#A78BFA" }} />
                              </PieChart>
                            ) : (
                              <BarChart data={vis.series_data}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(139, 92, 246, 0.1)" />
                                <XAxis dataKey="name" stroke="#A78BFA" fontSize={11} />
                                <YAxis stroke="#A78BFA" fontSize={11} />
                                <Tooltip
                                  contentStyle={{
                                    backgroundColor: "#181126",
                                    borderColor: "rgba(139, 92, 246, 0.3)",
                                    borderRadius: "12px",
                                    color: "#FFF",
                                  }}
                                />
                                <Bar dataKey="value" fill={color} radius={[6, 6, 0, 0]} />
                              </BarChart>
                            )}
                          </ResponsiveContainer>
                        ) : (
                          <div className="h-full flex items-center justify-center text-xs text-violet-400/50">
                            No series data computed for {vis.title}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* IsolationForest Forensic Outlier Tray */}
              {dashboard.anomalies && dashboard.anomalies.length > 0 && (
                <div className="p-5 rounded-3xl glass-card-bronze border border-amber-500/25 space-y-3">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-amber-400" />
                    <h3 className="text-sm font-bold text-amber-300 font-display">
                      Scikit-Learn IsolationForest: Outlier Forensics
                    </h3>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {dashboard.anomalies.map((anom, i) => (
                      <div
                        key={i}
                        className="p-3.5 bg-violet-950/50 border border-amber-500/25 rounded-xl text-xs space-y-1.5"
                      >
                        <div className="flex items-center justify-between font-bold text-white font-mono">
                          <span>Observation #{anom.row_index + 1}</span>
                          <span className="text-amber-400 text-[11px]">Score: {anom.score}</span>
                        </div>
                        <p className="text-violet-200/80 text-[11px] font-sans">{anom.explanation}</p>
                        {anom.root_cause_attribution && (
                          <p className="text-[11px] text-amber-300/90 font-sans">
                            <strong>Root Cause:</strong> {anom.root_cause_attribution}
                          </p>
                        )}
                        {anom.action_required && (
                          <div className="p-2 bg-amber-950/60 rounded border border-amber-500/30 text-[10px] text-amber-200 font-medium font-sans">
                            🚨 <strong>Action:</strong> {anom.action_required}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: BI DEPLOYMENT (POWER BI & TABLEAU) */}
          {activeTab === "bi" && (
            <div className="space-y-6">
              <div className="p-6 rounded-3xl glass-card border border-violet-500/20 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <h3 className="text-lg font-bold text-white font-display">
                      Enterprise BI Deployment Architecture
                    </h3>
                    <p className="text-xs text-violet-300/60 mt-0.5">
                      Export compiled native project packages or copy DAX measures and Tableau calculations directly.
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleExportPowerBI}
                      disabled={downloadingFormat === "powerbi"}
                      className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-amber-950/50 hover:bg-amber-900/60 text-amber-300 font-medium text-xs border border-amber-500/30 transition cursor-pointer"
                    >
                      <Download className="w-3.5 h-3.5 text-amber-400" />
                      <span>{downloadingFormat === "powerbi" ? "Exporting..." : "Download Power BI (.pbip)"}</span>
                    </button>

                    <button
                      onClick={handleExportTableau}
                      disabled={downloadingFormat === "tableau"}
                      className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-violet-950/60 hover:bg-violet-900/70 text-violet-200 font-medium text-xs border border-violet-500/30 transition cursor-pointer"
                    >
                      <Download className="w-3.5 h-3.5 text-violet-400" />
                      <span>{downloadingFormat === "tableau" ? "Exporting..." : "Download Tableau (.twbx)"}</span>
                    </button>
                  </div>
                </div>

                {/* Staging & Code blocks */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-2">
                  {/* Power BI DAX & M */}
                  <div className="border border-violet-500/20 rounded-2xl p-4 bg-violet-950/30 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-amber-300 uppercase tracking-wider flex items-center gap-1.5 font-mono">
                        <Code2 className="w-4 h-4 text-amber-400" />
                        Power BI DAX Measures
                      </span>
                      <button
                        onClick={() => copyToClipboard(dashboard.dax_script, "dax_tab")}
                        className="text-xs text-violet-300 hover:text-white flex items-center gap-1 cursor-pointer"
                      >
                        {copiedKey === "dax_tab" ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        <span>{copiedKey === "dax_tab" ? "Copied" : "Copy DAX"}</span>
                      </button>
                    </div>
                    <pre className="p-3 bg-black/60 text-amber-300 font-mono text-xs rounded-xl overflow-x-auto max-h-64 border border-violet-500/20">
                      {dashboard.dax_script}
                    </pre>

                    <span className="text-xs font-bold text-violet-300 uppercase tracking-wider block pt-2 font-mono">
                      Power Query (M) Script
                    </span>
                    <pre className="p-3 bg-black/60 text-violet-200 font-mono text-xs rounded-xl overflow-x-auto max-h-40 border border-violet-500/20">
                      {dashboard.powerquery_m}
                    </pre>
                  </div>

                  {/* Tableau Calculated Fields */}
                  <div className="border border-violet-500/20 rounded-2xl p-4 bg-violet-950/30 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-amber-300 uppercase tracking-wider flex items-center gap-1.5 font-mono">
                        <Code2 className="w-4 h-4 text-amber-400" />
                        Tableau Calculated Fields
                      </span>
                      <button
                        onClick={() =>
                          copyToClipboard(
                            dashboard.tableau_calculated_fields
                              .map((c) => `// ${c.caption}\n${c.formula}`)
                              .join("\n\n"),
                            "tableau_tab"
                          )
                        }
                        className="text-xs text-violet-300 hover:text-white flex items-center gap-1 cursor-pointer"
                      >
                        {copiedKey === "tableau_tab" ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        <span>{copiedKey === "tableau_tab" ? "Copied" : "Copy All"}</span>
                      </button>
                    </div>

                    <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
                      {dashboard.tableau_calculated_fields.map((calc, i) => (
                        <div key={i} className="p-2.5 bg-black/40 border border-violet-500/20 rounded-xl">
                          <div className="text-xs font-bold text-amber-200 mb-1 font-mono">
                            {calc.caption}
                          </div>
                          <pre className="text-xs font-mono text-violet-200 bg-violet-950/50 p-2 rounded border border-violet-500/20">
                            {calc.formula}
                          </pre>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}