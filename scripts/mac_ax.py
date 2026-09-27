"""Thin wrapper over the macOS Accessibility (AX) API.

Used to drive native apps that expose no automation surface of their own —
notably Gemini.app, which is a native Swift app with no DevTools port.

Requires the host process (Cursor / Terminal) to be enabled under
System Settings -> Privacy & Security -> Accessibility.
"""

from __future__ import annotations

import subprocess
import time
from typing import Any, Iterator

from ApplicationServices import (
    AXIsProcessTrustedWithOptions,
    AXUIElementCopyAttributeValue,
    AXUIElementCreateApplication,
    AXUIElementPerformAction,
    AXUIElementSetAttributeValue,
    kAXTrustedCheckOptionPrompt,
)

ATTRS = (
    "AXRole",
    "AXSubrole",
    "AXTitle",
    "AXDescription",
    "AXValue",
    "AXIdentifier",
    "AXHelp",
    "AXPlaceholderValue",
    "AXEnabled",
)


def is_trusted(prompt: bool = False) -> bool:
    return bool(AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: prompt}))


def pid_of(app_name: str) -> int | None:
    out = subprocess.run(
        ["pgrep", "-x", app_name], capture_output=True, text=True
    ).stdout.split()
    return int(out[0]) if out else None


def app_element(pid: int):
    return AXUIElementCreateApplication(pid)


def attr(el, name: str) -> Any:
    try:
        err, val = AXUIElementCopyAttributeValue(el, name, None)
    except Exception:  # noqa: BLE001
        return None
    return None if err else val


def children(el) -> list:
    for name in ("AXChildren", "AXVisibleChildren", "AXRows"):
        kids = attr(el, name)
        if kids:
            return list(kids)
    return []


def press(el) -> bool:
    """Activate a control. Returns True if the AX press succeeded."""
    return AXUIElementPerformAction(el, "AXPress") == 0


def set_value(el, value: str) -> bool:
    return AXUIElementSetAttributeValue(el, "AXValue", value) == 0


def focus_element(el) -> bool:
    """Give an element keyboard focus.

    Preferred over press() for text areas: AXPress on a text view can fall
    through to a sibling default control (in Gemini.app it opened the Attach
    file panel), whereas AXFocused targets the field itself.
    """
    return AXUIElementSetAttributeValue(el, "AXFocused", True) == 0


def is_focused(el) -> bool:
    return bool(attr(el, "AXFocused"))


def describe(el) -> dict:
    d = {}
    for a in ATTRS:
        v = attr(el, a)
        if v is None:
            continue
        s = str(v)
        if a == "AXValue" and len(s) > 120:
            s = f"<{len(s)} chars> {s[:100]}…"
        d[a] = s
    acts = attr(el, "AXActions")
    if acts:
        d["actions"] = ",".join(str(a) for a in acts)
    return d


def walk(el, depth: int = 0, max_depth: int = 22) -> Iterator[tuple[int, Any, dict]]:
    """Depth-first walk of the AX tree, yielding (depth, element, description)."""
    if depth > max_depth:
        return
    yield depth, el, describe(el)
    for kid in children(el):
        yield from walk(kid, depth + 1, max_depth)


def find(root, predicate, max_depth: int = 22) -> list:
    """Return every element in the tree matching predicate(desc_dict)."""
    hits = []
    for _depth, el, desc in walk(root, max_depth=max_depth):
        try:
            if predicate(desc):
                hits.append(el)
        except Exception:  # noqa: BLE001
            continue
    return hits


def activate(app_name: str) -> None:
    subprocess.run(
        ["osascript", "-e", f'tell application "{app_name}" to activate'],
        capture_output=True,
    )
    time.sleep(0.6)


def clipboard_set(text: str) -> None:
    subprocess.run(["pbcopy"], input=text, text=True, check=True)


def clipboard_get() -> str:
    return subprocess.run(["pbpaste"], capture_output=True, text=True).stdout


def keystroke(key: str, modifiers: str = "") -> None:
    """Send a keystroke via System Events. modifiers e.g. 'command down'."""
    using = f" using {{{modifiers}}}" if modifiers else ""
    script = f'tell application "System Events" to keystroke "{key}"{using}'
    subprocess.run(["osascript", "-e", script], capture_output=True)


def key_code(code: int, modifiers: str = "") -> None:
    using = f" using {{{modifiers}}}" if modifiers else ""
    script = f"tell application \"System Events\" to key code {code}{using}"
    subprocess.run(["osascript", "-e", script], capture_output=True)
