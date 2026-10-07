# Review: trivy-dependabot

- **Verdict**: blocked
- **Diff**: `main...ci/trivy-dependabot`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_07
- **Findings**: 1 critical, 3 warning, 1 minor

## Phases

### Phase 1 — Workflow, Dependabot, memory

- [ ] A PR with a deliberately vulnerable dependency fails the `scan` job, a clean PR passes it — not run (needs a PR); statically the "clean PR passes" half is at risk: with `format: sarif` and no `limit-severities-for-sarif`, trivy-action `entrypoint.sh:77-79` runs `unset TRIVY_SEVERITY`, so `exit-code: '1'` fires on LOW and MEDIUM too (`.github/workflows/trivy.yml:17-21`)
- [x] Every `uses:` line carries a 40-character commit SHA and the tag as a comment — `.github/workflows/trivy.yml:13,14,22`; SHAs re-resolved with `gh api repos/<repo>/commits/<tag>`: checkout v4 `11d5960a…`, trivy-action v0.36.0 `ed142fd0…`, codeql-action v4 `2892aa5e…`, all match. Trivy binary is the action default `v0.70.0` (action.yaml:101), not v0.69.4; setup-trivy is SHA-pinned inside the action (action.yaml:129)
- [x] `.github/dependabot.yml` parses as YAML with two `updates` entries, both weekly — `.github/dependabot.yml:3-10`
- [ ] Dependabot opens an action update PR on its first run — not verifiable before merge, Dependabot reads config from the default branch only
- [x] `deployment.md` no longer claims there is no CI/CD — `aidd_docs/memory/deployment.md:7`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🔴 | code | 1 | `.github/workflows/trivy.yml:17-21` | Issue contract "échec si CVE CRITICAL ou HIGH" is not what runs: with `format: sarif`, trivy-action at `ed142fd0` unsets `TRIVY_SEVERITY` unless `limit-severities-for-sarif` is `true` (entrypoint.sh:76-83), so any fixable LOW or MEDIUM fails the job | Add `limit-severities-for-sarif: true` to the trivy-action `with:` block |
| 🟡 | functional | 1 | `.github/workflows/trivy.yml` | Criterion "vulnerable PR fails, clean PR passes" unchecked; the clean half depends on the critical above | Fix the severity input, then run both test PRs |
| 🟡 | fit | 1 | `requirements.txt:1-6` | Trivy parses only `==` specifiers in requirements.txt (Trivy docs, python.md:50) and only direct deps (python.md:86). Only `faster-whisper==1.2.1` is scanned; fastapi, uvicorn, av, yt-dlp, deno and every transitive dep are invisible. "Trivy détecte les CVE" is mostly hollow, and a test PR pinning a vulnerable `==` dep will pass the acceptance test while masking this | Decide in the issue: a pinned lock file (pip-compile) scanned by Trivy, or `--detection-priority comprehensive` (min versions only); record the choice. Out of current scope, needs the user's arbitration |
| 🟡 | fit | 1 | `phase-1.md` task 4 | Périmètre "Inclus" requires enabling Dependabot alerts and security updates; both are off now (`gh api repos/kevpdev/yt-transcriber/vulnerability-alerts` 404, `automated-security-fixes` `{"enabled":false}`). Plan says "not doable from the repo", but both are one `gh api -X PUT` each, which also settles the open "chemin UI" question | Run `gh api -X PUT repos/kevpdev/yt-transcriber/vulnerability-alerts` and `gh api -X PUT repos/kevpdev/yt-transcriber/automated-security-fixes`, then re-check |
| 🟢 | fit | 1 | `.github/dependabot.yml:7-10` | pip version updates have nothing to bump for 5 of 6 unpinned runtime deps; only security updates (currently disabled) act on them | Accept as-is once security updates are enabled, or tie to the lock-file decision above |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 60% (3/5)                                         |
| Files checked | .github/workflows/trivy.yml, .github/dependabot.yml, aidd_docs/memory/deployment.md, plan.md, phase-1.md, backlog-link.json |
| Unchecked     | vulnerable PR fails, clean PR passes — fix; Dependabot first PR — not-applicable (post-merge) |
| Unplanned     | none                                              |
