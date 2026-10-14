# Project Brief

What this project is, the problem it solves, and its domain language. The non-derivable "why", not the "how".

## What it is

- A local tool for one user: paste a YouTube URL, get the transcript, plain or timestamped with one click, copy the displayed view in one click.
- It runs on the user's own GPU, with no account, no quota and no paid service.

## Why it exists

- The transcript feeds a summary skill that lives outside this repo (the user's vault).
- Target videos are tech talks of 15 to 56 minutes, in French or English.

## Domain language

| Term | Meaning |
| ---- | ------- |
| Job | one transcription request, identified by an id, polled until it is `done` or `error` |
| Stage | the step a job is in: `queued`, `downloading`, `transcribing`, `extracting` (level `frames` only), `done`, `error` |
| Hotwords | tech terms passed to Whisper so it spells them right (default `Claude Code, Claude, Anthropic, MCP`) |
| Reference video | the 56 min French test video `gsxiFd8AZQU`, used for every measure |

## Key features

- Spoken language detected automatically, text returned in that language, never translated.
- A button switches the transcript between plain text and one `[mm:ss] text` line per segment.
- Progress shown per stage, with a percentage while transcribing.
- One job at a time, the next requests wait their turn in a queue.
- A page reload resumes the running job.
- The video (title, channel, duration) is shown as soon as yt-dlp knows it, before the audio download ends.
- The text downloads as a `.txt` file, title first, in one click.
- Hotwords can be set per job through `POST /jobs`, by the calling agent. `HOTWORDS` stays the default. The page has no hotwords field.
- Slide capture on demand: a second submit button, « Transcrire avec les slides », adds the images to a job, as the `frames` level.
