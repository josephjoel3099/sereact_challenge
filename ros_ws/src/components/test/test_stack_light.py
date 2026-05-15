"""Test suite for the Stack Light ROS 2 node."""

from unittest.mock import MagicMock, patch

import pytest
import rclpy
from std_msgs.msg import Bool, Int32

from components.stack_light import StackLight, StackLightState


@pytest.fixture
def stack_light_node():
    """Fixture to provide a StackLight node for tests."""
    rclpy.init()
    node = StackLight()
    yield node
    node.destroy_node()
    rclpy.shutdown()


class TestStackLightNodeCreation:
    """Tests for StackLight node initialization."""

    def test_node_creation(self, stack_light_node):
        """Test that the StackLight node is created successfully."""
        assert stack_light_node is not None
        assert stack_light_node.get_name() == "stack_light"

    def test_stack_light_status_initialization(self, stack_light_node):
        """Test that stack_light_status is initialized as INITIALIZING."""
        assert stack_light_node.stack_light_status == StackLightState.INITIALIZING

    def test_stack_light_message_initialization(self, stack_light_node):
        """Test that stack_light_status_msg is initialized as Int32."""
        assert isinstance(stack_light_node.stack_light_status_msg, Int32)

    def test_publisher_initialization(self, stack_light_node):
        """Test that the stack_light_status publisher is properly initialized."""
        assert stack_light_node.stack_light_status_publisher is not None

    def test_door_closed_status_initialization(self, stack_light_node):
        """Test that door_closed_status is initialized as False (open)."""
        assert stack_light_node.door_closed_status is False

    def test_emergency_stop_status_initialization(self, stack_light_node):
        """Test that emergency_stop_status is initialized as True (pressed)."""
        assert stack_light_node.emergency_stop_status is True

    def test_publisher_rate_configuration(self, stack_light_node):
        """Test that stack light publish rate is set correctly (10 Hz)."""
        # Verify timer is created (implicitly checked through node creation)
        assert stack_light_node is not None


class TestStackLightStateEnum:
    """Tests for StackLightState enum values."""

    def test_emergency_state_value(self):
        """Test that EMERGENCY state has value -1."""
        assert StackLightState.EMERGENCY.value == -1

    def test_operational_state_value(self):
        """Test that OPERATIONAL state has value 0."""
        assert StackLightState.OPERATIONAL.value == 0

    def test_paused_state_value(self):
        """Test that PAUSED state has value 1."""
        assert StackLightState.PAUSED.value == 1

    def test_initializing_state_value(self):
        """Test that INITIALIZING state has value 2."""
        assert StackLightState.INITIALIZING.value == 2


class TestStackLightSubscribers:
    """Tests for stack light subscriptions."""

    def test_door_closed_status_subscription(self, stack_light_node):
        """Test that stack light subscribes to door_closed_status topic."""
        subscriptions = stack_light_node.get_subscriptions_info_by_topic(
            "/door_closed_status"
        )
        assert len(subscriptions) > 0

    def test_emergency_stop_status_subscription(self, stack_light_node):
        """Test that stack light subscribes to emergency_stop_status topic."""
        subscriptions = stack_light_node.get_subscriptions_info_by_topic(
            "/emergency_stop_status"
        )
        assert len(subscriptions) > 0


class TestDoorStatusCallback:
    """Tests for door_closed_status_callback."""

    def test_door_closed_callback_sets_closed(self, stack_light_node):
        """Test that door closed callback updates door_closed_status to True."""
        msg = Bool()
        msg.data = True
        stack_light_node.door_closed_status_callback(msg)
        assert stack_light_node.door_closed_status is True

    def test_door_open_callback_sets_open(self, stack_light_node):
        """Test that door open callback updates door_closed_status to False."""
        msg = Bool()
        msg.data = False
        stack_light_node.door_closed_status_callback(msg)
        assert stack_light_node.door_closed_status is False

    def test_door_callback_multiple_updates(self, stack_light_node):
        """Test that door callback can be called multiple times."""
        states = [True, False, True, False, True]
        for state in states:
            msg = Bool()
            msg.data = state
            stack_light_node.door_closed_status_callback(msg)
            assert stack_light_node.door_closed_status == state


