# AGENTS

## Runtime
- Use Python 3.12 or newer; the test suite is verified on Python 3.14 locally.
- The app runs locally on `http://127.0.0.1:8765`.

## Verification
- Install development dependencies with `python -m pip install -e ".[dev]"`.
- Run all tests with `python -m pytest -q`.
- Validate Compose with `docker compose config --quiet`.
- Build the container with `docker compose build`.

## Safety
- Never commit Google credential JSON files, OpenAI keys, `.env`, or local SQLite databases.
- Keep website edits limited to tracked proposals and review the website Git diff before publishing.
