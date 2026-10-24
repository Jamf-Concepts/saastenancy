#!/usr/bin/env python3
"""Generate the per-application CloudFormation templates from generator/base.yaml.

The templates differ only in the tenant-restriction header(s), the upstream
host and a few strings, so a security fix to the shared parts (TLS verification,
IMDSv2, NoEcho, mobileconfig, nginx hardening) is made once in base.yaml.

    python3 generator/generate.py          # rewrite the templates
    python3 generator/generate.py --check  # exit 1 if any template is stale
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "generator" / "base.yaml"
OUT_DIR = ROOT / "aws_cloudformation_templates"

# Continuation lines of the nginx_header / nginx_proxy_pass shell strings.
NGINX_INDENT = " " * 32

DOMAIN_PARAM = """\
Domain:
  Description: internal domain to add to the header if multiple seperated by space
  Type: String
  Default: "example.com example.dev\""""

TENANT_POLICY_PARAM = """\
TenantPolicy:
  Description: "Tenant restriction policy in format TenantId:policyGuid (e.g., aaaabbbb-0000-cccc-1111-dddd2222eeee:1aaaaaa1-2bb2-3cc3-4dd4-5eeeeeeeeee5)"
  Type: String
  Default: "your-tenant-id:your-policy-guid\""""

MICROSOFT_SANS = [
    "stamp2.login.microsoftonline.com", "login.microsoftonline-int.com",
    "login.microsoftonline-p.com", "login.microsoftonline.com",
    "login2.microsoftonline-int.com", "login2.microsoftonline.com",
    "loginex.microsoftonline-int.com", "loginex.microsoftonline.com",
    "stamp2.login.microsoftonline-int.com", "login.microsoft.com",
    "login.windows.net", "login.live.com",
]


def san(*names):
    return ", ".join(f"DNS:{n}" for n in names)


def csr_block(label, name, cn):
    return f"""\
# Creating CSR for {label}
openssl req -newkey rsa:2048 -keyout /etc/nginx/server.key -nodes -out /etc/nginx/{name}.csr -subj "/C=US/ST=MN/L=Minneapolis/O=Jamf/OU=Security/CN={cn}"
# Signing the CSR with internal CA
openssl x509 -req -in /etc/nginx/{name}.csr -CA /etc/nginx/intermediateCA.pem -CAkey /etc/nginx/intermediateCA.key -CAcreateserial -out /etc/nginx/server.crt -days 365 -sha256 -extfile /etc/nginx/server.ext"""


def proxy_pass_lines(upstream_url, ssl_name):
    """Upstream proxy_pass with TLS verification against the system CA bundle."""
    return [
        f"proxy_pass {upstream_url};",
        "proxy_ssl_verify on;",
        "proxy_ssl_trusted_certificate /etc/pki/tls/certs/ca-bundle.crt;",
        "proxy_ssl_verify_depth 2;",
        "proxy_ssl_server_name on;",
        f"proxy_ssl_name {ssl_name};",
    ]


def shell_string(var, lines, append=False):
    """nginx_header="\n<lines>" -- one directive per line, closing quote on the last."""
    body = "\n".join(NGINX_INDENT + line for line in lines)
    return f'{var}{"+" if append else ""}="\n{body}"'


def header_lines(headers, value):
    return [f"proxy_set_header '{h}' {value};" for h in headers]


def multi_domain_logic(app):
    """Single or space-separated list of domains injected as header values."""
    csr = csr_block(app["csr_label"], app["csr_name"], app["csr_cn"])
    proxy = proxy_pass_lines(app["upstream_url"], app["ssl_name"])
    indent = lambda text, n: "\n".join(" " * n + l if l else l for l in text.split("\n"))
    return "\n".join([
        "# Checking if domain is multiple",
        "# Check if the string contains a space and if so convert to array",
        'if echo "$domain" | grep -q " "; then',
        '    echo "Multiple Domains splitting into Array" > /tmp/log.txt',
        "    # If it does, split the string into an array using IFS and read",
        "    IFS=' ' read -r -a array <<< \"$domain\"",
        "",
        "    # Loop through the array and append each element to the new variable",
        '    for element in "${!array[@]}"',
        "    do",
        indent(csr, 8),
        indent(shell_string("nginx_header", header_lines(app["headers"], "$element"), append=True), 8),
        indent(shell_string("nginx_proxy_pass", proxy), 8),
        "    done",
        "",
        "else",
        indent(csr, 4),
        indent(shell_string("nginx_header", header_lines(app["headers"], "$domain")), 4),
        indent(shell_string("nginx_proxy_pass", proxy), 4),
        "fi",
    ])


