"""
P5-E6: WebSocket real-time event layer.

Endpoint: GET /ws/events?token=<jwt>
Broadcasts fleet events to all connected clients for a tenant.

Event envelope:
{
  "type": "location_update" | "stop_status" | "plan_generated" | "order_at_risk",
  "tenant_id": "<uuid>",
  "payload": { ... }
}
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Dict, List

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """Thread-safe enough for single-process uvicorn; use Redis pub-sub for multi-worker."""

    def __init__(self) -> None:
        self._connections: Dict[str, List[WebSocket]] = defaultdict(list)

    async def connect(self, ws: WebSocket, tenant_id: str) -> None:
        await ws.accept()
        self._connections[tenant_id].append(ws)
        logger.info("WS connect: tenant=%s  total=%d", tenant_id, len(self._connections[tenant_id]))

    def disconnect(self, ws: WebSocket, tenant_id: str) -> None:
        conns = self._connections.get(tenant_id, [])
        if ws in conns:
            conns.remove(ws)
        logger.info("WS disconnect: tenant=%s  remaining=%d", tenant_id, len(conns))

    async def broadcast(self, tenant_id: str, event: dict) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._connections.get(tenant_id, [])):
            try:
                await ws.send_text(json.dumps(event))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, tenant_id)

    async def broadcast_all(self, event: dict) -> None:
        for tenant_id in list(self._connections.keys()):
            await self.broadcast(tenant_id, event)


manager = ConnectionManager()


@router.websocket("/ws/events")
async def ws_events(
    ws: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    """
    WebSocket endpoint for real-time fleet events.
    Authenticate by passing the JWT as ?token=<jwt>.
    """
    from app.core.security import decode_token

    try:
        payload = decode_token(token)
        tenant_id: str = str(payload.get("tenant_id", ""))
        if not tenant_id or tenant_id == "None":
            await ws.close(code=4001, reason="No tenant")
            return
    except JWTError:
        await ws.close(code=4001, reason="Invalid token")
        return

    await manager.connect(ws, tenant_id)
    try:
        while True:
            msg = await ws.receive_text()
            if msg == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(ws, tenant_id)
