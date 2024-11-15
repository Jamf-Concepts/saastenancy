# saastenancy

Jamf Connect SaaS Tenancy

This CloudFormation template creates an AWS EC2 instance running Nginx, configured to serve as a proxy for SaaS applications over HTTPS. 

## Overview:

When paired with Jamf Security Cloud's [Custom DNS Hostname Mapping](https://learn.jamf.com/en-US/bundle/jamf-security-cloud-setup-guide/page/Hostname_Mapping.html), this CloudFormation template enables organizations to securely route and control access to specified SaaS applications through a centralized proxy server, enhancing security, and ultimately preventing Data Loss by ensuring that users cannot use personal accounts to login to SaaS applications from from managed devices. 

![](diagram.png)

## AWS CloudFormation Technical Components:

- Nginx Reverse Proxy: The EC2 instance will act as a reverse proxy server using Nginx, which will handle incoming HTTPS requests from clients and forward them to the appropriate SaaS applications based on the specified domain and SaaS application type.
- SSL/TLS Termination: Nginx will terminate SSL/TLS connections from clients, allowing for secure communication between clients and the proxy server. This enables the proxy server to inspect and manipulate the HTTP headers and payload before forwarding requests to the destination SaaS applications.
- Custom Header Injection: Depending on the selected SaaS application (Google, Microsoft, Slack, Dropbox), custom headers will be injected into the HTTP requests before forwarding them to the SaaS destination. These headers are designed to ensure only organization-specified domain accounts are able to be used with the SaaS app.
- Dynamic Configuration: The template allows for dynamic configuration of Nginx based on parameters such as the domain and SaaS application type provided during stack creation. This flexibility enables the proxy server to adapt to different environments and use cases.
- Elastic IP Association: An Elastic IP address is allocated and associated with the EC2 instance, providing a static public IP address for external access to the proxy server.

## Jamf Security Cloud:

Using Custom DNS hostname mapping, an administrator can map specified domain hostnames to the custom IP addresses allocated with the EC2 instance. Once configured, users attempting to access accounts.google.com from their device would be routed to the EC2 Elastic IP proxy created via the CloudFormation template. The custom headers would be injected into the HTTP requests and then forwarded to the destination.

Configuration within the supported SaaS destination for blocking access from personal accounts is required.

- Google: [Block Access to Consumer Accounts](https://support.google.com/a/answer/1668854?hl=en)
- Microsoft: [Set up Tenant Restrictions](https://learn.microsoft.com/en-us/entra/external-id/tenant-restrictions-v2#migrate-tenant-restrictions-v1-policies-to-v2-on-the-proxy)

## License:

Copyright 2024, Jamf

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS-IS," WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL JAMF SOFTWARE, LLC OR ANY OF ITS AFFILIATES BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN CONTRACT, TORT, OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OF OR OTHER DEALINGS IN THE SOFTWARE, INCLUDING BUT NOT LIMITED TO DIRECT, INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL OR PUNITIVE DAMAGES AND OTHER DAMAGES SUCH AS LOSS OF USE, PROFITS, SAVINGS, TIME OR DATA, BUSINESS INTERRUPTION, OR PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES.