def single_tenant_logic(app):
    """One fixed policy value, no domain list."""
    csr = csr_block(app["csr_label"], app["csr_name"], app["csr_cn"])
    proxy = proxy_pass_lines(app["upstream_url"], app["ssl_name"])
    return "\n".join([
        csr,
        "",
        shell_string("nginx_header", header_lines(app["headers"], "$tenant_policy")),
        shell_string("nginx_proxy_pass", proxy),
    ])


def extra_server_block(host, extra_directives=()):
    lines = [
        "server {",
        "    listen 443 ssl;",
        "    listen [::]:443 ssl;",
        f"    server_name {host};",
        "    ssl_certificate     /etc/nginx/server.crt;",
        "    ssl_certificate_key /etc/nginx/server.key;",
        "    location / {",
        *(f"        {d}" for d in extra_directives),
        "        proxy_ssl_verify on;",
        "        proxy_ssl_trusted_certificate /etc/pki/tls/certs/ca-bundle.crt;",
        "        proxy_ssl_verify_depth 2;",
        "        proxy_ssl_server_name on;",
        f"        proxy_ssl_name {host};",
        f"        proxy_pass https://{host};",
        "    }",
        "}",
    ]
    return "\n".join(lines)


def microsoft_v1_extra_blocks():
    """Hosts served by dedicated server blocks; the primary block proxies login.microsoftonline.com.

    login.live.com is the consumer-account endpoint; restrict-msa blocks personal
    Microsoft accounts (without it they bypass the tenant restriction).
    """
    blocks = [
        extra_server_block("login.microsoft.com"),
        extra_server_block("login.windows.net"),
        extra_server_block(
            "login.live.com",
            ['proxy_set_header sec-Restrict-Tenant-Access-Policy "restrict-msa";'],
        ),
    ]
    return "\n".join(["read -r -d '' extra_server_blocks <<'BLOCKEOF'", *blocks, "BLOCKEOF"])


