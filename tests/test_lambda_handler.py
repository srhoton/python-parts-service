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
    format_appsync_response,
    get_current_timestamp,
    get_part,
    get_table_name,
    is_appsync_event,
    lambda_handler,
    parse_appsync_event,
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
    def test_get_table_name_custom_env(self):
        """Test getting table name from custom environment variable."""
        assert get_table_name() == "custom-table"

    @patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "unt-part-svc"}, clear=True)
    def test_get_table_name_from_env(self):
        """Test getting table name from environment variable."""
        assert get_table_name() == "unt-part-svc"

    @patch.dict("os.environ", {}, clear=True)
    def test_get_table_name_no_env_vars(self):
        """Test error when no environment variables are set."""
        with pytest.raises(
            ValueError,
            match="Neither SECRET_NAME nor DYNAMODB_TABLE_NAME environment "
            "variables are set",
        ):
            get_table_name()


class TestAppSyncEventHandling:
    """Test AppSync event detection and parsing."""

    def test_is_appsync_event_true(self):
        """Test detection of valid AppSync event."""
        appsync_event = {
            "info": {"fieldName": "getPart", "parentTypeName": "Query"},
            "arguments": {},
        }
        assert is_appsync_event(appsync_event) is True

    def test_is_appsync_event_false_api_gateway(self):
        """Test detection of API Gateway event as non-AppSync."""
        api_gateway_event = {
            "httpMethod": "GET",
            "pathParameters": {"uuid": "test-uuid"},
        }
        assert is_appsync_event(api_gateway_event) is False

    def test_is_appsync_event_false_missing_info(self):
        """Test detection fails when info is missing."""
        incomplete_event = {"arguments": {}}
        assert is_appsync_event(incomplete_event) is False

    def test_parse_appsync_event_get_part(self):
        """Test parsing AppSync getPart operation."""
        appsync_event = {
            "info": {
                "fieldName": "getPart",
                "parentTypeName": "Query",
                "requestId": "test-request-123",
            },
            "arguments": {"uuid": "test-uuid-123"},
        }

        operation_type, parsed_data = parse_appsync_event(appsync_event)

        assert operation_type == "GET"
        assert parsed_data["httpMethod"] == "GET"
        assert parsed_data["pathParameters"]["uuid"] == "test-uuid-123"
        assert parsed_data["requestContext"]["appsync"] is True

    def test_parse_appsync_event_create_part(self):
        """Test parsing AppSync createPart operation."""
        part_data = {
            "accountId": "acc123",
            "category": "Electronics",
            "segment": "Consumer",
            "partTerminologyName": "Resistor",
        }

        appsync_event = {
            "info": {"fieldName": "createPart", "parentTypeName": "Mutation"},
            "arguments": {"part": part_data},
        }

        operation_type, parsed_data = parse_appsync_event(appsync_event)

        assert operation_type == "POST"
        assert parsed_data["httpMethod"] == "POST"
        body = json.loads(parsed_data["body"])
        assert body["part"] == part_data

    def test_parse_appsync_event_update_part(self):
        """Test parsing AppSync updatePart operation."""
        update_data = {"category": "Updated Electronics"}

        appsync_event = {
            "info": {"fieldName": "updatePart", "parentTypeName": "Mutation"},
            "arguments": {"uuid": "test-uuid-456", "part": update_data},
        }

        operation_type, parsed_data = parse_appsync_event(appsync_event)

        assert operation_type == "PUT"
        assert parsed_data["httpMethod"] == "PUT"
        assert parsed_data["pathParameters"]["uuid"] == "test-uuid-456"
        body = json.loads(parsed_data["body"])
        assert body["part"] == update_data

    def test_parse_appsync_event_delete_part(self):
        """Test parsing AppSync deletePart operation."""
        appsync_event = {
            "info": {"fieldName": "deletePart", "parentTypeName": "Mutation"},
            "arguments": {"uuid": "test-uuid-789"},
        }

        operation_type, parsed_data = parse_appsync_event(appsync_event)

        assert operation_type == "DELETE"
        assert parsed_data["httpMethod"] == "DELETE"
        assert parsed_data["pathParameters"]["uuid"] == "test-uuid-789"

    def test_parse_appsync_event_unsupported_operation(self):
        """Test parsing unsupported AppSync operation raises error."""
        appsync_event = {
            "info": {"fieldName": "unsupportedOperation", "parentTypeName": "Query"},
            "arguments": {},
        }

        with pytest.raises(
            ValueError, match="Unsupported AppSync operation: unsupportedOperation"
        ):
            parse_appsync_event(appsync_event)

    def test_parse_appsync_event_alternative_argument_names(self):
        """Test parsing with alternative argument names (id, input)."""
        appsync_event = {
            "info": {"fieldName": "getPart", "parentTypeName": "Query"},
            "arguments": {"id": "test-uuid-alt"},
        }

        operation_type, parsed_data = parse_appsync_event(appsync_event)

        assert operation_type == "GET"
        assert parsed_data["pathParameters"]["uuid"] == "test-uuid-alt"

    def test_format_appsync_response_get_success(self):
        """Test formatting successful GET response for AppSync."""
        http_response = {
            "statusCode": 200,
            "body": json.dumps(
                {"part": {"PK": "test-uuid", "category": "Electronics"}}
            ),
        }

        result = format_appsync_response(http_response, "GET")

        assert result == {"PK": "test-uuid", "category": "Electronics"}

    def test_format_appsync_response_post_success(self):
        """Test formatting successful POST response for AppSync."""
        http_response = {
            "statusCode": 201,
            "body": json.dumps(
                {
                    "message": "Part created successfully",
                    "uuid": "new-uuid",
                    "part": {"PK": "new-uuid", "category": "Electronics"},
                }
            ),
        }

        result = format_appsync_response(http_response, "POST")

        assert result["uuid"] == "new-uuid"
        assert result["message"] == "Part created successfully"
        assert result["part"]["PK"] == "new-uuid"

    def test_format_appsync_response_put_success(self):
        """Test formatting successful PUT response for AppSync."""
        http_response = {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Part updated successfully",
                    "part": {"PK": "updated-uuid", "category": "Updated"},
                }
            ),
        }

        result = format_appsync_response(http_response, "PUT")

        assert result["message"] == "Part updated successfully"
        assert result["part"]["category"] == "Updated"

    def test_format_appsync_response_delete_success(self):
        """Test formatting successful DELETE response for AppSync."""
        http_response = {
            "statusCode": 200,
            "body": json.dumps({"message": "Part deleted successfully"}),
        }

        result = format_appsync_response(http_response, "DELETE")

        assert result["message"] == "Part deleted successfully"
        assert result["success"] is True

    def test_format_appsync_response_error(self):
        """Test formatting error response for AppSync."""
        http_response = {
            "statusCode": 404,
            "body": json.dumps({"error": "Part not found"}),
        }

        result = format_appsync_response(http_response, "GET")

        assert result["error"]["message"] == "Part not found"
        assert result["error"]["statusCode"] == 404

    def test_format_appsync_response_invalid_json(self):
        """Test formatting response with invalid JSON body."""
        http_response = {"statusCode": 200, "body": "invalid json"}

        result = format_appsync_response(http_response, "GET")

        assert result["error"]["message"] == "Invalid response format"


