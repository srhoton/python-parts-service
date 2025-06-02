# Python Parts Service

A Python 3.13 AWS Lambda service for managing parts inventory with full CRUD operations via API Gateway v2.

## Overview

This service provides a RESTful API for managing parts in a DynamoDB table. It supports creating, reading, updating, and soft-deleting parts with comprehensive validation and error handling.

## Features

- **Full CRUD Operations**: Create, Read, Update, and Delete parts
- **Soft Delete**: Parts are marked as deleted rather than permanently removed
- **Data Validation**: Comprehensive validation for required fields and data types
- **AWS Lambda**: Serverless deployment with API Gateway v2 integration
- **DynamoDB**: NoSQL storage with configurable table name
- **Type Safety**: Full type annotations with MyPy validation
- **Comprehensive Testing**: 60%+ test coverage with pytest
- **Code Quality**: Ruff linting and formatting

## Project Structure

```
python-parts-service/
├── src/
│   └── parts_service/
│       ├── __init__.py
│       └── lambda_handler.py      # Main Lambda handler
├── tests/
│   ├── __init__.py
│   └── test_lambda_handler.py     # Comprehensive test suite
├── terraform/                     # Infrastructure as Code
│   ├── main.tf                   # DynamoDB table definition
│   ├── variables.tf              # Terraform variables
│   ├── outputs.tf                # Terraform outputs
│   ├── providers.tf              # AWS provider config
│   └── versions.tf               # Version constraints
├── pyproject.toml                # Project configuration
├── requirements.txt              # Production dependencies
├── README.md                     # This file
└── LICENSE                       # MIT License
```

## API Specification

### Data Model

Each part contains the following fields:

#### Required Fields (for creation)
- `accountId` (string): Account identifier
- `category` (string): Part category
- `segment` (string): Market segment
- `partTerminologyName` (string): Standardized part name

#### Optional Fields
- `customerId` (string): Customer identifier
- `locationId` (string): Location identifier
- `categoryProductId` (number): Category product ID
- `categoryId` (number): Category ID
- `segmentId` (number): Segment ID
- `partTerminologyId` (number): Part terminology ID
- `additionalFields` (array): Additional metadata fields

#### System Fields (auto-generated)
- `PK` (string): UUID primary key
- `SK` (string): Sort key (accountId)
- `createdAt` (string): ISO timestamp of creation
- `updatedAt` (string): ISO timestamp of last update
- `deletedAt` (string): ISO timestamp of deletion (soft delete)

### Additional Fields Structure

The `additionalFields` array contains objects with the following structure:

```json
{
  "referenceFieldNumber": 123,  // optional number
  "fieldName": "color",         // required string
  "codedValue": "red"           // required string
}
```

### Endpoints

#### GET /parts/{uuid}
Retrieve a specific part by UUID.

**Response (200)**:
```json
{
  "part": {
    "PK": "550e8400-e29b-41d4-a716-446655440000",
    "SK": "acc123",
    "accountId": "acc123",
    "category": "Electronics",
    "segment": "Consumer",
    "partTerminologyName": "Resistor",
    "createdAt": "2024-01-01T12:00:00Z"
  }
}
```

**Response (404)**:
```json
{
  "error": "Part not found"
}
```

#### POST /parts
Create a new part.

**Request Body**:
```json
{
  "part": {
    "accountId": "acc123",
    "category": "Electronics",
    "segment": "Consumer",
    "partTerminologyName": "Resistor",
    "additionalFields": [
      {
        "fieldName": "color",
        "codedValue": "red"
      }
    ]
  }
}
```

**Response (201)**:
```json
{
  "message": "Part created successfully",
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "part": {
    "PK": "550e8400-e29b-41d4-a716-446655440000",
    "SK": "acc123",
    "accountId": "acc123",
    "category": "Electronics",
    "segment": "Consumer",
    "partTerminologyName": "Resistor",
    "createdAt": "2024-01-01T12:00:00Z",
    "additionalFields": [
      {
        "fieldName": "color",
        "codedValue": "red"
      }
    ]
  }
}
```

#### PUT /parts/{uuid}
Update an existing part.

**Request Body**:
```json
{
  "part": {
    "category": "Updated Electronics",
    "segment": "Industrial"
  }
}
```

**Response (200)**:
```json
{
  "message": "Part updated successfully",
  "part": {
    "PK": "550e8400-e29b-41d4-a716-446655440000",
    "SK": "acc123",
    "category": "Updated Electronics",
    "segment": "Industrial",
    "updatedAt": "2024-01-01T13:00:00Z"
  }
}
```

