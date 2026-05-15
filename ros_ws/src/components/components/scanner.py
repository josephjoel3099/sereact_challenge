import random

from rclpy.node import Node
from std_msgs.msg import Int32
from std_srvs.srv import Trigger

NODE_NAME = "scanner"
TOPIC_SCANNED_BARCODE = "scanned_barcode"
SERVICE_GET_LATEST_BARCODE = "get_latest_barcode"
QUEUE_SIZE = 10
PUBLISH_RATE = 1  # Hz
BARCODE_MIN = 10000
BARCODE_MAX = 99999


class Scanner(Node):
    """ROS2 node that periodically publishes a simulated scanned barcode."""

    def __init__(self) -> None:
        super().__init__(NODE_NAME)

        self.barcode_msg: Int32 = Int32()

        self.init_publishers()
        self.init_services()

        self.create_timer(1.0 / PUBLISH_RATE, self.publish_barcode)

        self.get_logger().info("Scanner node initialized")

    def init_publishers(self) -> None:
        """Create the scanned barcode publisher."""
        self.barcode_publisher = self.create_publisher(Int32, TOPIC_SCANNED_BARCODE, QUEUE_SIZE)

    def init_services(self) -> None:
        """Register the service for retrieving the most recently scanned barcode."""
        self.create_service(Trigger, SERVICE_GET_LATEST_BARCODE, self.get_latest_barcode)

    def get_latest_barcode(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        """Return the last published barcode value as a string in the response message."""
        response.success = True
        response.message = f"{self.barcode_msg.data}"
        return response

    def random_barcode_generator(self) -> int:
        """Return a random 5-digit integer simulating a scanned barcode."""
        return random.randint(BARCODE_MIN, BARCODE_MAX)

    def publish_barcode(self) -> None:
        """Generate and publish a new barcode on the timer callback."""
        self.barcode_msg.data = self.random_barcode_generator()
        self.barcode_publisher.publish(self.barcode_msg)


def main(args: list[str] | None = None) -> None:
    """Entry point: spin the Scanner node with a single-threaded executor."""
    import rclpy
    from rclpy.executors import SingleThreadedExecutor

    rclpy.init(args=args)
    node = Scanner()

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
