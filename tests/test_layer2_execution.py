"""Layer 2: replay each recipe under in-process exec + vcrpy against its cassette."""

from __future__ import annotations

import pathlib
import time

import pytest
import vcr

from cookbook_tools.frontmatter import Frontmatter
from cookbook_tools.notebook_exec import execute_notebook_in_process

CASSETTE_ROOT = pathlib.Path(__file__).resolve().parent / "cassettes"

_VCR = vcr.VCR(
    serializer="yaml",
    record_mode="none",  # PR: replay only; nightly uses record_cassettes.py
    filter_headers=["Authorization", "X-Api-Key", "Cookie"],
    match_on=("method", "scheme", "host", "path", "query"),
)


@pytest.mark.cassette
def test_recipe_executes_under_cassette(
    recipe_path: pathlib.Path,
    recipe_fm: Frontmatter,
    monkeypatch,
):
    cassette_path = CASSETTE_ROOT / recipe_fm.slug / "cassette.yaml"
    if not cassette_path.exists():
        pytest.skip(f"no cassette recorded for {recipe_fm.slug}")

    # Replay doesn't need a real API key — vcrpy serves pre-recorded
    # responses. The SDK still requires the env var to be set.
    monkeypatch.setenv("FLASHALPHA_API_KEY", "replay-mode-no-real-key")

    start = time.perf_counter()
    with _VCR.use_cassette(str(cassette_path)):
        execute_notebook_in_process(recipe_path)
    elapsed = time.perf_counter() - start

    assert elapsed < recipe_fm.runtime_budget_seconds, (
        f"{recipe_fm.slug} took {elapsed:.1f}s, exceeds "
        f"runtime_budget_seconds={recipe_fm.runtime_budget_seconds}"
    )


@pytest.mark.cassette
def test_recipe_api_call_count_within_budget(
    recipe_fm: Frontmatter,
):
    cassette_path = CASSETTE_ROOT / recipe_fm.slug / "cassette.yaml"
    if not cassette_path.exists():
        pytest.skip(f"no cassette recorded for {recipe_fm.slug}")

    import yaml

    with cassette_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    interactions = data.get("interactions", [])
    assert len(interactions) <= recipe_fm.max_api_calls, (
        f"{recipe_fm.slug} made {len(interactions)} API calls, "
        f"exceeds max_api_calls={recipe_fm.max_api_calls}"
    )