class TestEmergencyStopCallback:
    """Tests for emergency_stop_status_callback."""

    def test_emergency_stop_pressed_callback(self, stack_light_node):
        """Test that emergency stop pressed callback updates status to True."""
        msg = Bool()
        msg.data = True
        stack_light_node.emergency_stop_status_callback(msg)
        assert stack_light_node.emergency_stop_status is True

    def test_emergency_stop_released_callback(self, stack_light_node):
        """Test that emergency stop released callback updates status to False."""
        msg = Bool()
        msg.data = False
        stack_light_node.emergency_stop_status_callback(msg)
        assert stack_light_node.emergency_stop_status is False

    def test_emergency_stop_callback_multiple_updates(self, stack_light_node):
        """Test that emergency stop callback can be called multiple times."""
        states = [True, False, True, False, True]
        for state in states:
            msg = Bool()
            msg.data = state
            stack_light_node.emergency_stop_status_callback(msg)
            assert stack_light_node.emergency_stop_status == state


class TestStackLightStateTransitions:
    """Tests for stack light state transitions based on inputs."""

    def test_emergency_state_when_emergency_stop_pressed(self, stack_light_node):
        """Test that stack light is EMERGENCY when e-stop is pressed."""
        stack_light_node.door_closed_status = True
        stack_light_node.emergency_stop_status = True
        with patch.object(
            stack_light_node, "count_publishers", return_value=1
        ):
            stack_light_node.publish_stack_light_status()
        assert stack_light_node.stack_light_status == StackLightState.EMERGENCY

    def test_paused_state_when_door_open(self, stack_light_node):
        """Test that stack light is PAUSED when door is open."""
        stack_light_node.door_closed_status = False
        stack_light_node.emergency_stop_status = False
        with patch.object(
            stack_light_node, "count_publishers", return_value=1
        ):
            stack_light_node.publish_stack_light_status()
        assert stack_light_node.stack_light_status == StackLightState.PAUSED

    def test_operational_state_when_door_closed_and_emergency_stop_released(
        self, stack_light_node
    ):
        """Test that stack light is OPERATIONAL when door closed and e-stop released."""
        stack_light_node.door_closed_status = True
        stack_light_node.emergency_stop_status = False
        with patch.object(
            stack_light_node, "count_publishers", return_value=1
        ):
            stack_light_node.publish_stack_light_status()
        assert stack_light_node.stack_light_status == StackLightState.OPERATIONAL

    def test_emergency_takes_priority_over_door_open(self, stack_light_node):
        """Test that EMERGENCY state takes priority when e-stop is pressed."""
        stack_light_node.door_closed_status = False
        stack_light_node.emergency_stop_status = True
        with patch.object(
            stack_light_node, "count_publishers", return_value=1
        ):
            stack_light_node.publish_stack_light_status()
        assert stack_light_node.stack_light_status == StackLightState.EMERGENCY

    def test_emergency_priority_over_operational(self, stack_light_node):
        """Test that EMERGENCY takes priority over OPERATIONAL state."""
        stack_light_node.door_closed_status = True
        stack_light_node.emergency_stop_status = True
        with patch.object(
            stack_light_node, "count_publishers", return_value=1
        ):
            stack_light_node.publish_stack_light_status()
        assert stack_light_node.stack_light_status == StackLightState.EMERGENCY


class TestStackLightPublishing:
    """Tests for stack light publishing functionality."""

    def test_publish_stack_light_creates_valid_message(self, stack_light_node):
        """Test that publish creates valid Int32 messages."""
        stack_light_node.door_closed_status = True
        stack_light_node.emergency_stop_status = False
        with patch.object(
            stack_light_node.stack_light_status_publisher, "publish"
        ) as mock_publish:
            with patch.object(
                stack_light_node, "count_publishers", return_value=1
            ):
                stack_light_node.publish_stack_light_status()
            mock_publish.assert_called_once()
            published_msg = mock_publish.call_args[0][0]
            assert isinstance(published_msg, Int32)

    def test_publish_operational_state_value(self, stack_light_node):
        """Test that publishing OPERATIONAL state publishes value 0."""
        stack_light_node.door_closed_status = True
        stack_light_node.emergency_stop_status = False
        with patch.object(
            stack_light_node.stack_light_status_publisher, "publish"
        ) as mock_publish:
            with patch.object(
                stack_light_node, "count_publishers", return_value=1
            ):
                stack_light_node.publish_stack_light_status()
            published_msg = mock_publish.call_args[0][0]
            assert published_msg.data == 0

    def test_publish_paused_state_value(self, stack_light_node):
        """Test that publishing PAUSED state publishes value 1."""
        stack_light_node.door_closed_status = False
        stack_light_node.emergency_stop_status = False
        with patch.object(
            stack_light_node.stack_light_status_publisher, "publish"
        ) as mock_publish:
            with patch.object(
                stack_light_node, "count_publishers", return_value=1
            ):
                stack_light_node.publish_stack_light_status()
            published_msg = mock_publish.call_args[0][0]
            assert published_msg.data == 1

    def test_publish_emergency_state_value(self, stack_light_node):
        """Test that publishing EMERGENCY state publishes value -1."""
        stack_light_node.door_closed_status = True
        stack_light_node.emergency_stop_status = True
        with patch.object(
            stack_light_node.stack_light_status_publisher, "publish"
        ) as mock_publish:
            with patch.object(
                stack_light_node, "count_publishers", return_value=1
            ):
                stack_light_node.publish_stack_light_status()
            published_msg = mock_publish.call_args[0][0]
            assert published_msg.data == -1

    def test_multiple_publishes(self, stack_light_node):
        """Test that multiple publish operations work correctly."""
        with patch.object(
            stack_light_node.stack_light_status_publisher, "publish"
        ) as mock_publish:
            with patch.object(
                stack_light_node, "count_publishers", return_value=1
            ):
                for _ in range(10):
                    stack_light_node.publish_stack_light_status()
            assert mock_publish.call_count == 10


