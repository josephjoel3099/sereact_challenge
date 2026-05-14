from rclpy.node import Node
from std_msgs.msg import Bool
from std_srvs.srv import Trigger


class EmergencyStop(Node):
    """ROS2 node that publishes e-stop status and exposes a toggle service."""

    def __init__(self) -> None:
        super().__init__("emergency_stop")

        # Initialized as emergency stop active
        self.emergency_stop_status: bool = True
        self.emergency_stop_msg: Bool = Bool()
        self.emergency_stop_publisher_rate: int = 10

        self.init_publishers()
        self.init_services()

        self.create_timer(
            1.0 / self.emergency_stop_publisher_rate, self.publish_emergency_stop_status
        )

        self.get_logger().info("Emergency stop node initialized")

    def init_publishers(self) -> None:
        """Create the emergency stop status publisher."""
        self.emergency_stop_publisher = self.create_publisher(
            Bool, "emergency_stop_status", 10
        )

    def init_services(self) -> None:
        """Register the service for toggling the emergency stop."""
        self.create_service(Trigger, "emergency_stop_toggle", self.emergency_stop)

    def emergency_stop(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        """Toggle the e-stop state and acknowledge the request."""
        self.emergency_stop_status = not self.emergency_stop_status
        self.emergency_stop_msg.data = self.emergency_stop_status
        response.success = True
        response.message = (
            f"Emergency stop status toggled to {self.emergency_stop_status}"
        )

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
