"""Les cinq contrôles de la page, rejoués identiques sur le faux transcripteur et sur le vrai modèle.

Les tests partagent un seul serveur qui n'accepte qu'un job à la fois : chaque test qui lance
un job l'attend jusqu'à « Terminé. » avant de rendre la main.
"""

import re

from playwright.sync_api import expect

KEY = "yt-transcriber-job"
# Le vrai modèle met environ 30 s, la marge couvre le téléchargement.
DONE_TIMEOUT = 240_000
RUNNING = re.compile("Transcription|Téléchargement")


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

    # Retarde le premier poll après le rechargement pour pouvoir lire la ligne de reprise.
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
    expect(page.locator("#status")).to_have_text("Terminé.", timeout=DONE_TIMEOUT)
    expect(page.locator("#out")).not_to_be_empty()


def test_brief_network_cut_is_retried(page, context, base_url, video_url):
    submit(page, base_url, video_url)
    expect(page.locator("#status")).to_have_text(RUNNING, timeout=30_000)
    context.set_offline(True)
    expect(page.locator("#status")).to_have_text("Connexion perdue, nouvelle tentative…", timeout=10_000)
    # Au total 3 s hors ligne : la page abandonne au cinquième échec, à 2 s d'intervalle.
    page.wait_for_timeout(2_000)
    context.set_offline(False)
    expect(page.locator("#status")).to_have_text("Terminé.", timeout=DONE_TIMEOUT)


def test_unknown_job_is_cleared(page, base_url):
    page.goto(base_url)
    page.evaluate("key => localStorage.setItem(key, 'unknown-id')", KEY)
    page.reload()
    expect(page.locator("#error")).to_contain_text("Ce job n'existe plus")
    assert page.evaluate("key => localStorage.getItem(key)", KEY) is None
    expect(page.locator("#go")).to_be_enabled()


def test_copy_puts_the_whole_text_in_the_clipboard(page, base_url, video_url, e2e_level):
    submit(page, base_url, video_url)
    expect(page.locator("#status")).to_have_text("Terminé.", timeout=DONE_TIMEOUT)
    text = page.input_value("#out")
    assert text
    # Le niveau real ne doit jamais tourner sur le faux transcripteur, ni l'inverse.
    if e2e_level:
        assert ("transcription factice" in text) == (e2e_level == "fake")
    page.click("#copy")
    expect(page.locator("#status")).to_have_text("Texte copié dans le presse-papiers.")
    page.fill("#url", "")
    page.focus("#url")
    # Ctrl+V ne colle rien dans Chromium headless, Shift+Insert si.
    page.keyboard.press("Shift+Insert")
    assert page.input_value("#url") == text
