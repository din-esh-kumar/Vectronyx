# backend/app/modules/data_analyst/routes.py
import json
import logging
import re
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import StreamingResponse
from typing import Optional

from app.core.config import settings
from app.modules.data_analyst.schemas import (
    DatasetIntakeResponse,
    DatasetProfile,
    DashboardPlan,
)
from app.modules.data_analyst.problem_definer import verify_and_define_dataset
from app.modules.data_analyst.analyst import (
    profile_dataset,
    generate_complete_dashboard,
    generate_complete_dashboard_stream,
    generate_dossier_markdown,
)
from app.modules.data_analyst.export_powerbi import generate_powerbi_pbip_archive
from app.modules.data_analyst.export_tableau import generate_tableau_twbx_archive

logger = logging.getLogger("vectronyx.analyst_router")
router = APIRouter(tags=["Data Analyst & Dashboard Generator"])

MAX_UPLOAD_BYTES = max(1, settings.MAX_CSV_UPLOAD_MB) * 1024 * 1024


async def _read_upload_bounded(file: UploadFile) -> str:
    chunks: list[bytes] = []
    total = 0
    chunk_size = 1024 * 1024
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Uploaded file exceeds the {settings.MAX_CSV_UPLOAD_MB} MB size limit.",
            )
        chunks.append(chunk)
    return b"".join(chunks).decode("utf-8", errors="replace")


def _validate_raw_csv_size(raw_csv: str) -> str:
    if len(raw_csv.encode("utf-8", errors="ignore")) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"CSV payload exceeds the {settings.MAX_CSV_UPLOAD_MB} MB size limit.",
        )
    return raw_csv


def _sanitize_filename_base(dataset_name: Optional[str], default: str = "Vectronyx_Dashboard") -> str:
    if not dataset_name:
        return default
    stem = re.sub(r"\.(csv|tsv|txt)$", "", dataset_name.strip(), flags=re.IGNORECASE)
    sanitized = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_")
    return sanitized or default

@router.post("/profile", response_model=DatasetProfile)
async def upload_and_profile_dataset(file: UploadFile = File(...)):
    """
    Ingests an uploaded CSV file, profiles data types, distribution quantiles,
    and runs IsolationForest anomaly detection.
    """
    try:
        csv_text = await _read_upload_bounded(file)
        _, profile, _ = profile_dataset(csv_text)
        return profile
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error profiling dataset: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Failed to profile CSV dataset.")


