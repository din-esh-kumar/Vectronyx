# backend/app/core/sse.py
"""
Server-Sent Events (SSE) serialization helpers for real-time telemetry and token streaming.
"""
import json
from typing import Any

def sse_event(event: str, data: Any) -> str:
    """
    Encodes an event and payload into standard W3C SSE format:
    event: <event_name>\\ndata: <json_or_text>\\n\\n
    """
    if isinstance(data, (dict, list)):
        payload = json.dumps(data, ensure_ascii=False)
    else:
        payload = str(data)
    
    # SSE specifications require prefixing each line of multiline data with 'data: '
    lines = payload.split("\n")
    data_lines = "\n".join(f"data: {line}" for line in lines)
    return f"event: {event}\n{data_lines}\n\n"
