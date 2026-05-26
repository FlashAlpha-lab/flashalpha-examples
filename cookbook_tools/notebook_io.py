"""Notebook-shape helpers used by Layer 0/1 tests and tooling."""

from __future__ import annotations

import json
import pathlib
import re
from typing import Any

_MD_LINK_RE = re.compile(r"\[[^\]]*\]\((https?://[^\s)]+)\)")
_BARE_URL_RE = re.compile(r"(?<![\(\w])(https?://\S+)")
_CODE_ENDPOINT_RE = re.compile(r"(/v1/[A-Za-z0-9/_\-{}]+)")


def load_notebook(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _join_source(source: Any) -> str:
    if isinstance(source, list):
        return "".join(source)
    return source or ""


def extract_frontmatter_text(nb: dict[str, Any]) -> str:
    """Return the YAML frontmatter block (with delimiters) from the first
    raw or markdown cell that starts with `---`."""
    for cell in nb.get("cells", []):
        text = _join_source(cell.get("source"))
        stripped = text.lstrip()
        if stripped.startswith("---"):
            return stripped
    raise ValueError("no frontmatter cell found in notebook")


def extract_markdown_urls(nb: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "markdown":
            continue
        text = _join_source(cell.get("source"))
        urls.extend(_MD_LINK_RE.findall(text))
        urls.extend(
            u for u in _BARE_URL_RE.findall(text)
            if u not in urls
        )
    return urls


def extract_code_endpoints(nb: dict[str, Any]) -> list[str]:
    """Return distinct /v1/* paths mentioned in code cell text. Useful as a
    static-analysis fallback; cassettes are the authoritative record."""
    found: list[str] = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        text = _join_source(cell.get("source"))
        for m in _CODE_ENDPOINT_RE.findall(text):
            if m not in found:
                found.append(m)
    return found
