#!/usr/bin/env python3
"""Export all data from every LanceDB table to JSON files.

Usage:
    python scripts/lancedb_export.py                  # export all tables, drop vectors
    python scripts/lancedb_export.py --with-vectors    # keep the raw embedding column too
    python scripts/lancedb_export.py --table lms_document_text_store
"""

import argparse
import json
import os
import sys
from pathlib import Path

import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "LMS_SYSTEM.settings")
django.setup()

import lancedb
from django.conf import settings

OUT_DIR = Path(__file__).parent / "lancedb_export"


def print_table(rows: list[dict], max_rows: int = 20):
    if not rows:
        print("  (empty)")
        return
    keys = list(rows[0].keys())
    col_w = {k: max(len(k), max(len(str(r.get(k, ""))) for r in rows[:max_rows])) for k in keys}
    col_w = {k: min(v, 40) for k, v in col_w.items()}

    header = "  " + "  |  ".join(k.ljust(col_w[k]) for k in keys)
    sep = "  " + "--+--".join("-" * col_w[k] for k in keys)
    print(header)
    print(sep)
    for r in rows[:max_rows]:
        row = "  " + "  |  ".join(str(r.get(k, "")).ljust(col_w[k])[:col_w[k]] for k in keys)
        print(row)
    if len(rows) > max_rows:
        print(f"  ... and {len(rows) - max_rows} more rows")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--table", default=None, help="only export this table (default: all tables)")
    p.add_argument("--with-vectors", action="store_true", help="keep the raw embedding vector column")
    args = p.parse_args()

    db_path = os.path.join(settings.BASE_DIR, "lancedb")
    db = lancedb.connect(db_path)

    if args.table:
        table_names = [args.table]
    else:
        result = db.list_tables()
        table_names = list(getattr(result, "tables", result))
    if not table_names:
        print(f"No tables found in {db_path}")
        return

    OUT_DIR.mkdir(exist_ok=True)
    print(f"LanceDB path: {db_path}")
    print(f"Tables:       {table_names}\n")

    summary = []

    for name in table_names:
        try:
            tbl = db.open_table(name)
        except Exception as e:
            print(f"Skipping '{name}': {e}")
            continue

        print(f"{'=' * 60}")
        print(f"Table: {name}  ({tbl.count_rows()} rows)")
        print(f"{'=' * 60}")

        rows = tbl.to_arrow().to_pylist()

        for r in rows:
            if not args.with_vectors:
                r.pop("vector", None)
            if "metadata_json" in r and r["metadata_json"]:
                try:
                    r["metadata_json"] = json.loads(r["metadata_json"])
                except (TypeError, ValueError):
                    pass

        print_table(rows, max_rows=30)

        out_file = OUT_DIR / f"{name}.json"
        out_file.write_text(json.dumps(rows, ensure_ascii=False, indent=2, default=str))
        print(f"\n  Saved {len(rows)} row(s) -> {out_file}\n")

        summary.append({"table": name, "count": len(rows), "file": str(out_file)})

    print(f"\n{'=' * 60}")
    print("EXPORT SUMMARY")
    print(f"{'=' * 60}")
    for s in summary:
        print(f"  {s['table']:<35} {s['count']:>6} row(s)  ->  {s['file']}")

    combined = OUT_DIR / "_all_tables.json"
    all_data = {s["table"]: json.loads((OUT_DIR / f"{s['table']}.json").read_text()) for s in summary}
    combined.write_text(json.dumps(all_data, ensure_ascii=False, indent=2, default=str))
    print(f"\n  Combined export -> {combined}")


if __name__ == "__main__":
    main()
