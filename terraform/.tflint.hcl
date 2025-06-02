# TFLint configuration for Parts Service Terraform code

config {
  # Disable terraform provider plugin by default
  disabled_by_default = false
  
  # Enable specific rule sets
  plugin_dir = "~/.tflint.d/plugins"
}

# AWS plugin configuration
plugin "aws" {
  enabled = true
  version = "0.30.0"
  source  = "github.com/terraform-linters/tflint-ruleset-aws"
}

# Enable Terraform core rules
plugin "terraform" {
  enabled = true
  version = "0.5.0"
  source  = "github.com/terraform-linters/tflint-ruleset-terraform"
}

# Terraform core rules
rule "terraform_deprecated_interpolation" {
  enabled = true
}

rule "terraform_deprecated_index" {
  enabled = true
}

rule "terraform_unused_declarations" {
  enabled = true
}

rule "terraform_comment_syntax" {
  enabled = true
}

rule "terraform_documented_outputs" {
  enabled = true
}

rule "terraform_documented_variables" {
  enabled = true
}

rule "terraform_typed_variables" {
  enabled = true
}

rule "terraform_naming_convention" {
  enabled = true
  format  = "snake_case"
}

rule "terraform_standard_module_structure" {
  enabled = true
}

# AWS resource rules
rule "aws_resource_missing_tags" {
  enabled = false  # Disabled as we use default_tags in provider
}