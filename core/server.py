"""
JARVIS WebSocket Hub — FastAPI server on port 7799.
All external devices (phone, tablet, etc.) connect here.
The PC voice loop also routes through the same brain.
"""
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from core.brain import think
from core.device_manager import device_manager
from core import memory as mem

app = FastAPI(title="JARVIS Hub", version="1.0")


@app.on_event("startup")
async def startup():
    await mem.init_db()
    print("[Server] JARVIS Hub started on port 7799")


@app.on_event("shutdown")
async def shutdown():
    await mem.close_db()


# ─── REST endpoints ───────────────────────────────────────────────────────────

@app.get("/status")
async def status():
    devices = device_manager.active_device_ids()
    return {"status": "online", "connected_devices": devices}


@app.get("/memories")
async def list_memories():
    return await mem.get_memories()


# ─── WebSocket endpoint ───────────────────────────────────────────────────────

@app.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: str):
    await device_manager.connect(device_id, websocket)
    await mem.upsert_device(device_id, "mobile", device_id)

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            user_text = data.get("text", "")

            if not user_text:
                continue

            print(f"[Hub] [{device_id}] > {user_text}")
            reply = await think(user_text, device_id=device_id)
            print(f"[Hub] [{device_id}] < {reply}")

            await device_manager.send(device_id, {"type": "response", "text": reply})

    except WebSocketDisconnect:
        device_manager.disconnect(device_id)
    except Exception as e:
        print(f"[Hub] Error for {device_id}: {e}")
        device_manager.disconnect(device_id)
