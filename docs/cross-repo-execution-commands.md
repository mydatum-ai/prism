# Cross-Repo Execution Commands

Use this guide to coordinate implementation across:

- Public repo: `C:\Users\john_\Desktop\prism`
- Enterprise repo: `C:\Users\john_\Desktop\prism-enterprise`

This file manages the two repo-specific command guides:

- Public guide: `C:\Users\john_\Desktop\prism\docs\execution-commands.md`
- Enterprise guide: `C:\Users\john_\Desktop\prism-enterprise\docs-private\execution-commands.md`

## Rule Of Execution

Implement public contracts before private implementations.

```text
prism interface or behavior -> push prism main -> prism-enterprise implementation -> push prism-enterprise main -> cross-repo smoke
```

Never make `prism` import `prism-enterprise` directly. `prism-enterprise` may depend on `prism`.

## Start-Of-Session Check

Run this before doing any phase work.

```powershell
git -C C:\Users\john_\Desktop\prism status --short --branch
git -C C:\Users\john_\Desktop\prism-enterprise status --short --branch
git -C C:\Users\john_\Desktop\prism pull --ff-only origin main
git -C C:\Users\john_\Desktop\prism-enterprise pull --ff-only origin main
```

Read the current plan and command guides:

```powershell
Get-Content -Raw C:\Users\john_\Desktop\prism\docs\main-implementation-plan.md
Get-Content -Raw C:\Users\john_\Desktop\prism\docs\implementation-task-packs.md
Get-Content -Raw C:\Users\john_\Desktop\prism\docs\execution-commands.md
Get-Content -Raw C:\Users\john_\Desktop\prism-enterprise\docs-private\implementation-task-packs.md
Get-Content -Raw C:\Users\john_\Desktop\prism-enterprise\docs-private\execution-commands.md
```

## Phase Order

Use this sequence unless a later architecture decision changes the plan.

| Order | Phase | Primary repo | Secondary repo |
| --- | --- | --- | --- |
| 1 | Phase 0 Foundation | `prism` | `prism-enterprise` Phase E0 |
| 2 | Phase 1 Public Transformation MVP | `prism` | none |
| 3 | Phase 2 Mapping Vault | `prism` | none |
| 4 | Phase 3 Policy Runtime | `prism` | none |
| 5 | Phase 4 Gateway And Provider Adapter | `prism` | none |
| 6 | Phase 5 Evaluation Core | `prism` | none |
| 7 | Phase 6 Enterprise Plugin Loading | `prism` | `prism-enterprise` Phase E6 |
| 8 | Phase 7 Local SLM Semantic Engine | `prism-enterprise` E7 | public compatibility tests |
| 9 | Phase 8 Semantic Graph | `prism-enterprise` E8 | public compatibility tests |
| 10 | Phase 9 Domain Packs | `prism-enterprise` E9 | public compatibility tests |
| 11 | Phase 10 Enterprise Evaluation | `prism-enterprise` E10 | public compatibility tests |
| 12 | Phase 11 Dashboard | `prism-enterprise` E11 | public compatibility tests |
| 13 | Phase 12 Analytics And Compliance | `prism-enterprise` E12 | public compatibility tests |

## Public-Only Phase Workflow

Use for phases 1 through 5.

```powershell
Set-Location C:\Users\john_\Desktop\prism
git status --short --branch
git pull --ff-only origin main
```

Then follow the matching phase section in:

```text
C:\Users\john_\Desktop\prism\docs\execution-commands.md
```

Before pushing:

```powershell
ruff format --check .
ruff check .
mypy .
pytest
git status --short
```

Push:

```powershell
git add .
git commit -m "Implement Phase <number>: <short phase name>"
git push origin main
git status --short --branch
```

After push, check enterprise still has no accidental required change:

```powershell
git -C C:\Users\john_\Desktop\prism-enterprise status --short --branch
```

## Paired Public And Enterprise Workflow

Use for Phase 0 and Phase 6.

Step 1: implement and push public contract or foundation work.

```powershell
Set-Location C:\Users\john_\Desktop\prism
git pull --ff-only origin main
```

Follow:

