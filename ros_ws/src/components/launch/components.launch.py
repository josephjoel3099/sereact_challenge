from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            Node(package="components", executable="emergency_stop"),
            Node(package="components", executable="door"),
            Node(package="components", executable="stack_light"),
            Node(package="components", executable="scanner"),
        ]
    )
