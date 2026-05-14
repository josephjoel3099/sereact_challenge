from rclpy.node import Node
from std_msgs.msg import Bool
from std_srvs.srv import Trigger


class Door(Node):
    """ROS2 node that publishes door closed status and exposes a toggle service."""

    def __init__(self) -> None:
        super().__init__("door")

        # initialize door as open (sensor will determine closed status)
        self.door_closed_status: bool = False
        self.door_closed_status_msg: Bool = Bool()
        self.door_closed_status_publish_rate: float = 1.0

        self.init_publishers()
        self.init_services()

        self.create_timer(
            1.0 / self.door_closed_status_publish_rate, self.publish_door_closed_status
        )

        self.get_logger().info("Door node initialized")

    def init_publishers(self) -> None:
        """Create the door closed status publisher."""
        self.door_closed_status_publisher = self.create_publisher(
            Bool, "door_closed_status", 10
        )

    def init_services(self) -> None:
        """Register the service for toggling the door closed status."""
        self.create_service(
            Trigger, "door_closed_status_toggle", self.door_closed_status_callback
        )

    def door_closed_status_callback(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        """Toggle the door closed state; response.success reflects the new state."""
        self.door_closed_status = not self.door_closed_status
        response.success = self.door_closed_status
        response.message = "Door closed status toggled"
        return response

    def publish_door_closed_status(self) -> None:
        """Publish the current door closed status on the timer callback."""
        self.door_closed_status_msg.data = self.door_closed_status
        self.door_closed_status_publisher.publish(self.door_closed_status_msg)


def main(args: list[str] | None = None) -> None:
    """Entry point: spin the Door node with a single-threaded executor."""
    import rclpy
    from rclpy.executors import SingleThreadedExecutor

    rclpy.init(args=args)
    node = Door()

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
