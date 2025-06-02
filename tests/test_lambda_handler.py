"""Comprehensive test suite for the Parts Service Lambda handler."""

import json
import uuid
from datetime import datetime
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

from src.parts_service.lambda_handler import (
    PartValidationError,
    create_part,
    delete_part,
    get_current_timestamp,
    get_part,
    get_table_name,
    lambda_handler,
    update_part,
    validate_additional_fields,
    validate_part_data,
)


@pytest.fixture
def dynamodb_table():
    """Create a mock DynamoDB table for testing."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        # Create table
        table = dynamodb.create_table(
            TableName="unt-part-svc",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        yield table


@pytest.fixture
def sample_part_data():
    """Sample valid part data for testing."""
    return {
        "accountId": "acc123",
        "customerId": "cust456",
        "locationId": "loc789",
        "categoryProductId": 101,
        "categoryId": 5,
        "category": "Electronics",
        "segmentId": 20,
        "segment": "Consumer",
        "partTerminologyId": 1001,
        "partTerminologyName": "Resistor",
        "additionalFields": [
            {"referenceFieldNumber": 1, "fieldName": "color", "codedValue": "red"},
            {"fieldName": "size", "codedValue": "small"},
        ],
    }


@pytest.fixture
def sample_lambda_event():
    """Sample Lambda event structure."""
    return {
        "httpMethod": "POST",
        "pathParameters": None,
        "body": None,
        "requestContext": {"requestId": "test-request-id"},
    }


class TestPartValidation:
    """Test part data validation functions."""

    def test_validate_part_data_success(self, sample_part_data):
        """Test successful validation of part data."""
        result = validate_part_data(sample_part_data)

        assert result["accountId"] == "acc123"
        assert result["category"] == "Electronics"
        assert result["categoryProductId"] == 101
        assert len(result["additionalFields"]) == 2

    def test_validate_part_data_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        incomplete_data = {
            "accountId": "acc123",
            "category": "Electronics",
            # Missing segment and partTerminologyName
        }

        with pytest.raises(PartValidationError) as exc_info:
            validate_part_data(incomplete_data)

        assert "Missing required fields" in str(exc_info.value)

    def test_validate_part_data_invalid_type(self):
        """Test validation fails with invalid data types."""
        invalid_data = {
            "accountId": "acc123",
            "category": "Electronics",
            "segment": "Consumer",
            "partTerminologyName": "Resistor",
            "categoryProductId": "not_a_number",
        }

        with pytest.raises(PartValidationError) as exc_info:
            validate_part_data(invalid_data)

        assert "must be a number" in str(exc_info.value)

    def test_validate_part_data_update_mode(self, sample_part_data):
        """Test validation in update mode (no required field check)."""
        partial_data = {"category": "Updated Category"}

        result = validate_part_data(partial_data, is_update=True)
        assert result["category"] == "Updated Category"

    def test_validate_additional_fields_success(self):
        """Test successful validation of additional fields."""
        valid_fields = [
            {"fieldName": "color", "codedValue": "red"},
            {"referenceFieldNumber": 1, "fieldName": "size", "codedValue": "large"},
        ]

        # Should not raise an exception
        validate_additional_fields(valid_fields)

    def test_validate_additional_fields_invalid_structure(self):
        """Test validation fails with invalid additional fields structure."""
        invalid_fields = [
            {"fieldName": "color"}  # Missing codedValue
        ]

        with pytest.raises(PartValidationError) as exc_info:
            validate_additional_fields(invalid_fields)

        assert "Missing required fields in additionalFields" in str(exc_info.value)


class TestUtilityFunctions:
    """Test utility functions."""

    def test_get_current_timestamp(self):
        """Test timestamp generation."""
        timestamp = get_current_timestamp()

        # Should be a valid ISO format timestamp
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None

    @patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "custom-table"})
    def test_get_table_name_from_env(self):
        """Test getting table name from environment variable."""
        assert get_table_name() == "custom-table"

    @patch.dict("os.environ", {}, clear=True)
    def test_get_table_name_default(self):
        """Test getting default table name."""
        assert get_table_name() == "unt-part-svc"


class TestCreatePart:
    """Test create part functionality."""

    def test_create_part_success(
        self, dynamodb_table, sample_part_data, sample_lambda_event
    ):
        """Test successful part creation."""
        event = sample_lambda_event.copy()
        event["body"] = json.dumps({"part": sample_part_data})

        with patch("src.parts_service.lambda_handler.dynamodb") as mock_dynamodb:
            mock_dynamodb.Table.return_value = dynamodb_table

            result = create_part(event)

            assert result["statusCode"] == 201
            body = json.loads(result["body"])
            assert "uuid" in body
            assert body["message"] == "Part created successfully"

    def test_create_part_missing_part_field(self, sample_lambda_event):
        """Test create part fails when 'part' field is missing."""
        event = sample_lambda_event.copy()
        event["body"] = json.dumps({"other_field": "value"})

        result = create_part(event)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Missing 'part' in request body" in body["error"]

    def test_create_part_invalid_json(self, sample_lambda_event):
        """Test create part fails with invalid JSON."""
        event = sample_lambda_event.copy()
        event["body"] = "invalid json"

        result = create_part(event)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Invalid JSON" in body["error"]

    def test_create_part_validation_error(self, sample_lambda_event):
        """Test create part fails with validation error."""
        event = sample_lambda_event.copy()
        invalid_part = {
            "accountId": "acc123"
            # Missing required fields
        }
        event["body"] = json.dumps({"part": invalid_part})

        result = create_part(event)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Missing required fields" in body["error"]


class TestGetPart:
    """Test get part functionality."""

    def test_get_part_success(self, dynamodb_table, sample_part_data):
        """Test successful part retrieval."""
        # First create a part
        part_uuid = str(uuid.uuid4())
        item = {
            "PK": part_uuid,
            "SK": sample_part_data["accountId"],
            "createdAt": get_current_timestamp(),
            **sample_part_data,
        }
        dynamodb_table.put_item(Item=item)

        event = {"pathParameters": {"uuid": part_uuid}}

        with patch("src.parts_service.lambda_handler.dynamodb") as mock_dynamodb:
            mock_dynamodb.Table.return_value = dynamodb_table

            result = get_part(event)

            assert result["statusCode"] == 200
            body = json.loads(result["body"])
            assert body["part"]["PK"] == part_uuid

    def test_get_part_not_found(self, dynamodb_table):
        """Test get part when part doesn't exist."""
        event = {"pathParameters": {"uuid": str(uuid.uuid4())}}

        with patch("src.parts_service.lambda_handler.dynamodb") as mock_dynamodb:
            mock_dynamodb.Table.return_value = dynamodb_table

            result = get_part(event)

            assert result["statusCode"] == 404
            body = json.loads(result["body"])
            assert "Part not found" in body["error"]

    def test_get_part_missing_uuid(self):
        """Test get part fails when UUID is missing."""
        event = {"pathParameters": None}

        result = get_part(event)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Missing UUID" in body["error"]

    def test_get_part_deleted(self, dynamodb_table, sample_part_data):
        """Test get part fails when part is deleted."""
        # Create a deleted part
        part_uuid = str(uuid.uuid4())
        item = {
            "PK": part_uuid,
            "SK": sample_part_data["accountId"],
            "createdAt": get_current_timestamp(),
            "deletedAt": get_current_timestamp(),
            **sample_part_data,
        }
        dynamodb_table.put_item(Item=item)

        event = {"pathParameters": {"uuid": part_uuid}}

        with patch("src.parts_service.lambda_handler.dynamodb") as mock_dynamodb:
            mock_dynamodb.Table.return_value = dynamodb_table

            result = get_part(event)

            assert result["statusCode"] == 404


