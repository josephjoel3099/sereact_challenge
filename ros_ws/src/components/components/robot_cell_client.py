import asyncio
import json
import threading

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi import Request as FastAPIRequest
from pydantic import BaseModel
from rclpy.node import Node
from std_msgs.msg import Int32, String
from std_srvs.srv import Trigger

from components.stack_light import StackLightState

WMS_CONFIRM_URL = "http://localhost:8081/confirmPick"
ROBOT_CELL_HOST = "0.0.0.0"
ROBOT_CELL_PORT = 8080
NODE_NAME = "robot_cell_client"
TOPIC_PICK_REQUEST = "pick_request"
TOPIC_PICK_RESPONSE = "pick_response"
QUEUE_SIZE = 10
SCANNER_SERVICE_TIMEOUT = 3.0  # seconds
SCANNER_WAIT_TIMEOUT = 5.0  # seconds


class PickRequest(BaseModel):
    pickId: int
    quantity: int


class PickConfirmation(BaseModel):
    pickId: int
    pickSuccessful: bool
    errorMessage: str | None
    itemBarcode: int


app = FastAPI()


@app.post("/pick", status_code=202)
async def receive_pick(http_request: FastAPIRequest, body: PickRequest):
    """Receive a pick request from WMS and process it asynchronously."""
    node: RobotCellClient = http_request.app.state.node
    asyncio.create_task(node.process_pick(body))
    return {"message": "Pick request received", "pickId": body.pickId}


class RobotCellClient(Node):
    """ROS2 node that receives pick requests via HTTP and confirms with a scanned barcode."""

    def __init__(self) -> None:
        super().__init__(NODE_NAME)

        self._stack_light_status: StackLightState = StackLightState.INITIALIZING

        self.init_clients()
        self.init_publishers()
        self.init_subscribers()

        self.get_logger().info("RobotCellClient node initialized")

    def init_clients(self) -> None:
        """Create service clients."""
        self._scanner_client = self.create_client(Trigger, "get_latest_barcode")

    def init_publishers(self) -> None:
        """Create publishers for pick events so the HMI can display them."""
        self._pick_request_pub = self.create_publisher(String, TOPIC_PICK_REQUEST, QUEUE_SIZE)
        self._pick_response_pub = self.create_publisher(String, TOPIC_PICK_RESPONSE, QUEUE_SIZE)

    def init_subscribers(self) -> None:
        """Create subscribers."""
        self.create_subscription(
            Int32, "/stack_light_status", self.stack_light_status_callback, 1
        )

    def get_barcode(self) -> int:
        """Call the scanner service and return the barcode. Blocks until response or timeout."""
        if not self._scanner_client.wait_for_service(timeout_sec=SCANNER_SERVICE_TIMEOUT):
            raise RuntimeError("Scanner service unavailable")

        future = self._scanner_client.call_async(Trigger.Request())
        event = threading.Event()
        future.add_done_callback(lambda _: event.set())

        if not event.wait(timeout=SCANNER_WAIT_TIMEOUT):
            raise TimeoutError("Scanner service timed out")

        result = future.result()
        if result is None:
            raise RuntimeError("Scanner service returned no result")
        return int(result.message)

    def stack_light_status_callback(self, msg: Int32) -> None:
        self._stack_light_status = StackLightState(msg.data)

    async def process_pick(self, request: PickRequest) -> None:
        """Get barcode from scanner service and send confirmation to WMS."""
        self.get_logger().info(
            f"Processing pick {request.pickId}, quantity {request.quantity}"
        )

        req_msg = String()
        req_msg.data = json.dumps({"pickId": request.pickId, "quantity": request.quantity})
        self._pick_request_pub.publish(req_msg)

        try:
            barcode = await asyncio.to_thread(self.get_barcode)
            pick_successful = (
                False
                if self._stack_light_status == StackLightState.PAUSED
                or self._stack_light_status == StackLightState.EMERGENCY
                or self._stack_light_status == StackLightState.INITIALIZING
                else True
            )
            error_message = (
                f"Robot stopped with stack light state: {self._stack_light_status.name}"
                if not pick_successful
                else None
            )
        except Exception as e:
            self.get_logger().error(f"Failed to get barcode: {e}")
            barcode = 0
            pick_successful = False
            error_message = f"Unknown error with message: {str(e)}"

        confirmation = PickConfirmation(
            pickId=request.pickId,
            pickSuccessful=pick_successful,
            errorMessage=error_message,
            itemBarcode=barcode,
        )

        res_msg = String()
        res_msg.data = json.dumps(confirmation.model_dump())
        self._pick_response_pub.publish(res_msg)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    WMS_CONFIRM_URL, json=confirmation.model_dump()
                )
                self.get_logger().info(f"Confirmation sent: {response.status_code}")
            except Exception as e:
                self.get_logger().error(f"Failed to send confirmation: {e}")


def main(args: list[str] | None = None) -> None:
    """Entry point: spin the RobotCellClient node alongside a uvicorn HTTP server."""
    import rclpy
    from rclpy.executors import MultiThreadedExecutor

    rclpy.init(args=args)
    node = RobotCellClient()
    app.state.node = node

    server = uvicorn.Server(
        uvicorn.Config(
            app, host=ROBOT_CELL_HOST, port=ROBOT_CELL_PORT, log_level="warning"
        )
    )
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    # MultiThreadedExecutor needed so ROS can process service responses
    # while uvicorn handles HTTP requests concurrently
    executor = MultiThreadedExecutor()
    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        server.should_exit = True
        executor.remove_node(node)
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
