"""Queue-aware adaptive signal controller for the SmartFlow SUMO mode.

The controller is deliberately independent of TraCI and of the observation
source. It consumes normalized per-lane observations and schedules only single-lane phases.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple


Observation = Dict[str, Any]


def _vehicle_count(observation: Observation) -> int:
    return int(sum(observation.get("counts_by_type", {}).values()))


def _group_stats(lanes: Sequence[Observation], members: Sequence[int]) -> Dict[str, float]:
    selected = [lanes[i] for i in members]
    return {
        "vehicles": float(sum(_vehicle_count(x) for x in selected)),
        "pcu": float(sum(float(x.get("density_pcu", 0.0)) for x in selected)),
        "oldest_wait": max(
            (float(x.get("oldest_wait_seconds", 0.0)) for x in selected),
            default=0.0
        ),
        "total_wait": sum(
            float(x.get("total_wait_seconds", 0.0)) for x in selected
        ),
        "queue_count": sum(
            float(x.get("queue_count", 0.0)) for x in selected
        ),
        "crossing_seconds": sum(
            float(x.get("waiting_crossing_seconds", 0.0)) for x in selected
        ),
    }


class AdaptiveController:
    """Selects exactly one lane using queue pressure and waiting-time urgency."""

    def __init__(
        self,
        cfg: Dict[str, str],
        groups: Optional[Sequence[Sequence[int]]] = None
    ):
        self.cfg = cfg

        self.groups: Tuple[Tuple[int, ...], ...] = tuple(
            tuple(g) for g in (
                groups or ((0,), (1,), (2,), (3,))
            )
        )

        self.previous_group: Optional[int] = None
        self.last_served_at: List[Optional[float]] = [
            None
        ] * len(self.groups)

    def choose(self, lanes: Sequence[Observation], now: float, mode: str = "smart"):
        """Return (group_index, initial_green_seconds, reason).

        A previous group is skipped whenever another non-empty group exists.
        Repeating it is allowed only when it is the sole group with demand.
        """

        stats = [
            _group_stats(lanes, group)
            for group in self.groups
        ]

        active = [
            i for i, item in enumerate(stats)
            if item["vehicles"] > 0
            or any(int(lanes[j].get("waiting_vehicle_count", 0)) > 0 for j in self.groups[i])
        ]

        if not active:
            return None, 0, "no queued vehicles"

        if mode == "fixed":
            candidates = [
                i for i in active
                if i != self.previous_group
            ] or active

            if self.previous_group is None:
                winner = min(candidates)
            else:
                winner = min(
                    candidates,
                    key=lambda i: (
                        (i - self.previous_group) % len(self.groups)
                        or len(self.groups)
                    )
                )

            green = int(
                float(self.cfg["fixed_green_seconds"])
            )

            reason = "fixed round-robin single-lane phase"

        else:
            threshold = float(
                self.cfg["sumo_starvation_threshold_seconds"]
            )

            candidates = [
                i for i in active
                if i != self.previous_group
            ] or active

            overdue = [
                i for i in candidates
                if stats[i]["oldest_wait"] >= threshold
            ]

            if overdue:
                winner = max(
                    overdue,
                    key=lambda i: (
                        stats[i]["oldest_wait"],
                        stats[i]["total_wait"],
                        stats[i]["pcu"]
                    )
                )

                reason = (
                    "waiting-time deadline: "
                    f"oldest={stats[winner]['oldest_wait']:.1f}s"
                )

            else:
                max_pcu = max(
                    (stats[i]["pcu"] for i in candidates),
                    default=0.0
                ) or 1.0

                max_wait = max(
                    (stats[i]["total_wait"] for i in candidates),
                    default=0.0
                ) or 1.0

                def score(i: int) -> float:
                    if self.last_served_at[i] is not None:
                        age = max(
                            0.0,
                            now - self.last_served_at[i]
                        )
                    else:
                        age = now

                    queue_component = (
                        stats[i]["pcu"] / max_pcu
                    )

                    oldest_component = min(
                        stats[i]["oldest_wait"] / threshold,
                        1.0
                    )

                    total_wait_component = (
                        stats[i]["total_wait"] / max_wait
                    )

                    service_age_component = min(
                        age / threshold,
                        1.0
                    )

                    return (
                        0.40 * queue_component
                        + 0.30 * oldest_component
                        + 0.20 * total_wait_component
                        + 0.10 * service_age_component
                    )

                winner = max(
                    candidates,
                    key=lambda i: (
                        score(i),
                        stats[i]["oldest_wait"],
                        stats[i]["pcu"]
                    )
                )

                reason = (
                    f"queue/age priority: score={score(winner):.3f}"
                )

            minimum = float(self.cfg["sumo_minimum_green_seconds"])
            maximum = float(self.cfg["sumo_maximum_green_seconds"])
            required = stats[winner]["crossing_seconds"]
            green = int(max(minimum, min(maximum, required)))

        self.previous_group = winner

        return winner, green, reason

    def should_extend(
        self,
        active_group: int,
        lanes: Sequence[Observation],
        active_green_seconds: float,
        yellow_seconds: float,
        all_red_seconds: float,
    ) -> Tuple[bool, str]:
        """Decide whether to add one green extension to the active group."""

        maximum = float(
            self.cfg["sumo_maximum_green_seconds"]
        )

        extension = float(
            self.cfg["sumo_green_extension_seconds"]
        )

        if active_green_seconds + 1e-9 >= maximum:
            return False, "maximum green reached"

        active_stats = _group_stats(
            lanes,
            self.groups[active_group]
        )

        if active_stats["queue_count"] <= 0:
            return False, "active group stopped queue cleared"

        threshold = float(
            self.cfg["sumo_starvation_threshold_seconds"]
        )

        stop_extension_at = max(
            0.0,
            threshold - yellow_seconds - all_red_seconds
        )

        for group_index, members in enumerate(self.groups):
            if group_index == active_group:
                continue

            competing = _group_stats(lanes, members)

            if (
                competing["vehicles"] > 0
                and competing["oldest_wait"] >= stop_extension_at
            ):
                return (
                    False,
                    "competing group approaching deadline "
                    f"({competing['oldest_wait']:.1f}s)"
                )

        return (
            True,
            f"queue remains; extend by {extension:.0f}s"
        )

    def mark_served(self, group_index: int, now: float) -> None:
        self.last_served_at[group_index] = float(now)