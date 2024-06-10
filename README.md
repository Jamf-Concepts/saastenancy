# saastenancy

Jamf Connect SaaS Tenancy

This CloudFormation template will result in the creation of an AWS EC2 instance running Nginx, configured to serve as a proxy for specified SaaS applications over HTTPS.

## Overview:

The resulting outcome of using this CloudFormation template when paired with Jamf Security Cloud's [Custom DNS Hostname Mapping](https://learn.jamf.com/en-US/bundle/jamf-security-cloud-setup-guide/page/Hostname_Mapping.html) enables organizations to securely route and control access to specified SaaS applications through a centralized proxy server, enhancing security, and ultimately preventing Data Loss (DLP) by ensuring personal accounts with the SaaS providers cannot be accessed from managed devices. ie. unable to use a personally-owned jane.appleseed@gmail.com email account, and rather only the org managed jane.appleseed@org.com gmail account would be able to be used.

## AWS CloudFormation Technical Components:

- Nginx Reverse Proxy: The EC2 instance will act as a reverse proxy server using Nginx, which will handle incoming HTTPS requests from clients and forward them to the appropriate SaaS applications based on the specified domain and SaaS application type.
- SSL/TLS Termination: Nginx will terminate SSL/TLS connections from clients, allowing for secure communication between clients and the proxy server. This enables the proxy server to inspect and manipulate the HTTP headers and payload before forwarding requests to the destination SaaS applications.
- Custom Header Injection: Depending on the selected SaaS application (Google, Microsoft, Slack, Dropbox), custom headers will be injected into the HTTP requests before forwarding them to the SaaS destination. These headers are designed to ensure only organization-specified domain accounts are able to be used with the SaaS app.
- Dynamic Configuration: The template allows for dynamic configuration of Nginx based on parameters such as the domain and SaaS application type provided during stack creation. This flexibility enables the proxy server to adapt to different environments and use cases.
- Elastic IP Association: An Elastic IP address is allocated and associated with the EC2 instance, providing a static public IP address for external access to the proxy server.

#Jamf Security Cloud:

Using Custom DNS hostname mapping, an administrator can map specified domain hostnames to the custom IP addresses allocated with the EC2 instance. Ie: Once configured, users attempting to access accounts.google.com from their device would be routed to the EC2 Elastic IP proxy created via the CloudFormation template. The custom headers would be injected into the HTTP requests and then forwarded to the destination.

Configuration within the supported SaaS destination for blocking access from personal accounts is required.

:google: Google: [Block Access to Consumer Accounts](https://support.google.com/a/answer/1668854?hl=en)
:microsoft: Microsoft: [Set up Tenant Restrictions](https://learn.microsoft.com/en-us/entra/external-id/tenant-restrictions-v2#migrate-tenant-restrictions-v1-policies-to-v2-on-the-proxy)
