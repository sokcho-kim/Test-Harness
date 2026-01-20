"""WebSocket 실시간 업데이트"""

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    """WebSocket 연결 관리"""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, test_run_id: str):
        await websocket.accept()
        if test_run_id not in self.active_connections:
            self.active_connections[test_run_id] = []
        self.active_connections[test_run_id].append(websocket)

    def disconnect(self, websocket: WebSocket, test_run_id: str):
        if test_run_id in self.active_connections:
            self.active_connections[test_run_id].remove(websocket)
            if not self.active_connections[test_run_id]:
                del self.active_connections[test_run_id]

    async def broadcast(self, test_run_id: str, message: dict):
        if test_run_id in self.active_connections:
            for connection in self.active_connections[test_run_id]:
                await connection.send_json(message)


manager = ConnectionManager()


@router.websocket("/ws/tests/{test_run_id}/progress")
async def test_progress(websocket: WebSocket, test_run_id: str):
    """테스트 실행 진행률 스트리밍"""
    await manager.connect(websocket, test_run_id)
    try:
        while True:
            # 클라이언트로부터 메시지 수신 대기
            data = await websocket.receive_text()
            # 필요시 처리
    except WebSocketDisconnect:
        manager.disconnect(websocket, test_run_id)
