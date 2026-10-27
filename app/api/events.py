import asyncio
import json
from typing import Set, Dict, Any
from fastapi import APIRouter, Request
from starlette.responses import StreamingResponse

router = APIRouter(prefix="/api/events", tags=["Live Real-Time Event Stream"])

# Active SSE listener queues
_subscribers: Set[asyncio.Queue] = set()

async def broadcast_event(event_data: Dict[str, Any]):
    """Broadcast an event dictionary to all connected browser clients."""
    if not _subscribers:
        return
    payload = json.dumps(event_data)
    message = f"data: {payload}\n\n"
    # Dispatch to all listeners
    for queue in list(_subscribers):
        try:
            queue.put_nowait(message)
        except Exception:
            _subscribers.discard(queue)

@router.get("/live")
async def sse_live_stream(request: Request):
    """
    Server-Sent Events (SSE) endpoint.
    Frontend connects to EventSource('/api/events/live') to receive instant updates.
    """
    queue: asyncio.Queue = asyncio.Queue()
    _subscribers.add(queue)

    async def event_generator():
        try:
            # Send initial keepalive/handshake
            yield ": connected\n\n"
            while True:
                # Check client disconnect
                if await request.is_disconnected():
                    break
                try:
                    # Wait for next event or send heartbeat every 15s
                    message = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield message
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            _subscribers.discard(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
