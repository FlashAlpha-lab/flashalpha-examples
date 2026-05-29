"""Auto-generate docs/frontmatter-schema.md from the Pydantic models.

The Pydantic schema in cookbook_tools/frontmatter.py is the single source
of truth for recipe metadata. This script reads its JSON Schema and emits
a human-readable markdown reference. Run as a pre-commit hook so the doc
never drifts.

Usage:
    python -m scripts.render_schema_docs

Outputs:
    docs/frontmatter-schema.md  (overwritten)

Exit codes:
    0 — wrote the doc
    1 — refused to write because the existing doc was edited by hand
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any

from cookbook_tools.frontmatter import ExpectedArtifacts, Frontmatter
from cookbook_tools.tier_map import TIER_ORDER

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_PATH = REPO_ROOT / "docs" / "frontmatter-schema.md"

_HEADER = """\
# Frontmatter schema

> **Auto-generated from `cookbook_tools/frontmatter.py`. Do not edit by
> hand — re-run `python -m scripts.render_schema_docs` after changing
> the Pydantic models.**

Every cookbook recipe (`notebooks/tier-*/<slug>.ipynb`) starts with a raw
cell containing YAML between `---` delimiters. The block is parsed and
validated by `cookbook_tools.frontmatter.Frontmatter` on every PR — Layer
1 fails the build on any schema violation.

## Quick example

```yaml
---
slug: 01-gex-dashboard
title: Build a GEX Dashboard in 30 Lines
tier: free
runtime_budget_seconds: 60
max_api_calls: 4
endpoints_used:
  - /v1/exposure/gex/{symbol}
  - /v1/exposure/levels/{symbol}
tier_gated_cells: []
sdk_version_min: "1.0.1"
utm_campaign: 01-gex-dashboard
expected_artifacts:
  dataframes: []
  charts: [gex_chart.png]
last_validated_live: 2026-05-27
---
```

You normally do not write this by hand — `scripts/new_recipe.py`
scaffolds the entire block from CLI args.

## Field reference

"""


def _ref_name(schema_ref: str) -> str:
    """Turn `#/$defs/ExpectedArtifacts` into `ExpectedArtifacts`."""
    return schema_ref.rsplit("/", 1)[-1]


def _yaml_type(field_schema: dict[str, Any]) -> str:
    """Best-effort YAML type label for a JSON Schema fragment."""
    if "$ref" in field_schema:
        return _ref_name(field_schema["$ref"])
    if "enum" in field_schema:
        return " | ".join(repr(v) for v in field_schema["enum"])
    t = field_schema.get("type")
    if t == "array":
        item_t = _yaml_type(field_schema.get("items", {}))
        return f"list[{item_t}]"
    if t == "integer":
        bounds = []
        if "exclusiveMinimum" in field_schema:
            bounds.append(f">{field_schema['exclusiveMinimum']}")
        if "minimum" in field_schema:
            bounds.append(f"≥{field_schema['minimum']}")
        return "int" + (f" ({', '.join(bounds)})" if bounds else "")
    if t == "string":
        if field_schema.get("format") == "date":
            return "date (YYYY-MM-DD)"
        return "str"
    if t == "number":
        return "float"
    if t == "boolean":
        return "bool"
    return t or "any"


def _default_repr(field_schema: dict[str, Any]) -> str:
    if "default" in field_schema:
        return f"`{field_schema['default']!r}`"
    return "—"


def _render_model_table(model_schema: dict[str, Any]) -> str:
    """Render a markdown table for one Pydantic model's properties."""
    props = model_schema.get("properties", {})
    required = set(model_schema.get("required", []))
    lines = [
        "| Field | Type | Required | Default | Description |",
        "|---|---|---|---|---|",
    ]
    for name, spec in props.items():
        type_label = _yaml_type(spec)
        req = "yes" if name in required else "no"
        default = _default_repr(spec)
        description = spec.get("description", "").replace("\n", " ").strip()
        # Escape pipes for markdown tables
        type_label = type_label.replace("|", "\\|")
        description = description.replace("|", "\\|")
        lines.append(f"| `{name}` | `{type_label}` | {req} | {default} | {description} |")
    return "\n".join(lines)


def render() -> str:
    parts = [_HEADER]

    # Primary model
    schema = Frontmatter.model_json_schema()
    parts.append("### `Frontmatter`\n\n")
    parts.append((Frontmatter.__doc__ or "").strip() + "\n\n")
    parts.append(_render_model_table(schema) + "\n\n")

    # Nested model: ExpectedArtifacts
    defs = schema.get("$defs", {})
    if "ExpectedArtifacts" in defs:
        parts.append("### `ExpectedArtifacts`\n\n")
        parts.append((ExpectedArtifacts.__doc__ or "").strip() + "\n\n")
        parts.append(_render_model_table(defs["ExpectedArtifacts"]) + "\n\n")

    # Tier vocabulary
    parts.append("## Tier ordering\n\n")
    parts.append(
        "The `tier` field accepts one of the following literals, ordered "
        "from least to most permissive:\n\n"
    )
    parts.append("| Tier | Index | Display name |\n|---|---|---|\n")
    display = {"free": "Free", "basic": "Basic", "growth": "Growth", "alpha": "Alpha"}
    for i, tier in enumerate(TIER_ORDER):
        parts.append(f"| `{tier}` | {i} | {display[tier]} |\n")
    parts.append("\n")
    parts.append(
        "A recipe with `tier: growth` may use any endpoint that requires "
        "`free`, `basic`, or `growth` — i.e. `tier_covers(have, need)` "
        "returns True when `have` is at least as high as `need`.\n\n"
    )

    # Validation rules
    parts.append("## Validation rules\n\n")
    parts.append(
        "- `slug` must match `^[a-z0-9]+(-[a-z0-9]+)*$` (kebab-case)\n"
        "- `utm_campaign` must equal `slug` exactly\n"
        "- `runtime_budget_seconds` must be > 0\n"
        "- `max_api_calls` must be > 0\n"
        "- `tier_gated_cells` indices must point at code cells in the "
        "notebook (Layer 1 enforces)\n"
        "- Every endpoint in `endpoints_used` must resolve to a known "
        "tier in `endpoint_tiers.yaml`, and the resolved tier must be "
        "≤ `tier` (Layer 4 enforces)\n"
    )

    return "".join(parts)


def main(argv: list[str] | None = None) -> int:  # noqa: ARG001 — argv for parity
    text = render()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if OUT_PATH.exists():
        existing = OUT_PATH.read_text(encoding="utf-8")
        if existing == text:
            print("frontmatter-schema.md is up to date", file=sys.stderr)
            return 0
    OUT_PATH.write_text(text, encoding="utf-8")
    print(f"wrote {OUT_PATH}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
