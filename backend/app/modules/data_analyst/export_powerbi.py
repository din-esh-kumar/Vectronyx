# backend/app/modules/data_analyst/export_powerbi.py
import csv
import io
import json
import re
import zipfile
from typing import Any, Dict, List, Optional, Tuple

from app.modules.data_analyst.schemas import DashboardPlan


THEME_FILENAME = "VectronyxExecutiveTheme.json"

CURRENCY_KEYWORDS = ("revenue", "sales", "arr", "mrr", "cost", "price", "profit", "margin", "ebitda", "ltv", "cac", "amount", "spend", "budget", "volume", "value", "fee", "salary", "income")
PERCENT_KEYWORDS = ("rate", "pct", "percent", "ratio", "churn", "margin_pct", "share", "cv", "yield", "conversion", "retention", "growth", "utilization")
DATE_PATTERNS = (
    re.compile(r"^\d{4}-\d{1,2}-\d{1,2}(?:[T\s]\d{2}:\d{2}(?::\d{2})?)?$"),
    re.compile(r"^\d{4}/\d{1,2}/\d{1,2}$"),
    re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$"),
    re.compile(r"^\d{4}-\d{2}$"),
)
ID_KEYWORDS = ("id", "uuid", "guid", "isbn", "sku", "code", "zip", "postal")


def _extract_dax_expression(formula: str) -> str:
    """
    Extracts the right-hand DAX expression for model.bim measures when
    given a 'Measure Name = EXPRESSION' string.
    """
    text = (formula or "").strip()
    if not text:
        return "0"
    lines = [line for line in text.splitlines() if not line.strip().startswith(("--", "//"))]
    cleaned = "\n".join(lines).strip() or text
    if "=" in cleaned:
        lhs, rhs = cleaned.split("=", 1)
        if lhs.strip() and rhs.strip():
            return rhs.strip()
    return cleaned


def _looks_like_date(val: str) -> bool:
    s = val.strip()
    return any(p.match(s) for p in DATE_PATTERNS)


def _infer_format_string(name: str, data_type: str = "double", sample_value: str = "") -> str:
    low = (name or "").lower()
    sv = (sample_value or "").strip()
    if data_type == "dateTime":
        return "yyyy-mm-dd"
    if "%" in sv or any(k in low for k in PERCENT_KEYWORDS):
        return "0.0%"
    if "$" in sv or any(k in low for k in CURRENCY_KEYWORDS):
        return "$#,0;($#,0);$0"
    if data_type == "int64":
        return "#,0"
    return "#,0.00"


def _infer_csv_columns_and_types(csv_content: str) -> List[Dict[str, Any]]:
    """
    Parses the CSV header and sample rows to emit strongly typed column
    definitions (dateTime, int64, double, string) with smart summarizeBy
    and formatString metadata for the Dataset table in model.bim.
    """
    cleaned_csv = (csv_content or "").lstrip("\ufeff")
    if not cleaned_csv.strip():
        return []

    reader = csv.reader(io.StringIO(cleaned_csv))
    try:
        headers = next(reader)
    except StopIteration:
        return []

    sample_rows: List[List[str]] = []
    for _, row in zip(range(80), reader):
        sample_rows.append(row)

    seen: Dict[str, int] = {}
    columns: List[Dict[str, Any]] = []
    for idx, raw_name in enumerate(headers):
        col_name = raw_name.strip() or f"Column_{idx + 1}"
        count = seen.get(col_name, 0)
        seen[col_name] = count + 1
        if count > 0:
            col_name = f"{col_name}_{count + 1}"

        values = [r[idx].strip() for r in sample_rows if idx < len(r) and r[idx].strip() != ""]
        data_type = "string"
        if values:
            if all(_looks_like_date(v) for v in values[:30]):
                data_type = "dateTime"
            else:
                all_int = True
                all_float = True
                for val in values:
                    is_zero_padded_id = len(val) > 1 and (
                        (val.startswith("0") and not val.startswith("0."))
                        or (val.startswith("-0") and not val.startswith("-0."))
                    )
                    if is_zero_padded_id:
                        all_int = False
                        all_float = False
                        break
                    cleaned_num = val.replace(",", "").replace("$", "").replace("%", "")
                    try:
                        int(cleaned_num)
                    except ValueError:
                        all_int = False
                    try:
                        float(cleaned_num)
                    except ValueError:
                        all_float = False
                        break
                if all_int:
                    data_type = "int64"
                elif all_float:
                    data_type = "double"

        low_col = col_name.lower()
        is_id_or_year = (
            low_col in ID_KEYWORDS
            or low_col.endswith("_id")
            or low_col.endswith("id") and len(low_col) <= 12
            or low_col in ("year", "month", "quarter")
        )
        col_def: Dict[str, Any] = {
            "name": col_name,
            "dataType": data_type,
            "sourceColumn": col_name,
        }
        if data_type in ("int64", "double"):
            col_def["summarizeBy"] = "none" if (is_id_or_year or any(k in low_col for k in PERCENT_KEYWORDS)) else "sum"
            col_def["formatString"] = _infer_format_string(col_name, data_type)
        elif data_type == "dateTime":
            col_def["formatString"] = "yyyy-mm-dd"
            col_def["dataCategory"] = "PaddedDateTableDates"
        columns.append(col_def)

    return columns


