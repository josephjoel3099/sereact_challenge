"""Test suite for the Door ROS 2 node."""

from unittest.mock import patch

import pytest
import rclpy
from std_msgs.msg import Bool
from std_srvs.srv import Trigger

from components.door import Door


@pytest.fixture
def door_node():
    """Fixture to provide a Door node for tests."""
    rclpy.init()
    node = Door()
    yield node
    node.destroy_node()
    rclpy.shutdown()


class TestDoorNodeCreation:
    """Tests for Door node initialization."""

    def test_node_creation(self, door_node):
        """Test that the Door node is created successfully."""
        assert door_node is not None
        assert door_node.get_name() == "door"

    def test_door_closed_status_initialization(self, door_node):
        """Test that door_closed_status is initialized as False (open)."""
        assert door_node.door_closed_status is False

    def test_door_message_initialization(self, door_node):
        """Test that door_closed_status_msg is initialized as Bool."""
        assert isinstance(door_node.door_closed_status_msg, Bool)

    def test_publisher_initialization(self, door_node):
        """Test that the door_closed_status publisher is properly initialized."""
        assert door_node.door_closed_status_publisher is not None

    def test_service_initialization(self, door_node):
        """Test that the door_closed_status_toggle service is properly initialized."""
        service_names = door_node.get_service_names_and_types()
        service_exists = any(
            "door_closed_status_toggle" in name for name, _ in service_names
        )
        assert service_exists, "door_closed_status_toggle service not found"

    def test_publish_rate_configuration(self, door_node):
        """Test that door publish rate is set correctly."""
        assert door_node.door_closed_status_publish_rate == 1.0


class TestDoorStatusPublishing:
    """Tests for door status publishing functionality."""

    def test_publish_door_closed_status_when_closed(self, door_node):
        """Test that door_closed_status_msg is updated with closed state."""
        door_node.door_closed_status = True
        door_node.publish_door_closed_status()
        assert door_node.door_closed_status_msg.data is True

    def test_publish_door_closed_status_when_open(self, door_node):
        """Test that door_closed_status_msg is updated with open state."""
        door_node.door_closed_status = False
        door_node.publish_door_closed_status()
        assert door_node.door_closed_status_msg.data is False

    def test_publish_door_creates_valid_message(self, door_node):
        """Test that publish_door_closed_status creates valid Bool messages."""
        door_node.door_closed_status = True
        with patch.object(
            door_node.door_closed_status_publisher, "publish"
        ) as mock_publish:
            door_node.publish_door_closed_status()
            mock_publish.assert_called_once()
            published_msg = mock_publish.call_args[0][0]
            assert isinstance(published_msg, Bool)
            assert published_msg.data is True

    def test_multiple_publishes(self, door_node):
        """Test that multiple publish operations work correctly."""
        with patch.object(
            door_node.door_closed_status_publisher, "publish"
        ) as mock_publish:
            for _ in range(5):
                door_node.publish_door_closed_status()
            assert mock_publish.call_count == 5


