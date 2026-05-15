"""Test suite for the Robot Cell Client ROS 2 node."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import rclpy
from std_msgs.msg import Int32, String
from std_srvs.srv import Trigger

from components.robot_cell_client import (
    NODE_NAME,
    PickConfirmation,
    PickRequest,
    RobotCellClient,
)
from components.stack_light import StackLightState


def run_async(coro):
    """Helper to run async functions in sync tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@pytest.fixture
def robot_cell_client_node():
    """Fixture to provide a RobotCellClient node for tests."""
    rclpy.init()
    node = RobotCellClient()
    yield node
    node.destroy_node()
    rclpy.shutdown()


class TestRobotCellClientNodeCreation:
    """Tests for RobotCellClient node initialization."""

    def test_node_creation(self, robot_cell_client_node):
        """Test that the RobotCellClient node is created successfully."""
        assert robot_cell_client_node is not None
        assert robot_cell_client_node.get_name() == NODE_NAME

    def test_stack_light_status_initialization(self, robot_cell_client_node):
        """Test that stack_light_status is initialized as INITIALIZING."""
        assert robot_cell_client_node._stack_light_status == StackLightState.INITIALIZING

    def test_scanner_client_initialization(self, robot_cell_client_node):
        """Test that scanner service client is properly initialized."""
        assert robot_cell_client_node._scanner_client is not None

    def test_pick_request_publisher_initialization(self, robot_cell_client_node):
        """Test that pick_request publisher is properly initialized."""
        assert robot_cell_client_node._pick_request_pub is not None

    def test_pick_response_publisher_initialization(self, robot_cell_client_node):
        """Test that pick_response publisher is properly initialized."""
        assert robot_cell_client_node._pick_response_pub is not None

    def test_stack_light_subscriber_initialization(self, robot_cell_client_node):
        """Test that stack_light_status subscriber is properly initialized."""
        subscriptions = robot_cell_client_node.get_subscriptions_info_by_topic(
            "/stack_light_status"
        )
        assert len(subscriptions) > 0


class TestPickRequestModel:
    """Tests for PickRequest Pydantic model."""

    def test_pick_request_creation(self):
        """Test that PickRequest can be created with valid data."""
        request = PickRequest(pickId=1, quantity=5)
        assert request.pickId == 1
        assert request.quantity == 5

    def test_pick_request_json_serialization(self):
        """Test that PickRequest can be serialized to JSON."""
        request = PickRequest(pickId=42, quantity=3)
        json_str = json.dumps(request.model_dump())
        assert "pickId" in json_str
        assert "42" in json_str

    def test_pick_request_json_deserialization(self):
        """Test that PickRequest can be deserialized from JSON."""
        json_str = '{"pickId": 99, "quantity": 7}'
        data = json.loads(json_str)
        request = PickRequest(**data)
        assert request.pickId == 99
        assert request.quantity == 7


class TestPickConfirmationModel:
    """Tests for PickConfirmation Pydantic model."""

    def test_pick_confirmation_creation(self):
        """Test that PickConfirmation can be created with valid data."""
        confirmation = PickConfirmation(
            pickId=1, pickSuccessful=True, errorMessage=None, itemBarcode=12345
        )
        assert confirmation.pickId == 1
        assert confirmation.pickSuccessful is True
        assert confirmation.errorMessage is None
        assert confirmation.itemBarcode == 12345

    def test_pick_confirmation_with_error_message(self):
        """Test that PickConfirmation can include error message."""
        confirmation = PickConfirmation(
            pickId=2,
            pickSuccessful=False,
            errorMessage="Door is open",
            itemBarcode=0,
        )
        assert confirmation.pickSuccessful is False
        assert confirmation.errorMessage == "Door is open"

    def test_pick_confirmation_json_serialization(self):
        """Test that PickConfirmation can be serialized to JSON."""
        confirmation = PickConfirmation(
            pickId=1, pickSuccessful=True, errorMessage=None, itemBarcode=54321
        )
        json_str = json.dumps(confirmation.model_dump())
        assert "pickId" in json_str
        assert "pickSuccessful" in json_str
        assert "itemBarcode" in json_str


