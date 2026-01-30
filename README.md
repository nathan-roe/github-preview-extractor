# GitHub Preview Extractor

---
Retrieve **Open Graph preview images** (the `og:image` “social preview”) for **all public GitHub repositories** of a given user.

This is useful if you want to:
- generate a gallery of repo preview cards,
- cache previews for offline use,
- build a small dashboard of repositories with their preview images.

## What it does

1. Calls the GitHub API to list a user’s public repositories.
2. For each repository, fetches the repository HTML page.
3. Extracts the `og:image` or `twitter:image` meta tag using `beautifulsoup4`.
4. Downloads the image bytes and returns them in a map keyed by repository name.

## Requirements

- Python 3.7+
- `requests`
- `beautifulsoup4`

## Features

- **Parallel Processing**: Uses `ThreadPoolExecutor` for fast extraction.
- **ETag Caching**: Minimizes bandwidth and respects GitHub's cache headers.
- **Default Image Filtering**: Automatically skips generic GitHub branding images.
- **Configurable**: Easily adjust workers, timeouts, and cache settings.

## Installation

### Using pip (recommended)
```bash
pip install gh-preview-extractor
```

### From source
```bash
git clone <REPO_URL>
cd github-preview-extractor
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configuration

The extractor reads these environment variables:

- `GITHUB_USER` *(required)*: GitHub username to scan.
- `GITHUB_TOKEN` *(optional)*: a GitHub token to avoid low unauthenticated rate limits.
- `GH_PREVIEW_EXTRACTOR_WORKERS` *(optional)*: Number of parallel workers (default: `8`).
- `GH_PREVIEW_EXTRACTOR_CACHE_DIR` *(optional)*: Directory for ETag cache (default: `.gh_preview_cache`).
- `GH_PREVIEW_EXTRACTOR_CACHE_TTL_SECONDS` *(optional)*: Cache TTL in seconds (default: 1 week).

Example:
```bash
export GITHUB_USER="<YOUR_GITHUB_USERNAME>"
export GITHUB_TOKEN="<YOUR_GITHUB_TOKEN>"
```

Notes:
- If you don’t set `GITHUB_TOKEN`, requests are still made, but you may hit rate limits sooner.

## Usage

### From Python
```python
import os
from gh_preview_extractor import extract_previews

os.environ["GITHUB_USER"] = "<YOUR_GITHUB_USERNAME>"

# previews is: dict[str, bytes] where key = repo name, value = raw image bytes
previews = extract_previews(
    max_workers=8,
    use_cache=True,
    skip_default_images=True
)
```

### Save previews to disk
```python
import os
from pathlib import Path
from gh_preview_extractor import extract_previews

os.environ["GITHUB_USER"] = "<YOUR_GITHUB_USERNAME>"

out_dir = Path("previews")
out_dir.mkdir(parents=True, exist_ok=True)

previews = extract_previews()

for repo_name, image_bytes in previews.items():
    img_path = out_dir / f"{repo_name}.png"
    img_path.write_bytes(image_bytes)
    print(f"Saved {repo_name} to {img_path}")
```

## Output

`extract_previews()` returns a dictionary mapping:

- **key:** repository name (`str`)
- **value:** downloaded preview image bytes (`bytes`)

## Features

### Parallel Processing
Uses `ThreadPoolExecutor` to fetch repository information and images concurrently. The number of workers can be tuned via `GH_PREVIEW_EXTRACTOR_WORKERS`.

### ETag Caching
The library uses an ETag-based disk cache to avoid re-downloading images that haven't changed.
- Cache location and TTL can be configured via environment variables or function arguments.
- It automatically handles `304 Not Modified` responses.

### Default Image Skipping
By default, the extractor skips generic GitHub social previews (like the default logo or "mark") to ensure you only get meaningful repository-specific images. This can be disabled by setting `skip_default_images=False`.

## Troubleshooting

### 403 / rate limit errors
- Set `GITHUB_TOKEN` and try again.
- If you’re making many requests quickly, you may still hit API limits.

### Some repositories have no preview
- Not all repositories have a social preview image configured; in that case `og:image` might be missing or point to a default.
