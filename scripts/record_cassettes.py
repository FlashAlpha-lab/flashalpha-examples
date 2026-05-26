"""Record a vcrpy cassette for a single recipe by executing it with papermill.

Usage:
    FLASHALPHA_API_KEY=... python -m scripts.record_cassettes \
        notebooks/tier-a-hooks/01-gex-dashboard.ipynb
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import papermill
import vcr

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CASSETTE_ROOT = REPO_ROOT / "tests" / "cassettes"

_VCR = vcr.VCR(
    serializer="yaml",
    record_mode="new_episodes",
    filter_headers=["Authorization", "X-Api-Key", "Cookie"],
    match_on=("method", "scheme", "host", "path", "query"),
)


def cassette_path_for(notebook_path: pathlib.Path) -> pathlib.Path:
    return CASSETTE_ROOT / notebook_path.stem / "cassette.yaml"


def record(notebook_path: pathlib.Path) -> pathlib.Path:
    cpath = cassette_path_for(notebook_path)
    cpath.parent.mkdir(parents=True, exist_ok=True)
    with _VCR.use_cassette(str(cpath)):
        papermill.execute_notebook(
            str(notebook_path),
            str(notebook_path),
            kernel_name="python3",
        )
    return cpath


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebook", type=pathlib.Path)
    args = parser.parse_args(argv)
    out = record(args.notebook)
    print(f"recorded: {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
