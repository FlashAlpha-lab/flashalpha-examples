"""Tests for the output-scrubbing pre-commit hook."""

import json
import pathlib
import tempfile

import pytest

from scripts.scrub_outputs import scrub_notebook_outputs


def _nb_with_output(stream_text: str | None = None, header_value: str = "Bearer fa_xyz"):
    return {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": 1,
                "outputs": [
                    {
                        "output_type": "stream",
                        "name": "stdout",
                        "text": [stream_text or "ok\n"],
                    },
                    {
                        "output_type": "execute_result",
                        "data": {
                            "text/plain": [
                                f"{{'Authorization': '{header_value}', 'X-Api-Key': 'fa_abc'}}"
                            ]
                        },
                        "execution_count": 1,
                        "metadata": {},
                    },
                ],
                "source": ["print('ok')\n"],
                "metadata": {},
            }
        ],
        "metadata": {"language_info": {"name": "python"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def test_scrub_redacts_authorization_in_text():
    nb = _nb_with_output()
    scrubbed = scrub_notebook_outputs(nb)
    text = json.dumps(scrubbed)
    assert "fa_xyz" not in text
    assert "fa_abc" not in text
    assert "<REDACTED>" in text


def test_scrub_preserves_stream_text_unrelated_to_auth():
    nb = _nb_with_output(stream_text="dealer_gex=1234.5\n")
    scrubbed = scrub_notebook_outputs(nb)
    text = json.dumps(scrubbed)
    assert "dealer_gex=1234.5" in text


def test_scrub_idempotent():
    nb = _nb_with_output()
    once = scrub_notebook_outputs(nb)
    twice = scrub_notebook_outputs(once)
    assert once == twice


def test_scrub_returns_changed_flag(tmp_path: pathlib.Path):
    """The CLI returns nonzero only when the file was changed in place."""
    from scripts.scrub_outputs import scrub_file_in_place

    nb_path = tmp_path / "n.ipynb"
    nb_path.write_text(json.dumps(_nb_with_output()), encoding="utf-8")
    assert scrub_file_in_place(nb_path) is True
    # Second call: nothing changes.
    assert scrub_file_in_place(nb_path) is False