class TestDoorToggleService:
    """Tests for door_closed_status_toggle service."""

    def test_toggle_service_from_open_to_closed(self, door_node):
        """Test that toggling door from open to closed works correctly."""
        door_node.door_closed_status = False
        request = Trigger.Request()
        response = Trigger.Response()
        result = door_node.door_closed_status_callback(request, response)
        assert result.success is True
        assert door_node.door_closed_status is True
        assert "True" in result.message

    def test_toggle_service_from_closed_to_open(self, door_node):
        """Test that toggling door from closed to open works correctly."""
        door_node.door_closed_status = True
        request = Trigger.Request()
        response = Trigger.Response()
        result = door_node.door_closed_status_callback(request, response)
        assert result.success is False
        assert door_node.door_closed_status is False
        assert "False" in result.message

    def test_toggle_service_response_reflects_new_state(self, door_node):
        """Test that service response.success reflects the new door state."""
        door_node.door_closed_status = False
        request = Trigger.Request()
        response = Trigger.Response()
        result = door_node.door_closed_status_callback(request, response)
        assert result.success == door_node.door_closed_status

    def test_toggle_multiple_times(self, door_node):
        """Test that toggling multiple times works correctly."""
        states = []
        for _ in range(4):
            request = Trigger.Request()
            response = Trigger.Response()
            result = door_node.door_closed_status_callback(request, response)
            states.append(door_node.door_closed_status)

        # Should cycle: False -> True -> False -> True -> False
        assert states == [True, False, True, False]

    def test_service_message_format(self, door_node):
        """Test that service returns proper message format."""
        request = Trigger.Request()
        response = Trigger.Response()
        result = door_node.door_closed_status_callback(request, response)
        assert isinstance(result.message, str)
        assert "Door closed status toggled to" in result.message

    def test_service_returns_trigger_response(self, door_node):
        """Test that service returns a Trigger response."""
        request = Trigger.Request()
        response = Trigger.Response()
        result = door_node.door_closed_status_callback(request, response)
        assert isinstance(result, Trigger.Response)


class TestDoorPublishingAndServiceSync:
    """Tests for synchronization between publishing and service."""

    def test_publishing_reflects_toggled_state(self, door_node):
        """Test that publish reflects the state changed by service."""
        request = Trigger.Request()
        response = Trigger.Response()

        # Toggle to closed
        door_node.door_closed_status_callback(request, response)
        door_node.publish_door_closed_status()
        assert door_node.door_closed_status_msg.data is True

        # Toggle to open
        door_node.door_closed_status_callback(request, response)
        door_node.publish_door_closed_status()
        assert door_node.door_closed_status_msg.data is False

    def test_multiple_toggle_and_publish_cycle(self, door_node):
        """Test multiple cycles of toggling and publishing."""
        for expected_state in [True, False, True, False]:
            request = Trigger.Request()
            response = Trigger.Response()
            door_node.door_closed_status_callback(request, response)
            door_node.publish_door_closed_status()
            assert door_node.door_closed_status_msg.data == expected_state


class TestDoorBehaviorRequirements:
    """Tests that verify door requirements from specification."""

    def test_door_initializes_as_open(self, door_node):
        """Requirement: Door should initialize as open (False)."""
        assert door_node.door_closed_status is False

    def test_door_publishes_boolean(self, door_node):
        """Requirement: Door should publish boolean values."""
        door_node.door_closed_status = True
        door_node.publish_door_closed_status()
        assert isinstance(door_node.door_closed_status_msg.data, bool)

    def test_door_true_means_closed(self, door_node):
        """Requirement: True should represent closed door."""
        door_node.door_closed_status = True
        door_node.publish_door_closed_status()
        assert door_node.door_closed_status_msg.data is True

    def test_door_false_means_open(self, door_node):
        """Requirement: False should represent open door."""
        door_node.door_closed_status = False
        door_node.publish_door_closed_status()
        assert door_node.door_closed_status_msg.data is False

    def test_door_has_toggle_service(self, door_node):
        """Requirement: Door should have service to toggle state."""
        request = Trigger.Request()
        response = Trigger.Response()
        initial_state = door_node.door_closed_status
        door_node.door_closed_status_callback(request, response)
        assert door_node.door_closed_status != initial_state

    def test_door_publishes_on_topic(self, door_node):
        """Requirement: Door should publish on door_closed_status topic."""
        publishers = door_node.get_publishers_info_by_topic("door_closed_status")
        assert len(publishers) > 0

    def test_door_continuous_publishing(self, door_node):
        """Requirement: Door should constantly publish state."""
        with patch.object(
            door_node.door_closed_status_publisher, "publish"
        ) as mock_publish:
            # Simulate timer callback multiple times
            for _ in range(10):
                door_node.publish_door_closed_status()
            # Verify publish was called multiple times (continuously)
            assert mock_publish.call_count == 10
