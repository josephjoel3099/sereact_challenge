"""Test suite for the Emergency Stop ROS 2 node."""

from unittest.mock import patch

import pytest
import rclpy
from std_msgs.msg import Bool
from std_srvs.srv import Trigger

from components.emergency_stop import EmergencyStop


@pytest.fixture
def emergency_stop_node():
    """Fixture to provide an EmergencyStop node for tests."""
    rclpy.init()
    node = EmergencyStop()
    yield node
    node.destroy_node()
    rclpy.shutdown()


class TestEmergencyStopNodeCreation:
    """Tests for EmergencyStop node initialization."""

    def test_node_creation(self, emergency_stop_node):
        """Test that the EmergencyStop node is created successfully."""
        assert emergency_stop_node is not None
        assert emergency_stop_node.get_name() == "emergency_stop"

    def test_emergency_stop_status_initialization(self, emergency_stop_node):
        """Test that emergency_stop_status is initialized as True (pressed)."""
        assert emergency_stop_node.emergency_stop_status is True

    def test_emergency_stop_message_initialization(self, emergency_stop_node):
        """Test that emergency_stop_msg is initialized as Bool."""
        assert isinstance(emergency_stop_node.emergency_stop_msg, Bool)

    def test_publisher_initialization(self, emergency_stop_node):
        """Test that the emergency_stop_status publisher is properly initialized."""
        assert emergency_stop_node.emergency_stop_publisher is not None

    def test_press_service_initialization(self, emergency_stop_node):
        """Test that the press_emergency_stop service is properly initialized."""
        service_names = emergency_stop_node.get_service_names_and_types()
        service_exists = any(
            "press_emergency_stop" in name for name, _ in service_names
        )
        assert service_exists, "press_emergency_stop service not found"

    def test_release_service_initialization(self, emergency_stop_node):
        """Test that the release_emergency_stop service is properly initialized."""
        service_names = emergency_stop_node.get_service_names_and_types()
        service_exists = any(
            "release_emergency_stop" in name for name, _ in service_names
        )
        assert service_exists, "release_emergency_stop service not found"

    def test_publish_rate_configuration(self, emergency_stop_node):
        """Test that emergency stop publish rate is set correctly."""
        assert emergency_stop_node.emergency_stop_publisher_rate == 10


class TestEmergencyStopStatusPublishing:
    """Tests for emergency stop status publishing functionality."""

    def test_publish_emergency_stop_when_pressed(self, emergency_stop_node):
        """Test that emergency_stop_msg is updated with pressed state (True)."""
        emergency_stop_node.emergency_stop_status = True
        emergency_stop_node.publish_emergency_stop_status()
        assert emergency_stop_node.emergency_stop_msg.data is True

    def test_publish_emergency_stop_when_released(self, emergency_stop_node):
        """Test that emergency_stop_msg is updated with released state (False)."""
        emergency_stop_node.emergency_stop_status = False
        emergency_stop_node.publish_emergency_stop_status()
        assert emergency_stop_node.emergency_stop_msg.data is False

    def test_publish_emergency_stop_creates_valid_message(self, emergency_stop_node):
        """Test that publish_emergency_stop_status creates valid Bool messages."""
        emergency_stop_node.emergency_stop_status = True
        with patch.object(
            emergency_stop_node.emergency_stop_publisher, "publish"
        ) as mock_publish:
            emergency_stop_node.publish_emergency_stop_status()
            mock_publish.assert_called_once()
            published_msg = mock_publish.call_args[0][0]
            assert isinstance(published_msg, Bool)
            assert published_msg.data is True

    def test_multiple_publishes(self, emergency_stop_node):
        """Test that multiple publish operations work correctly."""
        with patch.object(
            emergency_stop_node.emergency_stop_publisher, "publish"
        ) as mock_publish:
            for _ in range(10):
                emergency_stop_node.publish_emergency_stop_status()
            assert mock_publish.call_count == 10


