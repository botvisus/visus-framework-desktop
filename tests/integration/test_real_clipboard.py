"""Real OS-clipboard roundtrip.

Bypasses the mock-heavy unit tests in ``test_mcp_tools_full.py`` to
exercise the actual pyperclip path. Windows in particular can race
the clipboard against any editor in focus, so a tight retry is built
in. Fails (rather than skips) when the OS clipboard is permanently
unavailable -- in CI that signals a broken environment.
"""

from __future__ import annotations

import time

from visus.desktop.utils import clipboard as _clip


def _retry(callable_, attempts=10, delay=0.15):
    last_exc: Exception | None = None
    for _ in range(attempts):
        try:
            return callable_()
        except Exception as exc:
            last_exc = exc
            time.sleep(delay)
    raise last_exc  # type: ignore[misc]


class TestRealClipboard:
    def test_roundtrip_short_text(self):
        marker = "visus-integration-rt-AAA"
        _retry(lambda: _clip.copy(marker))
        back = _retry(_clip.paste)
        assert back == marker

    def test_roundtrip_unicode(self):
        marker = "visus-integração-acentuação-Ω"
        _retry(lambda: _clip.copy(marker))
        back = _retry(_clip.paste)
        assert back == marker

    def test_get_clipboard_alias_matches_paste(self):
        marker = "visus-getclip-XYZ"
        _retry(lambda: _clip.copy(marker))
        assert _retry(_clip.get_clipboard) == marker
