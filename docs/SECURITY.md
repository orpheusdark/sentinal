# Security

## Intended boundary

Sentinel is a local, single-administrator camera appliance. It is not a hardened public Internet service. Bind defaults to 127.0.0.1; startup refuses non-loopback binding without dashboard authentication. Local auth is optional for the single-device experience. Untrusted local processes/users are outside this boundary and can access loopback if authentication is off.

## Implemented protections

- Random session secrets replace predictable defaults; cookies are HttpOnly/SameSite=Lax, and Secure with direct HTTPS.
- A private password is required when enabling authentication. Werkzeug scrypt/pbkdf2 hashes and legacy plaintext credentials are supported.
- Login redirects must remain relative local paths. Repeated login failures trigger a bounded-time lockout.
- System information, video and administrative APIs are private under session auth. Optional API keys cover reads as well as writes and use constant-time comparisons; no URL keys.
- No permissive CORS. JSON writes require a custom request header; cross-origin writes are rejected.
- CSP, frame denial, no-sniff, same-origin referrer policy and no-store responses reduce browser exposure. Dynamic archive/timeline text uses safe DOM text insertion.
- Download paths resolve under the recordings root; cleanup skips symlinks and the current active recording.
- Environment credentials are excluded from settings persistence. Logs/database/bytecode/runtime files are ignored and removed from the tracked tree. Telegram errors omit credential-bearing URLs.

## Operational requirements and remaining risks

Use TLS and authentication for any network deployment; keep port access private and do not forward the local HTTP port directly to the Internet. The embedded Werkzeug server is appropriate to a local appliance; public exposure requires a reviewed deployment architecture. A trusted proxy must normalize Host/Origin correctly. Reverse-proxy TLS/cookie behavior requires acceptance testing; direct TLS is supported with both certificate files.

Credentials, recordings and SQLite data are not encrypted at rest. Apply OS file permissions and disk encryption if required. Login lockout is process-global and resets on restart; it can deny service to the sole admin. There are no per-user roles, durable rate limits or persistent audit trail of administrative actions. GET logout permits logout CSRF. Cross-origin write controls assume modern browsers and honest proxy headers; they do not replace authentication.

Removing historical runtime files from the current tree does not erase Git history. If a real secret was ever committed, rotate it and coordinate a separate history-cleaning change. No history rewrite is performed by this update. Do not attach raw logs or camera images to public issues. Redact tokens, paths, usernames and private footage.

Run `python -m pip_audit` before release. An advisory scan is a point-in-time dependency check, not proof of complete security. Report security issues privately to the repository owner rather than including exploitable details or secrets in a public issue.
