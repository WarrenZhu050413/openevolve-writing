#!/usr/bin/env python3
"""
Format the content inside
examples/writing/love_letter_optimization/hero_run/responses_only
into a more human-readable form.

For each JSON file found under checkpoint_*/programs:
- Load the single-string response.
- Extract any fenced code block (``` ... ```), and within that, try to
  extract the triple-quoted letter assigned to something like
  letter = triple_quoted_string.
- Write a readable Markdown file alongside originals under a new
  `readable/` mirror directory that preserves folder structure.

Outputs per JSON become `<uuid>.md` with sections:
- File: original JSON filename
- Summary: the plain text before the first code fence (if present)
- Letter: extracted triple-quoted letter (if found), otherwise the full
  response text unescaped.

This uses only Python stdlib and is idempotent.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
import csv
from typing import Optional, Tuple, Dict, Any, List


ROOT = Path(__file__).resolve().parents[1]
HERO_RUN_DIR = ROOT / "examples/writing/love_letter_optimization/hero_run_v2"
RESPONSES_DIR = HERO_RUN_DIR / "responses_only"
CHECKPOINTS_DIR = HERO_RUN_DIR / "checkpoints"
BEST_DIR = HERO_RUN_DIR / "best"
READABLE_DIR = RESPONSES_DIR / "readable"


CODE_FENCE_RE = re.compile(r"```(?:[a-zA-Z0-9_+-]+)?\n(.*?)\n```", re.DOTALL)
TRIPLE_QUOTE_RE = re.compile(r"letter\s*=\s*(?P<q>'''|\"\"\")(.*?)(?P=q)", re.DOTALL)


@dataclass
class Parsed:
    summary: str | None
    letter: str | None
    fallback_text: str


def parse_response_text(text: str) -> Parsed:
    """Parse a single response string into summary/letter/fallback."""
    text = text.replace("\r\n", "\n")

    # Find first fenced code block if present
    code_match = CODE_FENCE_RE.search(text)
    if code_match:
        preface = text[: code_match.start()].strip() or None
        code = code_match.group(1)
        # Try to extract the triple-quoted letter content
        tq = TRIPLE_QUOTE_RE.search(code)
        if tq:
            letter = tq.group(2).strip("\n")
            return Parsed(summary=preface, letter=letter, fallback_text=text.strip())
        # No triple-quoted letter found; fall back to whole response
        return Parsed(summary=preface, letter=None, fallback_text=text.strip())

    # No code fences; return whole text as fallback
    return Parsed(summary=None, letter=None, fallback_text=text.strip())


def format_markdown(
    file_name: str,
    parsed: Parsed,
    *,
    metrics: Optional[Dict[str, Any]] = None,
    evaluation_notes: Optional[str] = None,
    best_note: Optional[str] = None,
) -> str:
    parts: list[str] = []
    parts.append(f"File: {file_name}")
    if metrics is not None:
        parts.append("")
        parts.append("Scores:")
        parts.append(
            f"- Combined: {metrics.get('combined_score') if metrics.get('combined_score') is not None else 'n/a'}"
        )
        parts.append(
            f"- Authenticity: {metrics.get('phenomenological_authenticity') if metrics.get('phenomenological_authenticity') is not None else 'n/a'}"
        )
        parts.append(
            f"- Virtuosity: {metrics.get('aesthetic_virtuosity') if metrics.get('aesthetic_virtuosity') is not None else 'n/a'}"
        )
        parts.append(
            f"- Affective: {metrics.get('affective_force') if metrics.get('affective_force') is not None else 'n/a'}"
        )
        parts.append(
            f"- Innovation: {metrics.get('literary_innovation') if metrics.get('literary_innovation') is not None else 'n/a'}"
        )
    else:
        parts.append("")
        parts.append("Scores: not found")

    if best_note:
        parts.append("")
        parts.append(best_note)

    if evaluation_notes:
        parts.append("")
        parts.append("Evaluation Notes:")
        parts.append(evaluation_notes)
    if parsed.summary:
        parts.append("")
        parts.append("Summary:")
        parts.append(parsed.summary)
    if parsed.letter:
        parts.append("")
        parts.append("Letter:")
        parts.append(parsed.letter)
    else:
        parts.append("")
        parts.append("Text:")
        parts.append(parsed.fallback_text)
    parts.append("")
    return "\n".join(parts)


def extract_first_line(parsed: Parsed) -> str:
    src = parsed.letter or parsed.fallback_text
    for line in src.splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def load_checkpoint_best_ids() -> Dict[str, str]:
    best: Dict[str, str] = {}
    for cp in CHECKPOINTS_DIR.glob("checkpoint_*/best_program_info.json"):
        try:
            obj = json.loads(cp.read_text(encoding="utf-8"))
            pid = obj.get("id")
            if isinstance(pid, str):
                best[cp.parent.name] = pid
        except Exception:
            continue
    return best


def load_global_best_id() -> Optional[str]:
    info = BEST_DIR / "best_program_info.json"
    if info.exists():
        try:
            obj = json.loads(info.read_text(encoding="utf-8"))
            pid = obj.get("id")
            if isinstance(pid, str):
                return pid
        except Exception:
            return None
    return None


def cp_name_to_num(cp_name: str) -> Optional[int]:
    # cp_name like 'checkpoint_120'
    try:
        return int(cp_name.split("_")[-1])
    except Exception:
        return None


def find_program_json_for_id(program_id: str, preferred_cp_num: Optional[int]) -> Optional[Path]:
    # Primary: preferred checkpoint
    if preferred_cp_num is not None:
        preferred = CHECKPOINTS_DIR / f"checkpoint_{preferred_cp_num}" / "programs" / f"{program_id}.json"
        if preferred.exists():
            return preferred

    # Fallback: search all checkpoints and choose closest to preferred
    candidates: List[Tuple[int, Path]] = []
    for p in CHECKPOINTS_DIR.glob(f"checkpoint_*/programs/{program_id}.json"):
        num = cp_name_to_num(p.parents[1].name)
        if num is not None:
            candidates.append((num, p))

    if not candidates:
        return None

    if preferred_cp_num is None:
        # Choose the latest by number if no preference
        candidates.sort(key=lambda x: x[0])
        return candidates[-1][1]

    # Choose closest in absolute distance, tie-breaker: lower number
    candidates.sort(key=lambda x: (abs(x[0] - preferred_cp_num), x[0]))
    return candidates[0][1]


def load_metrics_for(program_id: str, checkpoint_name: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    cp_num = cp_name_to_num(checkpoint_name)
    prog_path = find_program_json_for_id(program_id, cp_num)
    if prog_path is None:
        return None, None
    try:
        obj = json.loads(prog_path.read_text(encoding="utf-8"))
    except Exception:
        return None, None

    metrics = obj.get("metrics")
    notes = None
    if isinstance(metrics, dict):
        notes = metrics.get("evaluation_notes")
    return metrics if isinstance(metrics, dict) else None, notes


def process_json_file(
    json_path: Path,
    out_dir: Path,
    checkpoint_name: str,
    best_checkpoint_ids: Dict[str, str],
    global_best_id: Optional[str],
    csv_rows: List[Dict[str, Any]],
) -> None:
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{json_path.stem}.md").write_text(
            f"File: {json_path.name}\n\nError: failed to parse JSON ({e})\n",
            encoding="utf-8",
        )
        return

    # Expect an array with one string; be defensive
    content: str
    if isinstance(data, list) and data and isinstance(data[0], str):
        content = data[0]
    elif isinstance(data, str):
        content = data
    else:
        content = json.dumps(data, ensure_ascii=False, indent=2)

    parsed = parse_response_text(content)
    program_id = json_path.stem
    metrics, evaluation_notes = load_metrics_for(program_id, checkpoint_name)

    best_note = None
    if best_checkpoint_ids.get(checkpoint_name) == program_id:
        best_note = "Best at this checkpoint"
    elif global_best_id == program_id:
        best_note = "Global best across run"

    md = format_markdown(
        json_path.name,
        parsed,
        metrics=metrics,
        evaluation_notes=evaluation_notes,
        best_note=best_note,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{json_path.stem}.md").write_text(md, encoding="utf-8")

    # Prepare CSV row
    first_line = extract_first_line(parsed)
    row = {
        "id": program_id,
        "combined_score": metrics.get("combined_score") if metrics else None,
        "phenomenological_authenticity": metrics.get("phenomenological_authenticity") if metrics else None,
        "aesthetic_virtuosity": metrics.get("aesthetic_virtuosity") if metrics else None,
        "affective_force": metrics.get("affective_force") if metrics else None,
        "literary_innovation": metrics.get("literary_innovation") if metrics else None,
        "first_line": first_line,
    }
    csv_rows.append(row)


def main() -> None:
    if not RESPONSES_DIR.exists():
        raise SystemExit(f"Responses directory not found: {RESPONSES_DIR}")

    best_checkpoint_ids = load_checkpoint_best_ids()
    global_best_id = load_global_best_id()

    all_counts: list[str] = []
    top_by_checkpoint: Dict[str, List[Tuple[str, float]]] = {}

    for checkpoint_dir in sorted(RESPONSES_DIR.glob("checkpoint_*/")):
        programs_dir = checkpoint_dir / "programs"
        if not programs_dir.is_dir():
            continue
        out_cp_dir = READABLE_DIR / checkpoint_dir.name
        out_programs_dir = out_cp_dir / "programs"
        csv_rows: List[Dict[str, Any]] = []

        for json_path in sorted(programs_dir.glob("*.json")):
            process_json_file(
                json_path,
                out_programs_dir,
                checkpoint_dir.name,
                best_checkpoint_ids,
                global_best_id,
                csv_rows,
            )

        # Write summary.csv for this checkpoint
        if csv_rows:
            out_cp_dir.mkdir(parents=True, exist_ok=True)
            csv_path = out_cp_dir / "summary.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "id",
                        "combined_score",
                        "phenomenological_authenticity",
                        "aesthetic_virtuosity",
                        "affective_force",
                        "literary_innovation",
                        "first_line",
                    ],
                )
                writer.writeheader()
                for row in csv_rows:
                    writer.writerow(row)

            # Track top 5 by combined score
            scored = [
                (r["id"], float(r["combined_score"]))
                for r in csv_rows
                if r.get("combined_score") is not None
            ]
            scored.sort(key=lambda x: x[1], reverse=True)
            top_by_checkpoint[checkpoint_dir.name] = scored[:5]

    # Also write a tiny index with counts
    for cp in sorted((READABLE_DIR).glob("checkpoint_*/programs")):
        total = len(list(cp.glob("*.md")))
        all_counts.append(f"{cp.parent.name}: {total} files")
        tops = top_by_checkpoint.get(cp.parent.name, [])
        if tops:
            all_counts.append("Top 5 by combined_score:")
            for pid, score in tops:
                all_counts.append(f"- {pid}: {score}")
        all_counts.append("")
    if all_counts:
        (READABLE_DIR / "INDEX.txt").write_text("\n".join(all_counts).rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
