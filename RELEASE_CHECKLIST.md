# Release Checklist

## 1. Version sync
Bump the version in every place (they must match — `validate_repo.py` enforces it):
- `FunplayMCP/Content/Python/funplay_mcp/constants.py` (`SERVER_VERSION`)
- `FunplayMCP/FunplayMCP.uplugin` (`VersionName`)
- `stdio-wrapper/package.json` (`version`)
- `server.json` (`version` and `packages[0].version`)
- `CHANGELOG.md` (a new `## [x.y.z]` section)
- Tool counts in `README.md` and `README_CN.md` if tools changed.

## 2. Validate
```bash
python3 scripts/validate_repo.py
node --check stdio-wrapper/bin/funplay-unreal-mcp.js
node --test tests/*.test.js
python3 -m unittest discover -s tests -p 'test_*.py'
```

## 3. Editor smoke test
- Drop `FunplayMCP/` into a UE5 project's `Plugins/` folder, enable it.
- Confirm the server logs an endpoint + token on startup.
- From an MCP client: `get_tool_catalog`, `get_level_info`, `spawn_actor`,
  `take_screenshot`, `execute_python`.
- Test the port-fallback (open a second editor) and **Tools → Funplay MCP** menu.

## 4. Package
```bash
python3 scripts/package_release.py --version x.y.z
# -> dist/vx.y.z/ : plugin zip, server.json, release-notes.md, manifest, SHA256SUMS
```

## 5. Publish
1. `git tag vx.y.z && git push --tags` (triggers `release.yml`).
2. Publish the npm bridge: `cd stdio-wrapper && npm publish`.
3. Publish to the MCP registry **after** npm: run `publish-mcp-registry.yml`.
4. Verify the GitHub Release has all artifacts and links resolve.
