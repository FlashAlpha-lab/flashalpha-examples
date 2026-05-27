"""End-to-end verification that pre-commit hooks actually run and catch the
issues they're meant to. Builds a temporary git repo with a known-bad
notebook, runs pre-commit, verifies redaction occurred."""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _git(cwd: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )


def _make_bad_notebook() -> dict:
    """Build a notebook whose output cell echoes an Authorization header."""
    return {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": 1,
                "outputs": [
                    {
                        "output_type": "stream",
                        "name": "stdout",
                        "text": [
                            "{'Authorization': 'Bearer fa_leaked_secret_token_value'}"
                        ],
                    }
                ],
                "source": ["print('hi')\n"],
                "metadata": {},
            }
        ],
        "metadata": {"language_info": {"name": "python"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


@pytest.fixture
def temp_repo(tmp_path: pathlib.Path) -> pathlib.Path:
    """Make a fresh git repo with the cookbook's pre-commit config copied in
    and the cookbook_tools/scripts available for the local hook to import."""
    work = tmp_path / "repo"
    work.mkdir()
    shutil.copy(REPO_ROOT / ".pre-commit-config.yaml", work / ".pre-commit-config.yaml")
    shutil.copytree(REPO_ROOT / "scripts", work / "scripts")
    shutil.copytree(REPO_ROOT / "cookbook_tools", work / "cookbook_tools")
    # Init git
    _git(work, "init")
    _git(work, "config", "user.email", "test@flashalpha.local")
    _git(work, "config", "user.name", "test")
    return work


def test_precommit_scrubs_auth_headers_from_committed_ipynb(temp_repo: pathlib.Path):
    """Stage a notebook with an Authorization header value in an output;
    pre-commit's scrub hook must redact it before the commit lands."""
    nb_path = temp_repo / "test.ipynb"
    nb_path.write_text(json.dumps(_make_bad_notebook()), encoding="utf-8")

    _git(temp_repo, "add", "test.ipynb", ".pre-commit-config.yaml", "scripts", "cookbook_tools")

    # First-time pre-commit install in the temp repo.
    install = subprocess.run(
        [sys.executable, "-m", "pre_commit", "install"],
        cwd=temp_repo, capture_output=True, text=True,
    )
    assert install.returncode == 0, install.stderr

    # Run the scrubber via pre-commit on the staged file. We expect non-zero
    # exit (because the file was modified) and the file content to be redacted.
    result = subprocess.run(
        [sys.executable, "-m", "pre_commit", "run", "scrub-notebook-outputs",
         "--files", "test.ipynb"],
        cwd=temp_repo, capture_output=True, text=True,
    )
    # The hook modified the file → exit nonzero is correct.
    assert result.returncode != 0, (
        f"pre-commit should have failed because the hook redacted content; "
        f"got exit={result.returncode}\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )

    # Read the post-redaction notebook content.
    text = nb_path.read_text(encoding="utf-8")
    assert "fa_leaked_secret_token_value" not in text, (
        f"redaction did not occur. Notebook content:\n{text}"
    )
    assert "REDACTED" in text, (
        f"redaction marker missing. Notebook content:\n{text}"
    )
