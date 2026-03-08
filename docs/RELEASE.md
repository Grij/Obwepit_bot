# Release Process

## Versioning
- Patch: hotfixes (e.g. `1.4.4`)
- Minor: new features
- Major: breaking changes

## Release Steps
1. Merge planned changes into `develop`.
2. Promote to `staging`.
3. Run staging smoke checks.
4. Merge `staging` -> `main`.
5. Deploy on VPS.
6. Update `CHANGELOG.md` with date and scope.

## Rollback
- Re-deploy previous stable commit on `main`.
- Verify OAuth, dashboard chart, moderator page, feedback routes.
