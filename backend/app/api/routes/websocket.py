from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.storage.redis_cache import subscribe_to_progress

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/progress/{review_id}")
async def progress_websocket(websocket: WebSocket, review_id: str):
    await websocket.accept()
    try:
        async for message in subscribe_to_progress(review_id):
            await websocket.send_json(message)
            if message.get("stage") == "synthesis" and message.get("status") == "complete":
                break
    except WebSocketDisconnect:
        pass