APPS = {
    "google": {
        "description": "Google tenant restrictions",
        "tenant_param": DOMAIN_PARAM,
        "tenant_var": "domain='${Domain}'",
        "san": san("accounts.google.com", "*.google.com"),
        "logic": multi_domain_logic,
        "csr_label": "Google", "csr_name": "google", "csr_cn": "*.google.com",
        "headers": ["X-GooGApps-Allowed-Domains"],
        "upstream_url": "https://accounts.google.com", "ssl_name": "accounts.google.com",
        "header_comment": "domain",
    },
    "dropbox": {
        "description": "Dropbox tenant restrictions",
        "tenant_param": DOMAIN_PARAM,
        "tenant_var": "domain='${Domain}'",
        "san": san("dropbox.com", "*.dropbox.com"),
        "logic": multi_domain_logic,
        "csr_label": "Dropbox", "csr_name": "dropbox", "csr_cn": "*.dropbox.com",
        "headers": ["X-Dropbox-allowed-Team-Ids"],
        "upstream_url": "https://www.dropbox.com/login", "ssl_name": "www.dropbox.com",
        "header_comment": "domain",
    },
    "slack": {
        "description": "Slack tenant restrictions",
        "tenant_param": DOMAIN_PARAM,
        "tenant_var": "domain='${Domain}'",
        "san": san("slack.com", "*.slack.com"),
        "logic": multi_domain_logic,
        "csr_label": "Slack", "csr_name": "slack", "csr_cn": "slack.com",
        "headers": ["X-Slack-Allowed-Workspaces-Requester", "X-Slack-Allowed-Workspaces"],
        "upstream_url": "https://slack.com/signin", "ssl_name": "slack.com",
        "header_comment": "domain",
    },
    "microsoft_v1": {
        "description": "Microsoft tenant restrictions (v1 - Restrict-Access-To-Tenants header)",
        "tenant_param": DOMAIN_PARAM,
        "tenant_var": "domain='${Domain}'",
        "san": san(*MICROSOFT_SANS),
        "logic": multi_domain_logic,
        "csr_label": "Microsoft", "csr_name": "microsoft", "csr_cn": "stamp2.login.microsoftonline.com",
        "headers": ["Restrict-Access-To-Tenants", "Restrict-Access-Context"],
        "upstream_url": "https://login.microsoftonline.com", "ssl_name": "login.microsoftonline.com",
        "header_comment": "domain",
        "extra_init": "extra_server_blocks=''",
        "extra_blocks": microsoft_v1_extra_blocks(),
        "extra_blocks_ref": "$extra_server_blocks",
    },
    "microsoft_v2": {
        "description": "Microsoft tenant restrictions (v2 - sec-Restrict-Tenant-Access-Policy header)",
        "tenant_param": TENANT_POLICY_PARAM,
        "tenant_var": "tenant_policy='${TenantPolicy}'",
        "san": san("login.live.com", "login.microsoft.com", "login.microsoftonline.com",
                   "login.windows.net", "stamp2.login.microsoftonline.com",
                   "login.microsoftonline-int.com", "login.microsoftonline-p.com",
                   "login2.microsoftonline-int.com", "login2.microsoftonline.com",
                   "loginex.microsoftonline-int.com", "loginex.microsoftonline.com",
                   "stamp2.login.microsoftonline-int.com"),
        "logic": single_tenant_logic,
        "csr_label": "Microsoft", "csr_name": "microsoft", "csr_cn": "login.microsoftonline.com",
        "headers": ["sec-Restrict-Tenant-Access-Policy"],
        "upstream_url": "https://login.microsoftonline.com", "ssl_name": "login.microsoftonline.com",
        "header_comment": "tenant restriction v2",
    },
}

def indent_block(text, indent):
    lines = text.split("\n")
    return "\n".join(indent + l if l else l for l in lines)


def render(name, app, base):
    inline = {
        "@@DESCRIPTION@@": app["description"],
        "@@SAN@@": app["san"],
        "@@HEADER_COMMENT@@": app["header_comment"],
    }
    block = {
        "@@TENANT_PARAM@@": app["tenant_param"],
        "@@TENANT_VAR@@": app["tenant_var"],
        "@@EXTRA_INIT@@": app.get("extra_init", ""),
        "@@EXTRA_BLOCKS@@": app.get("extra_blocks", ""),
        "@@TENANT_LOGIC@@": app["logic"](app),
        "@@EXTRA_BLOCKS_REF@@": app.get("extra_blocks_ref", ""),
    }
    out = []
    for line in base.split("\n"):
        stripped = line.strip()
        if stripped in block:
            value = block[stripped]
            if value:  # an empty slot drops its whole line
                out.append(indent_block(value, line[: len(line) - len(line.lstrip())]))
            continue
        for key, value in inline.items():
            line = line.replace(key, value)
        out.append(line)
    text = "\n".join(out)
    if "@@" in text:
        raise SystemExit(f"{name}: unreplaced slot in output")
    return text


def main():
    check = "--check" in sys.argv[1:]
    base = BASE.read_text()
    stale = []
    for name, app in APPS.items():
        path = OUT_DIR / f"jamf_saastenancy_{name}.yaml"
        text = render(name, app, base)
        if check:
            if not path.exists() or path.read_text() != text:
                stale.append(path.name)
        else:
            path.write_text(text)
            print(f"wrote {path.relative_to(ROOT)}")
    if stale:
        print("stale (run python3 generator/generate.py): " + ", ".join(stale), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
