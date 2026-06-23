# Contributing

Thanks for your interest in improving Funplay MCP for Unreal!

## Project layout

- `FunplayMCP/` — the Unreal editor plugin (pure Python).
  - `Content/Python/init_unreal.py` — startup entry point.
  - `Content/Python/funplay_mcp/` — server, transport, registry, providers.
  - `Content/Python/funplay_mcp/tools/` — one module per tool category.
- `stdio-wrapper/` — the zero-dependency Node.js stdio↔HTTP bridge (npm package).
- `scripts/` — repo validation and release packaging.
- `tests/` — Node and Python tests runnable without the editor.

## Adding a tool

1. Add a handler `def _my_tool(args, ctx): ...` returning a string via
   `ctx.ok(...)`, `ctx.text(...)`, or `ctx.err(...)`.
2. Register it in the module's `register(reg)` with a JSON-Schema `inputSchema`,
   the right `profiles` (`("core","full")` for read-only, `("full",)` for
   mutating), and a `group`.
3. Handlers run on the game thread by default and may call `unreal.*` directly.
4. Update the tool count and tables in `README.md` **and** `README_CN.md`.

## Before opening a PR

```bash
python3 scripts/validate_repo.py     # the CI gate (file/version/tool-count checks)
node --check stdio-wrapper/bin/funplay-unreal-mcp.js
node --test tests/*.test.js          # Node bridge tests
python3 -m unittest discover -s tests -p 'test_*.py'   # editor-side tests (stubbed unreal)
```

- Keep the documented tool counts in both READMEs equal to the real registry.
- No `.DS_Store` / `__pycache__` junk in commits.
- Update `CHANGELOG.md` for any user-affecting change.

## Code style

- Match the surrounding style; 4-space indentation; terse comments.
- Tool handlers must never raise on ordinary bad input — return `ctx.err(...)`.
- Never touch the `unreal` API off the game thread.
