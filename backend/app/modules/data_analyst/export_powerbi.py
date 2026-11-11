# backend/app/modules/data_analyst/export_powerbi.py
import csv
import io
import json
import zipfile
from typing import Dict, Any, List
from app.modules.data_analyst.schemas import DashboardPlan


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


def _infer_csv_columns_and_types(csv_content: str) -> List[Dict[str, str]]:
    """
    Parses the CSV header and sample rows to emit typed column definitions
    for the Dataset table in model.bim.
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
    for _, row in zip(range(50), reader):
        sample_rows.append(row)

    seen: Dict[str, int] = {}
    columns: List[Dict[str, str]] = []
    for idx, raw_name in enumerate(headers):
        col_name = raw_name.strip() or f"Column_{idx + 1}"
        count = seen.get(col_name, 0)
        seen[col_name] = count + 1
        if count > 0:
            col_name = f"{col_name}_{count + 1}"

        values = [r[idx].strip() for r in sample_rows if idx < len(r) and r[idx].strip() != ""]
        data_type = "string"
        if values:
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
                try:
                    int(val)
                except ValueError:
                    all_int = False
                try:
                    float(val)
                except ValueError:
                    all_float = False
                    break
            if all_int:
                data_type = "int64"
            elif all_float:
                data_type = "double"

        columns.append({
            "name": col_name,
            "dataType": data_type,
            "sourceColumn": col_name,
        })

    return columns


def generate_powerbi_pbip_archive(plan: DashboardPlan, csv_content: str, filename_base: str = "Vectronyx_Dashboard") -> io.BytesIO:
    """
    Generates a production-grade Power BI Project (.pbip) zip package
    containing .pbip, definition.pbir, report.json, definition.pbidataset,
    model.bim (TMSL schema with columns, M partition, and DAX measures),
    dataset.csv, and a DAX & Power Query setup manual.
    """
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        # 1. Root .pbip descriptor
        pbip_meta = {
            "version": "1.0",
            "artifacts": [
                {"report": {"path": f"{filename_base}.Report"}},
            ],
            "settings": {
                "enableAutoRecovery": True,
            },
        }
        z.writestr(f"{filename_base}.pbip", json.dumps(pbip_meta, indent=2))

        # 2. Report definition descriptor (PBIR-Legacy pointer to local .Dataset)
        pbir_meta = {
            "version": "1.0",
            "datasetReference": {
                "byPath": {
                    "path": f"../{filename_base}.Dataset",
                },
                "byConnection": None,
            },
        }
        z.writestr(f"{filename_base}.Report/definition.pbir", json.dumps(pbir_meta, indent=2))

        # 3. Report visual layout (report.json)
        # Power BI visual layout definition
        visual_containers = []
        
        # Add KPI cards
        for i, kpi in enumerate(plan.kpis):
            safe_kpi_title = kpi.title.replace("'", "''")
            visual_containers.append({
                "x": 20 + (i * 240),
                "y": 20,
                "width": 220,
                "height": 130,
                "config": json.dumps({
                    "name": f"kpi_card_{i}",
                    "layouts": [{"id": 0, "position": {"x": 20 + (i * 240), "y": 20, "width": 220, "height": 130}}],
                    "singleVisual": {
                        "visualType": "card",
                        "projections": {"Fields": [{"queryRef": f"Dataset.{kpi.title}"}]},
                        "visualContainerObjects": {
                            "title": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}, "text": {"expr": {"Literal": {"Value": f"'{safe_kpi_title}'"}}}}}]
                        }
                    }
                })
            })

        # Add Visuals
        chart_y = 170
        for i, vis in enumerate(plan.visuals):
            col_idx = i % 2
            row_idx = i // 2
            vx = 20 + (col_idx * 620)
            vy = chart_y + (row_idx * 340)

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

            safe_vis_title = vis.title.replace("'", "''")
            visual_containers.append({
                "x": vx,
                "y": vy,
                "width": 600,
                "height": 320,
                "config": json.dumps({
                    "name": f"visual_{vis.id}",
                    "singleVisual": {
                        "visualType": pb_visual_type,
                        "projections": {
                            "Category": [{"queryRef": f"Dataset.{vis.x_axis}"}],
                            "Y": [{"queryRef": f"Dataset.{vis.y_axis}"}]
                        },
                        "visualContainerObjects": {
                            "title": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}, "text": {"expr": {"Literal": {"Value": f"'{safe_vis_title}'"}}}}}]
                        }
                    }
                })
            })

        report_json = {
            "config": json.dumps({
                "version": "5.50",
                "themeCollection": {"baseTheme": {"name": "CY24SU02", "version": "5.50", "type": 2}}
            }),
            "layoutOptimization": 0,
            "sections": [
                {
                    "name": "ReportSection1",
                    "displayName": plan.title,
                    "width": 1280,
                    "height": max(720, chart_y + ((len(plan.visuals) + 1) // 2) * 360 + 50),
                    "visualContainers": visual_containers
                }
            ]
        }
        z.writestr(f"{filename_base}.Report/report.json", json.dumps(report_json, indent=2))

        # 4. Dataset descriptor & BIM Schema (Tabular Model Definition)
        pbidataset_meta = {
            "version": "1.0",
            "settings": {},
        }
        z.writestr(f"{filename_base}.Dataset/definition.pbidataset", json.dumps(pbidataset_meta, indent=2))

        m_code_content = plan.powerquery_m if plan.powerquery_m else (
            "let\n"
            "    Source = Csv.Document(File.Contents(\"dataset.csv\"), [Delimiter=\",\", Encoding=65001]),\n"
            "    #\"Promoted Headers\" = Table.PromoteHeaders(Source, [PromoteAllScalars=true])\n"
            "in\n"
            "    #\"Promoted Headers\""
        )

        columns = _infer_csv_columns_and_types(csv_content)
        measures = []
        for kpi in plan.kpis:
            measures.append({
                "name": kpi.title,
                "expression": _extract_dax_expression(kpi.formula_dax),
                "description": kpi.rationale
            })

        dataset_table: Dict[str, Any] = {
            "name": "Dataset",
            "description": f"Imported table for {plan.dataset_name}",
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
            "name": "DatasetModel",
            "compatibilityLevel": 1550,
            "model": {
                "culture": "en-US",
                "dataAccessOptions": {"legacyRedirectsEnabled": True, "fastCombine": True},
                "defaultPowerBIDataSourceVersion": "powerBI_V3",
                "tables": [dataset_table]
            }
        }
        z.writestr(f"{filename_base}.Dataset/model.bim", json.dumps(model_bim, indent=2))

        # 5. Include the raw dataset CSV
        z.writestr(f"{filename_base}.Dataset/dataset.csv", csv_content)

        # 6. Power BI Readme & Formula Quick-Copy
        readme_text = f"""========================================================================
VECTRONYX AI WORKBENCH — POWER BI PROJECT EXPORT (.pbip)
========================================================================
Dashboard: {plan.title}
Dataset:   {plan.dataset_name}

HOW TO OPEN:
1. Ensure you have Power BI Desktop (May 2023 or newer) installed.
2. Extract (unzip) this entire package into a folder.
3. Double click on '{filename_base}.pbip' to open the project in Power BI Desktop.
4. (Optional) To save as a single .pbix file, choose File > Save As > Power BI file (.pbix).

------------------------------------------------------------------------
DAX MEASURES (READY TO COPY & PASTE):
------------------------------------------------------------------------
"""
        for kpi in plan.kpis:
            readme_text += f"\n-- {kpi.title} ({kpi.rationale})\n{kpi.formula_dax}\n"

        if plan.dax_script:
            readme_text += f"\n-- Consolidated Script:\n{plan.dax_script}\n"

        readme_text += f"""
------------------------------------------------------------------------
POWER QUERY (M) ETL TRANSFORMATION:
------------------------------------------------------------------------
{m_code_content}
"""
        z.writestr("PowerBI_Setup_Guide.txt", readme_text)

    buffer.seek(0)
    return buffer
