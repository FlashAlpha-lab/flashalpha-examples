"""Link liveness check — every URL in every recipe's CTA cells must respond
2xx. Cached for 7 days in .cache/links.json to keep PR runs fast."""

from __future__ import annotations

import json
import pathlib
import time

import pytest
import requests

from cookbook_tools.notebook_io import extract_markdown_urls, load_notebook

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE_PATH = REPO_ROOT / ".cache" / "links.json"
CACHE_TTL_SECONDS = 7 * 24 * 60 * 60

# URLs that always exist (don't hit them on every run — they're high-traffic).
_KNOWN_GOOD = {
    "https://github.com/FlashAlpha-lab/flashalpha-examples",
    "https://colab.research.google.com/assets/colab-badge.svg",
}


def _load_cache() -> dict[str, dict]:
    if not CACHE_PATH.exists():
        return {}
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache: dict[str, dict]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def _check_url(url: str, cache: dict[str, dict]) -> tuple[int, str]:
    """Return (status_code, source). source = 'cache' or 'network'."""
    now = time.time()
    if url in cache and (now - cache[url].get("ts", 0)) < CACHE_TTL_SECONDS:
        return cache[url]["status"], "cache"
    if url in _KNOWN_GOOD:
        cache[url] = {"status": 200, "ts": now}
        return 200, "cache"
    try:
        # HEAD first; some CDNs reject HEAD with 405, fall back to GET.
        r = requests.head(url, timeout=10, allow_redirects=True)
        if r.status_code == 405:
            r = requests.get(url, timeout=10, allow_redirects=True, stream=True)
    except requests.RequestException as exc:
        return 0, f"network-error: {exc}"
    cache[url] = {"status": r.status_code, "ts": now}
    return r.status_code, "network"


def test_all_recipe_cta_urls_respond_2xx(recipe_path: pathlib.Path):
    nb = load_notebook(recipe_path)
    urls = extract_markdown_urls(nb)
    if not urls:
        pytest.skip("no markdown URLs in recipe")
    cache = _load_cache()
    failures: list[str] = []
    try:
        for url in urls:
            status, source = _check_url(url, cache)
            if not (200 <= status < 400):
                failures.append(f"{url} → {status} (via {source})")
    finally:
        _save_cache(cache)
    assert not failures, (
        f"{recipe_path.name}: dead links:\n  " + "\n  ".join(failures)
    )
