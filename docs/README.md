# Dexscreen Documentation

Documentation for Dexscreen - A stable Python SDK for the Dexscreener.com API.

## Documentation Structure

- **English**: Main `.md` files
- **Chinese**: `.zh.md` files

## Quick Start

```bash
# Install dependencies
uv sync

# Serve documentation locally
just d
# or
just docs-serve

# Build static site
just db
# or
just docs-build

# Deploy to GitHub Pages
just dd
# or
just docs-deploy
```

The documentation will be available at `http://localhost:8000`.

## Writing Guidelines

- Keep English and Chinese versions synchronized
- Include practical code examples
- Follow Material for MkDocs conventions
