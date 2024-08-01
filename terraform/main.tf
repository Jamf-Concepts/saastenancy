# Specify the provider and its version
provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "The body of the SSL/TLS certificate base64 encoded (leave empty for self signed)"
  type        = string
  default     = "us-west-2"
}
