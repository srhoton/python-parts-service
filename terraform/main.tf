# DynamoDB table for Parts Service
resource "aws_dynamodb_table" "parts_table" {
  name             = var.dynamodb_table_name
  billing_mode     = var.billing_mode
  hash_key         = var.primary_key_name
  range_key        = var.sort_key_name
  stream_enabled   = var.stream_enabled
  stream_view_type = var.stream_enabled ? var.stream_view_type : null

  deletion_protection_enabled = var.deletion_protection_enabled

  attribute {
    name = var.primary_key_name
    type = "S"
  }

  attribute {
    name = var.sort_key_name
    type = "S"
  }

  point_in_time_recovery {
    enabled = var.point_in_time_recovery_enabled
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name        = var.dynamodb_table_name
    Description = "DynamoDB table for Parts Service application"
    Component   = "database"
  }
}

# Secrets Manager secret for configuration
resource "aws_secretsmanager_secret" "parts_service_config" {
  name        = var.secrets_manager_secret_name
  description = var.secrets_manager_description

  tags = {
    Name        = var.secrets_manager_secret_name
    Description = var.secrets_manager_description
    Component   = "secrets"
  }
}

# Secrets Manager secret version with table name
resource "aws_secretsmanager_secret_version" "parts_service_config_version" {
  secret_id = aws_secretsmanager_secret.parts_service_config.id
  secret_string = jsonencode({
    DYNAMODB_TABLE_NAME = aws_dynamodb_table.parts_table.name
  })
}

# IAM role for Lambda execution
resource "aws_iam_role" "lambda_execution_role" {
  name = "${var.lambda_function_name}-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.lambda_function_name}-execution-role"
    Description = "IAM role for Parts Service Lambda execution"
    Component   = "iam"
  }
}

# IAM policy for Lambda basic execution
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_execution_role.name
}

# IAM policy for DynamoDB access
resource "aws_iam_role_policy" "lambda_dynamodb_policy" {
  name = "${var.lambda_function_name}-dynamodb-policy"
  role = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem",
          "dynamodb:DeleteItem",
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:UpdateItem",
          "dynamodb:DescribeTable",
          "dynamodb:GetRecords",
          "dynamodb:GetShardIterator",
          "dynamodb:DescribeStream",
          "dynamodb:ListStreams"
        ]
        Resource = [
          aws_dynamodb_table.parts_table.arn,
          "${aws_dynamodb_table.parts_table.arn}/*"
        ]
      }
    ]
  })
}

# IAM policy for Secrets Manager access
resource "aws_iam_role_policy" "lambda_secrets_manager_policy" {
  name = "${var.lambda_function_name}-secrets-manager-policy"
  role = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = aws_secretsmanager_secret.parts_service_config.arn
      }
    ]
  })
}

# Archive file for Lambda deployment package
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/lambda_deployment.zip"
  excludes    = ["__pycache__", "*.pyc", "*.pyo", ".pytest_cache", "tests"]
}

# Lambda function
resource "aws_lambda_function" "parts_service_lambda" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = var.lambda_function_name
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = var.lambda_handler
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      SECRET_NAME = aws_secretsmanager_secret.parts_service_config.name
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_iam_role_policy.lambda_dynamodb_policy,
    aws_iam_role_policy.lambda_secrets_manager_policy,
    aws_cloudwatch_log_group.lambda_log_group
  ]

  tags = {
    Name        = var.lambda_function_name
    Description = "Parts Service Lambda function"
    Component   = "compute"
  }
}

# CloudWatch log group for Lambda
resource "aws_cloudwatch_log_group" "lambda_log_group" {
  name              = "/aws/lambda/${var.lambda_function_name}"
  retention_in_days = 14

  tags = {
    Name        = "/aws/lambda/${var.lambda_function_name}"
    Description = "CloudWatch log group for Parts Service Lambda"
    Component   = "logging"
  }
}

# API Gateway v2 (HTTP API)
resource "aws_apigatewayv2_api" "parts_service_api" {
  name          = var.api_gateway_name
  protocol_type = "HTTP"
  description   = var.api_gateway_description

  cors_configuration {
    allow_credentials = false
    allow_headers     = ["content-type", "x-amz-date", "authorization", "x-api-key", "x-amz-security-token"]
    allow_methods     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_origins     = ["*"]
    expose_headers    = ["x-amz-request-id"]
    max_age           = 86400
  }

  tags = {
    Name        = var.api_gateway_name
    Description = var.api_gateway_description
    Component   = "api"
  }
}

# API Gateway integration with Lambda
resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id             = aws_apigatewayv2_api.parts_service_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.parts_service_lambda.invoke_arn

  payload_format_version = "2.0"
}

# API Gateway routes
resource "aws_apigatewayv2_route" "get_part" {
  api_id    = aws_apigatewayv2_api.parts_service_api.id
  route_key = "GET /parts/{uuid}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "create_part" {
  api_id    = aws_apigatewayv2_api.parts_service_api.id
  route_key = "POST /parts"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "update_part" {
  api_id    = aws_apigatewayv2_api.parts_service_api.id
  route_key = "PUT /parts/{uuid}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "delete_part" {
  api_id    = aws_apigatewayv2_api.parts_service_api.id
  route_key = "DELETE /parts/{uuid}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# API Gateway stage
resource "aws_apigatewayv2_stage" "parts_service_stage" {
  api_id      = aws_apigatewayv2_api.parts_service_api.id
  name        = var.api_gateway_stage_name
  auto_deploy = var.api_gateway_auto_deploy

  default_route_settings {
    detailed_metrics_enabled = true
    logging_level            = "INFO"
    throttling_burst_limit   = 5000
    throttling_rate_limit    = 10000
  }

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway_log_group.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      caller         = "$context.identity.caller"
      user           = "$context.identity.user"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      resourcePath   = "$context.resourcePath"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
      errorMessage   = "$context.error.message"
      errorType      = "$context.error.messageString"
    })
  }

  tags = {
    Name        = "${var.api_gateway_name}-${var.api_gateway_stage_name}"
    Description = "Stage for Parts Service API Gateway"
    Component   = "api"
  }
}

# CloudWatch log group for API Gateway
resource "aws_cloudwatch_log_group" "api_gateway_log_group" {
  name              = "/aws/apigateway/${var.api_gateway_name}"
  retention_in_days = 14

  tags = {
    Name        = "/aws/apigateway/${var.api_gateway_name}"
    Description = "CloudWatch log group for Parts Service API Gateway"
    Component   = "logging"
  }
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "api_gateway_lambda_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.parts_service_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.parts_service_api.execution_arn}/*/*"
}