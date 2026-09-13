# Security Policy

## Supported Versions

GridSentry is a student capstone project under active development. Only the
latest version on `main` receives fixes.

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |
| < 0.1   | No        |

## Reporting a Vulnerability

If you find a security issue (for example, an unauthenticated endpoint that
should require access control, or a dependency with a known CVE), please
email vkprahalad004@gmail.com instead of opening a public issue.

Include:

- A description of the issue and its potential impact
- Steps to reproduce it
- Any suggested fix, if you have one

You can expect an initial response within a few days. This runs as a local
FastAPI service with no authentication layer by design (it's not deployed
publicly), so most reports will concern the codebase itself rather than a
live deployment.
