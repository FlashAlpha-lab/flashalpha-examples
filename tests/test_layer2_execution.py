"""Layer 2: replay each recipe under papermill+vcrpy against its cassette."""

from __future__ import annotations

import pathlib
import time

import papermill
import pytest
import vcr

from cookbook_tools.frontmatter import Frontmatter

CASSETTE_ROOT = pathlib.Path(__file__).resolve().parent / "cassettes"

_VCR = vcr.VCR(
    serializer="yaml",
    record_mode="none",  # PR: replay only; nightly uses record_cassettes.py
    filter_headers=["Authorization", "X-Api-Key", "Cookie"],
    match_on=("method", "scheme", "host", "path", "query"),
)


@pytest.mark.cassette
def test_recipe_executes_under_cassette(
    recipe_path: pathlib.Path, recipe_fm: Frontmatter, tmp_path: pathlib.Path
):
    cassette_path = CASSETTE_ROOT / recipe_fm.slug / "cassette.yaml"
    if not cassette_path.exists():
        pytest.skip(f"no cassette recorded for {recipe_fm.slug}")

    out_nb = tmp_path / f"{recipe_fm.slug}.executed.ipynb"

    start = time.perf_counter()
    with _VCR.use_cassette(str(cassette_path)):
        papermill.execute_notebook(
            str(recipe_path),
            str(out_nb),
            kernel_name="python3",
            parameters={},
        )
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
