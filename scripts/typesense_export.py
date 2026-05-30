#!/usr/bin/env python3
"""Export all documents from every Typesense collection to JSON files."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import typesense
except ImportError:
    sys.exit("typesense package not found — run: pip install typesense")

# ── Config (reads from env or uses defaults) ──────────────────────────────────

HOST     = os.getenv("TYPESENSE_HOST",     "localhost")
PORT     = int(os.getenv("TYPESENSE_PORT", "8108"))
PROTOCOL = os.getenv("TYPESENSE_PROTOCOL", "http")
API_KEY  = os.getenv("TYPESENSE_API_KEY",  "xyz")

client = typesense.Client({
    "nodes": [{"host": HOST, "port": PORT, "protocol": PROTOCOL}],
    "api_key": API_KEY,
    "connection_timeout_seconds": 5,
})

# ── Output dir ────────────────────────────────────────────────────────────────

OUT_DIR = Path(__file__).parent / "typesense_export"
OUT_DIR.mkdir(exist_ok=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

def fetch_all(collection_name: str) -> list[dict]:
    """Page through all documents using export endpoint."""
    raw = client.collections[collection_name].documents.export()
    if not raw:
        return []
    return [json.loads(line) for line in raw.strip().splitlines()]


def pretty_value(v):
    """Format timestamps (int64 epoch seconds) as readable strings."""
    if isinstance(v, int) and 1_000_000_000 < v < 9_999_999_999:
        return f"{v}  ({datetime.fromtimestamp(v).strftime('%Y-%m-%d %H:%M:%S')})"
    return v


def print_table(docs: list[dict], max_rows: int = 20):
    if not docs:
        print("  (empty)")
        return
    keys = list(docs[0].keys())
    col_w = {k: max(len(k), max(len(str(d.get(k, ""))) for d in docs[:max_rows])) for k in keys}
    col_w = {k: min(v, 40) for k, v in col_w.items()}

    header = "  " + "  |  ".join(k.ljust(col_w[k]) for k in keys)
    sep    = "  " + "--+--".join("-" * col_w[k] for k in keys)
    print(header)
    print(sep)
    for doc in docs[:max_rows]:
        row = "  " + "  |  ".join(str(doc.get(k, "")).ljust(col_w[k])[:col_w[k]] for k in keys)
        print(row)
    if len(docs) > max_rows:
        print(f"  ... and {len(docs) - max_rows} more rows")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Health check
    try:
        healthy = client.operations.is_healthy()
    except Exception as e:
        sys.exit(f"Cannot connect to Typesense at {PROTOCOL}://{HOST}:{PORT} — {e}")

    if not healthy:
        sys.exit("Typesense is not healthy.")

    print(f"Connected to Typesense at {PROTOCOL}://{HOST}:{PORT}\n")

    # List collections
    collections = client.collections.retrieve()
    if not collections:
        print("No collections found.")
        return

    summary = []

    for col in collections:
        name  = col["name"]
        count = col.get("num_documents", "?")
        print(f"{'='*60}")
        print(f"Collection: {name}  ({count} documents)")
        print(f"{'='*60}")

        docs = fetch_all(name)

        # Print preview table
        print_table(docs, max_rows=30)

        # Save full JSON
        out_file = OUT_DIR / f"{name}.json"
        out_file.write_text(json.dumps(docs, ensure_ascii=False, indent=2))
        print(f"\n  Saved {len(docs)} docs → {out_file}\n")

        summary.append({"collection": name, "count": len(docs), "file": str(out_file)})

    # Print summary
    print(f"\n{'='*60}")
    print("EXPORT SUMMARY")
    print(f"{'='*60}")
    for s in summary:
        print(f"  {s['collection']:<30} {s['count']:>6} docs  →  {s['file']}")

    # Write combined export
    combined = OUT_DIR / "_all_collections.json"
    all_data = {s["collection"]: json.loads((OUT_DIR / f"{s['collection']}.json").read_text()) for s in summary}
    combined.write_text(json.dumps(all_data, ensure_ascii=False, indent=2))
    print(f"\n  Combined export → {combined}")


if __name__ == "__main__":
    main()
