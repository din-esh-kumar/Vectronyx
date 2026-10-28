# backend/app/modules/research_agent/routes.py
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.modules.research_agent.schemas import ResearchStreamRequest
from app.modules.research_agent.agent import stream_research_agent

logger = logging.getLogger("vectronyx.research_routes")
router = APIRouter(tags=["Autonomous Research Agent"])

@router.post("/stream")
async def stream_research_endpoint(req: ResearchStreamRequest):
    """
    Server-Sent Events (SSE) streaming endpoint for the Autonomous ReAct Research Agent.
    Streams live thoughts, tool executions (search/scrape), incremental Groq LLM tokens,
    and the final structured research dossier.
    """
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    return StreamingResponse(
        stream_research_agent(
            query=req.query.strip(),
            depth=req.depth or "react",
            csv_data=req.csv_data
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        }
    )

@router.get("/health")
def research_health():
    return {"status": "Research Agent Engine Online", "streaming": "Server-Sent Events (SSE) Supported"}
