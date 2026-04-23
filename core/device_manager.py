"""
Device Manager — tracks all connected WebSocket clients (phone, tablet, etc.)
and allows broadcasting messages to all or specific devices.
"""
import asyncio
import json
from typing import Any
from fastapi import WebSocket


class DeviceManager:
    def __init__(self):
        self._connections: dict[str, WebSocket] = {}

    async def connect(self, device_id: str, websocket: WebSocket):
        await websocket.accept()
        self._connections[device_id] = websocket
        print(f"[Hub] Device connected: {device_id} (total: {len(self._connections)})")

    def disconnect(self, device_id: str):
        self._connections.pop(device_id, None)
        print(f"[Hub] Device disconnected: {device_id}")

    async def send(self, device_id: str, payload: dict):
        ws = self._connections.get(device_id)
        if ws:
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                self.disconnect(device_id)

    async def broadcast(self, payload: dict, exclude: str = ""):
        data = json.dumps(payload)
        dead = []
        for device_id, ws in self._connections.items():
            if device_id == exclude:
                continue
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(device_id)
        for d in dead:
            self.disconnect(d)

    def active_device_ids(self) -> list[str]:
        return list(self._connections.keys())


device_manager = DeviceManager()