class TestStackLightStatusCallback:
    """Tests for stack_light_status_callback."""

    def test_stack_light_status_callback_operational(self, robot_cell_client_node):
        """Test that callback updates status to OPERATIONAL."""
        msg = Int32()
        msg.data = StackLightState.OPERATIONAL.value
        robot_cell_client_node.stack_light_status_callback(msg)
        assert robot_cell_client_node._stack_light_status == StackLightState.OPERATIONAL

    def test_stack_light_status_callback_paused(self, robot_cell_client_node):
        """Test that callback updates status to PAUSED."""
        msg = Int32()
        msg.data = StackLightState.PAUSED.value
        robot_cell_client_node.stack_light_status_callback(msg)
        assert robot_cell_client_node._stack_light_status == StackLightState.PAUSED

    def test_stack_light_status_callback_emergency(self, robot_cell_client_node):
        """Test that callback updates status to EMERGENCY."""
        msg = Int32()
        msg.data = StackLightState.EMERGENCY.value
        robot_cell_client_node.stack_light_status_callback(msg)
        assert robot_cell_client_node._stack_light_status == StackLightState.EMERGENCY

    def test_stack_light_status_callback_initializing(self, robot_cell_client_node):
        """Test that callback updates status to INITIALIZING."""
        msg = Int32()
        msg.data = StackLightState.INITIALIZING.value
        robot_cell_client_node.stack_light_status_callback(msg)
        assert robot_cell_client_node._stack_light_status == StackLightState.INITIALIZING

    def test_stack_light_status_callback_multiple_updates(self, robot_cell_client_node):
        """Test that callback can update status multiple times."""
        states = [
            StackLightState.OPERATIONAL,
            StackLightState.PAUSED,
            StackLightState.EMERGENCY,
        ]
        for state in states:
            msg = Int32()
            msg.data = state.value
            robot_cell_client_node.stack_light_status_callback(msg)
            assert robot_cell_client_node._stack_light_status == state


class TestGetBarcodeService:
    """Tests for get_barcode method."""

    def test_get_barcode_success(self, robot_cell_client_node):
        """Test that get_barcode successfully retrieves barcode from service."""
        test_barcode = 54321

        mock_response = MagicMock()
        mock_response.message = str(test_barcode)

        mock_future = MagicMock()
        mock_future.result.return_value = mock_response

        with patch.object(
            robot_cell_client_node._scanner_client, "wait_for_service", return_value=True
        ):
            with patch.object(
                robot_cell_client_node._scanner_client, "call_async", return_value=mock_future
            ):
                with patch("threading.Event") as mock_event:
                    mock_event_instance = MagicMock()
                    mock_event_instance.wait.return_value = True
                    mock_event.return_value = mock_event_instance

                    barcode = robot_cell_client_node.get_barcode()
                    assert barcode == test_barcode

    def test_get_barcode_service_unavailable(self, robot_cell_client_node):
        """Test that get_barcode raises error when service is unavailable."""
        with patch.object(
            robot_cell_client_node._scanner_client, "wait_for_service", return_value=False
        ):
            with pytest.raises(RuntimeError, match="Scanner service unavailable"):
                robot_cell_client_node.get_barcode()

    def test_get_barcode_timeout(self, robot_cell_client_node):
        """Test that get_barcode raises timeout error when service times out."""
        mock_future = MagicMock()

        with patch.object(
            robot_cell_client_node._scanner_client, "wait_for_service", return_value=True
        ):
            with patch.object(
                robot_cell_client_node._scanner_client, "call_async", return_value=mock_future
            ):
                with patch("threading.Event") as mock_event:
                    mock_event_instance = MagicMock()
                    mock_event_instance.wait.return_value = False
                    mock_event.return_value = mock_event_instance

                    with pytest.raises(TimeoutError, match="Scanner service timed out"):
                        robot_cell_client_node.get_barcode()

    def test_get_barcode_no_result(self, robot_cell_client_node):
        """Test that get_barcode raises error when service returns no result."""
        mock_future = MagicMock()
        mock_future.result.return_value = None

        with patch.object(
            robot_cell_client_node._scanner_client, "wait_for_service", return_value=True
        ):
            with patch.object(
                robot_cell_client_node._scanner_client, "call_async", return_value=mock_future
            ):
                with patch("threading.Event") as mock_event:
                    mock_event_instance = MagicMock()
                    mock_event_instance.wait.return_value = True
                    mock_event.return_value = mock_event_instance

                    with pytest.raises(RuntimeError, match="Scanner service returned no result"):
                        robot_cell_client_node.get_barcode()


