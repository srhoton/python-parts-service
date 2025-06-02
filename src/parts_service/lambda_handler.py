"""AWS Lambda handler for Parts Service CRUD operations."""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Type, Union

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")
secrets_client = boto3.client("secretsmanager")


class PartValidationError(Exception):
    """Raised when part data validation fails."""

    pass


class PartNotFoundError(Exception):
    """Raised when a part is not found."""

    pass


def get_table_name() -> str:
    """Get the DynamoDB table name from Secrets Manager or environment variables."""
    secret_name = os.environ.get("SECRET_NAME")
    fallback_table_name = os.environ.get("DYNAMODB_TABLE_NAME")
    
    if not secret_name:
        # Use environment variable if no secret is configured
        if not fallback_table_name:
            raise ValueError("Neither SECRET_NAME nor DYNAMODB_TABLE_NAME environment variables are set")
        return fallback_table_name
    
    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secrets = json.loads(response["SecretString"])
        table_name = secrets.get("DYNAMODB_TABLE_NAME")
        
        if not table_name:
            if fallback_table_name:
                logger.warning(f"DYNAMODB_TABLE_NAME not found in secret {secret_name}, using environment variable")
                return fallback_table_name
            else:
                raise ValueError(f"DYNAMODB_TABLE_NAME not found in secret {secret_name} and no fallback environment variable set")
        
        return table_name
    except ClientError as e:
        logger.error(f"Error retrieving secret {secret_name}: {e}")
        if fallback_table_name:
            logger.warning("Falling back to environment variable for table name")
            return fallback_table_name
        else:
            raise ValueError(f"Failed to retrieve secret {secret_name} and no fallback environment variable set") from e


def get_current_timestamp() -> str:
    """Get current ISO timestamp."""
    return datetime.now(timezone.utc).isoformat()


def decimal_default(obj: Any) -> Any:
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> None:
    """Validate that required fields are present in the data."""
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise PartValidationError(
            f"Missing required fields: {', '.join(missing_fields)}"
        )


def validate_additional_fields(additional_fields: List[Dict[str, Any]]) -> None:
    """Validate additional fields structure."""
    for field in additional_fields:
        if not isinstance(field, dict):
            raise PartValidationError("additionalFields must be an array of objects")

        required_in_additional = ["fieldName", "codedValue"]
        missing = [req for req in required_in_additional if req not in field]
        if missing:
            raise PartValidationError(
                f"Missing required fields in additionalFields: {', '.join(missing)}"
            )


def validate_part_data(data: Dict[str, Any], is_update: bool = False) -> Dict[str, Any]:
    """Validate part data and return cleaned data."""
    if not is_update:
        # For create operations, validate required fields
        required_fields = ["accountId", "category", "segment", "partTerminologyName"]
        validate_required_fields(data, required_fields)

    # Define valid fields and their expected types
    valid_fields: Dict[str, Union[Type[str], Type[list], tuple]] = {
        "accountId": str,
        "customerId": str,
        "locationId": str,
        "categoryProductId": (int, float),
        "categoryId": (int, float),
        "category": str,
        "segmentId": (int, float),
        "segment": str,
        "partTerminologyId": (int, float),
        "partTerminologyName": str,
        "additionalFields": list,
    }

    cleaned_data = {}

    for field, value in data.items():
        if field not in valid_fields:
            continue  # Skip unknown fields

        expected_type = valid_fields[field]

        # Type validation
        if not isinstance(value, expected_type):
            if field in [
                "categoryProductId",
                "categoryId",
                "segmentId",
                "partTerminologyId",
            ]:
                # Allow string numbers for numeric fields
                try:
                    cleaned_data[field] = (
                        float(value) if "." in str(value) else int(value)
                    )
                except (ValueError, TypeError):
                    raise PartValidationError(
                        f"Field {field} must be a number"
                    ) from None
            else:
                type_name = getattr(expected_type, '__name__', str(expected_type))
                raise PartValidationError(
                    f"Field {field} must be of type {type_name}"
                )
        else:
            cleaned_data[field] = value

        # Special validation for additionalFields
        if field == "additionalFields" and value:
            validate_additional_fields(value)

    return cleaned_data


def get_part_by_uuid(table: Any, part_uuid: str) -> Optional[Dict[str, Any]]:
    """Get a part by UUID if it exists and is not deleted."""
    try:
        response = table.query(
            KeyConditionExpression=Key("PK").eq(part_uuid),
            FilterExpression=Attr("deletedAt").not_exists()
        )

        items = response.get("Items", [])
        return items[0] if items else None

    except ClientError as e:
        logger.error(f"Error querying DynamoDB: {e}")
        raise


