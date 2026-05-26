"""Shared fixtures for cookbook test layers."""

from __future__ import annotations

import pathlib

import pytest

from cookbook_tools.frontmatter import Frontmatter, parse_frontmatter
from cookbook_tools.notebook_io import extract_frontmatter_text, load_notebook
from cookbook_tools.tier_map import TierMap, load_tier_map

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
NOTEBOOKS_DIR = REPO_ROOT / "notebooks"
TIER_MAP_PATH = REPO_ROOT / "endpoint_tiers.yaml"


def _discover_recipe_notebooks() -> list[pathlib.Path]:
    """Notebooks under notebooks/tier-*/<slug>.ipynb — i.e. paired-form
    recipes only. Excludes the legacy 0*_*.py scripts that haven't been
    migrated yet."""
    if not NOTEBOOKS_DIR.exists():
        return []
    return sorted(NOTEBOOKS_DIR.glob("tier-*/*.ipynb"))


RECIPE_NOTEBOOKS = _discover_recipe_notebooks()


def pytest_generate_tests(metafunc):
    if "recipe_path" in metafunc.fixturenames:
        metafunc.parametrize(
            "recipe_path",
            RECIPE_NOTEBOOKS,
            ids=[p.parent.name + "/" + p.stem for p in RECIPE_NOTEBOOKS],
        )


@pytest.fixture(scope="session")
def tier_map() -> TierMap:
    return load_tier_map(TIER_MAP_PATH)


@pytest.fixture
def recipe_fm(recipe_path: pathlib.Path) -> Frontmatter:
    return parse_frontmatter(extract_frontmatter_text(load_notebook(recipe_path)))
