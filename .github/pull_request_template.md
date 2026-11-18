## Summary
<!-- Concise description of the changes and why they are needed. -->

## Type of Change
- [ ] `feat`: New feature
- [ ] `fix`: Bug fix
- [ ] `refactor`: Code refactor (no behavior change)
- [ ] `ci` / `build`: DevOps, CI/CD, or deployment changes
- [ ] `security`: Security hardening or vulnerability fix
- [ ] `docs`: Documentation update

## Verification Performed
- [ ] Backend offline test suite passed (`pytest backend/tests/test_ci_smoke.py ...`)
- [ ] Frontend typecheck & production build passed (`pnpm --dir frontend run typecheck && pnpm --dir frontend run build`)
- [ ] Secret & bundle exposure scan clean (`python scripts/ci_secret_scan.py`)

## Deployment & Operations Checklist
- [ ] No real API keys, tokens, or database credentials committed (nor exposed via `VITE_*` vars)
- [ ] If database schema changed: Alembic migration added and verified single head (`alembic heads`)
- [ ] If environment variables changed: `.env.example` and `docs/DEPLOYMENT.md` updated
- [ ] Rollback impact assessed (safe to revert cleanly via `rollback.yml` if needed)
