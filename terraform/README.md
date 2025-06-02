# Terraform Infrastructure for Parts Service

This directory contains Terraform configuration files for provisioning AWS infrastructure for the Parts Service application.

## Overview

This Terraform configuration creates a complete serverless infrastructure for the Parts Service application with the following components:

### DynamoDB Table
- **Table Name**: `unt-part-svc`
- **Primary Key**: `PK` (String)
- **Sort Key**: `SK` (String)
- **Streams**: Enabled with `NEW_AND_OLD_IMAGES` view type
- **Billing Mode**: Pay-per-request (on-demand)
- **Encryption**: Server-side encryption enabled
- **Point-in-time Recovery**: Enabled by default

### AWS Lambda Function
- **Runtime**: Python 3.12
- **Memory**: 512 MB (configurable)
- **Timeout**: 30 seconds (configurable)
- **Handler**: `parts_service.lambda_handler.lambda_handler`
- **Environment**: Secrets Manager integration for configuration

### API Gateway v2 (HTTP API)
- **Protocol**: HTTP
- **CORS**: Enabled for web applications
- **Routes**: Full CRUD operations (GET, POST, PUT, DELETE)
- **Integration**: AWS Lambda proxy integration
- **Logging**: CloudWatch access logs enabled

### AWS Secrets Manager
- **Secret**: Configuration values including DynamoDB table name
- **Access**: Lambda execution role has read permissions
- **Security**: Encrypted at rest and in transit

### IAM Security
- **Lambda Execution Role**: Least privilege permissions
- **DynamoDB Access**: Full CRUD operations on the parts table
- **Secrets Manager**: Read-only access to configuration secret
- **CloudWatch Logs**: Write permissions for Lambda and API Gateway

## File Structure

```
terraform/
├── README.md           # This documentation file
├── versions.tf         # Terraform and provider version constraints
├── providers.tf        # AWS provider configuration
├── variables.tf        # Input variables
├── main.tf            # Main infrastructure resources (DynamoDB, Lambda, API Gateway, IAM, Secrets Manager)
└── outputs.tf         # Output values
```

## Prerequisites

1. **Terraform**: Version >= 1.0
2. **AWS CLI**: Configured with appropriate credentials
3. **AWS Provider**: Version ~> 5.0
4. **Archive Provider**: Version ~> 2.0 (for Lambda deployment package)
5. **Python Source Code**: Located in `../src/` directory relative to terraform

## Usage

### Initialize Terraform

```bash
cd terraform
terraform init
```

### Plan the Infrastructure

```bash
terraform plan
```

### Apply the Infrastructure

```bash
terraform apply
```

### Destroy the Infrastructure

```bash
terraform destroy
```

## Configuration Variables

| Variable | Description | Type | Default | Required |
|----------|-------------|------|---------|----------|
| `aws_region` | AWS region for resources | string | `us-east-1` | No |
| `environment` | Environment name (dev, staging, prod) | string | `dev` | No |
| `project_name` | Name of the project | string | `parts-service` | No |
| `owner` | Owner of the resources | string | `parts-team` | No |
| `dynamodb_table_name` | Name of the DynamoDB table | string | `unt-part-svc` | No |
| `primary_key_name` | Name of the primary key | string | `PK` | No |
| `sort_key_name` | Name of the sort key | string | `SK` | No |
| `billing_mode` | Billing mode (PAY_PER_REQUEST or PROVISIONED) | string | `PAY_PER_REQUEST` | No |
| `stream_enabled` | Enable DynamoDB streams | bool | `true` | No |
| `stream_view_type` | Stream view type | string | `NEW_AND_OLD_IMAGES` | No |
| `deletion_protection_enabled` | Enable deletion protection | bool | `false` | No |
| `point_in_time_recovery_enabled` | Enable point-in-time recovery | bool | `true` | No |
| `lambda_function_name` | Name of the Lambda function | string | `parts-service-lambda` | No |
| `lambda_runtime` | Lambda runtime version | string | `python3.12` | No |
| `lambda_timeout` | Lambda timeout in seconds | number | `30` | No |
| `lambda_memory_size` | Lambda memory in MB | number | `512` | No |
| `lambda_handler` | Lambda handler function | string | `parts_service.lambda_handler.lambda_handler` | No |
| `api_gateway_name` | Name of the API Gateway | string | `parts-service-api` | No |
| `api_gateway_description` | Description of the API Gateway | string | `HTTP API Gateway for Parts Service` | No |
| `api_gateway_stage_name` | API Gateway stage name | string | `v1` | No |
| `api_gateway_auto_deploy` | Auto-deploy API Gateway stage | bool | `true` | No |
| `secrets_manager_secret_name` | Name of the Secrets Manager secret | string | `parts-service-config` | No |
| `secrets_manager_description` | Description of the secret | string | `Configuration secrets for Parts Service` | No |

## Customization

To customize the configuration for different environments, you can:

