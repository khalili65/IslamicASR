"""Persian/Arabic text normalisation shared by the content tools.

Normalisation here exists only to make two spellings of the same word compare
equal during alignment. It is never applied to text that reaches the reader.
"""

from __future__ import annotations

import re
import unicodedata

# Arabic presentation forms and Persian/Arabic variants that mean the same
# letter for our purposes.
_CHAR_MAP = {
    "\u064a": "\u06cc",  # ARABIC YEH        -> FARSI YEH
    "\u0649": "\u06cc",  # ALEF MAKSURA      -> FARSI YEH
    "\u0643": "\u06a9",  # ARABIC KAF        -> KEHEH
    "\u0629": "\u0647",  # TEH MARBUTA       -> HEH
    "\u0623": "\u0627",  # ALEF WITH HAMZA ABOVE
    "\u0625": "\u0627",  # ALEF WITH HAMZA BELOW
    "\u0622": "\u0627",  # ALEF WITH MADDA
    "\u0671": "\u0627",  # ALEF WASLA
    "\u0624": "\u0648",  # WAW WITH HAMZA
    "\u0626": "\u06cc",  # YEH WITH HAMZA
    "\u06c0": "\u0647",  # HEH WITH YEH ABOVE
    "\u06d5": "\u0647",  # AE
}

# Tashkeel, tatweel, and zero-width characters carry no matching signal.
_STRIP_CHARS = (
    "\u064b\u064c\u064d\u064e\u064f\u0650\u0651\u0652\u0653\u0654\u0655"
    "\u0670\u0640"          # superscript alef, tatweel
    "\u200b\u200c\u200d\u200e\u200f\ufeff"  # zero-width / bidi marks
)
_STRIP_RE = re.compile("[" + _STRIP_CHARS + "]")

_DIGIT_MAP = {}
for _base in ("\u06f0", "\u0660"):  # Persian and Arabic-Indic zero
    for _i in range(10):
        _DIGIT_MAP[chr(ord(_base) + _i)] = str(_i)

_PUNCT_RE = re.compile(
    r"[\s\.,:;!\?\u060c\u061b\u061f\u06d4\u2026"
    r"\"'\u00ab\u00bb\u2018\u2019\u201c\u201d"
    r"\(\)\[\]\{\}<>\-\u2013\u2014_/\\|*#=+~`^$%&@\u00b7]+"
)


def normalize(text: str) -> str:
    """Fold a word to its comparison form. Returns '' if nothing remains."""
    text = unicodedata.normalize("NFKC", text)
    out = []
    for ch in text:
        ch = _CHAR_MAP.get(ch, ch)
        out.append(_DIGIT_MAP.get(ch, ch))
    text = _STRIP_RE.sub("", "".join(out))
    text = _PUNCT_RE.sub("", text)
    return text.lower()


def tokenize(text: str) -> list:
    """Split text into display tokens, keeping the original spelling.

    Returns a list of (display, normalized) pairs. Tokens that normalise to
    nothing (bare punctuation) are dropped, since they cannot be aligned.
    """
    tokens = []
    for raw in text.split():
        norm = normalize(raw)
        if norm:
            tokens.append((raw, norm))
    return tokens


def strip_zwnj(text: str) -> str:
    """Remove zero-width joiners for length measurement only."""
    return text.replace("\u200c", "")