def _resolve_column_name(requested: str, columns: List[Dict[str, Any]], fallback_types: Optional[Tuple[str, ...]] = None) -> str:
    """Maps a requested column name (exact or case-insensitive) to a real model.bim column."""
    if not columns:
        return requested
    exact = {c["name"]: c["name"] for c in columns}
    if requested in exact:
        return exact[requested]
    lower_map = {c["name"].lower(): c["name"] for c in columns}
    if (requested or "").lower() in lower_map:
        return lower_map[requested.lower()]
    if fallback_types:
        for c in columns:
            if c["dataType"] in fallback_types:
                return c["name"]
    return columns[0]["name"]


def _sanitize_dax_references(expression: str, columns: List[Dict[str, Any]]) -> str:
    """Normalizes casing of 'Dataset'[Col] references against actual CSV columns."""
    if not expression or not columns:
        return expression or "0"
    lower_map = {c["name"].lower(): c["name"] for c in columns}

    def _repl(match: re.Match) -> str:
        col = match.group(1)
        resolved = lower_map.get(col.lower(), col)
        return f"'Dataset'[{resolved}]"

    return re.sub(r"(?:'Dataset'|Dataset)\[([^\]]+)\]", _repl, expression)


def _build_executive_theme() -> Dict[str, Any]:
    """
    Production Power BI Custom Theme JSON engineered for 10+ year C-Suite
    readability: restrained slate canvas, crisp white/card hierarchy, cobalt &
    teal primary encodings, warm amber accent, and clear typography.
    """
    return {
        "name": "Vectronyx Executive Principal Theme",
        "dataColors": [
            "#2563EB",
            "#0D9488",
            "#D97706",
            "#7C3AED",
            "#E11D48",
            "#0284C7",
            "#059669",
            "#EA580C",
        ],
        "background": "#F8FAFC",
        "foreground": "#0F172A",
        "tableAccent": "#2563EB",
        "good": "#059669",
        "neutral": "#D97706",
        "bad": "#DC2626",
        "maximum": "#2563EB",
        "center": "#94A3B8",
        "minimum": "#E11D48",
        "textClasses": {
            "callout": {"fontSize": 24, "fontFace": "DIN", "color": "#0F172A"},
            "title": {"fontSize": 13, "fontFace": "Segoe UI Semibold", "color": "#0F172A"},
            "header": {"fontSize": 11, "fontFace": "Segoe UI Semibold", "color": "#334155"},
            "label": {"fontSize": 10, "fontFace": "Segoe UI", "color": "#475569"},
        },
        "visualStyles": {
            "*": {
                "*": {
                    "background": [{"color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0}],
                    "border": [{"show": True, "color": {"solid": {"color": "#E2E8F0"}}, "radius": 10}],
                    "dropShadow": [{"show": True, "color": {"solid": {"color": "#0F172A"}}, "transparency": 92, "preset": "BottomRight"}],
                    "title": [{"show": True, "fontColor": {"solid": {"color": "#0F172A"}}, "fontSize": 12, "fontFamily": "Segoe UI Semibold"}],
                    "labels": [{"show": True, "color": {"solid": {"color": "#334155"}}, "fontSize": 9}],
                    "legend": [{"show": True, "position": "Top", "labelColor": {"solid": {"color": "#475569"}}, "fontSize": 9}],
                }
            },
            "page": {
                "*": {
                    "background": [{"color": {"solid": {"color": "#F1F5F9"}}, "transparency": 0}],
                    "outspace": [{"color": {"solid": {"color": "#E2E8F0"}}}],
                }
            },
            "card": {
                "*": {
                    "labels": [{"color": {"solid": {"color": "#0F172A"}}, "fontSize": 24, "fontFamily": "DIN"}],
                    "categoryLabels": [{"show": True, "color": {"solid": {"color": "#64748B"}}, "fontSize": 10}],
                    "border": [{"show": True, "color": {"solid": {"color": "#CBD5E1"}}, "radius": 10}],
                }
            },
            "slicer": {
                "*": {
                    "data": [{"mode": "Dropdown"}],
                    "header": [{"fontColor": {"solid": {"color": "#1E293B"}}, "textSize": 10}],
                }
            },
        },
    }


def _make_textbox_visual(
    name: str,
    x: int,
    y: int,
    width: int,
    height: int,
    heading: str,
    paragraphs: List[str],
    *,
    dark_banner: bool = False,
) -> Dict[str, Any]:
    """Creates a clean Power BI native textbox visual container."""
    title_color = "#F8FAFC" if dark_banner else "#0F172A"
    body_color = "#CBD5E1" if dark_banner else "#334155"
    bg_color = "#0F172A" if dark_banner else "#FFFFFF"

    p_nodes: List[Dict[str, Any]] = [
        {
            "textRuns": [
                {
                    "value": heading,
                    "textStyle": {
                        "fontWeight": "bold",
                        "fontFamily": "Segoe UI Semibold",
                        "fontSize": "14pt" if dark_banner else "11pt",
                        "color": title_color,
                    },
                }
            ]
        }
    ]
    for para in paragraphs:
        if not para:
            continue
        p_nodes.append(
            {
                "textRuns": [
                    {
                        "value": para,
                        "textStyle": {
                            "fontFamily": "Segoe UI",
                            "fontSize": "9.5pt" if dark_banner else "9pt",
                            "color": body_color,
                        },
                    }
                ]
            }
        )

    config: Dict[str, Any] = {
        "name": name,
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "width": width, "height": height}}],
        "singleVisual": {
            "visualType": "textbox",
            "drillFilterOtherVisuals": True,
            "objects": {
                "general": [{"properties": {"paragraphs": p_nodes}}]
            },
            "vcObjects": {
                "background": [
                    {
                        "properties": {
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                            "color": {"solid": {"color": bg_color}},
                            "transparency": {"expr": {"Literal": {"Value": "0D"}}},
                        }
                    }
                ],
                "border": [
                    {
                        "properties": {
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                            "color": {"solid": {"color": "#1E293B" if dark_banner else "#CBD5E1"}},
                            "radius": {"expr": {"Literal": {"Value": "10D"}}},
                        }
                    }
                ],
            },
        },
    }
    return {"x": x, "y": y, "width": width, "height": height, "config": json.dumps(config)}


