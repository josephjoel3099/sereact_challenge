import random

from rclpy.node import Node
from std_msgs.msg import Int32
from std_srvs.srv import Trigger


class Scanner(Node):
    def __init__(self) -> None:
        super().__init__("scanner")

        self.barode_msg: Int32 = Int32()
        self.barcode_msg_publish_rate = 1

        self.init_publishers()
        self.init_services()

        self.timer = self.create_timer(
            self.barcode_msg_publish_rate, self.publish_barcode
        )

    def init_publishers(self) -> None:
        self.publisher = self.create_publisher(Int32, "scanned_barcode", 10)

    def init_services(self) -> None:
        self.create_service(Trigger, "get_latest_barcode", self.get_latest_barcode)

    def get_latest_barcode(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        response.success = True
        response.message = f"{self.barode_msg.data}"
        return response

    def random_barcode_generator(self) -> int:
        """
        Returns and random 5 digit number
        """
        return random.randint(10000, 99999)

    def publish_barcode(self) -> None:
        self.barode_msg.data = self.random_barcode_generator()
        self.publisher.publish(self.barode_msg)


def main(args: list[str] | None = None) -> None:
    import rclpy
    from rclpy.executors import SingleThreadedExecutor

    rclpy.init(args=args)
    node = Scanner()
    executor = SingleThreadedExecutor()
    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.remove_node(node)
        node.destroy_node()

        if not rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