1. **Create environment-specific `.tfvars` files**:
   ```bash
   # dev.tfvars
   environment = "dev"
   aws_region = "us-east-1"
   deletion_protection_enabled = false
   
   # prod.tfvars
   environment = "prod"
   aws_region = "us-west-2"
   deletion_protection_enabled = true
   ```

2. **Use the files with terraform commands**:
   ```bash
   terraform plan -var-file="dev.tfvars"
   terraform apply -var-file="prod.tfvars"
   ```

## Outputs

This configuration provides the following outputs:

### DynamoDB Outputs
- `dynamodb_table_name`: Name of the created DynamoDB table
- `dynamodb_table_id`: ID of the DynamoDB table
- `dynamodb_table_arn`: ARN of the DynamoDB table
- `dynamodb_table_stream_arn`: ARN of the DynamoDB table stream
- `dynamodb_table_stream_label`: Timestamp when the stream was enabled
- `dynamodb_table_hash_key`: Hash key (primary key) name
- `dynamodb_table_range_key`: Range key (sort key) name
- `dynamodb_table_billing_mode`: Billing mode of the table
- `dynamodb_table_stream_enabled`: Whether streams are enabled
- `dynamodb_table_stream_view_type`: Stream view type configuration

### Lambda Outputs
- `lambda_function_name`: Name of the Lambda function
- `lambda_function_arn`: ARN of the Lambda function
- `lambda_function_invoke_arn`: Invoke ARN of the Lambda function
- `lambda_execution_role_arn`: ARN of the Lambda execution role

### API Gateway Outputs
- `api_gateway_id`: ID of the API Gateway
- `api_gateway_arn`: ARN of the API Gateway
- `api_gateway_execution_arn`: Execution ARN of the API Gateway
- `api_gateway_endpoint`: Base URL of the API Gateway
- `api_gateway_stage_url`: Full URL of the API Gateway stage

### Secrets Manager Outputs
- `secrets_manager_secret_arn`: ARN of the Secrets Manager secret
- `secrets_manager_secret_name`: Name of the Secrets Manager secret

### CloudWatch Outputs
- `lambda_log_group_name`: Name of the Lambda CloudWatch log group
- `api_gateway_log_group_name`: Name of the API Gateway CloudWatch log group

## Security Features

- **Server-side encryption**: Enabled by default using AWS managed keys
- **Point-in-time recovery**: Enabled for data protection
- **Least privilege IAM**: Lambda execution role has minimal required permissions
- **Secrets management**: Configuration stored securely in AWS Secrets Manager
- **API security**: CORS configured for web application access
- **Monitoring**: CloudWatch logging enabled for Lambda and API Gateway
- **Default tags**: Applied for resource management and cost tracking
- **Input validation**: Variables include validation rules where appropriate

## Best Practices Implemented

- ✅ Consistent naming conventions using snake_case
- ✅ Comprehensive variable documentation with types and validation
- ✅ Explicit provider version constraints
- ✅ Descriptive resource and variable names
- ✅ Comprehensive tagging strategy
- ✅ Security best practices (encryption, recovery)
- ✅ Modular file organization
- ✅ Input validation for critical variables

## Troubleshooting

### Common Issues

1. **AWS Credentials**: Ensure your AWS credentials are properly configured
   ```bash
   aws configure list
   ```

2. **Permissions**: Verify you have the necessary IAM permissions for DynamoDB operations

3. **Region**: Ensure the specified AWS region supports all services (DynamoDB, Lambda, API Gateway, Secrets Manager)

4. **Source Code**: Verify the Python source code exists in `../src/` directory relative to terraform configuration

### Validation Commands

Before applying, run these commands to ensure code quality:

```bash
# Format the code
terraform fmt

# Validate the configuration
terraform validate

# Run tflint (if installed)
tflint
```

## API Endpoints

After deployment, the following REST API endpoints will be available:

- `GET {api_gateway_stage_url}/parts/{uuid}` - Retrieve a specific part
- `POST {api_gateway_stage_url}/parts` - Create a new part
- `PUT {api_gateway_stage_url}/parts/{uuid}` - Update an existing part
- `DELETE {api_gateway_stage_url}/parts/{uuid}` - Soft delete a part

The `{api_gateway_stage_url}` will be output after successful deployment.

## Related Documentation

- [AWS DynamoDB Terraform Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dynamodb_table)
- [AWS Lambda Terraform Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_function)
- [AWS API Gateway v2 Terraform Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apigatewayv2_api)
- [AWS Secrets Manager Terraform Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/secretsmanager_secret)
- [DynamoDB Streams Documentation](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html)
- [AWS Lambda Developer Guide](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)
- [API Gateway v2 Developer Guide](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html)
- [Terraform Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/index.html)

## Support

For issues related to this infrastructure configuration, please:

1. Check the troubleshooting section above
2. Refer to the AWS DynamoDB documentation
3. Create an issue in the project repository with relevant error messages and steps to reproduce