def _make_slicer_visual(name: str, column_name: str, x: int, y: int, width: int, height: int) -> Dict[str, Any]:
    safe_label = column_name.replace("_", " ").title().replace("'", "''")
    config = {
        "name": name,
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "width": width, "height": height}}],
        "singleVisual": {
            "visualType": "slicer",
            "projections": {"Values": [{"queryRef": f"Dataset.{column_name}", "active": True}]},
            "prototypeQuery": {
                "Version": 2,
                "From": [{"Name": "d", "Entity": "Dataset", "Type": 0}],
                "Select": [
                    {
                        "Column": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": column_name},
                        "Name": f"Dataset.{column_name}",
                    }
                ],
            },
            "objects": {
                "data": [{"properties": {"mode": {"expr": {"Literal": {"Value": "'Dropdown'"}}}}}],
                "header": [{"properties": {"text": {"expr": {"Literal": {"Value": f"'Filter: {safe_label}'"}}}}}],
            },
        },
    }
    return {"x": x, "y": y, "width": width, "height": height, "config": json.dumps(config)}


def _make_kpi_card_visual(name: str, measure_name: str, x: int, y: int, width: int, height: int) -> Dict[str, Any]:
    safe_title = measure_name.replace("'", "''")
    config = {
        "name": name,
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "width": width, "height": height}}],
        "singleVisual": {
            "visualType": "card",
            "projections": {"Values": [{"queryRef": f"Dataset.{measure_name}"}]},
            "prototypeQuery": {
                "Version": 2,
                "From": [{"Name": "d", "Entity": "Dataset", "Type": 0}],
                "Select": [
                    {
                        "Measure": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": measure_name},
                        "Name": f"Dataset.{measure_name}",
                    }
                ],
            },
            "vcObjects": {
                "title": [
                    {
                        "properties": {
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                            "text": {"expr": {"Literal": {"Value": f"'{safe_title}'"}}},
                        }
                    }
                ]
            },
        },
    }
    return {"x": x, "y": y, "width": width, "height": height, "config": json.dumps(config)}


def _make_chart_visual(
    vis: Any,
    columns: List[Dict[str, Any]],
    x: int,
    y: int,
    width: int,
    height: int,
) -> Dict[str, Any]:
    ctype = (vis.chart_type or "").lower()
    pb_visual_type = "clusteredColumnChart"
    if ctype == "line":
        pb_visual_type = "lineChart"
    elif ctype == "area":
        pb_visual_type = "areaChart"
    elif ctype == "pie":
        pb_visual_type = "donutChart"
    elif ctype == "scatter":
        pb_visual_type = "scatterChart"
    elif ctype == "horizontal_bar":
        pb_visual_type = "clusteredBarChart"
    elif ctype == "pareto":
        pb_visual_type = "lineClusteredColumnComboChart"
    elif ctype == "histogram":
        pb_visual_type = "clusteredColumnChart"

    x_col = _resolve_column_name(vis.x_axis, columns, fallback_types=("string", "dateTime"))
    y_col = _resolve_column_name(vis.y_axis, columns, fallback_types=("double", "int64"))
    safe_title = (vis.title or f"{y_col} by {x_col}").replace("'", "''")
    subtitle = (vis.key_insight or vis.description or "")[:140].replace("'", "''")

    if pb_visual_type == "scatterChart":
        projections = {
            "X": [{"queryRef": f"Dataset.{x_col}"}],
            "Y": [{"queryRef": f"Dataset.{y_col}"}],
        }
    elif pb_visual_type == "donutChart":
        projections = {
            "Category": [{"queryRef": f"Dataset.{x_col}"}],
            "Y": [{"queryRef": f"Dataset.{y_col}"}],
        }
    else:
        projections = {
            "Category": [{"queryRef": f"Dataset.{x_col}"}],
            "Y": [{"queryRef": f"Dataset.{y_col}"}],
        }

    config = {
        "name": f"visual_{vis.id}",
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "width": width, "height": height}}],
        "singleVisual": {
            "visualType": pb_visual_type,
            "projections": projections,
            "objects": {
                "labels": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}}}],
            },
            "vcObjects": {
                "title": [
                    {
                        "properties": {
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                            "text": {"expr": {"Literal": {"Value": f"'{safe_title}'"}}},
                        }
                    }
                ],
                "subTitle": [
                    {
                        "properties": {
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                            "text": {"expr": {"Literal": {"Value": f"'{subtitle}'"}}},
                        }
                    }
                ],
            },
        },
    }
    return {"x": x, "y": y, "width": width, "height": height, "config": json.dumps(config)}


