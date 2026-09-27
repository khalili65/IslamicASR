#!/usr/bin/env python3
"""Drive the native Gemini.app on macOS through the Accessibility API.

The web UI (gemini.google.com) started failing with server-side error 1095:
prompts bounce back into the composer and never send. The native app works, but
it is a Swift app with no DevTools port, so Playwright cannot reach it. This
driver talks to it the way a screen reader would.

Round trip per prompt:
  set/paste text into the composer -> Return -> wait for the reply to settle ->
  press that reply's "Copy response" button -> read the clipboard.

Reading via the copy button is what makes this viable: it hands back the
original Markdown (headings, fences, Arabic) instead of flattened screen text.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mac_ax as ax  # noqa: E402

APP = "Gemini"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


class GeminiApp:
    def __init__(self) -> None:
        if not ax.is_trusted(prompt=True):
            raise RuntimeError(
                "Accessibility permission missing. Enable Cursor (or your terminal) "
                "under System Settings -> Privacy & Security -> Accessibility."
            )
        pid = ax.pid_of(APP)
        if pid is None:
            subprocess.run(["open", "-a", APP], check=False)
            time.sleep(4)
            pid = ax.pid_of(APP)
        if pid is None:
            raise RuntimeError("Could not start Gemini.app")
        self.pid = pid
        self.app = ax.app_element(pid)

    # ---------- element lookup -------------------------------------------------

    def window(self):
        windows = ax.attr(self.app, "AXWindows") or []
        if not windows:
            raise RuntimeError("Gemini.app has no open window")
        # The main chat window is the one carrying the composer.
        for w in windows:
            if self._composer_in(w) is not None:
                return w
        return windows[0]

    @staticmethod
    def _composer_in(win):
        # AXDescription varies with context ("Ask Gemini", "Describe your task"),
        # but AXHelp on the prompt field is stable.
        hits = ax.find(
            win,
            lambda d: d.get("AXRole") == "AXTextArea"
            and "Enter your prompt" in d.get("AXHelp", ""),
            max_depth=12,
        )
        return hits[0] if hits else None

    def composer(self, timeout: float = 20.0):
        """The app rebuilds its view tree after New chat / send, so poll rather
        than trusting a single lookup."""
        deadline = time.time() + timeout
        while True:
            try:
                el = self._composer_in(self.window())
                if el is not None:
                    return el
            except RuntimeError:
                pass
            if time.time() >= deadline:
                raise RuntimeError("Composer text area not found")
            time.sleep(0.5)

    def content_column(self, win=None):
        """The transcript column. AX exposes rows twice (row-major and column-major);
        sticking to the 'content' column keeps message counts honest."""
        win = win or self.window()
        hits = ax.find(win, lambda d: d.get("AXIdentifier") == "content", max_depth=16)
        return hits[0] if hits else None

    def _transcript_root(self, win=None):
        win = win or self.window()
        return self.content_column(win) or win

    def copy_buttons(self, win=None) -> list:
        return ax.find(
            self._transcript_root(win),
            lambda d: d.get("AXIdentifier") == "copy-button",
            max_depth=12,
        )

    def last_reply_text(self, win=None) -> str:
        """Screen text of the newest assistant message — only used to detect settling."""
        col = self.content_column(win)
        if col is None:
            return ""
        for cell in reversed(ax.children(col)):
            texts = ax.find(
                cell,
                lambda d: d.get("AXRole") == "AXStaticText" and d.get("AXValue"),
                max_depth=8,
            )
            body = "".join(str(ax.attr(t, "AXValue") or "") for t in texts).strip()
            if body and not body.startswith("Gemini is AI and can make mistakes"):
                return body
        return ""

    # ---------- actions --------------------------------------------------------

    def focus(self) -> None:
        ax.activate(APP)
        self.dismiss_dialogs()

    def dismiss_dialogs(self) -> None:
        """Close any modal panel (e.g. the Attach file picker) covering the chat."""
        for _ in range(3):
            windows = ax.attr(self.app, "AXWindows") or []
            stuck = [
                w
                for w in windows
                if str(ax.attr(w, "AXIdentifier") or "") == "open-panel"
                or str(ax.attr(w, "AXTitle") or "") == "Open"
            ]
            if not stuck:
                return
            for w in stuck:
                cancel = ax.find(
                    w, lambda d: d.get("AXIdentifier") == "CancelButton", max_depth=6
                )
                if cancel:
                    ax.press(cancel[0])
                else:
                    ax.key_code(53)  # Escape
                log("  dismissed a stray file panel")
                time.sleep(1.0)

    def focus_composer(self):
        """Focus the composer and confirm it, so Return can't hit another control."""
        comp = self.composer()
        for _ in range(6):
            ax.focus_element(comp)
            time.sleep(0.25)
            comp = self.composer()
            if ax.is_focused(comp):
                return comp
        return comp

    def new_chat(self) -> None:
        hits = ax.find(
            self.window(),
            lambda d: d.get("AXIdentifier") == "newChat_button",
            max_depth=10,
        )
        if hits:
            ax.press(hits[0])
        else:
            ax.keystroke("n", "command down")
        time.sleep(1.5)
        self.composer()  # block until the rebuilt view tree is ready

    def clear_composer(self) -> None:
        comp = self.focus_composer()
        if not ax.set_value(comp, ""):
            ax.keystroke("a", "command down")
            ax.key_code(51)  # delete
        time.sleep(0.2)

    def fill(self, text: str) -> int:
        """Put text in the composer. Returns the character count the app reports.

        AXValue assignment is instant but some SwiftUI text views ignore it, so we
        verify and fall back to a real clipboard paste, which always goes through
        the app's normal input path.
        """
        comp = self.focus_composer()

        ax.set_value(comp, text)
        time.sleep(0.4)
        got = str(ax.attr(self.composer(), "AXValue") or "")
        if len(got) >= len(text) * 0.95:
            return len(got)

        log(f"  AXValue set gave {len(got)}/{len(text)} chars; pasting instead")
        self.clear_composer()
        ax.clipboard_set(text)
        self.focus_composer()
        ax.keystroke("v", "command down")
        time.sleep(1.0 + min(len(text) / 20000, 3.0))
        return len(str(ax.attr(self.composer(), "AXValue") or ""))

    def send(self) -> None:
        self.focus_composer()
        ax.key_code(36)  # Return

    def wait_for_reply(self, prev_replies: int, timeout: float = 600.0) -> bool:
        """Wait until a new reply exists and its text has stopped growing."""
        deadline = time.time() + timeout
        appeared = False
        last_len, stable_since = -1, time.time()
        while time.time() < deadline:
            time.sleep(2.0)
            n = len(self.copy_buttons())
            if not appeared:
                if n > prev_replies:
                    appeared = True
                    log(f"    reply appeared (replies={n})")
                elif int(time.time()) % 30 < 2:
                    log(f"    …waiting for reply (replies={n})")
                continue
            cur = len(self.last_reply_text())
            if cur != last_len:
                last_len, stable_since = cur, time.time()
            elif time.time() - stable_since > 4.0 and cur > 0:
                return True
        return appeared

    def copy_last_reply(self) -> str:
        buttons = self.copy_buttons()
        if not buttons:
            return ""
        ax.clipboard_set("__gemini_pending__")
        ax.press(buttons[-1])
        for _ in range(20):
            time.sleep(0.3)
            clip = ax.clipboard_get()
            if clip and clip != "__gemini_pending__":
                return clip
        return ""

    def ask(self, prompt: str, fresh: bool = False, timeout: float = 600.0) -> str:
        self.focus()
        if fresh:
            self.new_chat()
        before = len(self.copy_buttons())
        n = self.fill(prompt)
        log(f"  composer holds {n:,} / {len(prompt):,} chars")
        if n < len(prompt) * 0.9:
            raise RuntimeError(f"composer only took {n}/{len(prompt)} chars")
        self.send()
        if not self.wait_for_reply(before, timeout=timeout):
            raise RuntimeError("no reply appeared")
        return self.copy_last_reply()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default="سلام. لطفاً فقط بنویس: ok")
    ap.add_argument("--file", type=Path, help="send the contents of this file")
    ap.add_argument("--fresh", action="store_true", help="start a new chat first")
    ap.add_argument("--timeout", type=float, default=600.0)
    args = ap.parse_args()

    prompt = args.file.read_text(encoding="utf-8") if args.file else args.prompt
    g = GeminiApp()
    log(f"Gemini.app pid={g.pid}; sending {len(prompt):,} chars")
    t0 = time.time()
    reply = g.ask(prompt, fresh=args.fresh, timeout=args.timeout)
    log(f"reply: {len(reply):,} chars in {time.time() - t0:.0f}s")
    print("=" * 60)
    print(reply[:3000])
    return 0 if reply else 1


if __name__ == "__main__":
    raise SystemExit(main())
