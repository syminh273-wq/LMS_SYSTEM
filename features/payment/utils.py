import json


def dump_meta(meta: dict) -> str:
    return json.dumps(meta)


def parse_meta(extra_data: str) -> dict:
    if not extra_data:
        return {}
    try:
        return json.loads(extra_data)
    except Exception:
        return {}
