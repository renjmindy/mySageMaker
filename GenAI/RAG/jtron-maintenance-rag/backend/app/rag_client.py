"""Long-lived WebSocket client to the DGX Spark RAG service.

Protocol (assumed — swap when the real contract is confirmed):

    client -> server:
        {"type": "query", "request_id": "<uuid>", "prompt": "...", "history": [...]}

    server -> client (one or many of these, all tagged with the same request_id):
        {"type": "token", "request_id": "<uuid>", "text": "..."}
        {"type": "citation", "request_id": "<uuid>",
         "source": "<doc>", "page": <int|null>, "snippet": "...", "score": <float|null>}
        {"type": "error", "request_id": "<uuid>", "message": "..."}
        {"type": "done", "request_id": "<uuid>"}

One WebSocket is shared across all users. Each in-flight request owns an asyncio.Queue
that the receiver task routes frames into by request_id.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed

from app.config import get_settings

log = logging.getLogger(__name__)

_RECONNECT_BASE_DELAY = 1.0
_RECONNECT_MAX_DELAY = 30.0
_HEARTBEAT_INTERVAL = 30.0
_READY_WAIT_TIMEOUT = 10.0  # how long a query will wait for the WS to come up
_SENTINEL_DONE: dict[str, Any] = {"type": "done"}


@dataclass
class Token:
    text: str


@dataclass
class Citation:
    source: str
    page: int | None
    snippet: str | None
    score: float | None


@dataclass
class RagError:
    message: str


Chunk = Token | Citation | RagError


class RagClient:
    def __init__(self, url: str) -> None:
        self._url = url
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._send_lock = asyncio.Lock()
        self._pending: dict[str, asyncio.Queue[dict[str, Any]]] = {}
        self._receiver_task: asyncio.Task[None] | None = None
        self._connect_task: asyncio.Task[None] | None = None
        self._ready = asyncio.Event()
        self._closing = False

    async def start(self) -> None:
        self._closing = False
        self._connect_task = asyncio.create_task(self._connect_loop(), name="rag-connect")

    async def stop(self) -> None:
        self._closing = True
        if self._ws is not None:
            await self._ws.close()
        if self._connect_task is not None:
            self._connect_task.cancel()
            try:
                await self._connect_task
            except (asyncio.CancelledError, Exception):
                pass
        for queue in self._pending.values():
            queue.put_nowait({"type": "error", "message": "client shutting down"})
            queue.put_nowait(_SENTINEL_DONE)
        self._pending.clear()

    async def query(self, prompt: str, history: list[dict[str, str]]) -> AsyncIterator[Chunk]:
        return self._iterate(prompt, history)

    async def _iterate(
        self, prompt: str, history: list[dict[str, str]]
    ) -> AsyncIterator[Chunk]:
        try:
            await asyncio.wait_for(self._ready.wait(), timeout=_READY_WAIT_TIMEOUT)
        except asyncio.TimeoutError:
            yield RagError(
                message=f"RAG service is not reachable at {self._url} "
                f"(no WebSocket connection after {int(_READY_WAIT_TIMEOUT)}s)."
            )
            return
        request_id = str(uuid.uuid4())
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._pending[request_id] = queue
        try:
            await self._send(
                {
                    "type": "query",
                    "request_id": request_id,
                    "prompt": prompt,
                    "history": history,
                }
            )
            while True:
                frame = await queue.get()
                if frame is _SENTINEL_DONE:
                    return
                kind = frame.get("type")
                if kind == "token":
                    yield Token(text=frame.get("text", ""))
                elif kind == "citation":
                    yield Citation(
                        source=frame.get("source", ""),
                        page=frame.get("page"),
                        snippet=frame.get("snippet"),
                        score=frame.get("score"),
                    )
                elif kind == "error":
                    yield RagError(message=frame.get("message", "unknown RAG error"))
                    return
                elif kind == "done":
                    return
        finally:
            self._pending.pop(request_id, None)

    async def _send(self, payload: dict[str, Any]) -> None:
        if self._ws is None:
            raise RuntimeError("RAG websocket not connected")
        data = json.dumps(payload)
        async with self._send_lock:
            await self._ws.send(data)

    async def _connect_loop(self) -> None:
        delay = _RECONNECT_BASE_DELAY
        while not self._closing:
            try:
                log.info("connecting to RAG WS %s", self._url)
                async with websockets.connect(
                    self._url,
                    ping_interval=_HEARTBEAT_INTERVAL,
                    ping_timeout=_HEARTBEAT_INTERVAL,
                    max_size=None,
                ) as ws:
                    self._ws = ws
                    self._ready.set()
                    delay = _RECONNECT_BASE_DELAY
                    await self._receive_loop(ws)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                log.warning("RAG WS disconnected: %s", exc)
            finally:
                self._ws = None
                self._ready.clear()
                self._fail_all_pending("RAG connection lost")
            if self._closing:
                break
            await asyncio.sleep(delay)
            delay = min(delay * 2, _RECONNECT_MAX_DELAY)

    async def _receive_loop(self, ws: websockets.WebSocketClientProtocol) -> None:
        try:
            async for raw in ws:
                try:
                    frame = json.loads(raw)
                except (ValueError, TypeError):
                    log.warning("RAG WS: non-JSON frame dropped")
                    continue
                request_id = frame.get("request_id")
                queue = self._pending.get(request_id) if request_id else None
                if queue is None:
                    continue
                queue.put_nowait(frame)
                if frame.get("type") in ("done", "error"):
                    queue.put_nowait(_SENTINEL_DONE)
        except ConnectionClosed:
            return

    def _fail_all_pending(self, message: str) -> None:
        for queue in self._pending.values():
            queue.put_nowait({"type": "error", "message": message})
            queue.put_nowait(_SENTINEL_DONE)


_client: RagClient | None = None


def get_rag_client() -> RagClient:
    global _client
    if _client is None:
        _client = RagClient(get_settings().dgx_rag_ws_url)
    return _client
