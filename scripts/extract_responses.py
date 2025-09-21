#!/usr/bin/env python3
"""
Extract only the `responses` field from every program JSON under a checkpoints tree
and write them to a new output directory, preserving relative structure.

Usage:
  python scripts/extract_responses.py <input_root> <output_root>

Example:
  python scripts/extract_responses.py \
    examples/writing/love_letter_optimization/hero_run/checkpoints \
    examples/writing/love_letter_optimization/hero_run/responses_only
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python scripts/extract_responses.py <input_root> <output_root>")
        return 2

    input_root = Path(sys.argv[1]).resolve()
    output_root = Path(sys.argv[2]).resolve()

    if not input_root.exists() or not input_root.is_dir():
        print(f"Input root not found or not a directory: {input_root}")
        return 2

    count_total = 0
    count_written = 0
    count_missing = 0
    errors: list[tuple[Path, str]] = []

    for json_path in sorted(input_root.rglob("*.json")):
        # Only process files under a 'programs' directory (optional but narrows scope)
        if "programs" not in json_path.parts:
            continue
        count_total += 1
        try:
            with json_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:  # pragma: no cover - cautious error handling
            errors.append((json_path, f"read/parse error: {e}"))
            continue

        # Locate responses: prefer top-level; else within prompts/*/responses
        found: dict[str, list] = {}

        if isinstance(data.get("responses"), list):
            found["responses"] = data["responses"]
        else:
            prompts = data.get("prompts")
            if isinstance(prompts, dict):
                for pname, pobj in prompts.items():
                    if isinstance(pobj, dict) and isinstance(pobj.get("responses"), list):
                        found[str(pname)] = pobj["responses"]

        if not found:
            count_missing += 1
            continue

        # Build output path(s) preserving relative structure
        rel = json_path.relative_to(input_root)
        base_out = output_root / rel
        base_out.parent.mkdir(parents=True, exist_ok=True)

        try:
            if len(found) == 1:
                # Single responses list: write as the same filename
                responses = next(iter(found.values()))
                with base_out.open("w", encoding="utf-8") as f:
                    json.dump(responses, f, ensure_ascii=False, indent=2)
                    f.write("\n")
                count_written += 1
            else:
                # Multiple: create a sibling directory named after the file stem
                stem_dir = base_out.parent / base_out.stem
                stem_dir.mkdir(parents=True, exist_ok=True)
                for pname, responses in found.items():
                    out_path = stem_dir / f"{pname}.responses.json"
                    with out_path.open("w", encoding="utf-8") as f:
                        json.dump(responses, f, ensure_ascii=False, indent=2)
                        f.write("\n")
                    count_written += 1
        except Exception as e:  # pragma: no cover
            errors.append((json_path, f"write error: {e}"))
            continue

    # Summary
    print(f"Scanned:   {count_total}")
    print(f"Written:   {count_written}")
    print(f"No field:  {count_missing}")
    if errors:
        print(f"Errors:    {len(errors)}")
        for p, msg in errors[:10]:
            print(f" - {p}: {msg}")
        if len(errors) > 10:
            print(f" ... {len(errors)-10} more")

    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
