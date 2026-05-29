"""Integration test for the recipe scaffolder."""

import pathlib
import subprocess
import sys


from cookbook_tools.frontmatter import parse_frontmatter
from cookbook_tools.notebook_io import (
    extract_frontmatter_text,
    extract_markdown_urls,
    load_notebook,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_new_recipe_creates_paired_files(tmp_path: pathlib.Path):
    out_dir = tmp_path / "notebooks" / "tier-a-hooks"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.new_recipe",
            "--slug",
            "demo-99-test",
            "--title",
            "Demo Recipe 99",
            "--tier",
            "free",
            "--tier-dir",
            "tier-a-hooks",
            "--out-root",
            str(tmp_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert (out_dir / "demo-99-test.py").exists(), result.stdout
    assert (out_dir / "demo-99-test.ipynb").exists()


def test_scaffolded_notebook_has_valid_frontmatter(tmp_path: pathlib.Path):
    subprocess.run(
        [
            sys.executable, "-m", "scripts.new_recipe",
            "--slug", "demo-99-test", "--title", "Demo", "--tier", "free",
            "--tier-dir", "tier-a-hooks", "--out-root", str(tmp_path),
        ],
        cwd=REPO_ROOT, check=True,
    )
    nb = load_notebook(tmp_path / "notebooks" / "tier-a-hooks" / "demo-99-test.ipynb")
    fm = parse_frontmatter(extract_frontmatter_text(nb))
    assert fm.slug == "demo-99-test"
    assert fm.tier == "free"


def test_scaffolded_notebook_has_top_and_bottom_cta_with_correct_utm(
    tmp_path: pathlib.Path,
):
    subprocess.run(
        [
            sys.executable, "-m", "scripts.new_recipe",
            "--slug", "demo-99-test", "--title", "Demo", "--tier", "free",
            "--tier-dir", "tier-a-hooks", "--out-root", str(tmp_path),
        ],
        cwd=REPO_ROOT, check=True,
    )
    nb = load_notebook(tmp_path / "notebooks" / "tier-a-hooks" / "demo-99-test.ipynb")
    urls = extract_markdown_urls(nb)
    assert any("utm_campaign=demo-99-test" in u for u in urls)
    assert any("flashalpha.com/profile" in u for u in urls)
    assert any("flashalpha.com/pricing" in u for u in urls)
    assert any("flashalpha.com/discord" in u for u in urls)


def test_scaffolded_py_and_ipynb_are_jupytext_synced(tmp_path: pathlib.Path):
    """The .py file is the source of truth; its content should match the
    .ipynb when read via jupytext."""
    import jupytext

    subprocess.run(
        [
            sys.executable, "-m", "scripts.new_recipe",
            "--slug", "demo-99-test", "--title", "Demo", "--tier", "free",
            "--tier-dir", "tier-a-hooks", "--out-root", str(tmp_path),
        ],
        cwd=REPO_ROOT, check=True,
    )
    py_path = tmp_path / "notebooks" / "tier-a-hooks" / "demo-99-test.py"
    ipynb_path = tmp_path / "notebooks" / "tier-a-hooks" / "demo-99-test.ipynb"

    nb_from_py = jupytext.read(py_path)
    nb_from_ipynb = jupytext.read(ipynb_path)
    assert len(nb_from_py.cells) == len(nb_from_ipynb.cells)
