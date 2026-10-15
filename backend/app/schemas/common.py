from datetime import datetime, timezone
from typing import Annotated

from pydantic import AfterValidator, PlainSerializer


def _to_naive_utc(value: datetime) -> datetime:
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _to_iso_z(value: datetime) -> str:
    return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


# Input: any ISO datetime (naive = UTC). Output: always ISO-8601 with a trailing "Z".
UTCDateTime = Annotated[datetime, AfterValidator(_to_naive_utc), PlainSerializer(_to_iso_z, return_type=str)]
