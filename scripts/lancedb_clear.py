"""
Clear all LanceDB tables (vector index).
Run: python scripts/lancedb_clear.py
"""
import os
import shutil
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "LMS_SYSTEM.settings")

import django
django.setup()

from django.conf import settings

db_path = os.path.join(settings.BASE_DIR, "lancedb")

if not os.path.exists(db_path):
    print("LanceDB directory not found — nothing to clear.")
    sys.exit(0)

tables = [d for d in os.listdir(db_path) if d.endswith(".lance") or d == "__manifest"]
if not tables:
    print("No tables found — already empty.")
    sys.exit(0)

print(f"Found {len(tables)} table(s):")
for t in tables:
    print(f"  - {t}")

confirm = input("\nDelete all? [y/N] ").strip().lower()
if confirm != "y":
    print("Aborted.")
    sys.exit(0)

for t in tables:
    shutil.rmtree(os.path.join(db_path, t))
    print(f"  Deleted: {t}")

print("\nDone. LanceDB is empty.")