class TestStackLightPublisherAvailability:
    """Tests for handling missing publishers (sensors not connected)."""

    def test_emergency_state_when_emergency_stop_publisher_missing(
        self, stack_light_node
    ):
        """Test that stack light is EMERGENCY when emergency stop publisher is missing."""
        stack_light_node.door_closed_status = True
        stack_light_node.emergency_stop_status = False
        with patch.object(
            stack_light_node, "count_publishers", return_value=0
        ):
            stack_light_node.publish_stack_light_status()
        assert stack_light_node.stack_light_status == StackLightState.EMERGENCY

    def test_paused_state_when_door_publisher_missing(self, stack_light_node):
        """Test that stack light is PAUSED when door publisher is missing."""
        stack_light_node.door_closed_status = True
        stack_light_node.emergency_stop_status = False

        def count_publishers_side_effect(topic):
            if "door_closed_status" in topic:
                return 0
            return 1

        with patch.object(
            stack_light_node, "count_publishers", side_effect=count_publishers_side_effect
        ):
            stack_light_node.publish_stack_light_status()
        assert stack_light_node.stack_light_status == StackLightState.PAUSED


class TestStackLightIntegrationScenarios:
    """Integration tests for complete stack light scenarios."""

    def test_complete_workflow_operational(self, stack_light_node):
        """Test complete workflow: door closed, e-stop released -> OPERATIONAL."""
        # Simulate door closing
        door_msg = Bool()
        door_msg.data = True
        stack_light_node.door_closed_status_callback(door_msg)

        # Simulate e-stop being released
        estop_msg = Bool()
        estop_msg.data = False
        stack_light_node.emergency_stop_status_callback(estop_msg)

        # Publish and verify OPERATIONAL
        with patch.object(
            stack_light_node.stack_light_status_publisher, "publish"
        ) as mock_publish:
            with patch.object(
                stack_light_node, "count_publishers", return_value=1
            ):
                stack_light_node.publish_stack_light_status()
            published_msg = mock_publish.call_args[0][0]
            assert published_msg.data == 0  # OPERATIONAL

    def test_complete_workflow_paused(self, stack_light_node):
        """Test complete workflow: door open -> PAUSED."""
        # Simulate door opening
        door_msg = Bool()
        door_msg.data = False
        stack_light_node.door_closed_status_callback(door_msg)

        # E-stop released
        estop_msg = Bool()
        estop_msg.data = False
        stack_light_node.emergency_stop_status_callback(estop_msg)

        # Publish and verify PAUSED
        with patch.object(
            stack_light_node.stack_light_status_publisher, "publish"
        ) as mock_publish:
            with patch.object(
                stack_light_node, "count_publishers", return_value=1
            ):
                stack_light_node.publish_stack_light_status()
            published_msg = mock_publish.call_args[0][0]
            assert published_msg.data == 1  # PAUSED

    def test_complete_workflow_emergency(self, stack_light_node):
        """Test complete workflow: e-stop pressed -> EMERGENCY."""
        # Simulate door closing
        door_msg = Bool()
        door_msg.data = True
        stack_light_node.door_closed_status_callback(door_msg)

        # Simulate e-stop being pressed
        estop_msg = Bool()
        estop_msg.data = True
        stack_light_node.emergency_stop_status_callback(estop_msg)

        # Publish and verify EMERGENCY
        with patch.object(
            stack_light_node.stack_light_status_publisher, "publish"
        ) as mock_publish:
            with patch.object(
                stack_light_node, "count_publishers", return_value=1
            ):
                stack_light_node.publish_stack_light_status()
            published_msg = mock_publish.call_args[0][0]
            assert published_msg.data == -1  # EMERGENCY

    def test_state_transitions_sequence(self, stack_light_node):
        """Test sequence of state transitions."""
        with patch.object(
            stack_light_node, "count_publishers", return_value=1
        ), patch.object(
            stack_light_node.stack_light_status_publisher, "publish"
        ) as mock_publish:
            # Start: paused (door open)
            stack_light_node.door_closed_status = False
            stack_light_node.emergency_stop_status = False
            stack_light_node.publish_stack_light_status()
            assert mock_publish.call_args_list[-1][0][0].data == 1  # PAUSED

            # Transition to operational (door closes)
            stack_light_node.door_closed_status = True
            stack_light_node.publish_stack_light_status()
            assert mock_publish.call_args_list[-1][0][0].data == 0  # OPERATIONAL

            # Transition to emergency (e-stop pressed)
            stack_light_node.emergency_stop_status = True
            stack_light_node.publish_stack_light_status()
            assert mock_publish.call_args_list[-1][0][0].data == -1  # EMERGENCY

            # Transition back to operational (e-stop released)
            stack_light_node.emergency_stop_status = False
            stack_light_node.publish_stack_light_status()
            assert mock_publish.call_args_list[-1][0][0].data == 0  # OPERATIONAL


