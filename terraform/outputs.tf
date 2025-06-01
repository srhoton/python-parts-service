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