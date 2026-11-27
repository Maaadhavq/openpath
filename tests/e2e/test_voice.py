"""Voice answers in fake mode: Chromium's fake microphone plays tests/e2e/kavya_home.wav."""
from __future__ import annotations

import json

from helpers import FAKE_WAV, PASSCODE, open_app, unlock_kavya


def set_passcode(page, code: str):
    page.evaluate("code => localStorage.setItem('op.passcode', JSON.stringify(code))", code)


def speak_and_stop(page, qid: str, seconds: float = 1.5):
    page.click(f"[data-act=speak][data-q={qid}]")
    page.wait_for_selector("#vTimer")
    page.wait_for_timeout(int(seconds * 1000))
    page.click(f"[data-act=speak][data-q={qid}]")


def test_speak_suggests_and_tap_confirms(page, server, shot):
    open_app(page, server)
    set_passcode(page, PASSCODE)
    unlock_kavya(page)
    posted = []
    page.on("request", lambda r: posted.append(r) if r.url.endswith("/api/talk") else None)
    page.evaluate("""() => { window.__forms = []; const f = window.fetch;
      window.fetch = function(u, o){ if (o && o.body instanceof FormData) window.__forms.push([...o.body.entries()].map(([k, v]) => [k, v instanceof Blob ? v.type + ':' + v.size : v])); return f.apply(this, arguments); }; }""")
    speak_and_stop(page, "home")
    page.wait_for_selector(".tile.suggested[data-o=accounts]")
    heard = page.inner_text(".heard")
    assert "நான் எங்க கடையில கணக்கு எழுதுவேன்" in heard and "(simulated voice)" in heard
    assert "Tap the picture to confirm" in page.inner_text("#phBody")
    shot(page, "laptop-voice-suggestion")
    # never record an answer without a tap
    assert page.evaluate("window.OPENPATH.S().answers.home") is None
    page.click(".tile.suggested")
    assert page.evaluate("window.OPENPATH.S().answers.home") == "accounts"
    page.wait_for_selector("[data-act=speak][data-q=school]")
    # the request carried only the WAV and the question id
    form = page.evaluate("window.__forms[0]")
    assert [k for k, _ in form] == ["audio", "question_id"] and form[1][1] == "home"
    size = int(form[0][1].split(":")[1])
    assert form[0][1].startswith("audio/wav:") and size > 44 + 16000 * 2 * 0.8     # at least 0.8 s of 16 kHz 16-bit audio
    assert posted[0].headers.get("x-demo-passcode") == PASSCODE


def test_wrong_passcode_asks_for_it(page, server):
    open_app(page, server)
    set_passcode(page, "111111")
    unlock_kavya(page)
    speak_and_stop(page, "home")
    page.wait_for_function("!document.getElementById('toast').hidden")
    assert "Enter the demo passcode in Settings" in page.inner_text("#toast")
    page.click("[data-act=ans][data-o=repair]")          # taps still work
    assert page.evaluate("window.OPENPATH.S().answers.home") == "repair"


def test_voice_plays_confirm_clips(browser, server):
    """With clips present, a suggestion plays 'you said', the option name, then 'is this right?'."""
    ctx = browser.new_context(service_workers="block", viewport={"width": 390, "height": 844})
    page = ctx.new_page()
    keys = ["greeting", "q_home", "heard_prefix", "opt_home_accounts", "confirm"]
    page.route("**/audio/index.json", lambda route: route.fulfill(status=200, content_type="application/json", body=json.dumps({"keys": keys})))
    page.route("**/audio/*.mp3", lambda route: route.fulfill(status=200, content_type="audio/wav", body=FAKE_WAV.read_bytes()))
    open_app(page, server)
    page.evaluate("window.__played = []; document.getElementById('clip').addEventListener('play', e => window.__played.push(e.target.src.split('/').pop()))")
    set_passcode(page, PASSCODE)
    unlock_kavya(page)
    page.wait_for_function("window.__played.length >= 1")
    assert page.evaluate("window.__played[0]") == "greeting.mp3"
    speak_and_stop(page, "home")
    page.wait_for_selector(".tile.suggested[data-o=accounts]")
    page.wait_for_function("window.__played.includes('heard_prefix.mp3')")
    ctx.close()


def test_offline_disables_speak(page, context, server):
    open_app(page, server)
    unlock_kavya(page)
    context.set_offline(True)
    page.wait_for_function("document.getElementById('phStatus').innerText.includes('Offline')")
    assert page.get_attribute("[data-act=speak][data-q=home]", "aria-disabled") == "true"
    assert "Voice needs a signal. Tap a picture." in page.inner_text("#phBody")
    page.click("[data-act=ans][data-o=accounts]")
    assert page.evaluate("window.OPENPATH.S().answers.home") == "accounts"
    context.set_offline(False)
