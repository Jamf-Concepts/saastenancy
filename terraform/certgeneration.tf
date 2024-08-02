# This example creates a self-signed certificate,
# and uses it to create an AWS IAM Server certificate.
#
# THIS IS NOT RECOMMENDED FOR PRODUCTION SERVICES.
# See the detailed documentation of each resource for further
# security considerations and other practical tradeoffs.

resource "tls_private_key" "saastenkey" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "tls_self_signed_cert" "saastencert" {
  private_key_pem = tls_private_key.saastenkey.private_key_pem

  # Certificate expires after 12 hours.
  validity_period_hours = 8760

  # Generate a new certificate if Terraform is run within three
  # hours of the certificate's expiration time.
  early_renewal_hours = 120

  # Reasonable set of uses for a server SSL certificate.
  allowed_uses = [
    "key_encipherment",
    "digital_signature",
    "server_auth",
  ]

  dns_names = local.domain_array
  subject {
    common_name  = "jscproxy-root"
    organization = "Jamf"
  }
}


