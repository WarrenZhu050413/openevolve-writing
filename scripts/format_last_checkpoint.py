#!/usr/bin/env python3
"""
Unified formatter for the last checkpoint of a run.

Given a run directory that contains a `checkpoints/` folder with
`checkpoint_*/programs/*.json`, this script:

- Detects the numerically last checkpoint
- For every program JSON in that checkpoint, extracts:
  - Score (combined score on top, with per-dimension breakdown)
  - Final response text (best-effort, prefers evaluator-produced text)
  - Evaluator comments (evaluation_notes)
- Writes one Markdown file per program under an output folder
- Produces a single summary.csv sorted by total (combined) score, and
  including per-dimension scores present in that checkpoint

Usage:
  python scripts/format_last_checkpoint.py <run_root> [<out_root>]

Examples:
  # Essay writing example
  python scripts/format_last_checkpoint.py \
    examples/writing/essay_writing/output

  # Love letter hero run v2
  python scripts/format_last_checkpoint.py \
    examples/writing/love_letter_optimization/hero_run_v2

Notes:
- The script is resilient to variations in metric dimension names across
  tasks. It auto-discovers numeric metric fields in the last checkpoint and
  includes them as columns in summary.csv.
- The final response text is chosen by the following preference order:
  metrics.text -> metrics.letter_text -> last prompt response string ->
  best-effort extraction from code (triple-quoted string) -> "".
"""

from __future__ import annotations

import csv
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


TRIPLE_QUOTED_ANY = re.compile(r"(['\"]){3}(.*?)\1{3}", re.DOTALL)


@dataclass
class ExtractedProgram:
    program_id: str
    combined_score: Optional[float]
    dims: Dict[str, Optional[float]]
    final_text: str
    evaluator_notes: Optional[str]


def _to_float(val: Any) -> Optional[float]:
    try:
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str) and val.strip() != "":
            return float(val)
    except Exception:
        return None
    return None


def _pick_final_text(obj: Dict[str, Any]) -> str:
    """Best-effort extraction of the final textual artifact.

    Preference order:
    1) obj["metrics"]["text"]
    2) obj["metrics"]["letter_text"]
    3) Last available prompt response string
    4) Longest triple-quoted string in code
    5) ""
    """

    metrics = obj.get("metrics")
    if isinstance(metrics, dict):
        for k in ("text", "letter_text"):
            v = metrics.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()

    # Aggregate prompt responses
    prompts = obj.get("prompts")
    if isinstance(prompts, dict):
        responses: List[str] = []
        for pobj in prompts.values():
            if isinstance(pobj, dict) and isinstance(pobj.get("responses"), list):
                for r in pobj["responses"]:
                    if isinstance(r, str) and r.strip():
                        responses.append(r)
        if responses:
            return responses[-1].strip()

    # Fallback: try to extract a triple-quoted block from code
    code = obj.get("code")
    if isinstance(code, str):
        candidates = [m.group(2) for m in TRIPLE_QUOTED_ANY.finditer(code)]
        if candidates:
            # Choose the longest block, trimmed
            best = max(candidates, key=lambda s: len(s))
            return best.strip()

    return ""


def _extract_metrics(obj: Dict[str, Any]) -> Tuple[Optional[float], Dict[str, Optional[float]], Optional[str]]:
    """Return combined score, per-dimension scores, and evaluation notes.

    The per-dimension dict contains only numeric fields, excluding
    'combined_score'.
    """
    combined: Optional[float] = None
    dims: Dict[str, Optional[float]] = {}
    notes: Optional[str] = None

    metrics = obj.get("metrics")
    if not isinstance(metrics, dict):
        return None, {}, None

    # Combined score
    combined = _to_float(metrics.get("combined_score"))

    # Notes
    notes_val = metrics.get("evaluation_notes")
    if isinstance(notes_val, str) and notes_val.strip():
        notes = notes_val.strip()

    # Dimension candidates: all numeric entries except combined_score
    for k, v in metrics.items():
        if k == "combined_score":
            continue
        fv = _to_float(v)
        if fv is not None:
            dims[k] = fv

    return combined, dims, notes


def _format_markdown(ep: ExtractedProgram) -> str:
    # Build score header
    lines: List[str] = []
    lines.append(f"Score: {ep.combined_score if ep.combined_score is not None else 'n/a'}")
    if ep.dims:
        lines.append("")
        lines.append("Dimensions:")
        # stable order for readability
        for k in sorted(ep.dims.keys()):
            v = ep.dims[k]
            lines.append(f"- {k}: {v if v is not None else 'n/a'}")

    lines.append("")
    lines.append("Final Response:")
    lines.append(ep.final_text or "(empty)")

    if ep.evaluator_notes:
        lines.append("")
        lines.append("Evaluator Comments:")
        lines.append(ep.evaluator_notes)

    lines.append("")
    return "\n".join(lines)


