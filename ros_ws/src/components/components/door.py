from rclpy.node import Node
from std_msgs.msg import Bool
from std_srvs.srv import Trigger


class Door(Node):
    def __init__(self) -> None:
        super().__init__("door")

        # initialize door as open (sensor will determine closed status)
        self.door_closed_status = False
        self.door_closed_status_msg = Bool()
        self.door_closed_status_publish_rate = 1.0

        self.init_publishers()
        self.init_services()

        self.create_timer(
            1.0 / self.door_closed_status_publish_rate, self.publish_door_closed_status
        )

        self.get_logger().info("Door node initialized")

    def init_publishers(self) -> None:
        self.door_closed_status_publisher = self.create_publisher(
            Bool, "door_closed_status", 10
        )

    def init_services(self) -> None:
        self.create_service(
            Trigger, "door_closed_status_toggle", self.door_closed_status_callback
        )

    def door_closed_status_callback(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        self.door_closed_status = not self.door_closed_status
        response.success = self.door_closed_status
        response.message = "Door closed status toggled"
        return response

    def publish_door_closed_status(self) -> None:
        self.door_closed_status_msg.data = self.door_closed_status
        self.door_closed_status_publisher.publish(self.door_closed_status_msg)


def main(args: list[str] | None = None) -> None:
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
