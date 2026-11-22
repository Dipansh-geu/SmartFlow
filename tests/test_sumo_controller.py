"""Unit tests for the strict single-green-lane adaptive controller."""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(
    0,
    str(ROOT / "python" / "sumo_mode")
)

from controller import AdaptiveController


CFG = {
    "fixed_green_seconds": "45",
    "sumo_minimum_green_seconds": "15",
    "sumo_maximum_green_seconds": "40",
    "sumo_green_extension_seconds": "5",
    "yellow_seconds": "5",
    "all_red_seconds": "3",
    "sumo_starvation_threshold_seconds": "60"
}


GROUPS = (
    (0,),
    (1,),
    (2,),
    (3,)
)


def obs(count=0, pcu=0, oldest=0, total=0):
    return {
        "counts_by_type": {
            "bike": count,
            "car": 0,
            "bus": 0,
            "truck": 0
        },
        "density_pcu": pcu,
        "waiting_crossing_seconds": 0,
        "oldest_wait_seconds": oldest,
        "total_wait_seconds": total,
        "queue_count": count
    }


def test_deadline_prioritizes_overdue_lane():
    controller = AdaptiveController(CFG, GROUPS)

    lanes = [
        obs(20, 20, 10, 100),
        obs(1, 1, 60, 60),
        obs(),
        obs()
    ]

    lane, green, reason = controller.choose(
        lanes, 100, "smart"
    )

    assert lane == 1
    assert green == 15
    assert "deadline" in reason


def test_previous_lane_skipped_when_another_lane_has_demand():
    controller = AdaptiveController(CFG, GROUPS)

    lanes = [
        obs(2, 2),
        obs(2, 2),
        obs(),
        obs()
    ]

    first, _, _ = controller.choose(lanes, 0, "smart")
    second, _, _ = controller.choose(lanes, 20, "smart")

    assert first != second


def test_only_active_lane_can_repeat():
    controller = AdaptiveController(CFG, GROUPS)

    lanes = [
        obs(2, 2),
        obs(),
        obs(),
        obs()
    ]

    first, _, _ = controller.choose(lanes, 0, "smart")
    second, _, _ = controller.choose(lanes, 20, "smart")

    assert first == second == 0


def test_deadline_cannot_override_no_consecutive_lane_rule():
    controller = AdaptiveController(CFG, GROUPS)

    lanes = [
        obs(2, 2),
        obs(2, 2),
        obs(),
        obs()
    ]

    first, _, _ = controller.choose(lanes, 0, "smart")

    lanes[0] = obs(2, 2, 100, 120)
    lanes[1] = obs(2, 2, 5, 5)

    second, _, reason = controller.choose(
        lanes, 20, "smart"
    )

    assert first == 0
    assert second == 1


def test_extension_stops_before_competing_deadline():
    controller = AdaptiveController(CFG, GROUPS)

    lanes = [
        obs(5, 5, 2, 10),
        obs(1, 1, 52, 52),
        obs(),
        obs()
    ]

    extend, reason = controller.should_extend(
        0, lanes, 15, 5, 3
    )

    assert not extend
    assert "approaching deadline" in reason


def test_extension_requires_queue_and_respects_maximum():
    controller = AdaptiveController(CFG, GROUPS)

    lanes = [
        obs(5, 5, 2, 10),
        obs(),
        obs(),
        obs()
    ]

    assert controller.should_extend(
        0, lanes, 15, 5, 3
    )[0]

    assert not controller.should_extend(
        0, lanes, 40, 5, 3
    )[0]

    assert not controller.should_extend(
        0, [obs(), obs(), obs(), obs()], 15, 5, 3
    )[0]


def test_fixed_round_robin_four_separate_lanes():
    controller = AdaptiveController(CFG, GROUPS)

    lanes = [
        obs(1, 1),
        obs(1, 1),
        obs(1, 1),
        obs(1, 1)
    ]

    picks = [
        controller.choose(lanes, time, "fixed")[:2]
        for time in (0, 60, 120, 180)
    ]

    assert [
        item[0] for item in picks
    ] == [0, 1, 2, 3]

    assert all(
        item[1] == 45 for item in picks
    )


if __name__ == "__main__":
    for name, function in list(globals().items()):
        if name.startswith("test_") and callable(function):
            function()

    print("Single-lane SUMO controller unit tests passed.")
