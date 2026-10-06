resource "null_resource" "wait_for_profile" {
  depends_on = [aws_instance.SaaSTenancyNginx]

  triggers = {
    ssm_parameter_name = local.ssm_parameter_name
  }

  provisioner "local-exec" {
    command = <<-SCRIPT
      set -e
      MAX_ATTEMPTS=10
      ATTEMPT=0
      while [ $$ATTEMPT -lt $$MAX_ATTEMPTS ]; do
        ATTEMPT=$$((ATTEMPT + 1))
        VALUE=$$(aws ssm get-parameter --region '${var.aws_region}' --name '${local.ssm_parameter_name}' --query 'Parameter.Value' --output text 2>/dev/null) && \
          echo "$$VALUE" > '${path.module}/.profile.b64.tmp' && \
          mv '${path.module}/.profile.b64.tmp' '${path.module}/.profile.b64' && \
          echo "Profile retrieved on attempt $$ATTEMPT" && \
          exit 0
        echo "Attempt $$ATTEMPT of $$MAX_ATTEMPTS failed, waiting 20s..." >&2
        sleep 20
      done
      echo "ERROR: Failed to retrieve SSM parameter '${local.ssm_parameter_name}' after $$MAX_ATTEMPTS attempts" >&2
      exit 1
    SCRIPT
  }
}

data "local_file" "profile" {
  filename   = "${path.module}/.profile.b64"
  depends_on = [null_resource.wait_for_profile]
}

resource "jamfpro_macos_configuration_profile_plist" "jamfpro_macos_configuration_profile_SaaSTenCert" {
  name                = "SaaS Tenancy Cert"
  description         = "An example mobile device configuration profile."
  level               = "System"                // "User", "Device"
  distribution_method = "Install Automatically" // "Make Available in Self Service", "Install Automatically"
  payloads            = base64decode(trimspace(data.local_file.profile.content))
  payload_validate    = false

  user_removable = false

  scope {
    all_computers = true
  }

  lifecycle {
    precondition {
      condition     = length(base64decode(trimspace(data.local_file.profile.content))) > 0
      error_message = "Decoded profile content is empty; the SSM parameter may contain an invalid or empty value"
    }
  }
}

output "ssm_parameter_name" {
  description = "SSM parameter name holding the base64-encoded mobileconfig profile (operator needs ssm:GetParameter on this to inspect the profile)"
  value       = local.ssm_parameter_name
}
