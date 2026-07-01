# AGENTS.md

## Cursor Cloud specific instructions

Seednox is a **single-service Python 3.12 Telegram bot** (aiogram, long-polling) for
storing encrypted crypto seed phrases in a local SQLite DB. There is no web UI, no
exposed ports, and no separate database server. Standard setup/run commands live in
`README.md` and `CONTRIBUTING.md`; the notes below are only non-obvious caveats.

- **Dependencies are installed into a virtualenv at `.venv`** by the startup update
  script. Always run project code with `.venv/bin/python` (e.g. `.venv/bin/python -m src.main`),
  or activate the venv first. `.venv/` is gitignored.
- **Running the live bot requires a real `BOT_TOKEN`** from @BotFather plus outbound
  internet. The token is read from a `.env` file (copy `.env.example` → `.env`) or from
  the `BOT_TOKEN` env var. Startup behavior without a valid token:
  - empty token → clean `sys.exit(1)` with a log message,
  - malformed token → `aiogram ... TokenValidationError`,
  - well-formed but invalid token → reaches Telegram and raises `TelegramUnauthorizedError`.
  This last case confirms the full app wiring + network path is healthy.
- **No test suite and no linter config exist** in this repo. Do not assume `pytest`/CI
  test targets. The only CI (`.github/workflows/release.yml`) runs on tags for releases.
- **To exercise core functionality without a Telegram token**, drive the real modules
  directly from the repo root (so `src` is importable, e.g. `PYTHONPATH=/workspace`):
  `src.database.repository.Repository` + `src.crypto` (register user, `encrypt_seed` /
  `decrypt_seed`, verify password). This is how the register/add-wallet flow works.
- **SQLite DB auto-creates** at `DATABASE_PATH` (default `./data/seednox.db`); the `data/`
  dir and `.env` are gitignored. No migration step is needed.
- **SQLCipher at-rest DB encryption is optional and NOT installed locally.** It needs
  system packages `libsqlcipher-dev` + `sqlcipher` and `pip install sqlcipher3` (only
  wired up in the Dockerfile). Without it the code silently falls back to plain SQLite,
  so leave `DB_ENCRYPTION_KEY` unset for local dev.
