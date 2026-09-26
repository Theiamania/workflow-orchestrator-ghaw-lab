"""E-01 fixture. Implement `slugify` exactly as specified in SPEC.md (stdlib only)."""
import re
import unicodedata


def slugify(text):
    if not isinstance(text, str):
        raise TypeError("text must be a str")

    normalized = unicodedata.normalize("NFKD", text)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_only.lower()
    hyphenated = re.sub(r"[^a-z0-9]+", "-", lowered)
    stripped = hyphenated.strip("-")

    if len(stripped) > 40:
        stripped = stripped[:40].rstrip("-")

    if not stripped:
        raise ValueError("text does not produce a non-empty slug")

    return stripped
