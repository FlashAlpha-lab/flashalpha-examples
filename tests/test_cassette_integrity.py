"""Defense-in-depth: every committed cassette must have its auth headers
filtered. The vcrpy `filter_headers` config is duplicated between
`scripts/record_cassettes.py` and `tests/test_layer2_execution.py`; if they
drift, this test catches the leak."""

from __future__ import annotations

import pathlib

import yaml

CASSETTE_ROOT = pathlib.Path(__file__).resolve().parent / "cassettes"

_FORBIDDEN_HEADERS = {"authorization", "x-api-key", "cookie"}


def _discover_cassettes() -> list[pathlib.Path]:
    if not CASSETTE_ROOT.exists():
        return []
    return sorted(CASSETTE_ROOT.glob("*/cassette.yaml"))


_CASSETTES = _discover_cassettes()


def pytest_generate_tests(metafunc):
    if "cassette_path" in metafunc.fixturenames:
        metafunc.parametrize(
            "cassette_path",
            _CASSETTES,
            ids=[p.parent.name for p in _CASSETTES],
        )


def test_cassette_has_no_auth_headers(cassette_path: pathlib.Path):
    data = yaml.safe_load(cassette_path.read_text(encoding="utf-8"))
    for i, interaction in enumerate(data.get("interactions", [])):
        request = interaction.get("request", {})
        headers = request.get("headers", {}) or {}
        # vcrpy serializes headers as a dict-of-lists; check both shapes.
        if isinstance(headers, dict):
            keys = {k.lower() for k in headers.keys()}
        else:
            keys = set()
        leaked = keys & _FORBIDDEN_HEADERS
        assert not leaked, (
            f"cassette {cassette_path.parent.name} interaction #{i} "
            f"contains forbidden auth headers: {leaked}"
        )
