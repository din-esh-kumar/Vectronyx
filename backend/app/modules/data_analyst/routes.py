# backend/app/modules/data_analyst/routes.py
import json
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Response
from pydantic import BaseModel
from typing import Optional

from app.modules.data_analyst.schemas import (
    DatasetProfile,
    DashboardPlan,
    DashboardGenerateRequest,
)
from app.modules.data_analyst.analyst import (
    profile_dataset,
    generate_complete_dashboard,
    generate_dossier_markdown,
)
from app.modules.data_analyst.export_powerbi import generate_powerbi_pbip_archive
from app.modules.data_analyst.export_tableau import generate_tableau_twbx_archive

logger = logging.getLogger("vectronyx.analyst_router")
router = APIRouter(tags=["Data Analyst & Dashboard Generator"])

@router.post("/profile", response_model=DatasetProfile)
async def upload_and_profile_dataset(file: UploadFile = File(...)):
    """
    Ingests an uploaded CSV file, profiles data types, distribution quantiles,
    and runs IsolationForest anomaly detection.
    """
    try:
        content_bytes = await file.read()
        csv_text = content_bytes.decode("utf-8", errors="replace")
        _, profile, _ = profile_dataset(csv_text)
        return profile
    except Exception as e:
        logger.error(f"Error profiling dataset: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to profile CSV: {str(e)}")


@router.post("/generate-dashboard", response_model=DashboardPlan)
async def generate_dashboard_endpoint(
    file: Optional[UploadFile] = File(None),
    prompt: str = Form(...),
    dataset_name: Optional[str] = Form("dataset.csv"),
    raw_csv: Optional[str] = Form(None)
):
    """
    Generates an executive dashboard plan with KPIs, visual series aggregations,
    IsolationForest anomaly scores, DAX measures, and Tableau formulas.
    Accepts either multipart file upload or raw_csv string.
    """
    try:
        csv_text = ""
        if file:
            content_bytes = await file.read()
            csv_text = content_bytes.decode("utf-8", errors="replace")
            dataset_name = file.filename or dataset_name
        elif raw_csv:
            csv_text = raw_csv
        else:
            raise HTTPException(status_code=400, detail="Either 'file' or 'raw_csv' must be provided.")

        dashboard_plan = await generate_complete_dashboard(
            csv_text=csv_text,
            user_prompt=prompt,
            dataset_name=dataset_name or "dataset.csv"
        )
        return dashboard_plan
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating dashboard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate dashboard: {str(e)}")


@router.post("/export/powerbi")
async def export_powerbi_endpoint(
    file: Optional[UploadFile] = File(None),
    raw_csv: Optional[str] = Form(None),
    plan_json: str = Form(...)
):
    """
    Exports the generated dashboard as a deployable Power BI Project (.pbip) zip package,
    including report.json visual layout, model.bim schema with DAX measures, and dataset.csv.
    """
    try:
        csv_text = ""
        if file:
            content_bytes = await file.read()
            csv_text = content_bytes.decode("utf-8", errors="replace")
        elif raw_csv:
            csv_text = raw_csv
        else:
            raise HTTPException(status_code=400, detail="CSV data required for Power BI export.")

        plan_dict = json.loads(plan_json)
        plan = DashboardPlan(**plan_dict)

        archive_buffer = generate_powerbi_pbip_archive(plan, csv_text)
        
        return Response(
            content=archive_buffer.getvalue(),
            media_type="application/zip",
            headers={
                "Content-Disposition": 'attachment; filename="Vectronyx_PowerBI_Dashboard.zip"'
            }
        )
    except Exception as e:
        logger.error(f"Error exporting Power BI package: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export Power BI: {str(e)}")


@router.post("/export/tableau")
async def export_tableau_endpoint(
    file: Optional[UploadFile] = File(None),
    raw_csv: Optional[str] = Form(None),
    plan_json: str = Form(...)
):
    """
    Exports the generated dashboard as a packaged Tableau Workbook (.twbx)
    with XML sheets, zones, calculated fields, and embedded CSV.
    """
    try:
        csv_text = ""
        if file:
            content_bytes = await file.read()
            csv_text = content_bytes.decode("utf-8", errors="replace")
        elif raw_csv:
            csv_text = raw_csv
        else:
            raise HTTPException(status_code=400, detail="CSV data required for Tableau export.")

        plan_dict = json.loads(plan_json)
        plan = DashboardPlan(**plan_dict)

        archive_buffer = generate_tableau_twbx_archive(plan, csv_text)

        return Response(
            content=archive_buffer.getvalue(),
            media_type="application/vnd.tableau.workbook",
            headers={
                "Content-Disposition": 'attachment; filename="Vectronyx_Tableau_Dashboard.twbx"'
            }
        )
    except Exception as e:
        logger.error(f"Error exporting Tableau package: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export Tableau: {str(e)}")


@router.post("/export/dossier")
async def export_dossier_endpoint(plan_json: str = Form(...)):
    """
    Exports the 30-Year Veteran Executive Dossier as an authoritative Markdown document (.md).
    """
    try:
        plan_dict = json.loads(plan_json)
        plan = DashboardPlan(**plan_dict)
        markdown_content = generate_dossier_markdown(plan)

        filename = f"{plan.dataset_name.replace('.csv', '')}_Executive_Dossier.md"

        return Response(
            content=markdown_content,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        logger.error(f"Error exporting Executive Dossier: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export Dossier: {str(e)}")

