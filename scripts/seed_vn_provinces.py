"""
Fetch Vietnamese provinces + wards (post-2025 administrative reform) from
provinces.open-api.vn and write a compact JSON snapshot for backend validation
and frontend fallback.

Usage:
    python scripts/seed_vn_provinces.py
    python scripts/seed_vn_provinces.py --output path/to/output.json

Output JSON shape (compact):
    {
      "version": "2025-merged",
      "source": "https://provinces.open-api.vn/api/v2/?depth=2",
      "fetched_at": "2026-07-24T...",
      "provinces": [
        { "code": 79, "name": "Thành phố Hồ Chí Minh",
          "wards": [{ "code": 26740, "name": "Phường Bến Nghé" }, ...]
        }, ...
      ]
    }
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

SOURCE_URL = "https://provinces.open-api.vn/api/v2/?depth=2"
DEFAULT_OUTPUT = (
    Path(__file__).resolve().parent.parent
    / "features"
    / "account"
    / "static_data"
    / "vn_provinces.json"
)


def fetch_provinces(url: str = SOURCE_URL, timeout: int = 30) -> list[dict]:
    try:
        with urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, HTTPError) as e:
        sys.stderr.write(f"[ERROR] Failed to fetch {url}: {e}\n")
        sys.exit(1)


def transform(raw: list[dict]) -> dict:
    provinces = []
    for p in raw:
        provinces.append({
            "code": p["code"],
            "name": p["name"],
            "division_type": p.get("division_type", ""),
            "wards": [
                {"code": w["code"], "name": w["name"]}
                for w in p.get("wards", [])
            ],
        })
    return {
        "version": "2025-merged",
        "source": SOURCE_URL,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_provinces": len(provinces),
        "total_wards": sum(len(p["wards"]) for p in provinces),
        "provinces": provinces,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to write the JSON snapshot (default: %(default)s)",
    )
    parser.add_argument(
        "--source", "-s",
        default=SOURCE_URL,
        help="Source URL (default: %(default)s)",
    )
    args = parser.parse_args()

    print(f"Fetching {args.source} ...")
    raw = fetch_provinces(args.source)

    data = transform(raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    size_kb = args.output.stat().st_size / 1024
    print(
        f"[OK] wrote {args.output} "
        f"({data['total_provinces']} provinces, "
        f"{data['total_wards']} wards, {size_kb:.1f} KB)"
    )


if __name__ == "__main__":
    main()
