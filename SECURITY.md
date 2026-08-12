# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅        |

We support the latest minor release. Older versions may not receive security patches.

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT open a public issue.**
2. Email **security@seedforge.dev** with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)
3. You will receive an acknowledgment within **48 hours**.
4. We will investigate and provide a fix or mitigation timeline within **7 days**.
5. Once the fix is released, we will credit you in the release notes (unless you prefer anonymity).

## Scope

The following are in scope for security reports:

- CLI command injection or privilege escalation
- Dependency solver producing malicious lock files
- Install/sync writing outside the declared target directories
- Credential or token leakage in logs or error messages
- Malicious skill packages executed during sync

## Out of Scope

- Vulnerabilities in third-party skills installed via `harness-ai-kit add` (report to the skill author)
- Social engineering or phishing attacks
- Denial of service against the PyPI registry or GitHub API

## Security Measures

- **Sensitive scan**: CI blocks internal domains, IPs, and credential patterns on every push
- **SHA-256 integrity**: All installed assets verified against lock file checksums
- **Atomic install**: Staging-based install prevents partial/corrupted states
- **Minimal dependencies**: Only well-maintained, widely-used packages as runtime deps
