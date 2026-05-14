from enum import Enum

from rclpy.node import Node
from std_msgs.msg import Int32


class StackLightState(Enum):
    EMERGENCY = -1
    OPERATIONAL = 0
    PAUSED = 1
    INITIALIZING = 2


class StackLight(Node):
    def __init__(self) -> None:
        super().__init__("stack_light")

        self.stack_light_status = StackLightState.INITIALIZING
        self.stack_light_status_msg = Int32()
        self.stack_light_status_publisher_rate = 10

        self.init_publishers()

        self.create_timer(
            1.0 / self.stack_light_status_publisher_rate,
            self.publish_stack_light_status,
        )

        self.get_logger().info("StackLight node initialized")

    def init_publishers(self) -> None:
        self.stack_light_status_publisher = self.create_publisher(
            Int32, "stack_light_status", 10
        )

    def publish_stack_light_status(self) -> None:
        self.stack_light_status_msg.data = self.stack_light_status.value
        self.stack_light_status_publisher.publish(self.stack_light_status_msg)


def main(args: list[str] | None = None) -> None:
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
