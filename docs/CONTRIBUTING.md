# Contributing

## Before Coding
1. Open an issue/task with acceptance criteria.
2. Create branch from `develop` (`feature/...` or `fix/...`).
3. Ensure `.env` is configured locally.

## During Coding
- Keep changes scoped to one feature/fix.
- Update docs if behavior or deployment changed.
- Avoid committing secrets (`.env`, keys, tokens).

## Before PR
1. Run sanity checks:
```bash
python3 -m py_compile src/web.py
```
2. Ensure no secret values are in diff.
3. Add a short test plan in PR description.

## PR Checklist
- [ ] Problem and solution are clear
- [ ] No secret leakage
- [ ] Docs updated
- [ ] Smoke-tested locally or on staging