class TestPickPublishing:
    """Tests for pick request and response publishing."""

    def test_publish_pick_request(self, robot_cell_client_node):
        """Test that pick request is published correctly."""
        with patch.object(robot_cell_client_node._pick_request_pub, "publish") as mock_publish:
            request = PickRequest(pickId=1, quantity=5)
            req_msg = String()
            req_msg.data = json.dumps({"pickId": request.pickId, "quantity": request.quantity})
            robot_cell_client_node._pick_request_pub.publish(req_msg)

            mock_publish.assert_called_once()
            published_msg = mock_publish.call_args[0][0]
            assert isinstance(published_msg, String)
            data = json.loads(published_msg.data)
            assert data["pickId"] == 1
            assert data["quantity"] == 5

    def test_publish_pick_response_successful(self, robot_cell_client_node):
        """Test that successful pick response is published correctly."""
        with patch.object(robot_cell_client_node._pick_response_pub, "publish") as mock_publish:
            confirmation = PickConfirmation(
                pickId=1, pickSuccessful=True, errorMessage=None, itemBarcode=12345
            )
            res_msg = String()
            res_msg.data = json.dumps(confirmation.model_dump())
            robot_cell_client_node._pick_response_pub.publish(res_msg)

            mock_publish.assert_called_once()
            published_msg = mock_publish.call_args[0][0]
            data = json.loads(published_msg.data)
            assert data["pickSuccessful"] is True
            assert data["itemBarcode"] == 12345

    def test_publish_pick_response_failed(self, robot_cell_client_node):
        """Test that failed pick response is published correctly."""
        with patch.object(robot_cell_client_node._pick_response_pub, "publish") as mock_publish:
            confirmation = PickConfirmation(
                pickId=2,
                pickSuccessful=False,
                errorMessage="Door is open",
                itemBarcode=0,
            )
            res_msg = String()
            res_msg.data = json.dumps(confirmation.model_dump())
            robot_cell_client_node._pick_response_pub.publish(res_msg)

            mock_publish.assert_called_once()
            published_msg = mock_publish.call_args[0][0]
            data = json.loads(published_msg.data)
            assert data["pickSuccessful"] is False
            assert "Door is open" in data["errorMessage"]


class TestProcessPickOperational:
    """Tests for process_pick when system is operational."""

    def test_process_pick_operational_success(self, robot_cell_client_node):
        """Test successful pick when system is operational."""
        robot_cell_client_node._stack_light_status = StackLightState.OPERATIONAL
        test_barcode = 54321

        with patch.object(
            robot_cell_client_node, "get_barcode", return_value=test_barcode
        ):
            with patch.object(
                robot_cell_client_node._pick_request_pub, "publish"
            ) as mock_req_pub:
                with patch.object(
                    robot_cell_client_node._pick_response_pub, "publish"
                ) as mock_res_pub:
                    with patch("httpx.AsyncClient") as mock_client:
                        mock_async_client = AsyncMock()
                        mock_client.return_value.__aenter__.return_value = mock_async_client
                        mock_async_client.post.return_value.status_code = 200

                        request = PickRequest(pickId=1, quantity=5)
                        run_async(robot_cell_client_node.process_pick(request))

                        mock_req_pub.assert_called_once()
                        mock_res_pub.assert_called_once()
                        mock_async_client.post.assert_called_once()

                        res_msg = mock_res_pub.call_args[0][0]
                        data = json.loads(res_msg.data)
                        assert data["pickSuccessful"] is True
                        assert data["itemBarcode"] == test_barcode


