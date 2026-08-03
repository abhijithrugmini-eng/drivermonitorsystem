"""Turns a violation into driver-facing "recommended action" copy — simple rule-based templates, not ML."""

from app.db import models


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def build_recommended_action(
    *,
    violation_type: str,
    event_count: int,
    window_seconds: float | None,
    event: models.Event,
) -> str:
    window_min = round((window_seconds or 0) / 60, 1)
    waypoint = event.waypoint_name
    distance = event.distance_to_waypoint_km

    if violation_type == "DROWSINESS_PATTERN":
        ordinal = _ordinal(event_count)
        if waypoint and distance is not None:
            return (
                f"{ordinal} micro-sleep in {window_min} min. "
                f"Advise rest stop at {waypoint}, {distance} km ahead."
            )
        return f"{ordinal} micro-sleep in {window_min} min. Advise driver to pull over safely."

    if violation_type == "PHONE_USAGE":
        return "Phone usage detected while driving. Advise driver to stop handheld device use immediately."

    if violation_type == "DISTRACTION_PATTERN":
        return (
            f"{event_count} distraction events in {window_min} min. "
            "Advise driver to refocus attention on the road."
        )

    if violation_type == "CONTINUOUS_DRIVE":
        return "Driver has exceeded 4 continuous hours without a break. Advise scheduling a rest stop."

    return "Monitor driver behaviour."
