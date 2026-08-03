from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, payload: dict) -> None:
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_json(payload)
            except Exception:
                dead.append(connection)
        for connection in dead:
            self.disconnect(connection)


manager = ConnectionManager()


@router.websocket("/ws/alerts")
async def alerts_stream(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            # Push-only channel — the UI gets its initial snapshot via REST.
            # We still need to await something so a client disconnect is detected.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
