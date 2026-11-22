"""Static tests for SUMO route generation and phase wiring."""

import importlib.util
import pathlib
import sys
import tempfile
import xml.etree.ElementTree as ET


ROOT = pathlib.Path(__file__).resolve().parents[1]

SUMO_DIR = ROOT / "python" / "sumo_mode"

sys.path.insert(0, str(SUMO_DIR))

from config import load_config


spec = importlib.util.spec_from_file_location(
    "smartflow_run_sumo",
    SUMO_DIR / "run_sumo.py"
)

run_sumo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_sumo)


def test_mode_a_config_is_unchanged_and_sumo_settings_are_separate():

    cfg = load_config(str(ROOT / "config.ini"))

    assert cfg["minimum_green_seconds"] == "20"
    assert cfg["maximum_green_seconds"] == "90"
    assert cfg["starvation_threshold_seconds"] == "180"

    assert cfg["sumo_minimum_green_seconds"] == "15"
    assert cfg["sumo_maximum_green_seconds"] == "90"
    assert cfg["sumo_starvation_threshold_seconds"] == "180"


def test_route_file_is_valid_and_globally_sorted():

    cfg = load_config(str(ROOT / "config.ini"))

    with tempfile.TemporaryDirectory() as folder:

        route_file = pathlib.Path(folder) / "traffic.rou.xml"

        generated = run_sumo.make_routes(cfg, route_file)

        root = ET.parse(route_file).getroot()
        vehicles = root.findall("vehicle")

        departures = [
            float(vehicle.attrib["depart"])
            for vehicle in vehicles
        ]

        assert generated == len(vehicles)
        assert departures == sorted(departures)
        assert generated > 0


def test_routes_use_only_70_percent_straight_and_30_percent_right():

    cfg = load_config(str(ROOT / "config.ini"))
    cfg["simulation_duration_seconds"] = "3600"

    with tempfile.TemporaryDirectory() as folder:

        route_file = pathlib.Path(folder) / "traffic.rou.xml"

        run_sumo.make_routes(cfg, route_file)

        root = ET.parse(route_file).getroot()

        routes = {
            r.attrib["id"]: r.attrib["edges"]
            for r in root.findall("route")
        }

        assert routes["r0_straight"] == "n_in s_out"
        assert routes["r0_right"] == "n_in w_out"

        vehicles = root.findall("vehicle")

        turn_ids = [
            v.attrib["route"].rsplit("_", 1)[-1]
            for v in vehicles
            if not v.attrib["id"].startswith("start_")
        ]

        assert turn_ids
        assert set(turn_ids) == {"straight", "right"}

        straight_ratio = turn_ids.count("straight") / len(turn_ids)

        assert 0.65 <= straight_ratio <= 0.75


def test_exactly_one_green_lane_per_phase():

    cfg = load_config(str(ROOT / "config.ini"))

    groups = run_sumo._phase_groups(cfg)

    assert groups == (
        (0,),
        (1,),
        (2,),
        (3,)
    )

    lane_links = [
        [0],
        [1],
        [2],
        [3]
    ]

    for group in groups:

        state = run_sumo.signal_state(
            4,
            lane_links,
            group,
            "G"
        )

        assert state.count("G") == 1
        assert state[group[0]] == "G"


if __name__ == "__main__":

    test_mode_a_config_is_unchanged_and_sumo_settings_are_separate()
    test_route_file_is_valid_and_globally_sorted()
    test_routes_use_only_70_percent_straight_and_30_percent_right()
    test_exactly_one_green_lane_per_phase()

    print("SUMO runner static tests passed.")
