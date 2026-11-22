"""Collect YOLO training images from the actual SUMO GUI with TraCI labels.

The screenshot is the model input. Vehicle positions/types from TraCI are used
only to create training annotations; runtime inference remains image-based.
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

from config import load_config
from network import build_network
from run_sumo import (ensure_sumo_tools, find_sumo, make_routes, lane_observations, signal_state, IN_EDGES, LANES, resolve_gui_view_id, capture_sumo_screenshot, maximize_sumo_window)
from controller import AdaptiveController

CLASSES = {"bike": 0, "car": 1, "bus": 2, "truck": 3}


def yolo_box(traci, vehicle_id, bounds, image_size):
    lo_x, lo_y, hi_x, hi_y = bounds
    x, y = map(float, traci.vehicle.getPosition(vehicle_id))
    length = float(traci.vehicle.getLength(vehicle_id))
    width = float(traci.vehicle.getWidth(vehicle_id))
    angle = float(traci.vehicle.getAngle(vehicle_id))

    import math
    theta = math.radians(angle)
    x -= math.sin(theta) * length / 2.0
    y -= math.cos(theta) * length / 2.0
    box_w_world = abs(math.sin(theta)) * length + abs(math.cos(theta)) * width
    box_h_world = abs(math.cos(theta)) * length + abs(math.sin(theta)) * width

    cx = (x - lo_x) / (hi_x - lo_x)
    cy = (hi_y - y) / (hi_y - lo_y)
    bw = box_w_world / (hi_x - lo_x)
    bh = box_h_world / (hi_y - lo_y)

    x1 = max(0.0, cx - bw / 2)
    y1 = max(0.0, cy - bh / 2)
    x2 = min(1.0, cx + bw / 2)
    y2 = min(1.0, cy + bh / 2)
    if x2 <= x1 or y2 <= y1:
        return None
    return ((x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1)


def main():
    parser = argparse.ArgumentParser(description="Collect SUMO GUI images and YOLO labels.")
    parser.add_argument("--out", default="dataset")
    parser.add_argument("--frames", type=int, default=800)
    parser.add_argument("--gui", action="store_true", help="Show SUMO GUI while collecting (recommended).")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    if args.frames < 20:
        parser.error("--frames must be at least 20")
    if not args.gui:
        parser.error("--gui is required: synthetic headless frames are not valid training data")

    ensure_sumo_tools()
    try:
        import traci
    except ImportError as exc:
        raise SystemExit(
            "TraCI could not be imported. Check SUMO_HOME or the SUMO installation."
        ) from exc

    project = Path(__file__).resolve().parents[2]
    cfg = load_config(project / "config.ini")
    out = Path(args.out).resolve()
    image_size = int(cfg["sumo_image_size"])
    interval = max(1, int(float(cfg["detection_interval_seconds"])))
    bounds = (
        float(cfg["sumo_view_min_x"]), float(cfg["sumo_view_min_y"]),
        float(cfg["sumo_view_max_x"]), float(cfg["sumo_view_max_y"]),
    )

    for folder in ("images/train", "images/val", "labels/train", "labels/val"):
        target = out / folder
        target.mkdir(parents=True, exist_ok=True)
        for old in target.iterdir():
            if old.is_file():
                old.unlink()

    route_file = out / "dataset.rou.xml"
    vehicle_count = make_routes(cfg, str(route_file))
    print(f"Generated {vehicle_count} SUMO vehicles in {route_file}", flush=True)
    print(f"SUMO camera bounds: x={bounds[0]}..{bounds[2]}, y={bounds[1]}..{bounds[3]}", flush=True)
    net_file = build_network(str(project))
    sumocfg = out / "dataset.sumocfg"
    sumocfg.write_text(
        "<configuration><input>"
        f'<net-file value="{Path(net_file).as_posix()}"/>'
        f'<route-files value="{route_file.as_posix()}"/>'
        "</input><time>"
        f'<begin value="0"/>'
        f'<end value="{cfg["simulation_duration_seconds"]}"/>'
        f'<step-length value="{cfg["sumo_step_length"]}"/>'
        "</time></configuration>", encoding="utf-8"
    )

    executable = find_sumo(gui=args.gui)
    if not executable:
        raise SystemExit("SUMO executable not found. Install SUMO and set SUMO_HOME/PATH.")

    command = [
        executable, "-c", str(sumocfg), "--seed", str(args.seed),
        "--no-step-log", "true",
        "--log", str(out / "dataset_sumo.log"),
        "--error-log", str(out / "dataset_sumo_error.log"),
    ]
    print("Starting SUMO with route file:", route_file, flush=True)
    traci.start(command)
    view_id = resolve_gui_view_id(traci)
    if args.gui:
        maximize_sumo_window()
        traci.gui.setSchema(view_id, "real world")
        traci.gui.setBoundary(view_id, *bounds)
        traci.gui.setOffset(view_id, 120.0, 120.0)
        traci.gui.setZoom(view_id, float(cfg.get("sumo_zoom", "500")))
        lower, upper = traci.gui.getBoundary(view_id)
        bounds = (float(lower[0]), float(lower[1]),
                  float(upper[0]), float(upper[1]))
        view_aspect = (bounds[2] - bounds[0]) / (bounds[3] - bounds[1])
        capture_size = (image_size, max(1, round(image_size / view_aspect)))
        print(
            f"SUMO dataset view: real-world scheme, zoom="
            f"{traci.gui.getZoom(view_id):.0f}, bounds={bounds}",
            flush=True
        )

    controller = AdaptiveController(cfg, groups=((0,), (1,), (2,), (3,)))
    controlled_links = traci.trafficlight.getControlledLinks("center")
    lane_links = []
    for edge in IN_EDGES:
        indexes = []
        for index, link_group in enumerate(controlled_links):
            if link_group and any(link[0].startswith(edge + "_") for link in link_group):
                indexes.append(index)
        lane_links.append(indexes)
    if any(not indexes for indexes in lane_links):
        traci.close()
        raise RuntimeError(f"Could not map all incoming lanes to traffic-light links: {lane_links}")
    link_count = len(controlled_links)
    traci.trafficlight.setRedYellowGreenState("center", "r" * link_count)

    yellow = float(cfg["yellow_seconds"])
    all_red = float(cfg["all_red_seconds"])
    phase = "idle"
    phase_end = 0.0
    active_group = None
    active_green = 0.0

    print("SUMO connected. Expected vehicles:", traci.simulation.getMinExpectedNumber(), flush=True)
    train_count = int(args.frames * 0.8)
    split_rng = random.Random(args.seed + 1)
    validation_indices = set(
        split_rng.sample(range(args.frames), args.frames - train_count)
    )
    saved = 0
    step = 0
    try:
        while traci.simulation.getMinExpectedNumber() > 0 and saved < args.frames:
            traci.simulationStep()
            step += 1
            now = float(traci.simulation.getTime())
            observations = lane_observations(traci, cfg)
            if phase == "green" and now >= phase_end:
                extend, _ = controller.should_extend(active_group, observations, active_green, yellow, all_red)
                if extend:
                    extra = float(cfg["sumo_green_extension_seconds"])
                    active_green += extra
                    phase_end += extra
                else:
                    traci.trafficlight.setRedYellowGreenState("center", signal_state(link_count, lane_links, (active_group,), "y"))
                    phase = "yellow"
                    phase_end = now + yellow
            elif phase == "yellow" and now >= phase_end:
                traci.trafficlight.setRedYellowGreenState("center", "r" * link_count)
                phase = "all_red"
                phase_end = now + all_red
            elif phase == "all_red" and now >= phase_end:
                controller.mark_served(active_group, now)
                active_group = None
                phase = "idle"
            if phase == "idle":
                selected, green, _ = controller.choose(observations, now, "smart")
                if selected is not None:
                    active_group = selected
                    active_green = float(green)
                    phase = "green"
                    phase_end = now + active_green
                    traci.trafficlight.setRedYellowGreenState("center", signal_state(link_count, lane_links, (selected,), "G"))
            if step % interval:
                continue

            split = "val" if saved in validation_indices else "train"
            stem = f"frame_{saved:06d}"
            image_path = out / "images" / split / f"{stem}.jpg"

            if not args.gui:
                raise SystemExit("Training dataset collection requires --gui. Headless synthetic frames are not valid training images.")
            capture_sumo_screenshot(traci, view_id, image_path, capture_size, retries=8)
            now = float(traci.simulation.getTime())

            annotations = []
            for vehicle_id in traci.vehicle.getIDList():
                cls = CLASSES.get(traci.vehicle.getTypeID(vehicle_id))
                if cls is None:
                    continue
                box = yolo_box(traci, vehicle_id, bounds, image_size)
                if box is None:
                    continue
                cx, cy, bw, bh = box
                annotations.append(f"{cls} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")

            (out / "labels" / split / f"{stem}.txt").write_text(
                "\n".join(annotations), encoding="utf-8"
            )
            saved += 1
            if saved % 50 == 0:
                print(f"Collected {saved}/{args.frames} frames")
    finally:
        traci.close()

    (out / "data.yaml").write_text(
        f"path: {out.as_posix()}\n"
        "train: images/train\n"
        "val: images/val\n"
        "names:\n  0: bike\n  1: car\n  2: bus\n  3: truck\n",
        encoding="utf-8",
    )
    print(f"Dataset saved to: {out}")
    train_images = len(list((out / "images" / "train").glob("*.jpg")))
    val_images = len(list((out / "images" / "val").glob("*.jpg")))
    train_labels = len(list((out / "labels" / "train").glob("*.txt")))
    val_labels = len(list((out / "labels" / "val").glob("*.txt")))
    print(f"Frames: {saved}. GUI collection: {args.gui}")
    print(f"Split: train={train_images} images/{train_labels} labels; "
          f"val={val_images} images/{val_labels} labels")
    if saved < args.frames:
        print(f"WARNING: requested {args.frames} frames but collected only {saved}. "
              "Check the SUMO route horizon and dataset_sumo_error.log.")
    if train_images != train_labels or val_images != val_labels:
        raise RuntimeError("Dataset image/label counts do not match.")
    print("Review a sample of images and labels before training.")


if __name__ == "__main__":
    main()