class TestProcessPickPaused:
    """Tests for process_pick when system is paused."""

    def test_process_pick_paused_door_open(self, robot_cell_client_node):
        """Test that pick fails when door is open (PAUSED state)."""
        robot_cell_client_node._stack_light_status = StackLightState.PAUSED
        test_barcode = 54321

        with patch.object(
            robot_cell_client_node, "get_barcode", return_value=test_barcode
        ):
            with patch.object(
                robot_cell_client_node._pick_request_pub, "publish"
            ) as mock_req_pub:
                with patch.object(
                    robot_cell_client_node._pick_response_pub, "publish"
                ) as mock_res_pub:
                    with patch("httpx.AsyncClient") as mock_client:
                        mock_async_client = AsyncMock()
                        mock_client.return_value.__aenter__.return_value = mock_async_client
                        mock_async_client.post.return_value.status_code = 200

                        request = PickRequest(pickId=1, quantity=5)
                        run_async(robot_cell_client_node.process_pick(request))

                        res_msg = mock_res_pub.call_args[0][0]
                        data = json.loads(res_msg.data)
                        assert data["pickSuccessful"] is False
                        assert "PAUSED" in data["errorMessage"]


class TestProcessPickEmergency:
    """Tests for process_pick when emergency stop is pressed."""

    def test_process_pick_emergency(self, robot_cell_client_node):
        """Test that pick fails when e-stop is pressed (EMERGENCY state)."""
        robot_cell_client_node._stack_light_status = StackLightState.EMERGENCY
        test_barcode = 54321

        with patch.object(
            robot_cell_client_node, "get_barcode", return_value=test_barcode
        ):
            with patch.object(
                robot_cell_client_node._pick_request_pub, "publish"
            ) as mock_req_pub:
                with patch.object(
                    robot_cell_client_node._pick_response_pub, "publish"
                ) as mock_res_pub:
                    with patch("httpx.AsyncClient") as mock_client:
                        mock_async_client = AsyncMock()
                        mock_client.return_value.__aenter__.return_value = mock_async_client
                        mock_async_client.post.return_value.status_code = 200

                        request = PickRequest(pickId=1, quantity=5)
                        run_async(robot_cell_client_node.process_pick(request))

                        res_msg = mock_res_pub.call_args[0][0]
                        data = json.loads(res_msg.data)
                        assert data["pickSuccessful"] is False
                        assert "EMERGENCY" in data["errorMessage"]


class TestProcessPickInitializing:
    """Tests for process_pick during system initialization."""

    def test_process_pick_initializing(self, robot_cell_client_node):
        """Test that pick fails while system is initializing."""
        robot_cell_client_node._stack_light_status = StackLightState.INITIALIZING
        test_barcode = 54321

        with patch.object(
            robot_cell_client_node, "get_barcode", return_value=test_barcode
        ):
            with patch.object(
                robot_cell_client_node._pick_request_pub, "publish"
            ) as mock_req_pub:
                with patch.object(
                    robot_cell_client_node._pick_response_pub, "publish"
                ) as mock_res_pub:
                    with patch("httpx.AsyncClient") as mock_client:
                        mock_async_client = AsyncMock()
                        mock_client.return_value.__aenter__.return_value = mock_async_client
                        mock_async_client.post.return_value.status_code = 200

                        request = PickRequest(pickId=1, quantity=5)
                        run_async(robot_cell_client_node.process_pick(request))

                        res_msg = mock_res_pub.call_args[0][0]
                        data = json.loads(res_msg.data)
                        assert data["pickSuccessful"] is False
                        assert "INITIALIZING" in data["errorMessage"]


