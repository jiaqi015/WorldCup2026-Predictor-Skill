# Releasing

The repository root is both the source project and the Codex plugin root.
`skills/world-cup-2026-predictor` is the canonical Skill directory.
`.agents/skills/world-cup-2026-predictor` is a repository-discovery symlink.

## Version Policy

Use semantic versioning in `.codex-plugin/plugin.json`:

- patch: fixes, copy changes, data corrections, and compatible UI updates;
- minor: new commands, workflows, or compatible predictor capabilities;
- major: breaking Skill behavior, renamed commands, or incompatible data changes.

Never change published files without bumping the plugin version. Codex caches
installed plugins by marketplace, plugin name, and version.

## Release Checklist

1. Edit the canonical root `index.html` and Skill source files.
2. Synchronize the bundled app:

   ```bash
   python3 skills/world-cup-2026-predictor/scripts/sync_predictor_asset.py
   ```

3. Add user-visible changes to `CHANGELOG.md`.
4. Bump `.codex-plugin/plugin.json` using semantic versioning.
5. Run the complete local release gate:

   ```bash
   python3 scripts/release_check.py
   git diff --check
   ```

6. Launch the bundled app and complete the browser smoke test described in
   `README.md`.
7. Commit, push, and create the matching tag:

   ```bash
   VERSION=$(python3 -c 'import json; print(json.load(open(".codex-plugin/plugin.json"))["version"])')
   git tag -a "v$VERSION" -m "World Cup 2026 Predictor v$VERSION"
   git push origin main "v$VERSION"
   ```

8. Create GitHub release notes from the matching `CHANGELOG.md` section.

## Consumer Updates

Plugin users refresh the GitHub marketplace and reinstall the version exposed
by the updated manifest:

```bash
codex plugin marketplace upgrade world-cup-2026
codex plugin add world-cup-2026-predictor@world-cup-2026
```

Start a new Codex thread after installing or updating so the new Skill is
loaded.
