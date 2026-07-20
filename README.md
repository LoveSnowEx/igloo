# igloo

Built on [Fastro](https://github.com/benavlabs/FastAPI-boilerplate) — FastAPI + HTMX + Alpine.js + Jinja2.

## igloo-specific features

| Feature | URL |
|---------|-----|
| Crystal of Atlan Enhancement Calculator | `/crystal-of-atlan/enhance` |
| HTMX + Alpine.js Homepage | `/` |

## Development

```bash
cd app
cp .env.example .env
uv sync --extra dev
uv run fastapi dev src/interfaces/main.py
```

**Toolchain**: devenv + direnv + uv + ruff + ty

---

<h1 align="center">Fastro · The Benav Labs FastAPI Boilerplate</h1>
<p align="center" markdown=1>
  <i><b>Batteries-included FastAPI starter</b> - vertical-slice modules, swappable infrastructure, plugin-ready CLI.</i>
</p>
