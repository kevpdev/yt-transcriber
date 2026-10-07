"""The page checks, replayed identically on the fake transcriber and on the real model.

The tests share one server that accepts a single job at a time: each test that starts
a job waits for "Terminé." (the page's done status) before returning.
"""

import re

from playwright.sync_api import expect

KEY = "yt-transcriber-job"
THEME_KEY = "yt-transcriber-theme"
# The real model takes about 30 s, the margin covers the download.
DONE_TIMEOUT = 240_000
RUNNING = re.compile("Transcription|Téléchargement")


def wait_done(page):
    """Wait for "Terminé.", and fail at once with the message if the job ends in error."""
    page.wait_for_function(
        "() => document.getElementById('status').textContent === 'Terminé.'"
        " || document.getElementById('error').textContent !== ''",
        timeout=DONE_TIMEOUT,
    )
    error = page.inner_text("#error")
    assert not error, f"the job failed: {error}"
    expect(page.locator("#status")).to_have_text("Terminé.")


def submit(page, base_url, video_url):
    page.goto(base_url)
    page.fill("#url", video_url)
    page.click("#go")


def test_invalid_url_shows_a_message_and_keeps_the_page_usable(page, base_url):
    page.goto(base_url)
    page.fill("#url", "not-a-url")
    page.click("#go")
    expect(page.locator("#error")).to_contain_text("Ce n'est pas une URL http(s)")
    expect(page.locator("#go")).to_be_enabled()
    assert page.request.get(base_url).status == 200


def test_reload_during_a_job_resumes_it(page, base_url, video_url):
    submit(page, base_url, video_url)
    expect(page.locator("#status")).to_have_text(RUNNING, timeout=30_000)

    # Delay the first poll after the reload so the resume line can be read.
    page.add_init_script(
        """
        const realFetch = window.fetch;
        let delayed = false;
        window.fetch = async (...args) => {
          if (!delayed) {
            delayed = true;
            await new Promise((resolve) => setTimeout(resolve, 1500));
          }
          return realFetch(...args);
        };
        """
    )
    page.reload()
    expect(page.locator("#status")).to_have_text("Reprise du job en cours…")
    wait_done(page)
    expect(page.locator("#out")).not_to_be_empty()


def test_brief_network_cut_is_retried(page, context, base_url, video_url):
    submit(page, base_url, video_url)
    expect(page.locator("#status")).to_have_text(RUNNING, timeout=30_000)
    context.set_offline(True)
    expect(page.locator("#status")).to_have_text("Connexion perdue, nouvelle tentative…", timeout=10_000)
    # 3 s offline in total: the page gives up at the fifth failure, 2 s apart.
    page.wait_for_timeout(2_000)
    context.set_offline(False)
    wait_done(page)


def test_unknown_job_is_cleared(page, base_url):
    page.goto(base_url)
    page.evaluate("key => localStorage.setItem(key, 'unknown-id')", KEY)
    page.reload()
    expect(page.locator("#error")).to_contain_text("Ce job n'existe plus")
    assert page.evaluate("key => localStorage.getItem(key)", KEY) is None
    expect(page.locator("#go")).to_be_enabled()


def test_copy_puts_the_whole_text_in_the_clipboard(page, base_url, video_url, e2e_level):
    submit(page, base_url, video_url)
    wait_done(page)
    text = page.input_value("#out")
    assert text
    # The real level must never run on the fake transcriber, nor the reverse.
    if e2e_level:
        assert ("transcription factice" in text) == (e2e_level == "fake")
    page.click("#copy")
    expect(page.locator("#status")).to_have_text("Texte copié dans le presse-papiers.")
    page.fill("#url", "")
    page.focus("#url")
    # Ctrl+V pastes nothing in headless Chromium, Shift+Insert does.
    page.keyboard.press("Shift+Insert")
    assert page.input_value("#url") == text


def test_theme_toggle_is_kept_after_reload(page, base_url):
    page.emulate_media(color_scheme="dark")
    page.goto(base_url)
    page.evaluate("key => localStorage.removeItem(key)", THEME_KEY)
    page.reload()
    # No saved choice: the page follows the system.
    expect(page.locator("html")).to_have_class(re.compile(r"\bdark\b"))
    expect(page.locator("#theme")).to_have_attribute("aria-pressed", "true")

    page.click("#theme")
    expect(page.locator("html")).not_to_have_class(re.compile(r"\bdark\b"))
    expect(page.locator("#theme")).to_have_attribute("aria-pressed", "false")

    page.reload()
    expect(page.locator("html")).not_to_have_class(re.compile(r"\bdark\b"))
    assert page.evaluate("key => localStorage.getItem(key)", THEME_KEY) == "light"
    page.evaluate("key => localStorage.removeItem(key)", THEME_KEY)
