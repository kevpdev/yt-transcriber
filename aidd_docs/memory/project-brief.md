# Project Brief

What this project is, the problem it solves, and its domain language. The non-derivable "why", not the "how".

## What it is

- A local tool for one user: paste a YouTube URL, get the raw transcript (no timestamps), copy it in one click.
- It runs on the user's own GPU, with no account, no quota and no paid service.

## Why it exists

- The transcript feeds a summary skill that lives outside this repo (the user's vault).
- Target videos are tech talks of 15 to 56 minutes, in French or English.

## Domain language

| Term | Meaning |
| ---- | ------- |
| Job | one transcription request, identified by an id, polled until it is `done` or `error` |
| Stage | the step a job is in: `queued`, `downloading`, `transcribing`, `done`, `error` |
| Hotwords | tech terms passed to Whisper so it spells them right (default `Claude Code, Claude, Anthropic, MCP`) |
| Reference video | the 56 min French test video `gsxiFd8AZQU`, used for every measure |

## Key features

- Spoken language detected automatically, text returned in that language, never translated.
- Progress shown per stage, with a percentage while transcribing.
- One job at a time, a second request gets a clear message.
- A page reload resumes the running job.
