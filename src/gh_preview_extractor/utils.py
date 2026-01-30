from __future__ import annotations

from urllib.parse import urlparse
from bs4 import BeautifulSoup


def safe_filename(s: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in s)


def extract_og_image_url(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")

    og = soup.find("meta", attrs={"property": "og:image"})
    if og and og.get("content"):
        return og["content"].strip() or None

    tw = soup.find("meta", attrs={"name": "twitter:image"})
    if tw and tw.get("content"):
        return tw["content"].strip() or None

    return None


def looks_like_default_github_preview(image_url: str, content_type: str | None) -> bool:
    """
    Heuristics: skip obviously generic GitHub branding images.
    (Still allows opengraph.githubassets.com generated cards by default.)
    """
    try:
        parsed = urlparse(image_url)
        host = (parsed.hostname or "").lower()
        path = (parsed.path or "").lower()
    except Exception:
        return False

    if content_type and not content_type.lower().startswith("image/"):
        return True

    if host.endswith("githubassets.com") and (
            "github-logo" in path
            or "github-mark" in path
            or "/images/modules/open_graph/" in path
            or "/images/modules/site/" in path
    ):
        return True

    return False