#### DELETE /parts/{uuid}
Soft delete a part.

**Response (200)**:
```json
{
  "message": "Part deleted successfully"
}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DYNAMODB_TABLE_NAME` | Name of the DynamoDB table | `unt-part-svc` |

## Development Setup

### Prerequisites

- Python 3.13+
- Poetry, PDM, or pip for dependency management
- AWS CLI configured (for deployment)
- Terraform (for infrastructure)

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd python-parts-service
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

### Running Tests

```bash
# Run all tests with coverage
pytest

# Run tests with verbose output
pytest -v

# Run specific test file
pytest tests/test_lambda_handler.py

# Generate coverage report
pytest --cov-report=html
```

### Code Quality

```bash
# Format code
ruff format

# Lint code
ruff check

# Type checking
mypy src/ tests/

# Security scanning
bandit -r src/
```

## Infrastructure Deployment

### DynamoDB Table

Use the included Terraform configuration to create the required DynamoDB table:

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

The table will be created with:
- Table name: `unt-part-svc` (configurable)
- Primary key: `PK` (String)
- Sort key: `SK` (String)
- Billing mode: Pay-per-request
- Streams: Enabled
- Encryption: Server-side encryption enabled

### Lambda Deployment

1. **Package the Lambda**:
   ```bash
   # Create deployment package
   mkdir lambda-package
   pip install -r requirements.txt -t lambda-package/
   cp -r src/parts_service lambda-package/
   cd lambda-package && zip -r ../lambda-deployment.zip . && cd ..
   ```

2. **Deploy via AWS CLI**:
   ```bash
   aws lambda create-function \
     --function-name parts-service \
     --runtime python3.13 \
     --role arn:aws:iam::ACCOUNT:role/lambda-execution-role \
     --handler parts_service.lambda_handler.lambda_handler \
     --zip-file fileb://lambda-deployment.zip \
     --environment Variables='{DYNAMODB_TABLE_NAME=unt-part-svc}'
   ```

3. **Update function**:
   ```bash
   aws lambda update-function-code \
     --function-name parts-service \
     --zip-file fileb://lambda-deployment.zip
   ```

## API Gateway Integration

Configure API Gateway v2 to route requests to the Lambda function:

- **GET** `/parts/{uuid}` → Lambda with `uuid` path parameter
- **POST** `/parts` → Lambda with request body
- **PUT** `/parts/{uuid}` → Lambda with `uuid` path parameter and request body
- **DELETE** `/parts/{uuid}` → Lambda with `uuid` path parameter

## Error Handling

The service returns standard HTTP status codes:

- **200**: Success
- **201**: Created
- **400**: Bad Request (validation errors, missing fields)
- **404**: Not Found (part doesn't exist or is deleted)
- **405**: Method Not Allowed
- **500**: Internal Server Error

All error responses include a JSON body with an `error` field describing the issue.

## Security Considerations

- No hardcoded credentials or sensitive data
- Input validation for all fields
- Type checking to prevent injection attacks
- Soft delete preserves data integrity
- Server-side encryption for DynamoDB
- IAM roles for least privilege access

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and ensure they pass (`pytest`)
5. Run code quality checks (`ruff check`, `mypy`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## Code Quality Standards

This project enforces:

- **Ruff**: Fast Python linter and formatter
- **MyPy**: Static type checking
- **Pytest**: Testing framework with 60%+ coverage requirement
- **Bandit**: Security vulnerability scanning
- **Python 3.13**: Latest Python version support

## Performance Considerations

- DynamoDB pay-per-request billing for cost optimization
- Efficient queries using partition key (PK) and sort key (SK)
- Soft delete for data preservation and audit trails
- JSON serialization for fast API responses
- Minimal dependencies for faster Lambda cold starts

## Monitoring and Logging

- CloudWatch Logs integration
- Structured logging with INFO level
- Request/response logging for debugging
- Error tracking with stack traces
- Performance monitoring via CloudWatch metrics

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For questions or issues:

1. Check the documentation above
2. Review existing issues in the repository
3. Create a new issue with detailed information about the problem
4. Include logs, error messages, and steps to reproduce

## Changelog

### v0.1.0
- Initial implementation of Parts Service Lambda
- Full CRUD operations with DynamoDB
- Comprehensive test suite with 60%+ coverage
- Type safety with MyPy
- Code quality with Ruff
- Terraform infrastructure configuration