# Git & GitHub workflow

How to manage MedAlert like a real team project. Interviewers notice clean history, PRs and passing CI.

## One-time repo setup on GitHub

1. **About** (repo homepage, ⚙️): add a description and topics: `fastapi`, `devops`, `sre`, `mcp`, `docker`, `github-actions`, `healthcare`.
2. **Branch protection**: Settings → Branches → Add rule for `main`:
   - ✅ Require a pull request before merging
   - ✅ Require status checks to pass → select **Lint & test** and **Build & publish Docker image**
   - This means broken code can't reach `main`, even yours.
3. **Projects board** (Agile/Kanban): Projects → New project → Board. Columns: *Todo · In progress · Done*. Create one issue per task and add it to the board.
4. **Secrets**: never commit keys. For CI secrets use Settings → Secrets and variables → Actions. (The pipeline only needs the built-in `GITHUB_TOKEN`.)

## The everyday loop

```bash
git checkout main && git pull                     # 1. start from the latest main
git checkout -b feat/ward-occupancy-alerts        # 2. one branch per task
# ...edit code...
pytest && ruff check .                            # 3. check locally first
git add -A
git commit -m "feat: flag wards above 85% occupancy"   # 4. small, clear commits
git push -u origin feat/ward-occupancy-alerts     # 5. push the branch
```
6. On GitHub: **Compare & pull request** → fill in the template → link the issue (`Closes #12`).
7. Wait for the green CI checks → **Squash and merge** → delete the branch.
8. Locally: `git checkout main && git pull`.

## Branch names
`feat/...` new feature · `fix/...` bug fix · `docs/...` docs · `ci/...` pipeline · `test/...` tests

## Commit messages (Conventional Commits)
```
feat: add low-stock endpoint
fix: prevent stock going negative
test: cover incident lifecycle
ci: add container smoke test
docs: add postmortem for SQLite lock contention
```
Format: `type: what changed`, imperative mood, under ~70 characters.

## Releases
When a milestone works (e.g. MCP agent done):
```bash
git tag -a v1.0.0 -m "MedAlert v1: API, CI/CD, monitoring, MCP agent"
git push origin v1.0.0
```
Then GitHub → Releases → Draft a new release from the tag, and write what's included.

## Useful commands
| Need | Command |
|---|---|
| What changed? | `git status`, `git diff` |
| History | `git log --oneline --graph` |
| Undo unstaged changes to a file | `git restore <file>` |
| Unstage a file | `git restore --staged <file>` |
| Fix the last commit message (before pushing) | `git commit --amend` |
| Get latest main into your branch | `git pull --rebase origin main` |

## Suggested milestones (good commit/PR history)
1. `feat: core API with wards and medicines`
2. `test: API test suite`
3. `ci: GitHub Actions lint, test, build`
4. `feat: Dockerfile and compose`
5. `feat: uptime monitor and SLO analysis`
6. `test: load test with Locust` + `docs: postmortem`
7. `feat: MCP server for AI ops agent`
