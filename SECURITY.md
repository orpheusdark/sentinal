# Security policy

Sentinel 0.2.x is currently a preview. Security fixes are developed on `main` and included in subsequent preview releases; older preview binaries do not receive separate backports.

## Reporting a vulnerability

Use the repository's **Security → Report a vulnerability** option to submit a private report when available. Include the affected version, impact, reproduction steps and a minimal example with synthetic data. If private reporting is unavailable, contact the repository owner privately before sharing exploit details.

Do not include real passwords, API keys, Telegram tokens, private video or unredacted personal data. Public issues are appropriate for general questions and non-sensitive bugs.

## Deployment boundary

The default application is a local, single-administrator appliance. Do not expose its HTTP port directly to the public Internet. Configure authentication, TLS and restricted access before remote viewing. Read the [security guide](docs/SECURITY.md) and [deployment guide](docs/DEPLOYMENT.md) for the actual protections and remaining limits.

Release checksums help verify file integrity; preview binaries do not yet have distribution signing.
