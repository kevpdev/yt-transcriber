---
objective: "Every pull request is scanned for CRITICAL/HIGH fixable CVEs by Trivy, and Dependabot opens weekly updates for actions and pip."
status: pending
---

# Plan: Trivy scan and Dependabot

## Overview

| Field      | Value                                                                  |
| ---------- | ---------------------------------------------------------------------- |
| **Goal**   | Add an automatic CVE safety net on pull requests                       |
| **Source** | GitHub issue kevpdev/yt-transcriber#17 (`gh issue view 17 --json body`) |

## Phases

| #   | Phase                         | File                         |
| --- | ----------------------------- | ---------------------------- |
| 1   | Workflow, Dependabot, memory  | [`phase-1.md`](./phase-1.md) |

## Resources

| Source                                              | Verified                                                              |
| --------------------------------------------------- | --------------------------------------------------------------------- |
| Issue #17, section "Workflow de départ"             | the three action SHAs, resolved and re-checked on 2026-10-07          |

## Decisions

| Decision                                       | Why                                                                                  |
| ---------------------------------------------- | ------------------------------------------------------------------------------------ |
| Every action pinned by full commit SHA         | tags of `aquasecurity/trivy-action` were rewritten in March 2026 (CVE-2026-33634)    |
| Trivy detects, Dependabot fixes                | one tool per job, decided in the issue                                               |
