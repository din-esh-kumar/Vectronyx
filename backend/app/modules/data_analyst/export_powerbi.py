# backend/app/modules/data_analyst/export_powerbi.py
import io
import json
import zipfile
from typing import Dict, Any
from app.modules.data_analyst.schemas import DashboardPlan

def generate_powerbi_pbip_archive(plan: DashboardPlan, csv_content: str, filename_base: str = "Vectronyx_Dashboard") -> io.BytesIO:
    """
    Generates a production-grade Power BI Project (.pbip) zip package
    containing report.json, model.bim (TMDL/BIM schema), dataset.csv,
    and a DAX & Power Query setup manual.
    """
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        # 1. Root .pbip descriptor
        pbip_meta = {
            "version": "1.0",
            "artifacts": [
                {"report": {"path": f"{filename_base}.Report"}},
                {"dataset": {"path": f"{filename_base}.Dataset"}}
            ]
        }
        z.writestr(f"{filename_base}.pbip", json.dumps(pbip_meta, indent=2))

        # 2. Report visual layout (report.json)
        # Power BI visual layout definition
        visual_containers = []
        x_offset = 20
        y_offset = 20
        
        # Add KPI cards
        for i, kpi in enumerate(plan.kpis):
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
                        "projections": {"Fields": [{"queryRef": f"Measures.{kpi.title}"}]},
                        "visualContainerObjects": {
                            "title": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}, "text": {"expr": {"Literal": {"Value": f"'{kpi.title}'"}}}}}]
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
            
            pb_visual_type = "clusteredColumnChart"
            if vis.chart_type == "line":
                pb_visual_type = "lineChart"
            elif vis.chart_type == "area":
                pb_visual_type = "areaChart"
            elif vis.chart_type == "pie":
                pb_visual_type = "donutChart"
            elif vis.chart_type == "scatter":
                pb_visual_type = "scatterChart"

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
                            "title": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}, "text": {"expr": {"Literal": {"Value": f"'{vis.title}'"}}}}}]
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

        # 3. Dataset BIM Schema (Tabular Model Definition)
        measures = []
        for kpi in plan.kpis:
            measures.append({
                "name": kpi.title,
                "expression": kpi.formula_dax,
                "description": kpi.rationale
            })

        model_bim = {
            "name": "DatasetModel",
            "compatibilityLevel": 1550,
            "model": {
                "culture": "en-US",
                "dataAccessOptions": {"legacyRedirectsEnabled": True, "fastCombine": True},
                "defaultPowerBIDataSourceVersion": "powerBI_V3",
                "tables": [
                    {
                        "name": "Dataset",
                        "description": f"Imported table for {plan.dataset_name}",
                        "measures": measures
                    }
                ]
            }
        }
        z.writestr(f"{filename_base}.Dataset/model.bim", json.dumps(model_bim, indent=2))

        # 4. Include the raw dataset CSV
        z.writestr(f"{filename_base}.Dataset/dataset.csv", csv_content)

        # 5. Power BI Readme & Formula Quick-Copy
        readme_text = f"""========================================================================
VECTRONYX AI WORKBENCH — POWER BI PROJECT EXPORT (.pbip)
========================================================================
Dashboard: {plan.title}
Dataset:   {plan.dataset_name}

HOW TO OPEN:
1. Ensure you have Power BI Desktop (May 2023 or newer) installed.
2. Unzip this package.
3. Double click on '{filename_base}.pbip' to open the project directly in Power BI Desktop!

------------------------------------------------------------------------
DAX MEASURES (READY TO COPY & PASTE):
------------------------------------------------------------------------
"""
        for kpi in plan.kpis:
            readme_text += f"\n-- {kpi.title} ({kpi.rationale})\n{kpi.formula_dax}\n"

        if plan.dax_script:
            readme_text += f"\n-- Consolidated Script:\n{plan.dax_script}\n"

        m_code_content = plan.powerquery_m if plan.powerquery_m else (
            "-- Standard CSV Ingestion\n"
            "let\n"
            "    Source = Csv.Document(File.Contents(\"dataset.csv\"), [Delimiter=\",\", Encoding=65001]),\n"
            "    #\"Promoted Headers\" = Table.PromoteHeaders(Source)\n"
            "in\n"
            "    #\"Promoted Headers\""
        )

        readme_text += f"""
------------------------------------------------------------------------
POWER QUERY (M) ETL TRANSFORMATION:
------------------------------------------------------------------------
{m_code_content}
"""
        z.writestr("PowerBI_Setup_Guide.txt", readme_text)

    buffer.seek(0)
    return buffer