class TestUpdatePart:
    """Test update part functionality."""

    def test_update_part_success(self, dynamodb_table, sample_part_data):
        """Test successful part update."""
        # First create a part
        part_uuid = str(uuid.uuid4())
        item = {
            "PK": part_uuid,
            "SK": sample_part_data["accountId"],
            "createdAt": get_current_timestamp(),
            **sample_part_data,
        }
        dynamodb_table.put_item(Item=item)

        event = {
            "pathParameters": {"uuid": part_uuid},
            "body": json.dumps(
                {"part": {"category": "Updated Category", "segment": "Updated Segment"}}
            ),
        }

        with patch("src.parts_service.lambda_handler.dynamodb") as mock_dynamodb:
            mock_dynamodb.Table.return_value = dynamodb_table

            result = update_part(event)

            assert result["statusCode"] == 200
            body = json.loads(result["body"])
            assert body["message"] == "Part updated successfully"
            assert body["part"]["category"] == "Updated Category"

    def test_update_part_not_found(self, dynamodb_table):
        """Test update part when part doesn't exist."""
        event = {
            "pathParameters": {"uuid": str(uuid.uuid4())},
            "body": json.dumps({"part": {"category": "Updated"}}),
        }

        with patch("src.parts_service.lambda_handler.dynamodb") as mock_dynamodb:
            mock_dynamodb.Table.return_value = dynamodb_table

            result = update_part(event)

            assert result["statusCode"] == 404
            body = json.loads(result["body"])
            assert "Part not found" in body["error"]

    def test_update_part_missing_uuid(self):
        """Test update part fails when UUID is missing."""
        event = {
            "pathParameters": None,
            "body": json.dumps({"part": {"category": "Updated"}}),
        }

        result = update_part(event)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Missing UUID" in body["error"]

    def test_update_part_missing_part_field(self):
        """Test update part fails when 'part' field is missing."""
        event = {
            "pathParameters": {"uuid": str(uuid.uuid4())},
            "body": json.dumps({"other_field": "value"}),
        }

        result = update_part(event)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Missing 'part' in request body" in body["error"]


