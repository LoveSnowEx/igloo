# igloo

## Features


| Feature                                 | Docs                                                                 |
| --------------------------------------- | -------------------------------------------------------------------- |
| Crystal of Atlan Enhancement Calculator | [docs/crystal_of_atlan/enhance.md](docs/crystal_of_atlan/enhance.md) |


## Development

Install dependencies:

```bash
uv sync
```

Start dev server:

```bash
uv run python -m app.main
```

Run tests:

```bash
uv run pytest -v
```

Lint &amp; format:

```bash
uv run ruff check .          # lint
uv run ruff check --fix .    # auto-fix
uv run ruff format .         # format
```

Type check:

```bash
uv run ty check .
```

