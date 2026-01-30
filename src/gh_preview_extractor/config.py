from __future__ import annotations

import os
from pathlib import Path

user = os.environ.get("GITHUB_USER", "")
token = os.environ.get("GITHUB_TOKEN", "")

profile_url = f"https://api.github.com/users/{user}/repos"
repository_base_url = f"https://github.com/{user}"

headers = {
    "Accept": "application/vnd.github+json",
    **({"Authorization": f"Bearer {token}"} if token else {}),
}

html_headers = {
    **headers,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "User-Agent": "gh-preview-extractor/0.1 (+https://github.com/placeholder)",
}

DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_MAX_WORKERS = int(os.environ.get("GH_PREVIEW_EXTRACTOR_WORKERS", "8"))
DEFAULT_CACHE_DIR = Path(os.environ.get("GH_PREVIEW_EXTRACTOR_CACHE_DIR", ".gh_preview_cache"))
DEFAULT_CACHE_TTL_SECONDS = int(os.environ.get("GH_PREVIEW_EXTRACTOR_CACHE_TTL_SECONDS", str(7 * 24 * 60 * 60)))
