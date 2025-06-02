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