class TestProcessPickErrorHandling:
    """Tests for error handling in process_pick."""

    def test_process_pick_barcode_error(self, robot_cell_client_node):
        """Test that pick fails gracefully when barcode retrieval fails."""
        robot_cell_client_node._stack_light_status = StackLightState.OPERATIONAL

        with patch.object(
            robot_cell_client_node,
            "get_barcode",
            side_effect=RuntimeError("Scanner service unavailable"),
        ):
            with patch.object(
                robot_cell_client_node._pick_request_pub, "publish"
            ) as mock_req_pub:
                with patch.object(
                    robot_cell_client_node._pick_response_pub, "publish"
                ) as mock_res_pub:
                    with patch("httpx.AsyncClient") as mock_client:
                        mock_async_client = AsyncMock()
                        mock_client.return_value.__aenter__.return_value = mock_async_client
                        mock_async_client.post.return_value.status_code = 200

                        request = PickRequest(pickId=1, quantity=5)
                        run_async(robot_cell_client_node.process_pick(request))

                        res_msg = mock_res_pub.call_args[0][0]
                        data = json.loads(res_msg.data)
                        assert data["pickSuccessful"] is False
                        assert data["itemBarcode"] == 0
                        assert "Unknown error" in data["errorMessage"]

    def test_process_pick_wms_confirmation_error(self, robot_cell_client_node):
        """Test that pick completes even if WMS confirmation fails."""
        robot_cell_client_node._stack_light_status = StackLightState.OPERATIONAL
        test_barcode = 54321

        with patch.object(
            robot_cell_client_node, "get_barcode", return_value=test_barcode
        ):
            with patch.object(
                robot_cell_client_node._pick_request_pub, "publish"
            ) as mock_req_pub:
                with patch.object(
                    robot_cell_client_node._pick_response_pub, "publish"
                ) as mock_res_pub:
                    with patch("httpx.AsyncClient") as mock_client:
                        mock_async_client = AsyncMock()
                        mock_client.return_value.__aenter__.return_value = mock_async_client
                        mock_async_client.post.side_effect = RuntimeError("Connection failed")

                        request = PickRequest(pickId=1, quantity=5)
                        # Should not raise even if WMS confirmation fails
                        run_async(robot_cell_client_node.process_pick(request))

                        res_msg = mock_res_pub.call_args[0][0]
                        data = json.loads(res_msg.data)
                        assert data["pickSuccessful"] is True


class TestProcessPickSequence:
    """Tests for sequences of pick requests."""

    def test_process_multiple_picks_operational(self, robot_cell_client_node):
        """Test processing multiple pick requests while operational."""
        robot_cell_client_node._stack_light_status = StackLightState.OPERATIONAL

        with patch.object(
            robot_cell_client_node, "get_barcode"
        ) as mock_barcode:
            mock_barcode.side_effect = [11111, 22222, 33333]

            with patch.object(
                robot_cell_client_node._pick_response_pub, "publish"
            ) as mock_res_pub:
                with patch("httpx.AsyncClient") as mock_client:
                    mock_async_client = AsyncMock()
                    mock_client.return_value.__aenter__.return_value = mock_async_client
                    mock_async_client.post.return_value.status_code = 200

                    async def run_picks():
                        for i in range(3):
                            request = PickRequest(pickId=i, quantity=5)
                            await robot_cell_client_node.process_pick(request)

                    run_async(run_picks())

                    assert mock_res_pub.call_count == 3
                    assert mock_barcode.call_count == 3

    def test_process_pick_state_change_mid_sequence(self, robot_cell_client_node):
        """Test processing picks when state changes mid-sequence."""
        with patch.object(
            robot_cell_client_node, "get_barcode"
        ) as mock_barcode:
            mock_barcode.side_effect = [11111, 22222]

            with patch.object(
                robot_cell_client_node._pick_response_pub, "publish"
            ) as mock_res_pub:
                with patch("httpx.AsyncClient") as mock_client:
                    mock_async_client = AsyncMock()
                    mock_client.return_value.__aenter__.return_value = mock_async_client
                    mock_async_client.post.return_value.status_code = 200

                    async def run_picks_with_state_change():
                        # First pick - operational
                        robot_cell_client_node._stack_light_status = StackLightState.OPERATIONAL
                        request = PickRequest(pickId=1, quantity=5)
                        await robot_cell_client_node.process_pick(request)

                        # State changes to paused
                        robot_cell_client_node._stack_light_status = StackLightState.PAUSED
                        request = PickRequest(pickId=2, quantity=5)
                        await robot_cell_client_node.process_pick(request)

                    run_async(run_picks_with_state_change())

                    # Check results
                    res_msgs = [call[0][0] for call in mock_res_pub.call_args_list]
                    data1 = json.loads(res_msgs[0].data)
                    data2 = json.loads(res_msgs[1].data)

                    assert data1["pickSuccessful"] is True
                    assert data2["pickSuccessful"] is False


