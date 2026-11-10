# Contributing

Create a branch, install requirements-dev.txt in an isolated Python 3.11+ environment and run the checks in TESTING.md. Keep changes focused and use a clear single-line commit message. Include the problem, behavior change, verification and limitations in your pull request.

Preserve driver interfaces and existing endpoint contracts unless a documented security/correctness change is needed. Close database sessions on every path, avoid disk/network work per frame where possible, and test with temporary storage. Never commit recordings, logs, databases, environment files, credentials or cached bytecode. Use synthetic frames and mock network failures for reproducible tests.

For UI changes, preserve keyboard operation, visible focus, semantic labels, contrast, narrow layouts, reduced motion and explicit disconnected/error states. Do not insert untrusted API data into HTML. Add regression coverage for material bugs rather than assertions that only mirror implementation.

For release changes, build on each target platform, run frozen resource checks and complete physical-device acceptance checks. Review third-party license obligations before redistribution. The old README claimed MIT but the repository did not include a license text; the owner must explicitly settle licensing before public binary redistribution. Do not invent an owner license grant.
