data "http" "profile" {
  url = "http://${aws_eip.ElasticIP.public_ip}/download"

  # Retry block to handle retries
  retry {
    attempts     = 10    # Number of retry attempts
    min_delay_ms = 20000 # 20 seconds between retries
  }
}


output "profile" {
  value = data.http.profile.response_body
}
