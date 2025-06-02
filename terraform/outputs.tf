# Outputs for DynamoDB table information

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table"
  value       = aws_dynamodb_table.parts_table.name
}

output "dynamodb_table_id" {
  description = "ID of the DynamoDB table"
  value       = aws_dynamodb_table.parts_table.id
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table"
  value       = aws_dynamodb_table.parts_table.arn
}

output "dynamodb_table_stream_arn" {
  description = "ARN of the DynamoDB table stream"
  value       = aws_dynamodb_table.parts_table.stream_arn
}

output "dynamodb_table_stream_label" {
  description = "Timestamp of when the stream was enabled"
  value       = aws_dynamodb_table.parts_table.stream_label
}

output "dynamodb_table_hash_key" {
  description = "Hash key (primary key) of the DynamoDB table"
  value       = aws_dynamodb_table.parts_table.hash_key
}

output "dynamodb_table_range_key" {
  description = "Range key (sort key) of the DynamoDB table"
  value       = aws_dynamodb_table.parts_table.range_key
}

output "dynamodb_table_billing_mode" {
  description = "Billing mode of the DynamoDB table"
  value       = aws_dynamodb_table.parts_table.billing_mode
}

output "dynamodb_table_stream_enabled" {
  description = "Whether streams are enabled for the DynamoDB table"
  value       = aws_dynamodb_table.parts_table.stream_enabled
}

output "dynamodb_table_stream_view_type" {
  description = "Stream view type of the DynamoDB table"
  value       = aws_dynamodb_table.parts_table.stream_view_type
}

# Lambda function outputs

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.parts_service_lambda.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.parts_service_lambda.arn
}

output "lambda_function_invoke_arn" {
  description = "Invoke ARN of the Lambda function"
  value       = aws_lambda_function.parts_service_lambda.invoke_arn
}

output "lambda_execution_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_execution_role.arn
}

# API Gateway outputs

output "api_gateway_id" {
  description = "ID of the API Gateway"
  value       = aws_apigatewayv2_api.parts_service_api.id
}

output "api_gateway_arn" {
  description = "ARN of the API Gateway"
  value       = aws_apigatewayv2_api.parts_service_api.arn
}

output "api_gateway_execution_arn" {
  description = "Execution ARN of the API Gateway"
  value       = aws_apigatewayv2_api.parts_service_api.execution_arn
}

output "api_gateway_endpoint" {
  description = "Base URL of the API Gateway"
  value       = aws_apigatewayv2_api.parts_service_api.api_endpoint
}

output "api_gateway_stage_url" {
  description = "Full URL of the API Gateway stage"
  value       = "${aws_apigatewayv2_api.parts_service_api.api_endpoint}/${var.api_gateway_stage_name}"
}

# Secrets Manager outputs

output "secrets_manager_secret_arn" {
  description = "ARN of the Secrets Manager secret"
  value       = aws_secretsmanager_secret.parts_service_config.arn
}

output "secrets_manager_secret_name" {
  description = "Name of the Secrets Manager secret"
  value       = aws_secretsmanager_secret.parts_service_config.name
}

# CloudWatch log groups outputs

output "lambda_log_group_name" {
  description = "Name of the Lambda CloudWatch log group"
  value       = aws_cloudwatch_log_group.lambda_log_group.name
}

output "api_gateway_log_group_name" {
  description = "Name of the API Gateway CloudWatch log group"
  value       = aws_cloudwatch_log_group.api_gateway_log_group.name
}