class TestEmergencyStopPressService:
    """Tests for press_emergency_stop service."""

    def test_press_emergency_stop(self, emergency_stop_node):
        """Test that pressing emergency stop sets status to True."""
        emergency_stop_node.emergency_stop_status = False
        request = Trigger.Request()
        response = Trigger.Response()
        result = emergency_stop_node.press_emergency_stop(request, response)
        assert emergency_stop_node.emergency_stop_status is True
        assert result.success is True

    def test_press_emergency_stop_response_message(self, emergency_stop_node):
        """Test that press service returns appropriate response message."""
        request = Trigger.Request()
        response = Trigger.Response()
        result = emergency_stop_node.press_emergency_stop(request, response)
        assert isinstance(result.message, str)
        assert "Emergency stop status" in result.message
        assert "True" in result.message

    def test_press_when_already_pressed(self, emergency_stop_node):
        """Test that pressing when already pressed keeps state as True."""
        emergency_stop_node.emergency_stop_status = True
        request = Trigger.Request()
        response = Trigger.Response()
        result = emergency_stop_node.press_emergency_stop(request, response)
        assert emergency_stop_node.emergency_stop_status is True
        assert result.success is True

    def test_press_returns_trigger_response(self, emergency_stop_node):
        """Test that press service returns a Trigger response."""
        request = Trigger.Request()
        response = Trigger.Response()
        result = emergency_stop_node.press_emergency_stop(request, response)
        assert isinstance(result, Trigger.Response)

    def test_press_updates_msg(self, emergency_stop_node):
        """Test that press service updates the emergency_stop_msg."""
        emergency_stop_node.emergency_stop_status = False
        request = Trigger.Request()
        response = Trigger.Response()
        emergency_stop_node.press_emergency_stop(request, response)
        assert emergency_stop_node.emergency_stop_msg.data is True


class TestEmergencyStopReleaseService:
    """Tests for release_emergency_stop service."""

    def test_release_emergency_stop(self, emergency_stop_node):
        """Test that releasing emergency stop sets status to False."""
        emergency_stop_node.emergency_stop_status = True
        request = Trigger.Request()
        response = Trigger.Response()
        result = emergency_stop_node.release_emergency_stop(request, response)
        assert emergency_stop_node.emergency_stop_status is False
        assert result.success is True

    def test_release_emergency_stop_response_message(self, emergency_stop_node):
        """Test that release service returns appropriate response message."""
        request = Trigger.Request()
        response = Trigger.Response()
        result = emergency_stop_node.release_emergency_stop(request, response)
        assert isinstance(result.message, str)
        assert "Emergency stop status" in result.message
        assert "False" in result.message

    def test_release_when_already_released(self, emergency_stop_node):
        """Test that releasing when already released keeps state as False."""
        emergency_stop_node.emergency_stop_status = False
        request = Trigger.Request()
        response = Trigger.Response()
        result = emergency_stop_node.release_emergency_stop(request, response)
        assert emergency_stop_node.emergency_stop_status is False
        assert result.success is True

    def test_release_returns_trigger_response(self, emergency_stop_node):
        """Test that release service returns a Trigger response."""
        request = Trigger.Request()
        response = Trigger.Response()
        result = emergency_stop_node.release_emergency_stop(request, response)
        assert isinstance(result, Trigger.Response)

    def test_release_updates_msg(self, emergency_stop_node):
        """Test that release service updates the emergency_stop_msg."""
        emergency_stop_node.emergency_stop_status = True
        request = Trigger.Request()
        response = Trigger.Response()
        emergency_stop_node.release_emergency_stop(request, response)
        assert emergency_stop_node.emergency_stop_msg.data is False