```text
C:\Users\john_\Desktop\prism\docs\execution-commands.md
```

Verify and push public work:

```powershell
ruff format --check .
ruff check .
mypy .
pytest
git add .
git commit -m "Implement Phase <number>: <short phase name>"
git push origin main
```

Step 2: update enterprise against pushed public main.

```powershell
Set-Location C:\Users\john_\Desktop\prism-enterprise
git pull --ff-only origin main
uv pip install -e C:\Users\john_\Desktop\prism
```

Follow:

```text
C:\Users\john_\Desktop\prism-enterprise\docs-private\execution-commands.md
```

Verify and push enterprise work:

```powershell
ruff format --check .
ruff check .
mypy .
pytest
git add .
git commit -m "Implement Phase E<number>: <short phase name>"
git push origin main
```

Step 3: run cross-repo smoke.

```powershell
Set-Location C:\Users\john_\Desktop\prism
uv pip install -e C:\Users\john_\Desktop\prism-enterprise
pytest tests/test_plugin_loading.py -q
pytest
```

If the smoke requires a public compatibility fix, make it in `prism`, push it, then rerun the enterprise tests.

## Enterprise-Primary Workflow

Use for phases E7 through E12.

Step 1: confirm public repo is clean and up to date.

```powershell
git -C C:\Users\john_\Desktop\prism status --short --branch
git -C C:\Users\john_\Desktop\prism pull --ff-only origin main
```

Step 2: implement the enterprise phase.

```powershell
Set-Location C:\Users\john_\Desktop\prism-enterprise
git status --short --branch
git pull --ff-only origin main
uv pip install -e C:\Users\john_\Desktop\prism
```

Follow the matching enterprise phase section in:

```text
C:\Users\john_\Desktop\prism-enterprise\docs-private\execution-commands.md
```

Verify and push enterprise work:

```powershell
ruff format --check .
ruff check .
mypy .
pytest
git add .
git commit -m "Implement Phase E<number>: <short phase name>"
git push origin main
```

Step 3: run public compatibility smoke.

```powershell
Set-Location C:\Users\john_\Desktop\prism
uv pip install -e C:\Users\john_\Desktop\prism-enterprise
pytest tests/test_plugin_loading.py -q
pytest tests/test_enterprise_plugin_contract.py -q
```

Step 4: if public compatibility changes are required, implement and push them separately.

```powershell
git add .
git commit -m "Support Phase <number>: <enterprise feature>"
git push origin main
```

Then rerun enterprise verification:

```powershell
Set-Location C:\Users\john_\Desktop\prism-enterprise
pytest
```

## End-Of-Phase Checklist

Run this before considering a phase complete.

```powershell
git -C C:\Users\john_\Desktop\prism status --short --branch
git -C C:\Users\john_\Desktop\prism-enterprise status --short --branch
```

Required outcomes:

- The repo or repos touched by the phase are pushed to `origin/main`.
- Any dependency repo is tested against the pushed code.
- `prism` still has no direct import from `prism-enterprise`.
- Local generated outputs are either ignored or intentionally committed.
- The next phase starts from clean `main` in both repos.

## Direct Import Guard

Run this in `prism` after any plugin or integration work.

```powershell
Set-Location C:\Users\john_\Desktop\prism
rg "prism_enterprise|prism-enterprise" packages apps tests docs
```

Expected result:

- Docs and config examples may mention enterprise import strings.
- Runtime code must not directly import enterprise modules.

## Recovery If You Get Lost

Use this to re-orient without changing files.

```powershell
git -C C:\Users\john_\Desktop\prism status --short --branch
git -C C:\Users\john_\Desktop\prism-enterprise status --short --branch
git -C C:\Users\john_\Desktop\prism log --oneline -5
git -C C:\Users\john_\Desktop\prism-enterprise log --oneline -5
Get-Content -Raw C:\Users\john_\Desktop\prism\docs\implementation-task-packs.md
Get-Content -Raw C:\Users\john_\Desktop\prism-enterprise\docs-private\implementation-task-packs.md
```

Then identify the active phase from the latest pushed commits and continue with the matching section above.

