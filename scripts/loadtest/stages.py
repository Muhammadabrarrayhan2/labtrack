"""Stepped load profile for the stress test, kept free of locust imports so it can be unit tested.

Each stage holds a user count for a duration. The last stage drops back to a light load
to observe recovery after overload (latency and error rate should return to normal).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Stage:
    duration_s: int
    users: int
    spawn_rate: float


# 100 -> 300 virtual users in steps of 50, two minutes each, then two minutes of recovery
STRESS_STAGES: tuple[Stage, ...] = (
    Stage(120, 100, 10),
    Stage(120, 150, 10),
    Stage(120, 200, 10),
    Stage(120, 250, 10),
    Stage(120, 300, 10),
    Stage(120, 20, 50),
)


def total_duration(stages: tuple[Stage, ...] = STRESS_STAGES) -> int:
    return sum(s.duration_s for s in stages)


def target_at(elapsed_s: float, stages: tuple[Stage, ...] = STRESS_STAGES) -> tuple[int, float] | None:
    """(users, spawn_rate) for the given run time, or None when the test is over."""
    boundary = 0
    for stage in stages:
        boundary += stage.duration_s
        if elapsed_s < boundary:
            return stage.users, stage.spawn_rate
    return None
