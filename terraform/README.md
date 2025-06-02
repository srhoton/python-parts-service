# Terraform Infrastructure for Parts Service

This directory contains Terraform configuration files for provisioning AWS infrastructure for the Parts Service application.

## Overview

This Terraform configuration creates a DynamoDB table specifically designed for the Parts Service application with the following specifications:

- **Table Name**: `unt-part-svc`
- **Primary Key**: `PK` (String)
- **Sort Key**: `SK` (String)
- **Streams**: Enabled with `NEW_AND_OLD_IMAGES` view type
- **Billing Mode**: Pay-per-request (on-demand)
- **Encryption**: Server-side encryption enabled
- **Point-in-time Recovery**: Enabled by default

## File Structure

```
terraform/
├── README.md           # This documentation file
├── versions.tf         # Terraform and provider version constraints
├── providers.tf        # AWS provider configuration
├── variables.tf        # Input variables
├── main.tf            # Main DynamoDB table resource
└── outputs.tf         # Output values
```

## Prerequisites

1. **Terraform**: Version >= 1.0
2. **AWS CLI**: Configured with appropriate credentials
3. **AWS Provider**: Version ~> 5.0

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

## Security Features

- **Server-side encryption**: Enabled by default using AWS managed keys
- **Point-in-time recovery**: Enabled for data protection
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

3. **Region**: Ensure the specified AWS region supports DynamoDB (all regions do)

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

## Related Documentation

- [AWS DynamoDB Terraform Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dynamodb_table)
- [DynamoDB Streams Documentation](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html)
- [Terraform Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/index.html)

## Support

For issues related to this infrastructure configuration, please:

1. Check the troubleshooting section above
2. Refer to the AWS DynamoDB documentation
3. Create an issue in the project repository with relevant error messages and steps to reproduce