@router.post("/verify-and-define", response_model=DatasetIntakeResponse)
async def verify_and_define_endpoint(
    file: Optional[UploadFile] = File(None),
    raw_csv: Optional[str] = Form(None),
    dataset_name: Optional[str] = Form("dataset.csv"),
    user_goal: Optional[str] = Form(""),
):
    """
    Stage 1: Verify dataset readiness ('perfect', 'good_with_warnings', or 'unusable').
    Stage 2: If good, define the core question, business goal, decision needed,
             and align key metrics with stakeholders based on the received dataset.
    """
    try:
        csv_text = ""
        if file:
            csv_text = await _read_upload_bounded(file)
            dataset_name = file.filename or dataset_name
        elif raw_csv is not None:
            csv_text = _validate_raw_csv_size(raw_csv)
        else:
            raise HTTPException(status_code=400, detail="Either 'file' or 'raw_csv' must be provided.")

        return await verify_and_define_dataset(
            csv_text=csv_text,
            dataset_name=dataset_name or "dataset.csv",
            user_goal=user_goal or "",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying dataset and defining problem: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Failed to verify dataset.")


@router.post("/generate-dashboard", response_model=DashboardPlan)
async def generate_dashboard_endpoint(
    file: Optional[UploadFile] = File(None),
    prompt: str = Form(...),
    dataset_name: Optional[str] = Form("dataset.csv"),
    raw_csv: Optional[str] = Form(None),
    refinement_iterations: int = Form(3),
    target_quality_score: float = Form(92.0),
):
    """
    Generates an executive dashboard plan refined across N Principal Peer-Review
    iterations (max 16K tokens per pass) with KPIs, visual series aggregations,
    IsolationForest anomaly scores, enterprise DAX measures, and 3-page Power BI blueprint.
    """
    try:
        csv_text = ""
        if file:
            csv_text = await _read_upload_bounded(file)
            dataset_name = file.filename or dataset_name
        elif raw_csv:
            csv_text = _validate_raw_csv_size(raw_csv)
        else:
            raise HTTPException(status_code=400, detail="Either 'file' or 'raw_csv' must be provided.")

        clamped_iters = max(1, min(8, refinement_iterations))
        clamped_target = max(75.0, min(99.0, target_quality_score))
        dashboard_plan = await generate_complete_dashboard(
            csv_text=csv_text,
            user_prompt=prompt,
            dataset_name=dataset_name or "dataset.csv",
            refinement_iterations=clamped_iters,
            target_quality_score=clamped_target,
        )
        return dashboard_plan
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating dashboard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate dashboard.")


@router.post("/generate-dashboard/stream")
async def generate_dashboard_stream_endpoint(
    file: Optional[UploadFile] = File(None),
    prompt: str = Form(...),
    dataset_name: Optional[str] = Form("dataset.csv"),
    raw_csv: Optional[str] = Form(None),
    refinement_iterations: int = Form(3),
    target_quality_score: float = Form(92.0),
):
    """
    Server-Sent Events (SSE) telemetry stream for N-iteration Principal Analyst
    dashboard synthesis and 3-page Executive Power BI architecture generation.
    """
    try:
        csv_text = ""
        if file:
            csv_text = await _read_upload_bounded(file)
            dataset_name = file.filename or dataset_name
        elif raw_csv:
            csv_text = _validate_raw_csv_size(raw_csv)
        else:
            raise HTTPException(status_code=400, detail="Either 'file' or 'raw_csv' must be provided.")

        clamped_iters = max(1, min(8, refinement_iterations))
        clamped_target = max(75.0, min(99.0, target_quality_score))
        return StreamingResponse(
            generate_complete_dashboard_stream(
                csv_text=csv_text,
                user_prompt=prompt,
                dataset_name=dataset_name or "dataset.csv",
                refinement_iterations=clamped_iters,
                target_quality_score=clamped_target,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting dashboard stream: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to start dashboard stream.")



@router.post("/export/powerbi")
async def export_powerbi_endpoint(
    file: Optional[UploadFile] = File(None),
    raw_csv: Optional[str] = Form(None),
    plan_json: str = Form(...)
):
    """
    Exports the generated dashboard as a deployable Power BI Project (.pbip) zip package,
    including .pbip, definition.pbir, report.json visual layout, definition.pbidataset,
    model.bim schema with DAX measures, and dataset.csv.
    """
    try:
        csv_text = ""
        if file:
            csv_text = await _read_upload_bounded(file)
        elif raw_csv:
            csv_text = _validate_raw_csv_size(raw_csv)
        else:
            raise HTTPException(status_code=400, detail="CSV data required for Power BI export.")

        plan_dict = json.loads(plan_json)
        plan = DashboardPlan(**plan_dict)

        dataset_label = plan.dataset_name if plan.dataset_name and plan.dataset_name != "Dataset" else (file.filename if file else "Vectronyx_Dashboard")
        filename_base = _sanitize_filename_base(dataset_label)
        archive_buffer = generate_powerbi_pbip_archive(plan, csv_text, filename_base=filename_base)
        download_filename = f"{filename_base}_PowerBI_Dashboard.zip"

        return Response(
            content=archive_buffer.getvalue(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{download_filename}"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting Power BI package: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to export Power BI package.")


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
            csv_text = await _read_upload_bounded(file)
        elif raw_csv:
            csv_text = _validate_raw_csv_size(raw_csv)
        else:
            raise HTTPException(status_code=400, detail="CSV data required for Tableau export.")

        plan_dict = json.loads(plan_json)
        plan = DashboardPlan(**plan_dict)

        dataset_label = plan.dataset_name if plan.dataset_name and plan.dataset_name != "Dataset" else (file.filename if file else "Vectronyx_Dashboard")
        filename_base = _sanitize_filename_base(dataset_label)
        archive_buffer = generate_tableau_twbx_archive(plan, csv_text, filename_base=filename_base)
        download_filename = f"{filename_base}_Tableau_Dashboard.twbx"

        return Response(
            content=archive_buffer.getvalue(),
            media_type="application/vnd.tableau.workbook",
            headers={
                "Content-Disposition": f'attachment; filename="{download_filename}"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting Tableau package: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to export Tableau package.")


@router.post("/export/dossier")
async def export_dossier_endpoint(plan_json: str = Form(...)):
    """
    Exports the 30-Year Veteran Executive Dossier as an authoritative Markdown document (.md).
    """
    try:
        plan_dict = json.loads(plan_json)
        plan = DashboardPlan(**plan_dict)
        markdown_content = generate_dossier_markdown(plan)

        filename_base = _sanitize_filename_base(plan.dataset_name)
        filename = f"{filename_base}_Executive_Dossier.md"

        return Response(
            content=markdown_content,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting Executive Dossier: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to export Executive Dossier.")

