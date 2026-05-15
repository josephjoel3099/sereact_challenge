"""HMI node: browser dashboard served via FastAPI + WebSocket."""

import asyncio
import json
import threading
from pathlib import Path
from typing import Set

import rclpy
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import Bool, Int32, String

HMI_HOST = "0.0.0.0"
HMI_PORT = 8082

_HTML_FILE = Path(__file__).parent / "index.html"


class _ConnectionManager:
    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)

    async def broadcast(self, message: str) -> None:
        for ws in list(self._connections):
            try:
                await ws.send_text(message)
            except Exception:
                self._connections.discard(ws)


class HMINode(Node):
    """ROS2 node that subscribes to cell topics and streams state to WebSocket clients."""

    def __init__(self, manager: _ConnectionManager, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__("hmi")
        self._manager = manager
        self._loop = loop
        self._state: dict = {
            "emergency_stop": None,
            "door_closed": None,
            "stack_light": None,
            "pick_request": None,
            "pick_response": None,
        }
        self.create_subscription(Bool, "/emergency_stop_status", self._on_estop, 10)
        self.create_subscription(Bool, "/door_closed_status", self._on_door, 10)
        self.create_subscription(Int32, "/stack_light_status", self._on_stack_light, 10)
        self.create_subscription(String, "/pick_request", self._on_pick_request, 10)
        self.create_subscription(String, "/pick_response", self._on_pick_response, 10)
        self.get_logger().info(f"HMI node initialized — dashboard at http://localhost:{HMI_PORT}")

    def get_state(self) -> dict:
        return dict(self._state)

    def _push(self) -> None:
        asyncio.run_coroutine_threadsafe(
            self._manager.broadcast(json.dumps(self._state)), self._loop
        )

    def _on_estop(self, msg: Bool) -> None:
        self._state["emergency_stop"] = msg.data
        self._push()

    def _on_door(self, msg: Bool) -> None:
        self._state["door_closed"] = msg.data
        self._push()

    def _on_stack_light(self, msg: Int32) -> None:
        self._state["stack_light"] = msg.data
        self._push()

    def _on_pick_request(self, msg: String) -> None:
        try:
            self._state["pick_request"] = json.loads(msg.data)
        except json.JSONDecodeError:
            pass
        self._push()

    def _on_pick_response(self, msg: String) -> None:
        try:
            self._state["pick_response"] = json.loads(msg.data)
        except json.JSONDecodeError:
            pass
        self._push()


_manager = _ConnectionManager()
app = FastAPI()


@app.on_event("startup")
async def _startup() -> None:
    loop = asyncio.get_running_loop()
    node = HMINode(_manager, loop)
    app.state.node = node

    executor = MultiThreadedExecutor()
    executor.add_node(node)
    app.state.executor = executor

    ros_thread = threading.Thread(target=executor.spin, daemon=True)
    ros_thread.start()


@app.on_event("shutdown")
async def _shutdown() -> None:
    executor: MultiThreadedExecutor = app.state.executor
    node: HMINode = app.state.node
    executor.remove_node(node)
    node.destroy_node()
    executor.shutdown()


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return _HTML_FILE.read_text()


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await _manager.connect(ws)
    node: HMINode = app.state.node
    await ws.send_text(json.dumps(node.get_state()))
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        _manager.disconnect(ws)


def main(args: list[str] | None = None) -> None:
    """Entry point: start the HMI HTTP/WebSocket server with embedded ROS2 node."""
    rclpy.init(args=args)
    try:
        uvicorn.run(app, host=HMI_HOST, port=HMI_PORT, log_level="warning")
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