class TestRobotCellClientRequirements:
    """Tests verifying robot cell client requirements from specification."""

    def test_client_receives_pick_requests(self, robot_cell_client_node):
        """Requirement: Client should receive pick requests via HTTP."""
        assert robot_cell_client_node._pick_request_pub is not None

    def test_client_publishes_pick_requests(self, robot_cell_client_node):
        """Requirement: Client should publish pick requests to HMI."""
        publishers = robot_cell_client_node.get_publishers_info_by_topic("pick_request")
        assert len(publishers) > 0

    def test_client_publishes_pick_responses(self, robot_cell_client_node):
        """Requirement: Client should publish pick responses to HMI."""
        publishers = robot_cell_client_node.get_publishers_info_by_topic("pick_response")
        assert len(publishers) > 0

    def test_client_calls_scanner_service(self, robot_cell_client_node):
        """Requirement: Client should call scanner service to get barcode."""
        assert robot_cell_client_node._scanner_client is not None

    def test_client_monitors_stack_light_status(self, robot_cell_client_node):
        """Requirement: Client should monitor stack light status."""
        subscriptions = robot_cell_client_node.get_subscriptions_info_by_topic(
            "/stack_light_status"
        )
        assert len(subscriptions) > 0

    def test_client_respects_door_closed(self, robot_cell_client_node):
        """Requirement: Client should respond with pickSuccessful=false when door open."""
        robot_cell_client_node._stack_light_status = StackLightState.PAUSED
        assert robot_cell_client_node._stack_light_status == StackLightState.PAUSED

    def test_client_respects_emergency_stop(self, robot_cell_client_node):
        """Requirement: Client should respond with pickSuccessful=false when e-stop pressed."""
        robot_cell_client_node._stack_light_status = StackLightState.EMERGENCY
        assert robot_cell_client_node._stack_light_status == StackLightState.EMERGENCY

    def test_client_returns_barcode_in_response(self, robot_cell_client_node):
        """Requirement: Client should return barcode in pick confirmation."""
        confirmation = PickConfirmation(
            pickId=1, pickSuccessful=True, errorMessage=None, itemBarcode=12345
        )
        assert confirmation.itemBarcode == 12345

    def test_client_includes_pick_id_in_response(self, robot_cell_client_node):
        """Requirement: Client should include pickId in response."""
        confirmation = PickConfirmation(
            pickId=99, pickSuccessful=True, errorMessage=None, itemBarcode=12345
        )
        assert confirmation.pickId == 99

    def test_client_can_return_error_message(self, robot_cell_client_node):
        """Requirement: Client should optionally return error message."""
        confirmation = PickConfirmation(
            pickId=1,
            pickSuccessful=False,
            errorMessage="Door is open",
            itemBarcode=0,
        )
        assert confirmation.errorMessage is not None
        assert "Door" in confirmation.errorMessage


