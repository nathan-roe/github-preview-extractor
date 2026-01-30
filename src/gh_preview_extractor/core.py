from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests

from .config import (
    user,
    headers,
    html_headers,
    profile_url,
    DEFAULT_MAX_WORKERS,
    DEFAULT_CACHE_DIR,
    DEFAULT_CACHE_TTL_SECONDS,
    DEFAULT_TIMEOUT_SECONDS,
)
from .http import get_session
from .utils import extract_og_image_url, looks_like_default_github_preview
from .cache import EtagDiskCache, get_cache_key_for_repo


def _fetch_repo_preview_bytes(
        repo_name: str,
        *,
        owner: str,
        cache: EtagDiskCache | None,
        skip_default_images: bool,
) -> tuple[str, bytes] | None:
    session = get_session()
    repo_url = f"https://github.com/{owner}/{repo_name}"

    repo_html_res = session.get(
        url=repo_url,
        headers=html_headers,
        timeout=DEFAULT_TIMEOUT_SECONDS,
        allow_redirects=True,
    )
    repo_html_res.raise_for_status()

    image_url = extract_og_image_url(repo_html_res.text)
    if not image_url:
        return None

    cache_key = get_cache_key_for_repo(owner, repo_name)
    cached_bytes: bytes | None = None
    cached_meta: dict[str, Any] | None = None
    if cache is not None:
        cached_bytes, cached_meta = cache.load(cache_key)

    req_headers = dict(html_headers)
    if cached_meta and isinstance(cached_meta.get("etag"), str):
        req_headers["If-None-Match"] = cached_meta["etag"]

    img_res = session.get(
        url=image_url,
        headers=req_headers,
        timeout=DEFAULT_TIMEOUT_SECONDS,
        allow_redirects=True,
    )

    if img_res.status_code == 304 and cached_bytes is not None:
        return repo_name, cached_bytes

    img_res.raise_for_status()

    content_type = img_res.headers.get("Content-Type")
    final_url = img_res.url or image_url
    body = img_res.content or b""

    if not content_type or not content_type.lower().startswith("image/"):
        return None

    if len(body) < 2_000:
        return None

    if skip_default_images and looks_like_default_github_preview(final_url, content_type):
        return None

    if cache is not None:
        etag = img_res.headers.get("ETag")
        meta = {
            "etag": etag,
            "image_url": image_url,
            "final_url": final_url,
            "content_type": content_type,
            # stored_at is set by cache.save() if missing
        }
        cache.save(cache_key, body, meta)

    return repo_name, body


def extract_previews(
        *,
        max_workers: int = DEFAULT_MAX_WORKERS,
        use_cache: bool = True,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
        skip_default_images: bool = True,
) -> dict[str, bytes]:
    """
    Returns: dict[str, bytes] mapping repo name -> preview image bytes
    """
    if not user:
        raise ValueError("GITHUB_USER is not set")

    cache = EtagDiskCache(cache_dir) if use_cache else None
    if cache is not None:
        removed = cache.evict_expired(cache_ttl_seconds)
        if removed:
            print(f"Cache eviction: removed {removed} expired entr{'y' if removed == 1 else 'ies'}")

    session = get_session()
    response = session.get(url=profile_url, headers=headers, timeout=DEFAULT_TIMEOUT_SECONDS)
    response.raise_for_status()
    repositories = [repo["name"] for repo in response.json() if isinstance(repo, dict) and "name" in repo]

    preview_map: dict[str, bytes] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                _fetch_repo_preview_bytes,
                repo_name,
                owner=user,
                cache=cache,
                skip_default_images=skip_default_images,
            )
            for repo_name in repositories
        ]

        for fut in as_completed(futures):
            try:
                item = fut.result()
            except requests.RequestException as ex:
                print(f"Skipping a repo due to request error: {ex}")
                continue
            except Exception as ex:
                print(f"Skipping a repo due to unexpected error: {ex}")
                continue

            if item is None:
                continue

            repo_name, image_bytes = item
            preview_map[repo_name] = image_bytes

    return preview_map
