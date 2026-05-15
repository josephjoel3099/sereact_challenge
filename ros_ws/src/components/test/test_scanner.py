"""Test suite for the Scanner ROS 2 node."""

from unittest.mock import patch

import pytest
import rclpy
from std_msgs.msg import Int32
from std_srvs.srv import Trigger

from components.scanner import Scanner


@pytest.fixture
def scanner_node():
    """Fixture to provide a Scanner node for tests."""
    rclpy.init()
    node = Scanner()
    yield node
    node.destroy_node()
    rclpy.shutdown()


class TestScannerNodeCreation:
    """Tests for Scanner node initialization."""

    def test_node_creation(self, scanner_node):
        """Test that the Scanner node is created successfully."""
        assert scanner_node is not None
        assert scanner_node.get_name() == "scanner"

    def test_barcode_message_initialization(self, scanner_node):
        """Test that barcode_msg is initialized as Int32."""
        assert isinstance(scanner_node.barcode_msg, Int32)

    def test_publish_rate_configuration(self, scanner_node):
        """Test that barcode publish rate is set correctly."""
        assert scanner_node.barcode_msg_publish_rate == 1

    def test_publisher_initialization(self, scanner_node):
        """Test that the barcode publisher is properly initialized."""
        assert scanner_node.barcode_publisher is not None

    def test_service_initialization(self, scanner_node):
        """Test that the get_latest_barcode service is properly initialized."""
        service_names = scanner_node.get_service_names_and_types()
        service_exists = any("get_latest_barcode" in name for name, _ in service_names)
        assert service_exists, "get_latest_barcode service not found"


class TestBarcodeGeneration:
    """Tests for barcode generation functionality."""

    def test_barcode_generation_range(self, scanner_node):
        """Test that generated barcodes are 5-digit numbers."""
        for _ in range(100):
            barcode = scanner_node.random_barcode_generator()
            assert 10000 <= barcode <= 99999
            assert isinstance(barcode, int)

    def test_barcode_all_5_digits(self, scanner_node):
        """Test that all generated barcodes are exactly 5 digits."""
        for _ in range(50):
            barcode = scanner_node.random_barcode_generator()
            assert len(str(barcode)) == 5

    def test_barcode_generation_variety(self, scanner_node):
        """Test that barcode generator produces varied values."""
        barcodes = [scanner_node.random_barcode_generator() for _ in range(100)]
        unique_barcodes = set(barcodes)
        # With 100 random samples from 90000 possibilities, we should have many unique values
        assert len(unique_barcodes) > 50


class TestBarcodePublishing:
    """Tests for barcode publishing functionality."""

    def test_barcode_message_update(self, scanner_node):
        """Test that barcode_msg is updated when publish_barcode is called."""
        scanner_node.publish_barcode()
        new_value = scanner_node.barcode_msg.data
        assert 10000 <= new_value <= 99999

    def test_publish_barcode_creates_valid_message(self, scanner_node):
        """Test that publish_barcode creates valid Int32 messages."""
        with patch.object(scanner_node.barcode_publisher, "publish") as mock_publish:
            scanner_node.publish_barcode()
            mock_publish.assert_called_once()
            published_msg = mock_publish.call_args[0][0]
            assert isinstance(published_msg, Int32)
            assert 10000 <= published_msg.data <= 99999

    def test_multiple_publishes(self, scanner_node):
        """Test that multiple publish operations work correctly."""
        with patch.object(scanner_node.barcode_publisher, "publish") as mock_publish:
            for _ in range(5):
                scanner_node.publish_barcode()
            assert mock_publish.call_count == 5


class TestServiceFunctionality:
    """Tests for get_latest_barcode service."""

    def test_get_latest_barcode_service(self, scanner_node):
        """Test that the service returns the most recent barcode."""
        test_barcode = 12345
        scanner_node.barcode_msg.data = test_barcode
        request = Trigger.Request()
        response = Trigger.Response()
        result = scanner_node.get_latest_barcode(request, response)
        assert result.success is True
        assert result.message == str(test_barcode)

    def test_service_response_consistency(self, scanner_node):
        """Test that service always returns the most recently published barcode."""
        test_values = [10000, 50000, 99999, 12345, 67890]
        for test_value in test_values:
            scanner_node.barcode_msg.data = test_value
            request = Trigger.Request()
            response = Trigger.Response()
            result = scanner_node.get_latest_barcode(request, response)
            assert result.success is True
            assert result.message == str(test_value)

    def test_multiple_service_calls(self, scanner_node):
        """Test that multiple consecutive service calls work correctly."""
        scanner_node.barcode_msg.data = 54321
        for _ in range(5):
            request = Trigger.Request()
            response = Trigger.Response()
            result = scanner_node.get_latest_barcode(request, response)
            assert result.success is True
            assert result.message == "54321"

    def test_service_message_type(self, scanner_node):
        """Test that service returns a Trigger response."""
        request = Trigger.Request()
        response = Trigger.Response()
        result = scanner_node.get_latest_barcode(request, response)
        assert isinstance(result, Trigger.Response)


class TestBarcodeAndServiceSynchronization:
    """Tests for synchronization between published barcodes and service responses."""

    def test_barcode_and_service_synchronization(self, scanner_node):
        """Test that published barcode and service return value are synchronized."""
        for _ in range(10):
            scanner_node.publish_barcode()
            published_value = scanner_node.barcode_msg.data
            request = Trigger.Request()
            response = Trigger.Response()
            result = scanner_node.get_latest_barcode(request, response)
            assert int(result.message) == published_value

    def test_latest_barcode_after_multiple_publishes(self, scanner_node):
        """Test that service returns the latest barcode after multiple publishes."""
        published_values = []
        for _ in range(10):
            scanner_node.publish_barcode()
            published_values.append(scanner_node.barcode_msg.data)

        request = Trigger.Request()
        response = Trigger.Response()
        result = scanner_node.get_latest_barcode(request, response)
        assert int(result.message) == published_values[-1]


class TestIntegrationWorkflow:
    """Integration tests for complete workflows."""

    def test_complete_barcode_workflow(self, scanner_node):
        """Test complete workflow: generate -> publish -> retrieve via service."""
        published_barcodes = []
        for _ in range(5):
            scanner_node.publish_barcode()
            published_barcodes.append(scanner_node.barcode_msg.data)

        request = Trigger.Request()
        response = Trigger.Response()
        result = scanner_node.get_latest_barcode(request, response)
        assert int(result.message) == published_barcodes[-1]

    def test_barcode_validity_in_workflow(self, scanner_node):
        """Test that all barcodes in workflow are valid."""
        for _ in range(20):
            scanner_node.publish_barcode()
            barcode = scanner_node.barcode_msg.data
            assert 10000 <= barcode <= 99999

            request = Trigger.Request()
            response = Trigger.Response()
            result = scanner_node.get_latest_barcode(request, response)
            assert int(result.message) == barcode

    def test_service_always_returns_string(self, scanner_node):
        """Test that service always returns barcode as string."""
        for _ in range(10):
            scanner_node.publish_barcode()
            request = Trigger.Request()
            response = Trigger.Response()
            result = scanner_node.get_latest_barcode(request, response)
            assert isinstance(result.message, str)
            assert result.message.isdigit()
            assert len(result.message) == 5
