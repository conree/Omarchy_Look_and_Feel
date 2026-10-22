#!/usr/bin/env python3
"""Offline sunrise/sunset transitions for the Look & Feel scheduler.

Uses NOAA's compact solar declination/equation-of-time approximation
(https://gml.noaa.gov/grad/solcalc/solareqns.PDF). It needs only a local date,
manually entered coordinates, and an IANA time-zone name.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


UTC = timezone.utc
ZENITH_DEGREES = 90.833  # apparent sunrise/sunset, including refraction and solar disk


class SolarScheduleError(ValueError):
    """Invalid location/date or no solar transition for the requested day."""


class NoSolarEventError(SolarScheduleError):
    """Sunrise or sunset is absent on the requested local date."""


@dataclass(frozen=True)
class SolarEvents:
    sunrise: datetime
    sunset: datetime


@dataclass(frozen=True)
class ThemeTransition:
    at: datetime
    theme: str
    event: str


def _solar_terms(day: date) -> tuple[float, float]:
    """Return equation of time (minutes) and declination (radians)."""
    gamma = 2 * math.pi / 365 * (day.timetuple().tm_yday - 1)
    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )
    declination = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )
    return eqtime, declination


def solar_events(local_day: date, latitude: float, longitude: float, time_zone: str) -> SolarEvents:
    """Calculate apparent sunrise/sunset as aware local datetimes.

    Longitude is positive east. A date with polar day/night raises
    SolarScheduleError; callers should preserve the currently active theme and
    wait for the next calculable transition.
    """
    if not isinstance(local_day, date) or isinstance(local_day, datetime):
        raise SolarScheduleError("local_day must be a calendar date")
    if not math.isfinite(latitude) or not -90 <= latitude <= 90:
        raise SolarScheduleError("latitude must be between -90 and 90")
    if not math.isfinite(longitude) or not -180 <= longitude <= 180:
        raise SolarScheduleError("longitude must be between -180 and 180")
    try:
        zone = ZoneInfo(time_zone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise SolarScheduleError(f"unknown IANA time zone: {time_zone}") from exc

    lat = math.radians(latitude)
    cos_zenith = math.cos(math.radians(ZENITH_DEGREES))
    candidates: dict[str, list[datetime]] = {"sunrise": [], "sunset": []}

    # Local civil date and UTC date may differ. Evaluate adjacent UTC dates and
    # retain the events that actually map back to the requested local date.
    for utc_day in (local_day - timedelta(days=1), local_day, local_day + timedelta(days=1)):
        eqtime, declination = _solar_terms(utc_day)
        denominator = math.cos(lat) * math.cos(declination)
        if abs(denominator) < 1e-15:
            continue
        cos_hour_angle = cos_zenith / denominator - math.tan(lat) * math.tan(declination)
        if not -1 <= cos_hour_angle <= 1:
            continue
        hour_angle = math.degrees(math.acos(cos_hour_angle))
        for event, angle in (("sunrise", hour_angle), ("sunset", -hour_angle)):
            utc_minutes = 720 - 4 * (longitude + angle) - eqtime
            instant = datetime.combine(utc_day, time(), UTC) + timedelta(minutes=utc_minutes)
            local = instant.astimezone(zone)
            if local.date() == local_day:
                candidates[event].append(local)

    if not candidates["sunrise"] or not candidates["sunset"]:
        raise NoSolarEventError(f"sunrise or sunset does not occur on {local_day.isoformat()} at this location")
    return SolarEvents(min(candidates["sunrise"]), max(candidates["sunset"]))


def next_transition(
    now: datetime,
    latitude: float,
    longitude: float,
    time_zone: str,
    sunrise_offset_minutes: int = 0,
    sunset_offset_minutes: int = 0,
) -> ThemeTransition:
    """Return the next scheduled theme change, skipping polar no-event days."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise SolarScheduleError("now must be timezone-aware")
    for offset in (sunrise_offset_minutes, sunset_offset_minutes):
        if isinstance(offset, bool) or not isinstance(offset, int) or not -180 <= offset <= 180:
            raise SolarScheduleError("event offsets must be integers between -180 and 180 minutes")
    try:
        zone = ZoneInfo(time_zone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise SolarScheduleError(f"unknown IANA time zone: {time_zone}") from exc

    local_now = now.astimezone(zone)
    for day_offset in range(0, 371):
        day = local_now.date() + timedelta(days=day_offset)
        try:
            events = solar_events(day, latitude, longitude, time_zone)
        except NoSolarEventError:
            continue
        transitions = (
            ThemeTransition(events.sunrise + timedelta(minutes=sunrise_offset_minutes), "light", "sunrise"),
            ThemeTransition(events.sunset + timedelta(minutes=sunset_offset_minutes), "dark", "sunset"),
        )
        upcoming = [item for item in transitions if item.at.astimezone(UTC) > now.astimezone(UTC)]
        if upcoming:
            return min(upcoming, key=lambda item: item.at.astimezone(UTC))
    raise SolarScheduleError("no sunrise or sunset transition found within the next year")
