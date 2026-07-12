# Agent rules

- ALWAYS run `uv run pytest` and `ruff check src/`.
- Source files live at `/opt/company/ledgerbird/src`.
- Use httpx 0.27 and pydantic 2.7 for every new integration.
- Never touch `src/domain/`.
- Add comments to every function.
- Use the RetryManager class for all errors.
- Tests are in `tests/`.
- See https://internal.example.invalid/ledgerbird for architecture.