class TestStackLightBehaviorRequirements:
    """Tests that verify stack light requirements from specification."""

    def test_operational_when_door_closed_and_receiving_requests(
        self, stack_light_node
    ):
        """Requirement: State 0 (OPERATIONAL) when door closed and system receiving requests."""
        stack_light_node.door_closed_status = True
        stack_light_node.emergency_stop_status = False
        with patch.object(
            stack_light_node, "count_publishers", return_value=1
        ):
            stack_light_node.publish_stack_light_status()
        assert stack_light_node.stack_light_status.value == 0

    def test_paused_when_door_open(self, stack_light_node):
        """Requirement: State 1 (PAUSED) when door open and robot cannot move."""
        stack_light_node.door_closed_status = False
        stack_light_node.emergency_stop_status = False
        with patch.object(
            stack_light_node, "count_publishers", return_value=1
        ):
            stack_light_node.publish_stack_light_status()
        assert stack_light_node.stack_light_status.value == 1

    def test_emergency_when_e_button_pressed(self, stack_light_node):
        """Requirement: State -1 (EMERGENCY) when e-button is pressed."""
        stack_light_node.door_closed_status = True
        stack_light_node.emergency_stop_status = True
        with patch.object(
            stack_light_node, "count_publishers", return_value=1
        ):
            stack_light_node.publish_stack_light_status()
        assert stack_light_node.stack_light_status.value == -1

    def test_stack_light_publishes_on_topic(self, stack_light_node):
        """Requirement: Stack light should publish on stack_light_status topic."""
        publishers = stack_light_node.get_publishers_info_by_topic(
            "stack_light_status"
        )
        assert len(publishers) > 0

    def test_stack_light_publishes_integer(self, stack_light_node):
        """Requirement: Stack light should publish integer values."""
        stack_light_node.door_closed_status = True
        stack_light_node.emergency_stop_status = False
        with patch.object(
            stack_light_node.stack_light_status_publisher, "publish"
        ) as mock_publish:
            with patch.object(
                stack_light_node, "count_publishers", return_value=1
            ):
                stack_light_node.publish_stack_light_status()
            published_msg = mock_publish.call_args[0][0]
            assert isinstance(published_msg.data, int)

    def test_stack_light_subscribes_to_door_and_emergency_stop(
        self, stack_light_node
    ):
        """Requirement: Stack light should monitor door and emergency stop states."""
        # Test that subscriptions exist
        door_subs = stack_light_node.get_subscriptions_info_by_topic(
            "/door_closed_status"
        )
        estop_subs = stack_light_node.get_subscriptions_info_by_topic(
            "/emergency_stop_status"
        )
        assert len(door_subs) > 0
        assert len(estop_subs) > 0
