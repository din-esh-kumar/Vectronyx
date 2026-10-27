# backend/tests/test_sse_streaming.py
import pytest
import httpx
from app.main import app

@pytest.mark.asyncio
async def test_research_health():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/research/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("streaming") == "Server-Sent Events (SSE) Supported"


@pytest.mark.asyncio
async def test_research_stream_empty_query():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/research/stream", json={"query": "   "})
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_research_sse_event_stream():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"query": "pgvector vs pinecone benchmark", "depth": "quick"}
        async with client.stream("POST", "/api/research/stream", json=payload) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")

            events = []
            async for line in resp.aiter_lines():
                if line.startswith("event:"):
                    events.append(line.replace("event:", "").strip())
                    if len(events) >= 5:
                        break

            assert len(events) >= 3
            assert "status" in events
            assert "thought" in events


@pytest.mark.asyncio
async def test_analyst_sse_telemetry_stream():
    transport = httpx.ASGITransport(app=app)
    csv_sample = "id,region,revenue,units\n1,EMEA,4500,20\n2,APAC,1200,8\n3,AMER,8900,42"
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        form_data = {
            "prompt": "Evaluate regional revenue distributions",
            "dataset_name": "regional_metrics.csv",
            "raw_csv": csv_sample,
        }
        async with client.stream("POST", "/api/analyst/generate-dashboard/stream", data=form_data) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")

            received_events = []
            async for line in resp.aiter_lines():
                if line.startswith("event:"):
                    received_events.append(line.replace("event:", "").strip())

            assert "status" in received_events
            assert "complete" in received_events
