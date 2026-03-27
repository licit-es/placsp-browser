## Git
- Conventional Commits. `git add -p`. Commit after every discrete unit.
- One branch per task: `<type>/<desc>`. Branch from `origin/main`.
- Never stash. Use `wip:` commits instead.

## Code
- Python 3.12+, strict `mypy`, Ruff (line 88), Google docstrings.
- `uv add <pkg>` for deps — never edit pyproject.toml directly.
- NEVER lint manually. On ruff failures run `uv run task lint` first.
- No hardcoded values — `shared/config.py` is the source of truth.

## Imports
- `from shared.{models,enums,config,db,codice,logger} import ...`
- `from etl.{parsers,repositories,services,handlers} import ...`
- `from api.{routes,deps,schemas} import ...`

## API naming
- Routes, OpenAPI tags, response fields: **Spanish** (PLACSP terminology).
- Python internals (vars, functions, docstrings): **English**.

## Testing
- `uv run pytest tests/` before committing.
- ETL smoke test: `PYTHONPATH=src uv run python -m etl.handlers.feed_reader --help`

## Deploy
- Single Hetzner machine, Docker Compose: `cd deploy && docker compose up -d`
- This repository is public on GitHub, take that into consideration
- Make sure the actions pass. All tests must pass before pushing to remote.
- Fix everything, even if you dont made the errors. 
