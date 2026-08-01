from datetime import datetime, timezone, timedelta


VN_TZ = timezone(timedelta(hours=7), name='VN')
VN_OFFSET = timedelta(hours=7)


def now_vn() -> datetime:
    """Current wall-clock time in Asia/Ho_Chi_Minh, returned naive (so it
    can be persisted to Cassandra without tzinfo)."""
    return datetime.now(VN_TZ).replace(tzinfo=None)


def to_vn(value: datetime | None) -> datetime | None:
    """Convert an aware datetime to VN wall-clock (naive). Naive values
    are assumed already VN and returned unchanged."""
    if value is None:
        return None
    if not isinstance(value, datetime):
        return value
    if value.tzinfo is None:
        return value
    return value.astimezone(VN_TZ).replace(tzinfo=None)


def to_vn_iso(value) -> str | None:
    """Serialize a datetime as naive ISO (no Z suffix). The contract is:
    "this is a wall-clock VN time; the FE will display it as-is"."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if not isinstance(value, datetime):
        return value
    if value.tzinfo is not None:
        value = value.astimezone(VN_TZ).replace(tzinfo=None)
    return value.isoformat()