class TestRobotCellClientIntegration:
    """Integration tests for complete robot cell client workflows."""

    def test_complete_pick_workflow_success(self, robot_cell_client_node):
        """Test complete workflow: receive request -> get barcode -> send confirmation."""
        robot_cell_client_node._stack_light_status = StackLightState.OPERATIONAL
        test_barcode = 54321

        with patch.object(
            robot_cell_client_node, "get_barcode", return_value=test_barcode
        ):
            with patch.object(
                robot_cell_client_node._pick_request_pub, "publish"
            ) as mock_req_pub:
                with patch.object(
                    robot_cell_client_node._pick_response_pub, "publish"
                ) as mock_res_pub:
                    with patch("httpx.AsyncClient") as mock_client:
                        mock_async_client = AsyncMock()
                        mock_client.return_value.__aenter__.return_value = mock_async_client
                        mock_async_client.post.return_value.status_code = 200

                        request = PickRequest(pickId=42, quantity=3)
                        run_async(robot_cell_client_node.process_pick(request))

                        # Verify request was published
                        req_msg = mock_req_pub.call_args[0][0]
                        req_data = json.loads(req_msg.data)
                        assert req_data["pickId"] == 42
                        assert req_data["quantity"] == 3

                        # Verify response was published
                        res_msg = mock_res_pub.call_args[0][0]
                        res_data = json.loads(res_msg.data)
                        assert res_data["pickId"] == 42
                        assert res_data["pickSuccessful"] is True
                        assert res_data["itemBarcode"] == test_barcode

                        # Verify WMS confirmation was sent
                        mock_async_client.post.assert_called_once()

    def test_complete_pick_workflow_failure_door_open(self, robot_cell_client_node):
        """Test complete workflow failure: door open prevents pick."""
        robot_cell_client_node._stack_light_status = StackLightState.PAUSED
        test_barcode = 54321

        with patch.object(
            robot_cell_client_node, "get_barcode", return_value=test_barcode
        ):
            with patch.object(
                robot_cell_client_node._pick_request_pub, "publish"
            ) as mock_req_pub:
                with patch.object(
                    robot_cell_client_node._pick_response_pub, "publish"
                ) as mock_res_pub:
                    with patch("httpx.AsyncClient") as mock_client:
                        mock_async_client = AsyncMock()
                        mock_client.return_value.__aenter__.return_value = mock_async_client
                        mock_async_client.post.return_value.status_code = 200

                        request = PickRequest(pickId=1, quantity=5)
                        run_async(robot_cell_client_node.process_pick(request))

                        # Verify response indicates failure
                        res_msg = mock_res_pub.call_args[0][0]
                        res_data = json.loads(res_msg.data)
                        assert res_data["pickSuccessful"] is False
                        assert "PAUSED" in res_data["errorMessage"]
                        assert res_data["itemBarcode"] == test_barcode  # Barcode still scanned

    def test_complete_pick_workflow_failure_emergency(self, robot_cell_client_node):
        """Test complete workflow failure: emergency stop prevents pick."""
        robot_cell_client_node._stack_light_status = StackLightState.EMERGENCY
        test_barcode = 54321

        with patch.object(
            robot_cell_client_node, "get_barcode", return_value=test_barcode
        ):
            with patch.object(
                robot_cell_client_node._pick_response_pub, "publish"
            ) as mock_res_pub:
                with patch("httpx.AsyncClient") as mock_client:
                    mock_async_client = AsyncMock()
                    mock_client.return_value.__aenter__.return_value = mock_async_client
                    mock_async_client.post.return_value.status_code = 200

                    request = PickRequest(pickId=1, quantity=5)
                    run_async(robot_cell_client_node.process_pick(request))

                    # Verify response indicates failure
                    res_msg = mock_res_pub.call_args[0][0]
                    res_data = json.loads(res_msg.data)
                    assert res_data["pickSuccessful"] is False
                    assert "EMERGENCY" in res_data["errorMessage"]

    def test_pick_workflow_with_barcode_error(self, robot_cell_client_node):
        """Test workflow when barcode scanning fails."""
        robot_cell_client_node._stack_light_status = StackLightState.OPERATIONAL

        with patch.object(
            robot_cell_client_node,
            "get_barcode",
            side_effect=TimeoutError("Barcode timeout"),
        ):
            with patch.object(
                robot_cell_client_node._pick_response_pub, "publish"
            ) as mock_res_pub:
                with patch("httpx.AsyncClient") as mock_client:
                    mock_async_client = AsyncMock()
                    mock_client.return_value.__aenter__.return_value = mock_async_client
                    mock_async_client.post.return_value.status_code = 200

                    request = PickRequest(pickId=1, quantity=5)
                    run_async(robot_cell_client_node.process_pick(request))

                    # Verify response indicates failure
                    res_msg = mock_res_pub.call_args[0][0]
                    res_data = json.loads(res_msg.data)
                    assert res_data["pickSuccessful"] is False
                    assert res_data["itemBarcode"] == 0
                    assert "Unknown error" in res_data["errorMessage"]
