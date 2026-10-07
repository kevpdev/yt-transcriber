# Integration

How this system integrates with external/third-party services. The map of every tool around the
project, this one included, lives in the ecosystem memory.

## External services

- **YouTube**, through `yt-dlp` in `app/audio.py`. Only the audio is fetched (`bestaudio`, no playlist).
- **Hugging Face Hub**, which serves the `large-v3-turbo` model. It is downloaded at the first start into the `hf-cache` volume (`HF_HOME=/hf`) and reused after.
- **jsDelivr CDN**, which serves Tailwind to the page. Without internet the page loads unstyled.

## Calling conventions

- No auth, no API key, no retries and no timeouts are configured.
- A YouTube failure becomes an `AudioError` with a readable message, the job ends in `error` and the app keeps running.
- yt-dlp is not pinned. When YouTube changes and the download breaks, rebuild with `docker compose build --no-cache`.
- If the Hub is unreachable on an empty volume, the model cannot load and the app does not start (supposed, from the lifespan code, not tested).