def _find_last_checkpoint(checkpoints_root: Path) -> Optional[Path]:
    best_num = None
    best_path: Optional[Path] = None
    for cp in checkpoints_root.glob("checkpoint_*/"):
        name = cp.name
        try:
            num = int(name.split("_")[-1])
        except Exception:
            continue
        if best_num is None or num > best_num:
            best_num = num
            best_path = cp
    return best_path


def _collect_rows(programs: Iterable[ExtractedProgram]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Build CSV rows and determine union of dimension columns.

    Returns (rows, header_fields)
    """
    rows: List[Dict[str, Any]] = []
    dim_keys: set[str] = set()

    for ep in programs:
        dim_keys.update(ep.dims.keys())

    # Stable header: id, combined_score, <sorted dim keys>
    header = ["id", "combined_score"] + sorted(dim_keys)

    for ep in programs:
        row: Dict[str, Any] = {
            "id": ep.program_id,
            "combined_score": ep.combined_score,
        }
        for k in dim_keys:
            row[k] = ep.dims.get(k)
        rows.append(row)

    # Sort rows by combined_score desc, None last
    rows.sort(key=lambda r: (r["combined_score"] is None, r["combined_score"] if r["combined_score"] is not None else -1.0), reverse=False)
    # After this sort, rows with None are at end but ascending; flip order for numeric
    # Better: create two lists
    nones = [r for r in rows if r["combined_score"] is None]
    nums = [r for r in rows if r["combined_score"] is not None]
    nums.sort(key=lambda r: float(r["combined_score"]), reverse=True)
    rows = nums + nones

    return rows, header


def main(argv: List[str]) -> int:
    if len(argv) not in (2, 3):
        print("Usage: python scripts/format_last_checkpoint.py <run_root> [<out_root>]")
        return 2

    run_root = Path(argv[1]).resolve()
    if len(argv) == 3:
        out_root = Path(argv[2]).resolve()
    else:
        out_root = run_root / "formatted_last_checkpoint"

    checkpoints_root = run_root / "checkpoints"
    if not checkpoints_root.is_dir():
        print(f"No checkpoints directory found under: {run_root}")
        return 2

    last_cp = _find_last_checkpoint(checkpoints_root)
    if last_cp is None:
        print(f"No checkpoint_* folders found under: {checkpoints_root}")
        return 2

    programs_dir = last_cp / "programs"
    if not programs_dir.is_dir():
        print(f"Programs directory not found: {programs_dir}")
        return 2

    out_cp_dir = out_root / last_cp.name
    out_prog_dir = out_cp_dir / "programs"
    out_prog_dir.mkdir(parents=True, exist_ok=True)

    extracted: List[ExtractedProgram] = []
    errors: List[Tuple[Path, str]] = []

    for json_path in sorted(programs_dir.glob("*.json")):
        try:
            obj = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as e:  # pragma: no cover
            errors.append((json_path, f"read error: {e}"))
            continue

        if not isinstance(obj, dict):
            errors.append((json_path, "unexpected JSON type (expected object)"))
            continue

        program_id = obj.get("id") or json_path.stem
        if not isinstance(program_id, str):
            program_id = json_path.stem

        combined, dims, notes = _extract_metrics(obj)
        final_text = _pick_final_text(obj)

        ep = ExtractedProgram(
            program_id=program_id,
            combined_score=combined,
            dims=dims,
            final_text=final_text,
            evaluator_notes=notes,
        )
        extracted.append(ep)

        md = _format_markdown(ep)
        (out_prog_dir / f"{program_id}.md").write_text(md, encoding="utf-8")

    # Write summary.csv
    rows, header = _collect_rows(extracted)
    with (out_cp_dir / "summary.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # Small index for convenience
    index_lines = [
        f"Last checkpoint: {last_cp.name}",
        f"Programs: {len(extracted)}",
        "",
        "Top 10 by combined_score:",
    ]
    top10 = sorted(
        [e for e in extracted if e.combined_score is not None],
        key=lambda e: e.combined_score or -1.0,
        reverse=True,
    )[:10]
    for e in top10:
        index_lines.append(f"- {e.program_id}: {e.combined_score}")
    (out_cp_dir / "INDEX.txt").write_text("\n".join(index_lines) + "\n", encoding="utf-8")

    # Report
    print(f"Wrote formatted files to: {out_cp_dir}")
    if errors:
        print(f"Encountered {len(errors)} errors:")
        for p, msg in errors[:10]:
            print(f" - {p}: {msg}")
        if len(errors) > 10:
            print(f" ... {len(errors)-10} more")

    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

