# Variables for DynamoDB table configuration

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "parts-service"
}

variable "owner" {
  description = "Owner of the resources"
  type        = string
  default     = "parts-team"
}

variable "dynamodb_table_name" {
  description = "Name of the DynamoDB table for parts service"
  type        = string
  default     = "unt-part-svc"

  validation {
    condition     = length(var.dynamodb_table_name) >= 3 && length(var.dynamodb_table_name) <= 255
    error_message = "DynamoDB table name must be between 3 and 255 characters."
  }
}

variable "primary_key_name" {
  description = "Name of the primary key for the DynamoDB table"
  type        = string
  default     = "PK"
}

variable "sort_key_name" {
  description = "Name of the sort key for the DynamoDB table"
  type        = string
  default     = "SK"
}

variable "billing_mode" {
  description = "Billing mode for the DynamoDB table"
  type        = string
  default     = "PAY_PER_REQUEST"

  validation {
    condition     = contains(["PAY_PER_REQUEST", "PROVISIONED"], var.billing_mode)
    error_message = "Billing mode must be either PAY_PER_REQUEST or PROVISIONED."
  }
}

variable "stream_enabled" {
  description = "Enable DynamoDB streams for the table"
  type        = bool
  default     = true
}

variable "stream_view_type" {
  description = "Stream view type when streams are enabled"
  type        = string
  default     = "NEW_AND_OLD_IMAGES"

  validation {
    condition = contains([
      "KEYS_ONLY",
      "NEW_IMAGE",
      "OLD_IMAGE",
      "NEW_AND_OLD_IMAGES"
    ], var.stream_view_type)
    error_message = "Stream view type must be one of: KEYS_ONLY, NEW_IMAGE, OLD_IMAGE, NEW_AND_OLD_IMAGES."
  }
}

variable "deletion_protection_enabled" {
  description = "Enable deletion protection for the DynamoDB table"
  type        = bool
  default     = false
}

variable "point_in_time_recovery_enabled" {
  description = "Enable point-in-time recovery for the DynamoDB table"
  type        = bool
  default     = true
}