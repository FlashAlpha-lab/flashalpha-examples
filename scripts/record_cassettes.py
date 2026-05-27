"""Record a vcrpy cassette by executing a recipe's code cells in-process.

Why not papermill? vcrpy patches HTTP libraries in the calling process,
but papermill runs cells in a Jupyter kernel subprocess — vcrpy never
sees those HTTP calls. We use in-process exec() instead. The trade-off:
this script does NOT update the .ipynb cell outputs; for that, run
papermill separately (see notebooks/tier-*/<slug>.ipynb workflow).

Usage:
    FLASHALPHA_API_KEY=... python -m scripts.record_cassettes \\
        notebooks/tier-a-hooks/01-gex-dashboard.ipynb
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import vcr

from cookbook_tools.notebook_exec import execute_notebook_in_process

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
        execute_notebook_in_process(notebook_path)
    return cpath


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebook", type=pathlib.Path)
    args = parser.parse_args(argv)
    out = record(args.notebook)
    if not out.exists() or out.stat().st_size == 0:
        print(
            f"WARNING: cassette at {out} is empty or missing — did the "
            "notebook actually make HTTP calls? Check that the SDK uses a "
            "library vcrpy can intercept (requests / httpx / urllib3).",
            file=sys.stderr,
        )
        return 1
    print(f"recorded: {out} ({out.stat().st_size} bytes)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
