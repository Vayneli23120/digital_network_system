"""Time formatting helpers for API responses."""

from datetime import timezone


def utc_iso(dt):
    """Return an ISO-8601 UTC timestamp with an explicit Z suffix."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return f"{dt.isoformat()}Z"
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")