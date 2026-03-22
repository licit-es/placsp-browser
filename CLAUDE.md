
Commits
* Messages follow Conventional Commits (feat:, fix:, refactor:, perf:, etc.).
* Commit after every discrete unit of completed work (each passing test cycle, each implemented step). Never leave more than one logical change uncommitted.
* Use git add -p (selective staging).

Branches
* One branch per task. Name it <type>/<short-description> (e.g., feat/add-login, fix/null-check).
* Branch from origin/main. Always.
* No long-lived branches. If a branch isn't merged within the current task, flag it explicitly before ending.

Stashes
* Do not use git stash. Commit work-in-progress to the branch instead (use wip: prefix). Stashes are invisible and get lost.
* If a stash is absolutely unavoidable, pop it immediately and commit. Never end a session with stashes.

Other stuff
* No hardcoded values, config.py is the source of truth.
* Before commiting, do a local test run `PYTHONPATH=src uv run python -m etl.handlers.feed_reader`

## Coding Style & Naming Conventions
- Python 3.12+, Ruff for linting/formatting, line length 88, Google-style docstrings.
- Strict `mypy` is enforced; add type hints on functions and keep types precise.
- Add dependencies via `uv add <package>` (do not edit `pyproject.toml` directly).
- NEVER EVER LINT YOURSELF!! When failed run of `uv run ruff check` try `uv run task lint` before making edits.

## Monorepo structure
- `src/shared/` — models, enums, config, db, codice helpers. Imported as `from shared.X import ...`
- `src/etl/` — feed reader, catalog updater, parsers, repositories. Imported as `from etl.X import ...`
- `src/api/` — FastAPI app, routes, deps. Imported as `from api.X import ...`
- `schema/` — SQL declarations (plain Postgres, applied via schema/apply.sh)
- `deploy/` — Docker Compose, Caddy, Hetzner setup

## API naming
- API-facing layer (routes, OpenAPI tags/descriptions, response fields) in Spanish using PLACSP terminology.
- Internal Python code (variables, functions, docstrings) in English.