class TestDeletePart:
    """Test delete part functionality."""

    def test_delete_part_success(self, dynamodb_table, sample_part_data):
        """Test successful part deletion (soft delete)."""
        # First create a part
        part_uuid = str(uuid.uuid4())
        item = {
            "PK": part_uuid,
            "SK": sample_part_data["accountId"],
            "createdAt": get_current_timestamp(),
            **sample_part_data,
        }
        dynamodb_table.put_item(Item=item)

        event = {"pathParameters": {"uuid": part_uuid}}

        with patch("src.parts_service.lambda_handler.dynamodb") as mock_dynamodb:
            mock_dynamodb.Table.return_value = dynamodb_table

            result = delete_part(event)

            assert result["statusCode"] == 200
            body = json.loads(result["body"])
            assert body["message"] == "Part deleted successfully"

            # Verify the part now has deletedAt timestamp
            response = dynamodb_table.get_item(
                Key={"PK": part_uuid, "SK": sample_part_data["accountId"]}
            )
            assert "deletedAt" in response["Item"]

    def test_delete_part_not_found(self, dynamodb_table):
        """Test delete part when part doesn't exist."""
        event = {"pathParameters": {"uuid": str(uuid.uuid4())}}

        with patch("src.parts_service.lambda_handler.dynamodb") as mock_dynamodb:
            mock_dynamodb.Table.return_value = dynamodb_table

            result = delete_part(event)

            assert result["statusCode"] == 404
            body = json.loads(result["body"])
            assert "Part not found" in body["error"]

    def test_delete_part_missing_uuid(self):
        """Test delete part fails when UUID is missing."""
        event = {"pathParameters": None}

        result = delete_part(event)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Missing UUID" in body["error"]