def _make_cohort_table_visual(
    name: str,
    dimension_col: str,
    measure_names: List[str],
    x: int,
    y: int,
    width: int,
    height: int,
) -> Dict[str, Any]:
    values_proj = [{"queryRef": f"Dataset.{dimension_col}"}] + [
        {"queryRef": f"Dataset.{m}"} for m in measure_names[:4]
    ]
    safe_dim = dimension_col.replace("_", " ").title().replace("'", "''")
    config = {
        "name": name,
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "width": width, "height": height}}],
        "singleVisual": {
            "visualType": "tableEx",
            "projections": {"Values": values_proj},
            "vcObjects": {
                "title": [
                    {
                        "properties": {
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                            "text": {"expr": {"Literal": {"Value": f"'Cohort Performance Matrix by {safe_dim}'"}}},
                        }
                    }
                ]
            },
        },
    }
    return {"x": x, "y": y, "width": width, "height": height, "config": json.dumps(config)}


def _build_enterprise_measures(
    plan: DashboardPlan,
    columns: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Constructs a rich, display-folder organized set of Power BI TMSL measures
    with proper formatString and verified column names.
    """
    measures: List[Dict[str, Any]] = []
    seen: set[str] = set()

    def _add_measure(name: str, expression: str, folder: str, fmt: str, description: str) -> None:
        clean_name = (name or "").strip()
        if not clean_name or clean_name.lower() in seen:
            return
        seen.add(clean_name.lower())
        measures.append(
            {
                "name": clean_name,
                "expression": _sanitize_dax_references(expression, columns),
                "formatString": fmt,
                "displayFolder": folder,
                "description": description,
            }
        )

    # 1. Executive KPIs from DashboardPlan
    for kpi in plan.kpis:
        expr = _extract_dax_expression(kpi.formula_dax)
        fmt = _infer_format_string(kpi.title, sample_value=kpi.value)
        _add_measure(
            kpi.title,
            expr,
            "01 · Executive KPIs",
            fmt,
            kpi.executive_takeaway or kpi.rationale,
        )

    # 2. Identify primary numeric, categorical, and temporal columns for Senior Analyst DAX folders
    numeric_cols = [
        c["name"]
        for c in columns
        if c["dataType"] in ("double", "int64") and c.get("summarizeBy") != "none"
    ]
    if not numeric_cols:
        numeric_cols = [c["name"] for c in columns if c["dataType"] in ("double", "int64")]
    cat_cols = [c["name"] for c in columns if c["dataType"] == "string"]
    date_cols = [c["name"] for c in columns if c["dataType"] == "dateTime"]

    focused_num = next((m for m in (plan.focused_metrics or []) if any(c["name"].lower() == m.lower() for c in columns)), None)
    primary_num = _resolve_column_name(focused_num, columns, ("double", "int64")) if focused_num else (numeric_cols[0] if numeric_cols else None)
    focused_cat = next((d for d in (plan.focused_dimensions or []) if any(c["name"].lower() == d.lower() for c in columns)), None)
    primary_cat = _resolve_column_name(focused_cat, columns, ("string",)) if focused_cat else (cat_cols[0] if cat_cols else None)

    # Folder 02 · Statistical & Distribution
    _add_measure("Total Records", "COUNTROWS('Dataset')", "02 · Statistical & Distribution", "#,0", "Total active records in current filter context.")
    if primary_num:
        p_label = primary_num.replace("_", " ").title()
        p_fmt = _infer_format_string(primary_num, "double")
        _add_measure(f"{p_label} Median (P50)", f"MEDIANX('Dataset', 'Dataset'[{primary_num}])", "02 · Statistical & Distribution", p_fmt, "Non-parametric median resilient to fat-tail outliers.")
        _add_measure(f"{p_label} Q1 (P25)", f"PERCENTILEX.INC('Dataset', 'Dataset'[{primary_num}], 0.25)", "02 · Statistical & Distribution", p_fmt, "Lower quartile (25th percentile) threshold.")
        _add_measure(f"{p_label} Q3 (P75)", f"PERCENTILEX.INC('Dataset', 'Dataset'[{primary_num}], 0.75)", "02 · Statistical & Distribution", p_fmt, "Upper quartile (75th percentile) top-performer benchmark.")
        _add_measure(f"{p_label} P95 Tail", f"PERCENTILEX.INC('Dataset', 'Dataset'[{primary_num}], 0.95)", "02 · Statistical & Distribution", p_fmt, "95th percentile upper tail boundary.")
        _add_measure(f"{p_label} Volatility CV %", f"DIVIDE(STDEVX.P('Dataset', 'Dataset'[{primary_num}]), AVERAGEX('Dataset', 'Dataset'[{primary_num}]), 0)", "02 · Statistical & Distribution", "0.0%", "Coefficient of Variation (Std Dev / Mean).")
        _add_measure(
            f"{p_label} Tukey Outlier Count",
            (
                f"VAR Q1 = PERCENTILEX.INC(ALLSELECTED('Dataset'), 'Dataset'[{primary_num}], 0.25)\n"
                f"VAR Q3 = PERCENTILEX.INC(ALLSELECTED('Dataset'), 'Dataset'[{primary_num}], 0.75)\n"
                f"VAR UpperFence = Q3 + 1.5 * (Q3 - Q1)\n"
                f"RETURN COUNTROWS(FILTER('Dataset', 'Dataset'[{primary_num}] > UpperFence))"
            ),
            "02 · Statistical & Distribution",
            "#,0",
            "Count of records breaching the upper 1.5xIQR Tukey outlier fence.",
        )

        # Folder 03 · Cohort & Concentration
        if primary_cat:
            c_label = primary_cat.replace("_", " ").title()
            _add_measure(
                f"{p_label} Share of Selected %",
                f"DIVIDE(SUM('Dataset'[{primary_num}]), CALCULATE(SUM('Dataset'[{primary_num}]), ALLSELECTED('Dataset')), 0)",
                "03 · Cohort & Concentration",
                "0.0%",
                f"Percentage contribution of each {c_label} cohort within active slicers.",
            )
            _add_measure(
                f"{c_label} Rank",
                f"RANKX(ALLSELECTED('Dataset'[{primary_cat}]), CALCULATE(SUM('Dataset'[{primary_num}])), , DESC, DENSE)",
                "03 · Cohort & Concentration",
                "#,0",
                f"Dynamic dense ranking of {c_label} cohorts by {p_label}.",
            )
            _add_measure(
                f"{p_label} vs Portfolio Mean %",
                (
                    f"VAR CurrentAvg = AVERAGE('Dataset'[{primary_num}])\n"
                    f"VAR BaselineAvg = CALCULATE(AVERAGE('Dataset'[{primary_num}]), ALLSELECTED('Dataset'))\n"
                    f"RETURN DIVIDE(CurrentAvg - BaselineAvg, BaselineAvg, 0)"
                ),
                "03 · Cohort & Concentration",
                "+0.0%;-0.0%;0.0%",
                "Relative percentage spread of the selected cohort mean versus overall portfolio mean.",
            )

        # Folder 04 · Time Intelligence
        if date_cols:
            d_col = date_cols[0]
            _add_measure(
                f"{p_label} Running Cumulative",
                (
                    f"VAR MaxDate = MAX('Dataset'[{d_col}])\n"
                    f"RETURN CALCULATE(SUM('Dataset'[{primary_num}]), FILTER(ALLSELECTED('Dataset'), 'Dataset'[{d_col}] <= MaxDate))"
                ),
                "04 · Time Intelligence",
                p_fmt,
                f"Cumulative running total of {p_label} over '{d_col}'.",
            )

    return measures


def _build_default_m_code(columns: List[Dict[str, Any]]) -> str:
    type_map = {"int64": "Int64.Type", "double": "type number", "dateTime": "type date", "string": "type text"}
    pairs = [f'{{"{c["name"]}", {type_map.get(c["dataType"], "type text")}}}' for c in columns[:40]]
    if not pairs:
        return (
            "let\n"
            '    Source = Csv.Document(File.Contents("dataset.csv"), [Delimiter=",", Encoding=65001]),\n'
            '    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true])\n'
            "in\n"
            '    #"Promoted Headers"'
        )
    types_str = ",\n        ".join(pairs)
    return (
        "let\n"
        '    CsvFilePath = "dataset.csv",\n'
        '    Source = Csv.Document(File.Contents(CsvFilePath), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),\n'
        '    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),\n'
        '    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {\n'
        f"        {types_str}\n"
        "    })\n"
        "in\n"
        '    #"Changed Type"'
    )


def generate_powerbi_pbip_archive(
    plan: DashboardPlan,
    csv_content: str,
    filename_base: str = "Vectronyx_Dashboard",
) -> io.BytesIO:
    """
    Generates a 10+ Year Principal Data Analyst 3-Page Executive Power BI Project
    (.pbip) zip package complete with:
      - Custom Executive Power BI JSON Theme registered in report.json
      - 3 widescreen (1280x720) report pages (Executive Overview, Statistical &
        Cohort Diagnostics, Risk/Anomalies & Action Playbook)
      - Interactive slicers, formatted KPI cards, insight-subtitled visuals,
        cohort performance matrix tableEx, and SCR/Roadmap narrative cards
      - Enterprise model.bim (compat 1567) with strongly typed columns, display-folder
        organized DAX measures with formatStrings, and typed Power Query M
      - Full Executive_Analyst_Dossier.md, DAX_Measures_Library.dax & Setup Guide
    """
    columns = _infer_csv_columns_and_types(csv_content)
    measures = _build_enterprise_measures(plan, columns)
    measure_names = [m["name"] for m in measures]

    cat_cols = [c["name"] for c in columns if c["dataType"] == "string"]
    date_cols = [c["name"] for c in columns if c["dataType"] == "dateTime"]
    slicer_candidates: List[str] = []
    for dim in (plan.focused_dimensions or []) + cat_cols + date_cols:
        resolved = _resolve_column_name(dim, columns) if columns else dim
        if resolved and resolved not in slicer_candidates:
            slicer_candidates.append(resolved)
    slicer_cols = slicer_candidates[:2]
    primary_dim = slicer_cols[0] if slicer_cols else (columns[0]["name"] if columns else "Category")

    dossier = plan.dossier
    quality_badge = f"Principal Quality Score: {plan.quality_score:.0f}/100" if plan.quality_score else "Principal Executive Edition"
    integrity_val = dossier.data_integrity_score if dossier else 100.0

    # =========================================================================
    # PAGE 1: EXECUTIVE OVERVIEW (1280 x 720)
    # =========================================================================
    page1_visuals: List[Dict[str, Any]] = []
    # Top Executive Banner
    banner_w = 820 if slicer_cols else 1240
    page1_visuals.append(
        _make_textbox_visual(
            "p1_exec_banner",
            x=20,
            y=14,
            width=banner_w,
            height=74,
            heading=plan.title[:110],
            paragraphs=[
                f"Dataset: {plan.dataset_name}  |  Integrity: {integrity_val:.1f}%  |  {quality_badge}",
                (dossier.executive_verdict if dossier else plan.summary)[:240],
            ],
            dark_banner=True,
        )
    )
    # Interactive Slicers on Top-Right
    for s_idx, s_col in enumerate(slicer_cols):
        sx = 852 + (s_idx * 208)
        page1_visuals.append(_make_slicer_visual(f"p1_slicer_{s_idx}", s_col, x=sx, y=14, width=198, height=74))

    # Formatted KPI Scorecard Row (up to 5 cards spanning full 1240px width)
    top_kpis = plan.kpis[:5]
    if top_kpis:
        gap = 12
        card_w = (1240 - gap * (len(top_kpis) - 1)) // len(top_kpis)
        for idx, kpi in enumerate(top_kpis):
            kx = 20 + idx * (card_w + gap)
            page1_visuals.append(_make_kpi_card_visual(f"p1_kpi_{idx}", kpi.title, x=kx, y=100, width=card_w, height=104))

    # 2x2 Primary Analytical Visual Grid
    p1_charts = plan.visuals[:4]
    for idx, vis in enumerate(p1_charts):
        col_i = idx % 2
        row_i = idx // 2
        vx = 20 + col_i * 626
        vy = 216 + row_i * 246
        page1_visuals.append(_make_chart_visual(vis, columns, x=vx, y=vy, width=614, height=234))

    # =========================================================================
    # PAGE 2: STATISTICAL & COHORT DIAGNOSTICS (1280 x 720)
    # =========================================================================
    page2_visuals: List[Dict[str, Any]] = [
        _make_textbox_visual(
            "p2_banner",
            x=20,
            y=14,
            width=1020 if slicer_cols else 1240,
            height=64,
            heading=f"Statistical & Cohort Diagnostics — {plan.dataset_name}",
            paragraphs=[
                "Non-parametric quantiles (Median/IQR/P95), Pearson/Spearman correlations, ANOVA cohort variance & distribution forensics."
            ],
            dark_banner=True,
        )
    ]
    if slicer_cols:
        page2_visuals.append(_make_slicer_visual("p2_slicer_0", slicer_cols[0], x=1052, y=14, width=208, height=64))

    # Top Row on Page 2: Remaining visuals (or last 2 charts)
    p2_charts = plan.visuals[4:6] if len(plan.visuals) > 4 else plan.visuals[-2:]
    for idx, vis in enumerate(p2_charts[:2]):
        vx = 20 + idx * 626
        page2_visuals.append(_make_chart_visual(vis, columns, x=vx, y=90, width=614, height=290))

    # Bottom Left: Live Interactive Cohort Performance Table (tableEx)
    page2_visuals.append(
        _make_cohort_table_visual(
            "p2_cohort_table",
            dimension_col=primary_dim,
            measure_names=measure_names[:4],
            x=20,
            y=394,
            width=680,
            height=308,
        )
    )

    # Bottom Right: Statistical & Correlation Diagnostics Card
    stat_lines: List[str] = []
    if dossier and dossier.statistical_diagnostics:
        for d in dossier.statistical_diagnostics[:4]:
            stat_lines.append(
                f"• {d.metric_name}: Mean={d.mean}, Median={d.median}, IQR={d.p25}–{d.p75}, Skew={d.skewness}, Outliers={d.outlier_count} ({d.outlier_pct}%)"
            )
    if dossier and dossier.correlation_insights:
        for c in dossier.correlation_insights[:3]:
            stat_lines.append(f"• Driver: {c.metric_a} × {c.metric_b} → r={c.pearson_r:+.3f} ({c.strength} {c.direction})")
    if not stat_lines:
        stat_lines.append(plan.summary)

    page2_visuals.append(
        _make_textbox_visual(
            "p2_stats_card",
            x=714,
            y=394,
            width=546,
            height=308,
            heading="Empirical Quantiles & Multivariate Drivers",
            paragraphs=stat_lines,
        )
    )

    # =========================================================================
    # PAGE 3: RISK, ANOMALIES & STRATEGIC ACTION PLAYBOOK (1280 x 720)
    # =========================================================================
    scr_paragraphs = (
        [
            f"EXECUTIVE VERDICT: {dossier.executive_verdict}",
            f"SITUATION: {dossier.situation}",
            f"COMPLICATION: {dossier.complication}",
            f"RESOLUTION: {dossier.resolution}",
        ]
        if dossier
        else [plan.summary]
    )
    init_paragraphs: List[str] = []
    if dossier and dossier.strategic_initiatives:
        for init in dossier.strategic_initiatives[:5]:
            init_paragraphs.append(
                f"[{init.priority}] {init.title} — Impact: {init.expected_financial_impact} | Owner: {init.operational_owner}. {init.rationale}"
            )
    if not init_paragraphs:
        init_paragraphs.append("Review Executive_Analyst_Dossier.md for detailed 30/60/90-day strategic roadmap.")

    risk_paragraphs: List[str] = []
    if dossier and dossier.risk_matrix:
        for r in dossier.risk_matrix[:4]:
            risk_paragraphs.append(
                f"[{r.severity} / Prob: {r.probability}] {r.risk_title}: {r.business_exposure} Mitigation: {r.mitigation_protocol}"
            )
    if plan.anomalies:
        risk_paragraphs.append(
            f"ISOLATION FOREST OUTLIERS ({len(plan.anomalies)} flagged): Top observation #{plan.anomalies[0].row_index + 1} (score {plan.anomalies[0].score}) — {plan.anomalies[0].explanation}"
        )
    if not risk_paragraphs:
        risk_paragraphs.append("Zero critical structural risks detected in current sample.")

    page3_visuals: List[Dict[str, Any]] = [
        _make_textbox_visual(
            "p3_banner",
            x=20,
            y=14,
            width=1240,
            height=64,
            heading="Executive Decision Ledger — Risk Governance, Anomalies & Strategic Playbook",
            paragraphs=[f"Prepared for Boardroom Review  |  Dataset: {plan.dataset_name}  |  {quality_badge}"],
            dark_banner=True,
        ),
        _make_textbox_visual(
            "p3_scr_card",
            x=20,
            y=90,
            width=1240,
            height=210,
            heading="Situation → Complication → Resolution (SCR) Executive Brief",
            paragraphs=scr_paragraphs,
        ),
        _make_textbox_visual(
            "p3_initiatives_card",
            x=20,
            y=314,
            width=640,
            height=388,
            heading="Prioritized Strategic Initiatives Roadmap (P0 / P1 / P2)",
            paragraphs=init_paragraphs,
        ),
        _make_textbox_visual(
            "p3_risk_card",
            x=674,
            y=314,
            width=586,
            height=388,
            heading="Risk Governance Matrix & Outlier Forensics",
            paragraphs=risk_paragraphs,
        ),
    ]

    report_json = {
        "config": json.dumps(
            {
                "version": "5.54",
                "themeCollection": {
                    "baseTheme": {"name": "CY24SU02", "version": "5.54", "type": 2},
                    "customTheme": {"name": THEME_FILENAME, "version": "5.54", "type": 1},
                },
                "activeSectionIndex": 0,
            }
        ),
        "layoutOptimization": 0,
        "resourcePackages": [
            {
                "resourcePackage": {
                    "disabled": False,
                    "items": [
                        {
                            "name": THEME_FILENAME,
                            "path": THEME_FILENAME,
                            "type": 202,
                        }
                    ],
                    "name": "RegisteredResources",
                    "type": 1,
                }
            }
        ],
        "sections": [
            {
                "name": "ReportSection_ExecutiveOverview",
                "displayName": "Executive Overview",
                "width": 1280,
                "height": 720,
                "ordinal": 0,
                "visualContainers": page1_visuals,
            },
            {
                "name": "ReportSection_Diagnostics",
                "displayName": "Statistical & Cohort Diagnostics",
                "width": 1280,
                "height": 720,
                "ordinal": 1,
                "visualContainers": page2_visuals,
            },
            {
                "name": "ReportSection_ActionPlaybook",
                "displayName": "Risk, Anomalies & Action Playbook",
                "width": 1280,
                "height": 720,
                "ordinal": 2,
                "visualContainers": page3_visuals,
            },
        ],
    }

    m_code_content = (
        plan.powerquery_m
        if (plan.powerquery_m and "Table.TransformColumnTypes" in plan.powerquery_m)
        else _build_default_m_code(columns)
    )

    dataset_table: Dict[str, Any] = {
        "name": "Dataset",
        "description": f"Strongly typed enterprise table for {plan.dataset_name}",
        "columns": columns,
        "partitions": [
            {
                "name": "Dataset",
                "mode": "import",
                "source": {
                    "type": "m",
                    "expression": m_code_content,
                },
            }
        ],
        "measures": measures,
    }

    model_bim = {
        "name": "VectronyxSemanticModel",
        "compatibilityLevel": 1567,
        "model": {
            "culture": "en-US",
            "dataAccessOptions": {"legacyRedirectsEnabled": True, "fastCombine": True},
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "tables": [dataset_table],
        },
    }

    # Build consolidated DAX script grouped by display folder
    dax_by_folder: Dict[str, List[Dict[str, Any]]] = {}
    for m in measures:
        dax_by_folder.setdefault(m.get("displayFolder", "General"), []).append(m)
    dax_library_lines = [
        f"-- ============================================================================",
        f"-- VECTRONYX EXECUTIVE POWER BI DAX MEASURES LIBRARY — {plan.title}",
        f"-- Dataset: {plan.dataset_name} | {quality_badge}",
        f"-- ============================================================================",
    ]
    for folder, items in dax_by_folder.items():
        dax_library_lines.append(f"\n-- [{folder}]")
        for m in items:
            dax_library_lines.append(f"-- Format: {m.get('formatString', 'General')} | {m.get('description', '')}")
            dax_library_lines.append(f"{m['name']} =\n{m['expression']}\n")
    dax_library_text = "\n".join(dax_library_lines).strip() + "\n"

    # Import markdown dossier generator lazily to avoid circular imports
    from app.modules.data_analyst.analyst import generate_dossier_markdown

    dossier_md = generate_dossier_markdown(plan)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        # 1. Root .pbip descriptor
        pbip_meta = {
            "version": "1.0",
            "artifacts": [{"report": {"path": f"{filename_base}.Report"}}],
            "settings": {"enableAutoRecovery": True},
        }
        z.writestr(f"{filename_base}.pbip", json.dumps(pbip_meta, indent=2))

        # 2. Report descriptor, 3-page report.json & Custom Executive Theme
        pbir_meta = {
            "version": "1.0",
            "datasetReference": {
                "byPath": {"path": f"../{filename_base}.Dataset"},
                "byConnection": None,
            },
        }
        z.writestr(f"{filename_base}.Report/definition.pbir", json.dumps(pbir_meta, indent=2))
        z.writestr(f"{filename_base}.Report/report.json", json.dumps(report_json, indent=2))
        z.writestr(
            f"{filename_base}.Report/StaticResources/RegisteredResources/{THEME_FILENAME}",
            json.dumps(_build_executive_theme(), indent=2),
        )

        # 3. Dataset descriptor, Enterprise model.bim & raw CSV
        z.writestr(f"{filename_base}.Dataset/definition.pbidataset", json.dumps({"version": "1.0", "settings": {}}, indent=2))
        z.writestr(f"{filename_base}.Dataset/model.bim", json.dumps(model_bim, indent=2))
        z.writestr(f"{filename_base}.Dataset/dataset.csv", csv_content)

        # 4. Executive Handover Pack
        z.writestr("Executive_Analyst_Dossier.md", dossier_md)
        z.writestr("DAX_Measures_Library.dax", dax_library_text)

        readme_text = f"""========================================================================
VECTRONYX AI WORKBENCH — PRINCIPAL EXECUTIVE POWER BI PROJECT (.pbip)
========================================================================
Report Title:  {plan.title}
Dataset:       {plan.dataset_name}
Quality Grade: {quality_badge}
Report Pages:  3 Widescreen (1280x720) Pages
  1. Executive Overview (Banner, Interactive Slicers, KPI Cards, 2x2 Grid)
  2. Statistical & Cohort Diagnostics (Charts, Cohort Table, Quantiles)
  3. Risk, Anomalies & Action Playbook (SCR Brief, P0-P2 ROI Roadmap, Risks)

HOW TO OPEN IN POWER BI DESKTOP:
1. Ensure Power BI Desktop (May 2023 or newer) is installed with PBIP preview enabled.
2. Extract (unzip) this ENTIRE archive to a local folder.
3. Double-click '{filename_base}.pbip' to launch the 3-page Executive Report.
4. On first load, update CsvFilePath in Power Query Editor if prompted to point to:
   {filename_base}.Dataset\\dataset.csv
5. All {len(measures)} formatted DAX measures are organized in Display Folders inside the 'Dataset' table.
6. To export as a single file, choose File > Save As > Power BI file (.pbix).

INCLUDED HANDOVER FILES:
- {filename_base}.pbip                     (Power BI Project launcher)
- {filename_base}.Report/report.json       (3-page executive layout + custom theme)
- {filename_base}.Dataset/model.bim        (TMSL v1567 semantic model + {len(measures)} DAX measures)
- Executive_Analyst_Dossier.md             (Full 15-section Boardroom Markdown Dossier)
- DAX_Measures_Library.dax                 (Commented copy-paste DAX library by folder)
"""
        z.writestr("PowerBI_Setup_Guide.txt", readme_text)

    buffer.seek(0)
    return buffer
