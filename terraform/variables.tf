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

# Lambda function configuration variables

variable "lambda_function_name" {
  description = "Name of the Lambda function"
  type        = string
  default     = "parts-service-lambda"

  validation {
    condition     = length(var.lambda_function_name) >= 1 && length(var.lambda_function_name) <= 64
    error_message = "Lambda function name must be between 1 and 64 characters."
  }
}

variable "lambda_runtime" {
  description = "Runtime for the Lambda function"
  type        = string
  default     = "python3.12"

  validation {
    condition     = contains(["python3.9", "python3.10", "python3.11", "python3.12"], var.lambda_runtime)
    error_message = "Lambda runtime must be a supported Python version."
  }
}

variable "lambda_timeout" {
  description = "Timeout for the Lambda function in seconds"
  type        = number
  default     = 30

  validation {
    condition     = var.lambda_timeout >= 1 && var.lambda_timeout <= 900
    error_message = "Lambda timeout must be between 1 and 900 seconds."
  }
}

variable "lambda_memory_size" {
  description = "Memory size for the Lambda function in MB"
  type        = number
  default     = 512

  validation {
    condition     = var.lambda_memory_size >= 128 && var.lambda_memory_size <= 10240
    error_message = "Lambda memory size must be between 128 and 10240 MB."
  }
}

variable "lambda_handler" {
  description = "Handler for the Lambda function"
  type        = string
  default     = "parts_service.lambda_handler.lambda_handler"
}

# API Gateway configuration variables

variable "api_gateway_name" {
  description = "Name of the API Gateway"
  type        = string
  default     = "parts-service-api"
}

variable "api_gateway_description" {
  description = "Description of the API Gateway"
  type        = string
  default     = "HTTP API Gateway for Parts Service"
}

variable "api_gateway_stage_name" {
  description = "Name of the API Gateway stage"
  type        = string
  default     = "v1"
}

variable "api_gateway_auto_deploy" {
  description = "Whether to automatically deploy the API Gateway stage"
  type        = bool
  default     = true
}

# Secrets Manager configuration variables

variable "secrets_manager_secret_name" {
  description = "Name of the Secrets Manager secret"
  type        = string
  default     = "parts-service-config"
}

variable "secrets_manager_description" {
  description = "Description of the Secrets Manager secret"
  type        = string
  default     = "Configuration secrets for Parts Service"
}