class TestAppSyncLambdaIntegration:
    """Test AppSync integration with lambda handler."""

    @patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "unt-part-svc"})
    def test_lambda_handler_appsync_get_part(self, dynamodb_table, sample_part_data):
        """Test lambda handler with AppSync getPart request."""
        # Create a part first
        part_uuid = str(uuid.uuid4())
        item = {
            "PK": part_uuid,
            "SK": sample_part_data["accountId"],
            "createdAt": get_current_timestamp(),
            **sample_part_data,
        }
        dynamodb_table.put_item(Item=item)

        appsync_event = {
            "info": {
                "fieldName": "getPart",
                "parentTypeName": "Query",
                "requestId": "appsync-test-123",
            },
            "arguments": {"uuid": part_uuid},
        }

        with patch("src.parts_service.lambda_handler.dynamodb") as mock_dynamodb:
            mock_dynamodb.Table.return_value = dynamodb_table

            result = lambda_handler(appsync_event, {})

            assert "PK" in result
            assert result["PK"] == part_uuid
            assert result["category"] == "Electronics"

    @patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "unt-part-svc"})
    def test_lambda_handler_appsync_create_part(self, dynamodb_table, sample_part_data):
        """Test lambda handler with AppSync createPart request."""
        appsync_event = {
            "info": {"fieldName": "createPart", "parentTypeName": "Mutation"},
            "arguments": {"part": sample_part_data},
        }

        with patch("src.parts_service.lambda_handler.dynamodb") as mock_dynamodb:
            mock_dynamodb.Table.return_value = dynamodb_table

            result = lambda_handler(appsync_event, {})

            assert "uuid" in result
            assert result["message"] == "Part created successfully"
            assert result["part"]["category"] == "Electronics"

    @patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "unt-part-svc"})
    def test_lambda_handler_appsync_update_part(self, dynamodb_table, sample_part_data):
        """Test lambda handler with AppSync updatePart request."""
        # Create a part first
        part_uuid = str(uuid.uuid4())
        item = {
            "PK": part_uuid,
            "SK": sample_part_data["accountId"],
            "createdAt": get_current_timestamp(),
            **sample_part_data,
        }
        dynamodb_table.put_item(Item=item)

        appsync_event = {
            "info": {"fieldName": "updatePart", "parentTypeName": "Mutation"},
            "arguments": {
                "uuid": part_uuid,
                "part": {"category": "Updated Electronics"},
            },
        }

        with patch("src.parts_service.lambda_handler.dynamodb") as mock_dynamodb:
            mock_dynamodb.Table.return_value = dynamodb_table

            result = lambda_handler(appsync_event, {})

            assert result["message"] == "Part updated successfully"
            assert result["part"]["category"] == "Updated Electronics"

    @patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "unt-part-svc"})
    def test_lambda_handler_appsync_delete_part(self, dynamodb_table, sample_part_data):
        """Test lambda handler with AppSync deletePart request."""
        # Create a part first
        part_uuid = str(uuid.uuid4())
        item = {
            "PK": part_uuid,
            "SK": sample_part_data["accountId"],
            "createdAt": get_current_timestamp(),
            **sample_part_data,
        }
        dynamodb_table.put_item(Item=item)

        appsync_event = {
            "info": {"fieldName": "deletePart", "parentTypeName": "Mutation"},
            "arguments": {"uuid": part_uuid},
        }

        with patch("src.parts_service.lambda_handler.dynamodb") as mock_dynamodb:
            mock_dynamodb.Table.return_value = dynamodb_table

            result = lambda_handler(appsync_event, {})

            assert result["message"] == "Part deleted successfully"
            assert result["success"] is True

    def test_lambda_handler_appsync_unsupported_operation(self):
        """Test lambda handler with unsupported AppSync operation."""
        appsync_event = {
            "info": {"fieldName": "unsupportedOperation", "parentTypeName": "Query"},
            "arguments": {},
        }

        result = lambda_handler(appsync_event, {})

        assert "error" in result
        assert "Unsupported AppSync operation" in result["error"]["message"]
        assert result["error"]["statusCode"] == 400

    @patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "unt-part-svc"})
    def test_lambda_handler_appsync_part_not_found(self, dynamodb_table):
        """Test lambda handler AppSync request for non-existent part."""
        appsync_event = {
            "info": {"fieldName": "getPart", "parentTypeName": "Query"},
            "arguments": {"uuid": str(uuid.uuid4())},
        }

        with patch("src.parts_service.lambda_handler.dynamodb") as mock_dynamodb:
            mock_dynamodb.Table.return_value = dynamodb_table

            result = lambda_handler(appsync_event, {})

            assert "error" in result
            assert result["error"]["message"] == "Part not found"
            assert result["error"]["statusCode"] == 404

    def test_lambda_handler_appsync_unexpected_error(self):
        """Test lambda handler handles unexpected AppSync errors."""
        appsync_event = {
            "info": {"fieldName": "getPart", "parentTypeName": "Query"},
            "arguments": {"uuid": "test-uuid"},
        }

        with patch(
            "src.parts_service.lambda_handler.get_part",
            side_effect=Exception("Unexpected error"),
        ):
            result = lambda_handler(appsync_event, {})

            assert "error" in result
            assert result["error"]["message"] == "Internal server error"
            assert result["error"]["statusCode"] == 500


class TestCreatePart:
    """Test create part functionality."""

    @patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "unt-part-svc"})
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

    @patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "unt-part-svc"})
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

    @patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "unt-part-svc"})
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

    @patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "unt-part-svc"})
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

    @patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "unt-part-svc"})
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

    @patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "unt-part-svc"})
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

    @patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "unt-part-svc"})
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

    @patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "unt-part-svc"})
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

    @patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "unt-part-svc"})
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

    @patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "unt-part-svc"})
    def test_lambda_handler_post_method(self, dynamodb_table, sample_part_data):
        """Test lambda handler with POST method."""
        event = {"httpMethod": "POST", "body": json.dumps({"part": sample_part_data})}

        with patch("src.parts_service.lambda_handler.dynamodb") as mock_dynamodb:
            mock_dynamodb.Table.return_value = dynamodb_table

            result = lambda_handler(event, {})

            assert result["statusCode"] == 201

    @patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "unt-part-svc"})
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

    @patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "unt-part-svc"})
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

    @patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "unt-part-svc"})
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