def create_part(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle POST request to create a new part."""
    try:
        # Parse request body
        body = json.loads(event.get("body", "{}"))
        part_data = body.get("part")

        if not part_data:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing 'part' in request body"}),
            }

        # Validate part data
        validated_data = validate_part_data(part_data)

        # Generate UUID and prepare item
        part_uuid = str(uuid.uuid4())
        current_time = get_current_timestamp()

        item = {
            "PK": part_uuid,
            "SK": validated_data["accountId"],
            "createdAt": current_time,
            **validated_data,
        }

        # Get table and put item
        table = dynamodb.Table(get_table_name())
        table.put_item(Item=item)

        logger.info(f"Created part with UUID: {part_uuid}")

        return {
            "statusCode": 201,
            "body": json.dumps({
                "message": "Part created successfully",
                "uuid": part_uuid,
                "part": item
            }, default=decimal_default)
        }

    except PartValidationError as e:
        logger.warning(f"Validation error: {e}")
        return {"statusCode": 400, "body": json.dumps({"error": str(e)})}

    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid JSON in request body"}),
        }

    except Exception as e:
        logger.error(f"Error creating part: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"}),
        }


def get_part(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle GET request to retrieve a part."""
    try:
        # Extract UUID from path parameters
        path_params = event.get("pathParameters", {})
        part_uuid = path_params.get("uuid") if path_params else None

        if not part_uuid:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing UUID in path parameters"}),
            }

        # Get table and query for part
        table = dynamodb.Table(get_table_name())
        part = get_part_by_uuid(table, part_uuid)

        if not part:
            return {"statusCode": 404, "body": json.dumps({"error": "Part not found"})}

        logger.info(f"Retrieved part with UUID: {part_uuid}")

        return {
            "statusCode": 200,
            "body": json.dumps({"part": part}, default=decimal_default)
        }

    except Exception as e:
        logger.error(f"Error retrieving part: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"}),
        }


def update_part(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle PUT request to update a part."""
    try:
        # Extract UUID from path parameters
        path_params = event.get("pathParameters", {})
        part_uuid = path_params.get("uuid") if path_params else None

        if not part_uuid:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing UUID in path parameters"}),
            }

        # Parse request body
        body = json.loads(event.get("body", "{}"))
        part_data = body.get("part")

        if not part_data:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing 'part' in request body"}),
            }

        # Get table and check if part exists
        table = dynamodb.Table(get_table_name())
        existing_part = get_part_by_uuid(table, part_uuid)

        if not existing_part:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Part not found or already deleted"}),
            }

        # Validate update data
        validated_data = validate_part_data(part_data, is_update=True)

        # Prepare update expression with reserved keyword handling
        update_expression = "SET updatedAt = :updated_at"
        expression_values = {":updated_at": get_current_timestamp()}
        expression_names = {}

        # Reserved keywords in DynamoDB
        reserved_keywords = {
            "segment", "category", "status", "name", "size", "type", "data",
            "count", "group", "order", "range", "key", "value", "time", "date"
        }

        for field, value in validated_data.items():
            if field.lower() in reserved_keywords:
                # Use expression attribute names for reserved keywords
                attr_name = f"#{field}"
                update_expression += f", {attr_name} = :{field}"
                expression_names[attr_name] = field
            else:
                update_expression += f", {field} = :{field}"
            expression_values[f":{field}"] = value

        # Update the item
        update_params = {
            "Key": {"PK": part_uuid, "SK": existing_part["SK"]},
            "UpdateExpression": update_expression,
            "ExpressionAttributeValues": expression_values
        }

        if expression_names:
            update_params["ExpressionAttributeNames"] = expression_names

        table.update_item(**update_params)

        logger.info(f"Updated part with UUID: {part_uuid}")

        # Get updated item
        updated_part = get_part_by_uuid(table, part_uuid)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {"message": "Part updated successfully", "part": updated_part},
                default=decimal_default
            ),
        }

    except PartValidationError as e:
        logger.warning(f"Validation error: {e}")
        return {"statusCode": 400, "body": json.dumps({"error": str(e)})}

    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid JSON in request body"}),
        }

    except Exception as e:
        logger.error(f"Error updating part: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"}),
        }


def delete_part(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle DELETE request to soft delete a part."""
    try:
        # Extract UUID from path parameters
        path_params = event.get("pathParameters", {})
        part_uuid = path_params.get("uuid") if path_params else None

        if not part_uuid:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing UUID in path parameters"}),
            }

        # Get table and check if part exists
        table = dynamodb.Table(get_table_name())
        existing_part = get_part_by_uuid(table, part_uuid)

        if not existing_part:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Part not found or already deleted"}),
            }

        # Soft delete by adding deletedAt timestamp
        table.update_item(
            Key={"PK": part_uuid, "SK": existing_part["SK"]},
            UpdateExpression="SET deletedAt = :deleted_at",
            ExpressionAttributeValues={":deleted_at": get_current_timestamp()}
        )

        logger.info(f"Deleted part with UUID: {part_uuid}")

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Part deleted successfully"}),
        }

    except Exception as e:
        logger.error(f"Error deleting part: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"}),
        }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler function."""
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Get HTTP method
        http_method = event.get("httpMethod") or event.get("requestContext", {}).get(
            "http", {}
        ).get("method")

        if not http_method:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "HTTP method not found in event"}),
            }

        # Route based on HTTP method
        if http_method == "GET":
            return get_part(event)
        elif http_method == "POST":
            return create_part(event)
        elif http_method == "PUT":
            return update_part(event)
        elif http_method == "DELETE":
            return delete_part(event)
        else:
            return {
                "statusCode": 405,
                "body": json.dumps({"error": f"Method {http_method} not allowed"}),
            }

    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"}),
        }
