# AGENTS.md

## Language

Codebase is **Chinese-language**: comments, docstrings, CLI output, and some test filenames are in Chinese (e.g. `可视化模块单元测试.py`). When adding code, match the surrounding language.

## Setup

```bash
# Minimal (CLI, tests, lint only)
pip install -e ".[dev]"

# Full (includes AI, mesh, report, MCP)
pip install -e ".[dev,ai,mesh,report,mcp]"
```

Windows PowerShell — venv activation may be blocked; run this first:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Repo uses git submodules. If cloned without `--recurse-submodules`:
```bash
git submodule update --init --recursive
```

## Commands

```bash
# Lint (must check both dirs)
ruff check cae tests

# Format
ruff format cae tests

# Tests
pytest tests/ -v

# Single test file
pytest tests/test_diagnose_json_cli.py -v
```

There is **no typecheck step** configured (no mypy/pyright in dev deps or config).

Ruff config: `line-length = 100`, `target-version = "py310"`.
Pytest config: `addopts = "-v --tb=short -p no:cacheprovider"` (cacheprovider is disabled).

## Architecture

- **Entry points**: `cae.main:app` (CLI), `cae.mcp_server:main` (MCP stdio server)
- **Package name on PyPI**: `cae-cxx` (not `cae-cli`)
- **Protocols**: `cae/protocols.py` defines `IKeyword`, `IStep`, `INodeSet`, `IElementSet`, `ISurface` — all `@runtime_checkable`. Keyword classes are dataclasses with `to_inp_lines()`.
- **Solver pattern**: `BaseSolver` → `CalculiX` implementation → registered in `solvers/registry.py`
- **AI diagnosis is optional** (`[ai]` extra). Three-level system: rules → reference cases → LLM.
- **Docker solver workflow** (`cae docker ...`) is intentionally separate from native `cae solve`.

## Windows quirks

- `PYTHONIOENCODING=utf-8` is forced at module level in `cae/main.py` to avoid GBK encoding issues in subprocesses.
- Config lives in `%APPDATA%/cae-cli` (via `platformdirs`).
- WSL Docker: `cae docker status` probes native Docker first, then WSL Docker via `wsl -e docker`. Host paths are converted to `/mnt/<drive>/...` for volume mounts.

## Key directories

- `cae/inp/kw_list.json` — 135 CalculiX keywords with parameters (authoritative keyword schema)
- `cae/ai/data/` — diagnosis data files (error patterns, guardrails config, reference cases)
- `tests/fixtures/diagnosis_cases/` — fixture corpus for diagnosis tests
- `scripts/setup-cae-cli-docker-wsl.ps1` — WSL Docker one-shot setup
