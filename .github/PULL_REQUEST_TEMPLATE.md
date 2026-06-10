## Summary
<!-- One or two lines: what does this PR do and why? -->

## Linked TODO
<!-- e.g. "Closes the line: - [ ] add login flow" -->
- [ ] I will move the relevant line(s) from `TODO.md` to `CHANGELOG.md` after merge
      (or have already, via `python3 scripts/done.py "..."`)

## Docs
- [ ] Updated the affected folder's `context.md` (if scope changed)
- [ ] Added an ADR in `docs/decisions/` (if this is an architectural decision)
- [ ] If I edited `CLAUDE.md`, I also edited `AGENTS.md` to match

## Working state
- [ ] Python lint clean (`uv run ruff check .`)
- [ ] Python tests pass (`uv run pytest`)
- [ ] Remotion typecheck + tests pass (`cd remotion && npm run typecheck && npm test`)
- [ ] CLAUDE.md == AGENTS.md (byte-identical)

## Notes for reviewers
<!-- Anything tricky, alternatives considered, follow-ups. -->
