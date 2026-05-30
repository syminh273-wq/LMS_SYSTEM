#!/usr/bin/env python3
"""Drop all Typesense collections (or specific ones)."""

import os
import sys

try:
    import typesense
except ImportError:
    sys.exit("typesense package not found — run: pip install typesense")

HOST     = os.getenv("TYPESENSE_HOST",     "localhost")
PORT     = int(os.getenv("TYPESENSE_PORT", "8108"))
PROTOCOL = os.getenv("TYPESENSE_PROTOCOL", "http")
API_KEY  = os.getenv("TYPESENSE_API_KEY",  "xyz")

client = typesense.Client({
    "nodes": [{"host": HOST, "port": PORT, "protocol": PROTOCOL}],
    "api_key": API_KEY,
    "connection_timeout_seconds": 5,
})

def main():
    try:
        collections = client.collections.retrieve()
    except Exception as e:
        sys.exit(f"Cannot connect to Typesense: {e}")

    if not collections:
        print("No collections found.")
        return

    print(f"Found {len(collections)} collection(s):\n")
    for col in collections:
        print(f"  - {col['name']}  ({col.get('num_documents', '?')} docs)")

    print("\nDrop ALL collections? [y/N] ", end="", flush=True)
    answer = input().strip().lower()
    if answer != "y":
        print("Aborted.")
        return

    for col in collections:
        name = col["name"]
        try:
            client.collections[name].delete()
            print(f"  Dropped: {name}")
        except Exception as e:
            print(f"  Error dropping {name}: {e}")

    print("\nDone.")

if __name__ == "__main__":
    main()
