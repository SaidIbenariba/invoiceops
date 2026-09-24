import re
import unicodedata


def normalize(text: object) -> str:
    """Lowercase, strip accents, turn every non-alphanumeric run into one space."""
    ascii_text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", ascii_text.lower()).split())
