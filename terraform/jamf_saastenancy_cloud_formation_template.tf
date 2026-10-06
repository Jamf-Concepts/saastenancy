# Variables
variable "KeyName" {
  description = "Name of an existing EC2 KeyPair to enable SSH access to the instance"
  type        = string
}
variable "InstanceType" {
  description = "EC2 instance type"
  type        = string
  default     = "t4g.micro"
}
variable "CertificateBody" {
  description = "The body of the SSL/TLS certificate base64 encoded (leave empty for self signed)"
  type        = string
}
variable "CertificatePrivateKey" {
  description = "The private key of the SSL/TLS certificate base64 encoded (leave empty for self signed)"
  type        = string
  sensitive   = true
}
variable "TenantDomain" {
  description = "Tenant domain(s) to restrict sign-in to, injected into the SaaS tenant-restriction header; space separated if multiple"
  type        = string
  default     = "example.com"
}
variable "SaaSApplication" {
  description = "Choose which application to allow for the domain"
  type        = string
  default     = "Google"
}

data "aws_vpc" "default" {
  default = true
}

data "aws_caller_identity" "current" {}

resource "random_id" "ssm_suffix" {
  byte_length = 8
}


variable "VPCId" {
  description = "VPC Id where the instance will be launched"
  type        = string
}
variable "SubnetId" {
  description = "Subnet Id where the instance will be launched"
  type        = string
}

# Define local mappings for AMI IDs based on region
locals {
  region_amis = {
    "us-east-1"      = "ami-0eb01a520e67f7f20"
    "us-east-2"      = "ami-07a5db12eede6ff87"
    "us-west-1"      = "ami-05f45e0f5aeac9a24"
    "us-west-2"      = "ami-00a0b62a1660255c0"
    "ap-southeast-2" = "ami-01b5f7a30f320f409"
    "ap-northeast-1" = "ami-09ff6f432d0ee628e"
    "eu-central-1"   = "ami-00068b9d3a9643636"
    "eu-west-2"      = "ami-05e77069ed898709c"
  }

  saas_login_hostnames = {
    Google    = ["accounts.google.com"]
    Microsoft = ["login.microsoftonline.com", "login.microsoft.com", "login.windows.net", "login.live.com"]
    Slack     = ["slack.com"]
    Dropbox   = ["www.dropbox.com"]
  }

  ssm_parameter_name = "/saastenancy-${random_id.ssm_suffix.hex}/profile"

  init_script = templatefile("${path.module}/script.sh", {
    SaaSApplication       = var.SaaSApplication
    TenantDomain          = var.TenantDomain
    CertificateBody       = var.CertificateBody
    CertificatePrivateKey = var.CertificatePrivateKey
    SsmParameterName      = local.ssm_parameter_name
    AwsRegion             = var.aws_region
  })

  domain_array = local.saas_login_hostnames[var.SaaSApplication]
}



# Resources
resource "aws_security_group" "InstanceSecurityGroup" {
  name        = "InstanceSecurityGroup"
  description = "Allow access to port 443 and 80"
  # Use the VPC ID from the variable if it's provided, otherwise fall back to the default VPC
  vpc_id = var.VPCId != "" ? var.VPCId : data.aws_vpc.default.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Optional: Define egress rules (default allows all outbound traffic)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "InstanceSecurityGroup"
  }
}

resource "aws_iam_role" "SaaSTenancyInstanceRole" {
  name = "SaaSTenancyInstanceRole-${random_id.ssm_suffix.hex}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "SaaSTenancyInstanceSsmPolicy" {
  name = "SaaSTenancyInstanceSsmPolicy-${random_id.ssm_suffix.hex}"
  role = aws_iam_role.SaaSTenancyInstanceRole.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = "ssm:PutParameter"
        Effect   = "Allow"
        Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${local.ssm_parameter_name}"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "SaaSTenancyInstanceProfile" {
  name = "SaaSTenancyInstanceProfile-${random_id.ssm_suffix.hex}"
  role = aws_iam_role.SaaSTenancyInstanceRole.name
}

resource "aws_instance" "SaaSTenancyNginx" {
  instance_type          = var.InstanceType
  vpc_security_group_ids = [aws_security_group.InstanceSecurityGroup.id]
  key_name               = var.KeyName
  ami                    = local.region_amis[var.aws_region]
  subnet_id              = var.SubnetId
  user_data_base64       = base64gzip(local.init_script)
  iam_instance_profile   = aws_iam_instance_profile.SaaSTenancyInstanceProfile.name

  metadata_options {
    http_tokens = "required"
  }

  tags = {
    Name = "SaaSTenancyNginx"
  }

  # Add any other required configurations here.
}

resource "aws_eip" "ElasticIP" {
  domain   = "vpc"
  instance = aws_instance.SaaSTenancyNginx.id
}

# Outputs
output "InstanceId" {
  description = "The Instance ID"
  value       = aws_instance.SaaSTenancyNginx.id
}

output "PublicIP" {
  description = "The Public IP address of the instance please add this as your JSC custom gateway address"
  value       = aws_eip.ElasticIP.public_ip
}
