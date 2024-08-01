# Specify the provider and its version
terraform {
  required_providers {
    jsc = {
      source  = "danjamf/jsctfprovider"
      version = "0.0.14"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

provider "jsc" {
  username = var.jscusername
  password = var.jscpassword
}

variable "jscusername" {
  description = "JSC username (email)"
  type        = string
}

variable "jscpassword" {
  description = "JSC password"
  type        = string
  sensitive   = true
}


variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}
