# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SaaS Tenancy is a Jamf Connect project that deploys an Nginx reverse proxy on AWS EC2 to enforce SaaS tenant restrictions. When paired with Jamf Security Cloud's Custom DNS Hostname Mapping, it prevents users from accessing personal accounts on managed devices by injecting tenant-restriction headers into HTTP requests.

**Supported SaaS Applications:**
- Google (X-GooGApps-Allowed-Domains header)
- Microsoft (Restrict-Access-To-Tenants, Restrict-Access-Context headers)
- Slack (X-Slack-Allowed-Workspaces headers)
- Dropbox (X-Dropbox-allowed-Team-Ids header)

## Repository Structure

- `aws_cloudformation_templates/` - AWS CloudFormation templates (standalone deployment)
  - `jamf_saastenancy_google.yaml` - Google tenant restrictions
  - `jamf_saastenancy_microsoft_v1.yaml` - Microsoft Tenant Restrictions v1
  - `jamf_saastenancy_microsoft_v2.yaml` - Microsoft Tenant Restrictions v2
  - `jamf_saastenancy_slack.yaml` - Slack workspace restrictions
  - `jamf_saastenancy_dropbox.yaml` - Dropbox team restrictions
- `terraform/` - Terraform configuration for integrated deployment with Jamf Pro and JSC
  - `main.tf` - Provider configuration (AWS, JSC, Jamf Pro)
  - `jamf_saastenancy_cloud_formation_template.tf` - EC2 instance and security group resources
  - `script.sh` - EC2 user data script (Nginx setup, SSL cert generation)
  - `jscconfig.tf` - JSC hostname mapping configuration
  - `prosaasconfig.tf` - Jamf Pro configuration profile deployment
  - `proconfig.tf` - HTTP data source for profile download

## Deployment Options

### CloudFormation (Standalone)
```bash
# Example using Google template
aws cloudformation create-stack --stack-name saastenancy \
  --template-body file://aws_cloudformation_templates/jamf_saastenancy_google.yaml \
  --parameters ParameterKey=KeyName,ParameterValue=<key> \
               ParameterKey=VPCId,ParameterValue=<vpc-id> \
               ParameterKey=SubnetId,ParameterValue=<subnet-id> \
               ParameterKey=Domain,ParameterValue="example.com"
```

### Terraform (Integrated)
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

**Required Terraform Variables:**
- `jscusername` / `jscpassword` - Jamf Security Cloud credentials
- `KeyName` - EC2 key pair name
- `VPCId` / `SubnetId` - AWS networking
- `CertificateBody` / `CertificatePrivateKey` - SSL certs (empty for self-signed)
- `Domain` - Space-separated list of allowed domains
- `SaaSApplication` - One of: Google, Microsoft_v1 (Tenant Restrictions v1), Microsoft_v2 (Tenant Restrictions v2), Slack, Dropbox

## Architecture

1. **EC2 Instance** - Runs Nginx as HTTPS reverse proxy with custom header injection
2. **Elastic IP** - Static IP for DNS mapping in Jamf Security Cloud
3. **SSL/TLS** - Self-signed CA chain or provided certificates
4. **Mobile Profile** - Auto-generated `.mobileconfig` served at `/download` endpoint for certificate trust

The Terraform version additionally:
- Creates JSC hostname mappings pointing SaaS domains to the proxy IP
- Deploys the generated certificate profile to Jamf Pro for managed devices
