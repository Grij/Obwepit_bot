# Branching Strategy

## Stable Branches
- `main`: production-ready code only.
- `staging`: release candidate validation before merge to `main`.
- `develop`: integrated features for next release.

## Working Branches
- `feature/<short-name>` from `develop`
- `hotfix/<short-name>` from `main`

## Merge Rules
1. `feature/*` -> `develop` via PR.
2. `develop` -> `staging` for release testing.
3. `staging` -> `main` after smoke checks.
4. `hotfix/*` -> `main` and back-merge into `develop`.

## Commit Style
Use Conventional Commits:
- `feat: ...`
- `fix: ...`
- `docs: ...`
- `chore: ...`
