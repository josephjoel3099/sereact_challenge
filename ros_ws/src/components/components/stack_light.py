from enum import Enum

from rclpy.node import Node
from std_msgs.msg import Bool, Int32

STACK_LIGHT_STATUS_TOPIC = "stack_light_status"
STACK_LIGHT_STATUS_PUBLISHER_RATE = 10  # Hz
DOOR_CLOSED_STATUS_TOPIC = "/door_closed_status"
EMERGENCY_STOP_STATUS_TOPIC = "/emergency_stop_status"
QUEUE_SIZE = 10


class StackLightState(Enum):
    """Operational states mapped to stack light color codes."""

    EMERGENCY = -1
    OPERATIONAL = 0
    PAUSED = 1
    INITIALIZING = 2


class StackLight(Node):
    """ROS2 node that publishes the current stack light state as an integer."""

    def __init__(self) -> None:
        super().__init__("stack_light")

        self.stack_light_status: StackLightState = StackLightState.INITIALIZING
        self.stack_light_status_msg: Int32 = Int32()

        self.door_closed_status: bool = False
        self.emergency_stop_status: bool = True

        self.init_publishers()
        self.init_subscribers()

        self.create_timer(
            1.0 / STACK_LIGHT_STATUS_PUBLISHER_RATE,
            self.publish_stack_light_status,
        )

        self.get_logger().info("StackLight node initialized")

    def init_publishers(self) -> None:
        """Create the stack light status publisher."""
        self.stack_light_status_publisher = self.create_publisher(
            Int32, STACK_LIGHT_STATUS_TOPIC, QUEUE_SIZE
        )

    def init_subscribers(self) -> None:
        """Create the stack light status subscriber."""
        self.create_subscription(
            Bool, DOOR_CLOSED_STATUS_TOPIC, self.door_closed_status_callback, 1
        )
        self.create_subscription(
            Bool, EMERGENCY_STOP_STATUS_TOPIC, self.emergency_stop_status_callback, 1
        )

    def publish_stack_light_status(self) -> None:
        """Publish the current stack light state value on the timer callback."""
        if (
            self.emergency_stop_status
            or self.count_publishers(EMERGENCY_STOP_STATUS_TOPIC) == 0
        ):
            self.stack_light_status = StackLightState.EMERGENCY
        elif (
            not self.door_closed_status
            or self.count_publishers(DOOR_CLOSED_STATUS_TOPIC) == 0
        ):
            self.stack_light_status = StackLightState.PAUSED
        else:
            self.stack_light_status = StackLightState.OPERATIONAL

        self.stack_light_status_msg.data = self.stack_light_status.value
        self.stack_light_status_publisher.publish(self.stack_light_status_msg)

    def door_closed_status_callback(self, msg: Bool) -> None:
        self.door_closed_status = msg.data

    def emergency_stop_status_callback(self, msg: Bool) -> None:
        self.emergency_stop_status = msg.data


def main(args: list[str] | None = None) -> None:
    """Entry point: spin the StackLight node with a single-threaded executor."""
    import rclpy
    from rclpy.executors import SingleThreadedExecutor

    rclpy.init(args=args)
    node = StackLight()

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
