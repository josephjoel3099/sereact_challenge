from rclpy.node import Node
from std_msgs.msg import Bool
from std_srvs.srv import Trigger

NODE_NAME = "door"
TOPIC_DOOR_CLOSED_STATUS = "door_closed_status"
SERVICE_DOOR_CLOSED_STATUS_TOGGLE = "door_closed_status_toggle"
QUEUE_SIZE = 10
PUBLISH_RATE = 1.0  # Hz


class Door(Node):
    """ROS2 node that publishes door closed status and exposes a toggle service."""

    def __init__(self) -> None:
        super().__init__(NODE_NAME)

        # initialize door as open (sensor will determine closed status)
        self.door_closed_status: bool = False
        self.door_closed_status_msg: Bool = Bool()

        self.init_publishers()
        self.init_services()

        self.create_timer(
            1.0 / PUBLISH_RATE, self.publish_door_closed_status
        )

        self.get_logger().info("Door node initialized")

    def init_publishers(self) -> None:
        """Create the door closed status publisher."""
        self.door_closed_status_publisher = self.create_publisher(
            Bool, TOPIC_DOOR_CLOSED_STATUS, QUEUE_SIZE
        )

    def init_services(self) -> None:
        """Register the service for toggling the door closed status."""
        self.create_service(
            Trigger, SERVICE_DOOR_CLOSED_STATUS_TOGGLE, self.door_closed_status_callback
        )

    def door_closed_status_callback(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        """Toggle the door closed state; response.success reflects the new state."""
        self.door_closed_status = not self.door_closed_status
        response.success = self.door_closed_status
        response.message = f"Door closed status toggled to {self.door_closed_status}"
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
