# Contributing to Sentinel

Thanks for helping improve a local-first surveillance application.

For a bug, include the application version, operating system, architecture, steps to reproduce, expected result and a short redacted log excerpt. For a feature, explain the user problem and a practical example. Avoid posting credentials or private footage.

For code changes:

1. Create a focused branch from `main`.
2. Set up Python 3.11+ and install `requirements-dev.txt` in a virtual environment.
3. Add regression coverage for material behavior changes and update relevant documentation.
4. Run the test, lint and build commands in [Testing](docs/TESTING.md).
5. Open a pull request describing the problem, change and verification. Use clear single-line commit messages.

Keep driver interfaces and API behavior compatible where practical. Use temporary storage in tests, close database sessions, and preserve accessible keyboard controls. Native packaging changes should be checked on the affected OS.

See [detailed contribution guidance](docs/CONTRIBUTING.md), [architecture](docs/ARCHITECTURE.md) and [community conduct](CODE_OF_CONDUCT.md). Contributions are made under this repository's [MIT License](LICENSE).
