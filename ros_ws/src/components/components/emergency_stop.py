import threading

from rclpy.node import Node
from std_msgs.msg import Bool
from std_srvs.srv import Trigger

NODE_NAME = "emergency_stop"
TOPIC_EMERGENCY_STOP_STATUS = "emergency_stop_status"
SERVICE_PRESS_EMERGENCY_STOP = "press_emergency_stop"
SERVICE_RELEASE_EMERGENCY_STOP = "release_emergency_stop"
QUEUE_SIZE = 10
EMERGENCY_STOP_STATUS_PUBLISH_RATE = 10  # Hz
INITIAL_STATE_ACTIVE = True


class EmergencyStop(Node):
    """ROS2 node that publishes e-stop status and exposes a toggle service."""

    def __init__(self) -> None:
        super().__init__(NODE_NAME)

        # Lock to protect shared state from concurrent access
        self._state_lock = threading.Lock()

        # Initialized as emergency stop active
        self.emergency_stop_status: bool = INITIAL_STATE_ACTIVE
        self.emergency_stop_msg: Bool = Bool()

        self.init_publishers()
        self.init_services()

        self.create_timer(
            1.0 / EMERGENCY_STOP_STATUS_PUBLISH_RATE, self.publish_emergency_stop_status
        )

        self.get_logger().info("Emergency stop node initialized")

    def init_publishers(self) -> None:
        """Create the emergency stop status publisher."""
        self.emergency_stop_publisher = self.create_publisher(
            Bool, TOPIC_EMERGENCY_STOP_STATUS, QUEUE_SIZE
        )

    def init_services(self) -> None:
        """Register the service for toggling the emergency stop."""
        self.create_service(Trigger, SERVICE_PRESS_EMERGENCY_STOP, self.press_emergency_stop)
        self.create_service(Trigger, SERVICE_RELEASE_EMERGENCY_STOP, self.release_emergency_stop)

    def press_emergency_stop(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        """Press the e-stop state and acknowledge the request."""
        with self._state_lock:
            self.emergency_stop_status = True
            self.emergency_stop_msg.data = self.emergency_stop_status
            status = self.emergency_stop_status

        response.success = True
        response.message = f"Emergency stop status: {status}"

        return response

    def release_emergency_stop(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        """Release the e-stop state and acknowledge the request."""
        with self._state_lock:
            self.emergency_stop_status = False
            self.emergency_stop_msg.data = self.emergency_stop_status
            status = self.emergency_stop_status

        response.success = True
        response.message = f"Emergency stop status: {status}"

        return response

    def publish_emergency_stop_status(self) -> None:
        """Publish the current e-stop status on the timer callback."""
        self.emergency_stop_msg.data = self.emergency_stop_status
        self.emergency_stop_publisher.publish(self.emergency_stop_msg)


def main(args: list[str] | None = None) -> None:
    """Entry point: spin the EmergencyStop node with a single-threaded executor."""
    import rclpy
    from rclpy.executors import SingleThreadedExecutor

    rclpy.init(args=args)
    node = EmergencyStop()

    # Avoids race conditions
    executor = SingleThreadedExecutor()
    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.remove_node(node)
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
