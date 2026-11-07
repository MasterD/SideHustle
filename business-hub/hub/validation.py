"""Validation shared by dashboard and public booking workflows."""

from datetime import datetime, timedelta, timezone
import math
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def text_field(data, name, maximum=1000, required=False, default=""):
    value = data.get(name, default)
    if not isinstance(value, str):
        raise ApiError(400, f"{name} must be text.")
    value = value.strip()
    if required and not value:
        raise ApiError(400, f"Please provide {name}.")
    if len(value) > maximum:
        raise ApiError(400, f"{name} must be no longer than {maximum} characters.")
    return value


def number_field(data, name, default=0, maximum=1_000_000_000):
    value = data.get(name, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ApiError(400, f"{name} must be a number.")
    try:
        valid = math.isfinite(value) and 0 <= value <= maximum
    except OverflowError:
        valid = False
    if not valid:
        raise ApiError(400, f"{name} must be between 0 and {maximum}.")
    return float(value)


def choice_field(data, name, choices, default=None):
    value = data.get(name, default)
    if not isinstance(value, str) or value not in choices:
        raise ApiError(400, f"{name} must be one of: {', '.join(choices)}.")
    return value


def channels_field(data, default=None):
    channels = data.get("channels", default or ["website"])
    allowed = {"website", "facebook", "instagram", "linkedin"}
    if not isinstance(channels, list) or not channels or any(
        not isinstance(channel, str) or channel not in allowed for channel in channels
    ):
        raise ApiError(400, "Choose at least one supported publishing channel.")
    return list(dict.fromkeys(channels))


def contact_fields(data):
    name = text_field(data, "name", 120, required=True)
    email = text_field(data, "email", 254)
    phone = text_field(data, "phone", 40)
    if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ApiError(400, "Please provide a valid email address.")
    if phone and not re.fullmatch(r"[+()\d .-]{5,40}", phone):
        raise ApiError(400, "Please provide a valid phone number.")
    if not email and not phone:
        raise ApiError(400, "Please provide an email address or phone number.")
    return name, email, phone


def business_timezone(name):
    # Windows Python installations may not ship the IANA database. South
    # Africa uses UTC+02:00 all year, so our default needs no extra package.
    if name == "Africa/Johannesburg":
        return timezone(timedelta(hours=2), name)
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        raise ApiError(400, "Choose an available IANA timezone, such as Africa/Johannesburg.")


def parse_time(value, field):
    if not isinstance(value, str) or not re.fullmatch(r"\d{2}:\d{2}", value):
        raise ApiError(400, f"{field} must use HH:MM format.")
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        raise ApiError(400, f"{field} must be a valid time.")


def parse_datetime(value):
    if not isinstance(value, str):
        raise ApiError(400, "startAt must be an ISO date and time with a timezone offset.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ApiError(400, "startAt must be a valid ISO date and time.")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ApiError(400, "startAt must include a timezone offset.")
    return parsed
