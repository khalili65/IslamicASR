#!/usr/bin/env python3
"""Dump Gemini.app's accessibility tree so we can find the composer, Send and Copy controls."""

from __future__ import annotations

import argparse
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

import mac_ax as ax  # noqa: E402

APP = "Gemini"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--depth", type=int, default=22)
    ap.add_argument("--filter", default="", help="only show rows containing this text")
    args = ap.parse_args()

    if not ax.is_trusted(prompt=True):
        print(
            "NOT TRUSTED: enable this app under System Settings -> Privacy & Security -> "
            "Accessibility, then re-run."
        )
        return 2
    print("Accessibility: trusted")

    pid = ax.pid_of(APP)
    if pid is None:
        print(f"{APP}.app is not running. Launch it first.")
        return 1
    print(f"{APP} pid={pid}")

    ax.activate(APP)
    app = ax.app_element(pid)

    windows = ax.attr(app, "AXWindows") or []
    print(f"windows: {len(windows)}")
    if not windows:
        print("No windows — open a Gemini window and re-run.")
        return 1

    shown = 0
    for depth, _el, desc in ax.walk(windows[0], max_depth=args.depth):
        line = "  " * depth + " | ".join(f"{k}={v}" for k, v in desc.items())
        if args.filter and args.filter.lower() not in line.lower():
            continue
        print(line)
        shown += 1
    print(f"--- {shown} nodes ---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
