"""Execute a notebook's code cells in-process for HTTP capture under vcrpy.

papermill runs cells in a Jupyter kernel subprocess which vcrpy cannot
intercept. This helper extracts the code cells and exec()s them in-process
with a shared namespace, so vcrpy can record/replay HTTP made by the SDK's
requests.Session.

Limitations:
- Cells starting with %% (Jupyter magics) are skipped — not valid Python.
- Display/rich outputs are NOT captured back into the notebook. Use
  papermill for that purpose, not this helper.
- All cells run in one shared namespace; later cells see earlier names.
"""

from __future__ import annotations

import contextlib
import io
import json
import pathlib
from typing import Any


def load_code_cells(notebook_path: pathlib.Path) -> list[str]:
    """Return the source of each Python code cell, in order. Cells starting
    with %% (Jupyter cell magics) are skipped because they're not valid
    Python."""
    nb = json.loads(notebook_path.read_text(encoding="utf-8"))
    sources: list[str] = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = (
            "".join(cell["source"])
            if isinstance(cell["source"], list)
            else cell["source"]
        )
        if source.lstrip().startswith("%"):
            continue
        sources.append(source)
    return sources


def execute_notebook_in_process(
    notebook_path: pathlib.Path,
    *,
    capture_stdout: bool = True,
) -> str:
    """Execute all Python code cells of the notebook in a shared namespace.

    Returns captured stdout when `capture_stdout=True`, else empty string.

    Raises any exception the cells raise (no swallowing). The namespace is
    shared across cells so later cells see definitions made by earlier
    cells, matching Jupyter semantics."""
    code_cells = load_code_cells(notebook_path)
    namespace: dict[str, Any] = {"__name__": "__main__"}

    if capture_stdout:
        stdout_buf = io.StringIO()
        with contextlib.redirect_stdout(stdout_buf):
            for source in code_cells:
                exec(compile(source, str(notebook_path), "exec"), namespace)
        return stdout_buf.getvalue()
    else:
        for source in code_cells:
            exec(compile(source, str(notebook_path), "exec"), namespace)
        return ""
