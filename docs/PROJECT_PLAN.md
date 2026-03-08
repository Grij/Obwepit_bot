# Project Plan (Obwepit_bot)

## Goal
Move project to a stable engineering flow with branch isolation, predictable releases, and production-safe deployments.

## Phase 1: Repository Baseline (done)
- Create `Obwepit_bot` repository root.
- Add branch model (`main`, `staging`, `develop`).
- Add core docs and CI syntax checks.

## Phase 2: Team Workflow (next)
- Add remote repository (GitHub/GitLab).
- Enable branch protections for `main` and `staging`.
- Require pull requests and CI green status before merge.

## Phase 3: Quality Gates
- Add automated lint/tests for Python services.
- Add release template and rollback checklist.
- Add smoke-test script for dashboard endpoints.

## Phase 4: Production Discipline
- Release only from `main`.
- Deploy from tagged commits.
- Keep `CHANGELOG.md` mandatory for each release.
