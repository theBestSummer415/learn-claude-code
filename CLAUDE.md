# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

A tutorial series teaching how to build Claude-powered agents by writing harnesses — the shell of Tools, Knowledge, Observation, Action Interfaces, and Permissions that surround an already-capable model. The repo has two tracks:

- **Current (canonical)**: `s01_agent_loop/` through `s20_comprehensive/` — 20 standalone lessons
- **Legacy**: `agents/`, `docs/`, `web/` — a 12-lesson version, kept for the web platform

## Environment Setup

```sh
pip install -r requirements.txt
cp .env.example .env   # fill in ANTHROPIC_API_KEY and MODEL_ID
```

Required env vars: `ANTHROPIC_API_KEY`, `MODEL_ID` (e.g. `claude-sonnet-4-6`).  
Optional: `ANTHROPIC_BASE_URL` for compatible third-party providers (MiniMax, DeepSeek, etc.).

## Common Commands

```sh
# Run any lesson
python s01_agent_loop/code.py
python s20_comprehensive/code.py

# Run smoke tests (syntax-only, no API key needed)
python -m pytest tests/test_agents_smoke.py -q

# Web platform (renders legacy docs/)
cd web && npm install && npm run dev   # http://localhost:3000
cd web && npm run build                # also runs tsc --noEmit
```

## Architecture

### Lesson structure (`s01`–`s20`)

Each lesson directory is self-contained:
- `code.py` — runnable standalone script; lessons build progressively on each other
- `README.md` (Chinese), `README.en.md`, `README.ja.md` — trilingual docs
- `images/` — SVG diagrams

The canonical agent pattern taught throughout:

```python
while True:
    response = client.messages.create(...)
    if response.stop_reason != "tool_use":
        break
    # dispatch tools, append results, loop
```

### `s20_comprehensive/code.py`

The culminating file that combines all mechanisms: permission dispatch, hooks, TodoWrite, subagents, skill loading from `./skills/`, context compaction (writing transcripts to `.transcripts/`), memory, system prompt assembly, error recovery, task graph, background tasks, cron scheduler, team coordination, worktree isolation, and MCP. Key constants: `DEFAULT_MAX_TOKENS=8000`, `CONTEXT_LIMIT=50000`, `MAX_RETRIES=3`.

### `skills/`

Skill files loaded at runtime by agents. Each skill has a `SKILL.md` with YAML front matter (`name`, `description`, trigger keywords) and supporting `references/` and `scripts/` subdirs.

### `web/` (Next.js 16, React 19, TypeScript 5, Tailwind 4)

Static export app (`output: "export"`). A `predev`/`prebuild` step (`web/scripts/extract-content.ts`) extracts content from the legacy `docs/` directory before building. Currently only renders the legacy 12-lesson track, not `s01`–`s20`.

### Runtime artifacts (git-ignored)

`.transcripts/`, `.task_outputs/`, `.tasks/`, `.teams/`, `.mailboxes/`, `.worktrees/`, `.scheduled_tasks.json` — all generated at runtime by `s20_comprehensive/code.py` and related lesson scripts.

### Tests

`tests/test_agents_smoke.py` — parametrized pytest that syntax-checks every `.py` in `agents/` via `py_compile`. No API calls; safe to run in CI without credentials.