class TestLambdaHandler:
    """Test main lambda handler function."""

    def test_lambda_handler_get_method(self, dynamodb_table, sample_part_data):
        """Test lambda handler with GET method."""
        # Create a part first
        part_uuid = str(uuid.uuid4())
        item = {
            "PK": part_uuid,
            "SK": sample_part_data["accountId"],
            "createdAt": get_current_timestamp(),
            **sample_part_data,
        }
        dynamodb_table.put_item(Item=item)

        event = {"httpMethod": "GET", "pathParameters": {"uuid": part_uuid}}

        with patch("src.parts_service.lambda_handler.dynamodb") as mock_dynamodb:
            mock_dynamodb.Table.return_value = dynamodb_table

            result = lambda_handler(event, {})

            assert result["statusCode"] == 200

    def test_lambda_handler_post_method(self, dynamodb_table, sample_part_data):
        """Test lambda handler with POST method."""
        event = {"httpMethod": "POST", "body": json.dumps({"part": sample_part_data})}

        with patch("src.parts_service.lambda_handler.dynamodb") as mock_dynamodb:
            mock_dynamodb.Table.return_value = dynamodb_table

            result = lambda_handler(event, {})

            assert result["statusCode"] == 201

    def test_lambda_handler_put_method(self, dynamodb_table, sample_part_data):
        """Test lambda handler with PUT method."""
        # Create a part first
        part_uuid = str(uuid.uuid4())
        item = {
            "PK": part_uuid,
            "SK": sample_part_data["accountId"],
            "createdAt": get_current_timestamp(),
            **sample_part_data,
        }
        dynamodb_table.put_item(Item=item)

        event = {
            "httpMethod": "PUT",
            "pathParameters": {"uuid": part_uuid},
            "body": json.dumps({"part": {"category": "Updated"}}),
        }

        with patch("src.parts_service.lambda_handler.dynamodb") as mock_dynamodb:
            mock_dynamodb.Table.return_value = dynamodb_table

            result = lambda_handler(event, {})

            assert result["statusCode"] == 200

    def test_lambda_handler_delete_method(self, dynamodb_table, sample_part_data):
        """Test lambda handler with DELETE method."""
        # Create a part first
        part_uuid = str(uuid.uuid4())
        item = {
            "PK": part_uuid,
            "SK": sample_part_data["accountId"],
            "createdAt": get_current_timestamp(),
            **sample_part_data,
        }
        dynamodb_table.put_item(Item=item)

        event = {"httpMethod": "DELETE", "pathParameters": {"uuid": part_uuid}}

        with patch("src.parts_service.lambda_handler.dynamodb") as mock_dynamodb:
            mock_dynamodb.Table.return_value = dynamodb_table

            result = lambda_handler(event, {})

            assert result["statusCode"] == 200

    def test_lambda_handler_api_gateway_v2_format(
        self, dynamodb_table, sample_part_data
    ):
        """Test lambda handler with API Gateway v2 event format."""
        part_uuid = str(uuid.uuid4())
        item = {
            "PK": part_uuid,
            "SK": sample_part_data["accountId"],
            "createdAt": get_current_timestamp(),
            **sample_part_data,
        }
        dynamodb_table.put_item(Item=item)

        event = {
            "requestContext": {"http": {"method": "GET"}},
            "pathParameters": {"uuid": part_uuid},
        }

        with patch("src.parts_service.lambda_handler.dynamodb") as mock_dynamodb:
            mock_dynamodb.Table.return_value = dynamodb_table

            result = lambda_handler(event, {})

            assert result["statusCode"] == 200

    def test_lambda_handler_unsupported_method(self):
        """Test lambda handler with unsupported HTTP method."""
        event = {"httpMethod": "PATCH"}

        result = lambda_handler(event, {})

        assert result["statusCode"] == 405
        body = json.loads(result["body"])
        assert "Method PATCH not allowed" in body["error"]

    def test_lambda_handler_missing_method(self):
        """Test lambda handler when HTTP method is missing."""
        event = {}

        result = lambda_handler(event, {})

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "HTTP method not found" in body["error"]

    def test_lambda_handler_unexpected_error(self):
        """Test lambda handler handles unexpected errors gracefully."""
        event = {"httpMethod": "GET", "pathParameters": {"uuid": "test-uuid"}}

        with patch(
            "src.parts_service.lambda_handler.get_part",
            side_effect=Exception("Unexpected error"),
        ):
            result = lambda_handler(event, {})

            assert result["statusCode"] == 500
            body = json.loads(result["body"])
            assert "Internal server error" in body["error"]
