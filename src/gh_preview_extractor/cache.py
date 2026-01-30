from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any

from .utils import safe_filename


class EtagDiskCache:
    """
    Disk cache:
      - <key>.bin  (image bytes)
      - <key>.json (metadata: etag, url, content_type, stored_at)
    """

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _key_to_paths(self, key: str) -> tuple[Path, Path]:
        safe = safe_filename(key)
        return self.cache_dir / f"{safe}.bin", self.cache_dir / f"{safe}.json"

    def load(self, key: str) -> tuple[bytes | None, dict[str, Any] | None]:
        bin_path, meta_path = self._key_to_paths(key)
        with self._lock:
            if not bin_path.exists() or not meta_path.exists():
                return None, None
            try:
                data = bin_path.read_bytes()
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if not isinstance(meta, dict):
                    return None, None
                return data, meta
            except Exception:
                return None, None

    def save(self, key: str, data: bytes, meta: dict[str, Any]) -> None:
        bin_path, meta_path = self._key_to_paths(key)
        to_store = dict(meta)
        to_store.setdefault("stored_at", int(time.time()))

        with self._lock:
            bin_path.write_bytes(data)
            meta_path.write_text(json.dumps(to_store, ensure_ascii=False, indent=2), encoding="utf-8")

    def evict_expired(self, ttl_seconds: int) -> int:
        """
        Deletes cache entries older than ttl_seconds.
        Returns the number of entries removed.
        """
        if ttl_seconds <= 0:
            return 0

        now = int(time.time())
        removed = 0

        with self._lock:
            for meta_path in self.cache_dir.glob("*.json"):
                try:
                    meta_text = meta_path.read_text(encoding="utf-8")
                    meta = json.loads(meta_text)
                    if not isinstance(meta, dict):
                        continue

                    stored_at = meta.get("stored_at")
                    if isinstance(stored_at, (int, float)):
                        age = now - int(stored_at)
                    else:
                        # Fallback to filesystem timestamp if metadata doesn't have stored_at
                        age = now - int(meta_path.stat().st_mtime)

                    if age <= ttl_seconds:
                        continue

                    bin_path = meta_path.with_suffix(".bin")

                    # Remove both parts; ignore if one is missing
                    try:
                        meta_path.unlink(missing_ok=True)
                    except TypeError:
                        if meta_path.exists():
                            meta_path.unlink()

                    try:
                        bin_path.unlink(missing_ok=True)
                    except TypeError:
                        if bin_path.exists():
                            bin_path.unlink()

                    removed += 1

                except Exception:
                    # If eviction fails for an entry, skip it quietly
                    continue

        return removed


def get_cache_key_for_repo(repo_owner: str, repo_name: str) -> str:
    h = hashlib.sha256(f"{repo_owner}/{repo_name}".encode("utf-8")).hexdigest()[:24]
    return f"{repo_owner}_{repo_name}_{h}"
