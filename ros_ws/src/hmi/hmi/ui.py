"""HMI node: browser dashboard served via FastAPI + WebSocket.

This module embeds a ROS2 `hmi` node inside a FastAPI application and
streams a small structured `state` object to connected WebSocket clients.

Notes:
- Port numbers are TCP port values (unit: number).
- ROS subscription queue sizes are counts (unit: number of messages).
"""

import asyncio
import json
import threading
from pathlib import Path
from typing import Any, Dict, Set

import rclpy
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import Bool, Int32, String

HMI_HOST: str = "0.0.0.0"
# TCP port used by the HTTP/WebSocket server (unit: TCP port number)
HMI_PORT: int = 8082

# ROS topic names
TOPIC_ESTOP: str = "/emergency_stop_status"
TOPIC_DOOR: str = "/door_closed_status"
TOPIC_STACK_LIGHT: str = "/stack_light_status"
TOPIC_PICK_REQUEST: str = "/pick_request"
TOPIC_PICK_RESPONSE: str = "/pick_response"

# Subscription queue size for ROS subscriptions (unit: messages)
SUB_QUEUE_SIZE: int = 10

_HTML_FILE = Path(__file__).parent / "index.html"


class _ConnectionManager:
    """Manage active WebSocket client connections and broadcasting.

    The manager stores active `WebSocket` connections in a set and provides
    utilities to accept new connections, remove them, and broadcast text
    messages to all connected clients.
    """

    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        """Accept and register a new WebSocket client."""
        await ws.accept()
        self._connections.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        """Remove a WebSocket client from the active set."""
        self._connections.discard(ws)

    async def broadcast(self, message: str) -> None:
        """Send `message` to all connected clients (text frames).

        Any failing connection is removed from the active set. `message`
        should be a JSON-serialised string.
        """
        for ws in list(self._connections):
            try:
                await ws.send_text(message)
            except Exception:
                self._connections.discard(ws)


class HMINode(Node):
    """ROS2 `hmi` node that subscribes to ROS topics and streams JSON state.

    The node keeps a small dictionary `_state` representing the latest values
    observed on the configured topics and uses the provided connection
    manager to broadcast updates to connected WebSocket clients.
    """

    def __init__(self, manager: _ConnectionManager, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__("hmi")
        self._manager: _ConnectionManager = manager
        self._loop: asyncio.AbstractEventLoop = loop
        self._state: Dict[str, Any] = {
            "emergency_stop": None,
            "door_closed": None,
            "stack_light": None,
            "pick_request": None,
            "pick_response": None,
        }

        # Subscribe to ROS topics using constants and typed queue size
        self.create_subscription(Bool, TOPIC_ESTOP, self._on_estop, SUB_QUEUE_SIZE)
        self.create_subscription(Bool, TOPIC_DOOR, self._on_door, SUB_QUEUE_SIZE)
        self.create_subscription(Int32, TOPIC_STACK_LIGHT, self._on_stack_light, SUB_QUEUE_SIZE)
        self.create_subscription(String, TOPIC_PICK_REQUEST, self._on_pick_request, SUB_QUEUE_SIZE)
        self.create_subscription(String, TOPIC_PICK_RESPONSE, self._on_pick_response, SUB_QUEUE_SIZE)

        self.get_logger().info(f"HMI node initialized — dashboard at http://localhost:{HMI_PORT}")

    def get_state(self) -> Dict[str, Any]:
        """Return a shallow copy of the current HMI state."""
        return dict(self._state)

    def _push(self) -> None:
        """Serialize `_state` to JSON and broadcast it on the event loop."""
        asyncio.run_coroutine_threadsafe(
            self._manager.broadcast(json.dumps(self._state)), self._loop
        )

    def _on_estop(self, msg: Bool) -> None:
        """Callback for emergency stop status (unit: boolean)."""
        self._state["emergency_stop"] = bool(msg.data)
        self._push()

    def _on_door(self, msg: Bool) -> None:
        """Callback for door closed status (unit: boolean)."""
        self._state["door_closed"] = bool(msg.data)
        self._push()

    def _on_stack_light(self, msg: Int32) -> None:
        """Callback for stack light status (unit: integer code)."""
        self._state["stack_light"] = int(msg.data)
        self._push()

    def _on_pick_request(self, msg: String) -> None:
        """Callback for pick request JSON payload (unit: JSON object)."""
        try:
            self._state["pick_request"] = json.loads(str(msg.data))
        except json.JSONDecodeError:
            # leave previous value untouched on parse error
            pass
        self._push()

    def _on_pick_response(self, msg: String) -> None:
        """Callback for pick response JSON payload (unit: JSON object)."""
        try:
            self._state["pick_response"] = json.loads(str(msg.data))
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