class TestEmergencyStopPressAndReleaseCycle:
    """Tests for press and release cycle."""

    def test_press_and_release_cycle(self, emergency_stop_node):
        """Test pressing and releasing emergency stop in sequence."""
        # Start released
        emergency_stop_node.emergency_stop_status = False

        # Press
        request = Trigger.Request()
        response = Trigger.Response()
        emergency_stop_node.press_emergency_stop(request, response)
        assert emergency_stop_node.emergency_stop_status is True

        # Release
        request = Trigger.Request()
        response = Trigger.Response()
        emergency_stop_node.release_emergency_stop(request, response)
        assert emergency_stop_node.emergency_stop_status is False

    def test_multiple_press_release_cycles(self, emergency_stop_node):
        """Test multiple press and release cycles."""
        expected_states = [True, False, True, False, True]
        emergency_stop_node.emergency_stop_status = False

        for expected_state in expected_states:
            request = Trigger.Request()
            response = Trigger.Response()
            if expected_state:
                emergency_stop_node.press_emergency_stop(request, response)
            else:
                emergency_stop_node.release_emergency_stop(request, response)
            assert emergency_stop_node.emergency_stop_status == expected_state

    def test_publishing_reflects_press_and_release(self, emergency_stop_node):
        """Test that publishing reflects pressed and released states."""
        # Press and publish
        request = Trigger.Request()
        response = Trigger.Response()
        emergency_stop_node.press_emergency_stop(request, response)
        emergency_stop_node.publish_emergency_stop_status()
        assert emergency_stop_node.emergency_stop_msg.data is True

        # Release and publish
        request = Trigger.Request()
        response = Trigger.Response()
        emergency_stop_node.release_emergency_stop(request, response)
        emergency_stop_node.publish_emergency_stop_status()
        assert emergency_stop_node.emergency_stop_msg.data is False


class TestEmergencyStopBehaviorRequirements:
    """Tests that verify emergency stop requirements from specification."""

    def test_emergency_stop_initializes_as_pressed(self, emergency_stop_node):
        """Requirement: Emergency stop should initialize as pressed (True)."""
        # Create fresh node to test initialization
        rclpy.shutdown()
        rclpy.init()
        fresh_node = EmergencyStop()
        assert fresh_node.emergency_stop_status is True
        fresh_node.destroy_node()

    def test_emergency_stop_publishes_boolean(self, emergency_stop_node):
        """Requirement: Emergency stop should publish boolean values."""
        emergency_stop_node.emergency_stop_status = True
        emergency_stop_node.publish_emergency_stop_status()
        assert isinstance(emergency_stop_node.emergency_stop_msg.data, bool)

    def test_emergency_stop_true_means_pressed(self, emergency_stop_node):
        """Requirement: True should represent button pressed."""
        emergency_stop_node.emergency_stop_status = True
        emergency_stop_node.publish_emergency_stop_status()
        assert emergency_stop_node.emergency_stop_msg.data is True

    def test_emergency_stop_false_means_released(self, emergency_stop_node):
        """Requirement: False should represent button released."""
        emergency_stop_node.emergency_stop_status = False
        emergency_stop_node.publish_emergency_stop_status()
        assert emergency_stop_node.emergency_stop_msg.data is False

    def test_emergency_stop_has_press_service(self, emergency_stop_node):
        """Requirement: Emergency stop should have service to press button."""
        emergency_stop_node.emergency_stop_status = False
        request = Trigger.Request()
        response = Trigger.Response()
        emergency_stop_node.press_emergency_stop(request, response)
        assert emergency_stop_node.emergency_stop_status is True

    def test_emergency_stop_has_release_service(self, emergency_stop_node):
        """Requirement: Emergency stop should have service to release button."""
        emergency_stop_node.emergency_stop_status = True
        request = Trigger.Request()
        response = Trigger.Response()
        emergency_stop_node.release_emergency_stop(request, response)
        assert emergency_stop_node.emergency_stop_status is False

    def test_emergency_stop_publishes_on_topic(self, emergency_stop_node):
        """Requirement: Emergency stop should publish on emergency_stop_status topic."""
        publishers = emergency_stop_node.get_publishers_info_by_topic(
            "emergency_stop_status"
        )
        assert len(publishers) > 0

    def test_emergency_stop_continuous_publishing(self, emergency_stop_node):
        """Requirement: Emergency stop should constantly publish state."""
        with patch.object(
            emergency_stop_node.emergency_stop_publisher, "publish"
        ) as mock_publish:
            # Simulate timer callback multiple times
            for _ in range(10):
                emergency_stop_node.publish_emergency_stop_status()
            # Verify publish was called multiple times (continuously)
            assert mock_publish.call_count == 10
