"""Run fair Fixed vs adaptive SmartFlow SUMO scenarios.

STRICT SIGNAL RULE: exactly one incoming approach lane receives green at a
time. North, east, south and west are four separate signal phases.
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import random
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from config import load_config
from controller import AdaptiveController


TYPES = ("bike", "car", "bus", "truck")

PCU = {
    "bike": "pcu_bike",
    "car": "pcu_car",
    "bus": "pcu_bus",
    "truck": "pcu_truck",
}

CROSS = {
    "bike": "crossing_bike_seconds",
    "car": "crossing_car_seconds",
    "bus": "crossing_bus_seconds",
    "truck": "crossing_truck_seconds",
}

LANES = ("north", "east", "south", "west")

IN_EDGES = ("n_in", "e_in", "s_in", "w_in")

STRAIGHT_OUT_EDGES = ("s_out", "w_out", "n_out", "e_out")
RIGHT_OUT_EDGES = ("w_out", "n_out", "e_out", "s_out")




def resolve_gui_view_id(traci, preferred="View #0"):
    """Return a view that SUMO actually exposes through TraCI."""
    try:
        view_ids = list(traci.gui.getIDList())
    except Exception:
        view_ids = []
    if preferred in view_ids:
        return preferred
    if view_ids:
        return view_ids[0]
    return preferred


def maximize_sumo_window():
    """Maximize the SUMO-GUI top-level window on Windows without extra packages."""
    if os.name != "nt":
        return
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        EnumWindows = user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        matches = []

        def callback(hwnd, _):
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            title = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, title, length + 1)
            if "sumo" in title.value.lower():
                matches.append(hwnd)
            return True

        EnumWindows(EnumWindowsProc(callback), 0)
        if matches:
            user32.ShowWindow(matches[0], 3)   
    except Exception:
        pass


def capture_sumo_screenshot(traci, view_id, image_path, image_size=640, retries=3):
    """Capture the current SUMO GUI state through TraCI.

    SUMO queues GUI screenshots and writes them only after the NEXT
    simulationStep(). Therefore this helper must request the screenshot,
    advance exactly one controlled step, and only then verify the file.
    """
    import time
    from pathlib import Path
    from PIL import Image

    path = Path(image_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(image_size, (tuple, list)):
        capture_width, capture_height = int(image_size[0]), int(image_size[1])
    else:
        capture_width = capture_height = int(image_size)
    capture_path = path.with_suffix('.sumo_capture.jpg')
    last_error = None

    for attempt in range(max(1, int(retries))):
        try:
            capture_path.unlink(missing_ok=True)
            path.unlink(missing_ok=True)

            view_ids = list(traci.gui.getIDList())
            if view_id not in view_ids:
                if not view_ids:
                    raise RuntimeError('SUMO GUI reports no active views')
                view_id = view_ids[0]

            traci.gui.screenshot(
                view_id, str(capture_path), capture_width, capture_height
            )
            traci.simulationStep()

            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline:
                if capture_path.is_file() and capture_path.stat().st_size > 0:
                    with Image.open(capture_path) as image:
                        image = image.convert('RGB')
                        if image.size != (capture_width, capture_height):
                            image = image.resize(
                                (capture_width, capture_height),
                                Image.Resampling.BILINEAR,
                            )
                        image.save(path, format='JPEG', quality=95)
                    capture_path.unlink(missing_ok=True)
                    if path.is_file() and path.stat().st_size > 0:
                        return str(path)
                    raise RuntimeError('JPEG conversion did not create an output file')
                time.sleep(0.05)
            last_error = TimeoutError(
                f'SUMO did not create queued screenshot: {capture_path}'
            )
        except Exception as exc:
            last_error = exc
            message = str(exc).lower()
            if 'connection already closed' in message or 'connection closed' in message:
                break
            time.sleep(0.2)

    raise RuntimeError(
        f'SUMO GUI screenshot failed for view {view_id!r}; output={path}. '
        f'Last error: {last_error}'
    )


def ensure_sumo_tools():
    """Make SUMO's bundled Python tools (especially traci) importable on Windows."""
    candidates = []
    home = os.environ.get("SUMO_HOME", "")
    if home:
        candidates.append(Path(home) / "tools")
    candidates.extend([
        Path(r"C:\\Program Files (x86)\\SUMO\\tools"),
        Path(r"C:\\Program Files\\Eclipse\\Sumo\\tools"),
        Path(r"C:\\Program Files (x86)\\Eclipse\\Sumo\\tools"),
    ])
    for tools_dir in candidates:
        if (tools_dir / "traci").is_dir() and str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))
            os.environ.setdefault("SUMO_HOME", str(tools_dir.parent))
            return str(tools_dir)
    return None


def find_sumo(gui=False):
    names = (
        ("sumo-gui.exe", "sumo-gui")
        if gui
        else ("sumo.exe", "sumo")
    )

    for name in names:
        found = shutil.which(name)
        if found:
            return found

    home = os.environ.get("SUMO_HOME", "")

    if home:
        for name in names:
            candidate = os.path.join(home, "bin", name)

            if os.path.isfile(candidate):
                return candidate

    return None


def make_routes(cfg, path):
    """Generate Poisson-distributed SUMO arrivals with type-specific speeds."""

    rng = random.Random(int(cfg["seed"]))
    horizon = float(cfg["simulation_duration_seconds"])
    rates = [float(cfg[f"arrival_rate_lane{i}"]) for i in range(1, 5)]
    routes = ["<routes>"]

    colors = {
        "bike": "0,180,255",
        "car": "255,40,40",
        "bus": "30,210,70",
        "truck": "255,190,0",
    }
    dims = {
        "bike": (1.8, 0.7, "motorcycle"),
        "car": (4.5, 1.8, "passenger"),
        "bus": (10.0, 2.5, "bus"),
        "truck": (8.0, 2.5, "truck"),
    }
    vehicle_classes = {
        "bike": "motorcycle",
        "car": "passenger",
        "bus": "bus",
        "truck": "truck",
    }
    default_speeds_kmh = {
        "bike": 45.0,
        "car": 60.0,
        "bus": 40.0,
        "truck": 35.0,
    }

    for vehicle_type in TYPES:
        length, width, gui_shape = dims[vehicle_type]
        speed_kmh = float(
            cfg.get(f"speed_{vehicle_type}_kmh", default_speeds_kmh[vehicle_type])
        )
        if speed_kmh <= 0:
            raise ValueError(f"speed_{vehicle_type}_kmh must be positive")
        speed_mps = speed_kmh / 3.6

        routes.append(
            f'<vType id="{vehicle_type}" '
            f'vClass="{vehicle_classes[vehicle_type]}" '
            f'guiShape="{gui_shape}" '
            f'length="{length}" width="{width}" '
            f'color="{colors[vehicle_type]}" '
            f'accel="2.0" decel="4.5" '
            f'maxSpeed="{speed_mps:.3f}" '
            f'minGap="2.5" sigma="0.5"/>'
        )

    for lane, (incoming, straight, right) in enumerate(
        zip(IN_EDGES, STRAIGHT_OUT_EDGES, RIGHT_OUT_EDGES)
    ):
        routes.append(
            f'<route id="r{lane}_straight" edges="{incoming} {straight}"/>'
        )
        routes.append(
            f'<route id="r{lane}_right" edges="{incoming} {right}"/>'
        )

    for lane in range(4):
        routes.append(
            f'<vehicle id="start_{lane}" type="car" route="r{lane}_straight" '
            'depart="0.000" departLane="best" departPos="100" departSpeed="0"/>'
        )

    vehicles = []
    for lane, rate in enumerate(rates):
        if rate < 0:
            raise ValueError(f"arrival_rate_lane{lane + 1} cannot be negative")
        depart = 0.0
        vehicle_index = 0

        while rate > 0:
            depart += rng.expovariate(rate)
            if depart >= horizon:
                break
            vehicle_type = rng.choices(
                TYPES, weights=[0.45, 0.35, 0.10, 0.10], k=1
            )[0]
            turn = "straight" if rng.random() < 0.70 else "right"
            vehicles.append((depart, lane, vehicle_index, vehicle_type, turn))
            vehicle_index += 1

    for depart, lane, vehicle_index, vehicle_type, turn in sorted(
        vehicles, key=lambda item: (item[0], item[1], item[2])
    ):
        routes.append(
            f'<vehicle id="v{lane}_{vehicle_index}" type="{vehicle_type}" '
            f'route="r{lane}_{turn}" depart="{depart:.3f}" '
            'departLane="best" departSpeed="0"/>'
        )

    routes.append("</routes>")
    Path(path).write_text("\n".join(routes), encoding="utf-8")
    return len(vehicles) + 4


def _vehicle_waiting_time(traci, vehicle_id, window):
    values = []

    try:
        values.append(
            float(
                traci.vehicle.getAccumulatedWaitingTime(
                    vehicle_id,
                    window
                )
            )
        )
    except Exception:
        pass

    try:
        values.append(
            float(
                traci.vehicle.getWaitingTime(vehicle_id)
            )
        )
    except Exception:
        pass

    return max(values, default=0.0)


def lane_observations(traci, cfg, waiting_window=7200.0):
    """Build normalized lane observations directly from SUMO TraCI."""

    observations = []

    for edge in IN_EDGES:
        vehicle_ids = []

        for lane_index in range(
            traci.edge.getLaneNumber(edge)
        ):
            vehicle_ids.extend(
                traci.lane.getLastStepVehicleIDs(
                    f"{edge}_{lane_index}"
                )
            )

        counts = {
            vehicle_type: 0
            for vehicle_type in TYPES
        }

        crossing = 0.0
        waiting_values = []
        queue_count = 0

        for vehicle_id in vehicle_ids:
            vehicle_type = traci.vehicle.getTypeID(
                vehicle_id
            )

            if vehicle_type not in counts:
                vehicle_type = "car"

            counts[vehicle_type] += 1

            crossing += float(
                cfg[CROSS[vehicle_type]]
            )

            wait = _vehicle_waiting_time(
                traci,
                vehicle_id,
                waiting_window
            )

            waiting_values.append(wait)

            try:
                if (
                    float(
                        traci.vehicle.getSpeed(vehicle_id)
                    ) <= 0.1
                ):
                    queue_count += 1
            except Exception:
                pass

        pcu = sum(
            counts[vehicle_type] * float(cfg[PCU[vehicle_type]])
            for vehicle_type in TYPES
        )

        observations.append({
            "counts_by_type": counts,
            "density_pcu": pcu,
            "waiting_crossing_seconds": crossing,
            "oldest_wait_seconds": max(
                waiting_values,
                default=0.0
            ),
            "total_wait_seconds": sum(waiting_values),
            "queue_count": queue_count,
            "waiting_vehicle_count": len(vehicle_ids),
        })

    return observations


def synthetic_frame(
    traci,
    output_path,
    bounds=(-120, -120, 120, 120),
    size=640
):
    from PIL import Image, ImageDraw

    lo_x, lo_y, hi_x, hi_y = bounds

    image = Image.new(
        "RGB",
        (size, size),
        (45, 48, 52)
    )

    draw = ImageDraw.Draw(image)

    def to_pixel(point):
        return (
            (point[0] - lo_x) / (hi_x - lo_x) * size,
            (hi_y - point[1]) / (hi_y - lo_y) * size
        )

    cx, cy = to_pixel((0, 0))

    draw.rectangle(
        (cx - 42, 0, cx + 42, size),
        fill=(85, 85, 85)
    )

    draw.rectangle(
        (0, cy - 42, size, cy + 42),
        fill=(85, 85, 85)
    )

    draw.rectangle(
        (cx - 42, cy - 42, cx + 42, cy + 42),
        fill=(45, 48, 52)
    )

    colors = {
        "bike": "cyan",
        "car": "red",
        "bus": "lime",
        "truck": "orange",
    }

    for vehicle_id in traci.vehicle.getIDList():
        position = to_pixel(
            traci.vehicle.getPosition(vehicle_id)
        )

        vehicle_type = traci.vehicle.getTypeID(
            vehicle_id
        )

        angle = math.radians(
            traci.vehicle.getAngle(vehicle_id)
        )

        length = (
            traci.vehicle.getLength(vehicle_id)
            * size
            / (hi_x - lo_x)
        )

        width = (
            traci.vehicle.getWidth(vehicle_id)
            * size
            / (hi_y - lo_y)
        )

        dx = math.cos(angle) * length / 2
        dy = math.sin(angle) * length / 2

        draw.line(
            (
                position[0] - dx,
                position[1] + dy,
                position[0] + dx,
                position[1] - dy
            ),
            fill=colors.get(vehicle_type, "white"),
            width=max(3, int(width))
        )

    image.save(output_path)


def build_lane_regions(traci):
    """Return inbound lane centerlines and widths directly from SUMO geometry."""
    regions = []
    for edge in IN_EDGES:
        lanes = []
        for lane_index in range(traci.edge.getLaneNumber(edge)):
            lane_id = f"{edge}_{lane_index}"
            shape = [(float(x), float(y)) for x, y in traci.lane.getShape(lane_id)]
            if len(shape) >= 2:
                lanes.append({"shape": shape, "width": float(traci.lane.getWidth(lane_id))})
        regions.append(lanes)
    return regions


def _distance_to_polyline(point, shape):
    px, py = point
    best = float("inf")
    for (ax, ay), (bx, by) in zip(shape, shape[1:]):
        dx, dy = bx - ax, by - ay
        denom = dx * dx + dy * dy
        t = 0.0 if denom <= 1e-12 else max(0.0, min(1.0, ((px-ax)*dx + (py-ay)*dy) / denom))
        qx, qy = ax + t * dx, ay + t * dy
        best = min(best, math.hypot(px-qx, py-qy))
    return best


def yolo_observations(model, frame_path, cfg, lane_regions=None, view_bounds=None):
    """Run one full-frame inference and assign each detection to an inbound lane."""
    from PIL import Image
    image = Image.open(frame_path).convert("RGB")
    width, height = image.size
    bounds = view_bounds or (
        float(cfg["sumo_view_min_x"]), float(cfg["sumo_view_min_y"]),
        float(cfg["sumo_view_max_x"]), float(cfg["sumo_view_max_y"]),
    )
    lo_x, lo_y, hi_x, hi_y = bounds
    detected = [
        {"counts_by_type": {kind: 0 for kind in TYPES}, "density_pcu": 0.0,
         "waiting_crossing_seconds": 0.0, "oldest_wait_seconds": 0.0,
         "total_wait_seconds": 0.0, "queue_count": 0}
        for _ in range(4)
    ]
    aliases = {"motorcycle":"bike", "motorbike":"bike", "bicycle":"bike",
               "car":"car", "bus":"bus", "truck":"truck"}
    results = model.predict(image, imgsz=int(cfg.get("yolo_imgsz", 960)),
                            conf=float(cfg["yolo_confidence"]), verbose=False)[0]
    if lane_regions is None:
        lane_regions = [[] for _ in range(4)]
    for box in results.boxes:
        name = aliases.get(model.names[int(box.cls[0])], model.names[int(box.cls[0])])
        if name not in TYPES:
            continue
        x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
        px, py = (x1+x2)/2.0, (y1+y2)/2.0
        world = (lo_x + px / width * (hi_x-lo_x), hi_y - py / height * (hi_y-lo_y))
        distances = []
        for lane_index, lane_set in enumerate(lane_regions):
            d = min((_distance_to_polyline(world, lane["shape"]) - lane["width"]/2.0
                     for lane in lane_set), default=float("inf"))
            distances.append(d)
        lane_index = min(range(4), key=lambda i: distances[i])
        if distances[lane_index] <= 1.5:
            detected[lane_index]["counts_by_type"][name] += 1
    for item in detected:
        item["queue_count"] = sum(item["counts_by_type"].values())
        item["density_pcu"] = sum(item["counts_by_type"][kind] * float(cfg[PCU[kind]]) for kind in TYPES)
        item["waiting_crossing_seconds"] = sum(item["counts_by_type"][kind] * float(cfg[CROSS[kind]]) for kind in TYPES)
    return detected


def signal_state(
    link_count,
    lane_links,
    lane_indices=(),
    color="r"
):
    state = ["r"] * link_count

    for lane_index in lane_indices:
        for link_index in lane_links[lane_index]:
            state[link_index] = color

    result = "".join(state)
    green_links = {i for i, value in enumerate(result) if value in ("G", "g")}
    if green_links:
        owners = [lane for lane, indexes in enumerate(lane_links)
                  if green_links.intersection(indexes)]
        if len(owners) > 1:
            raise RuntimeError(f"Unsafe signal state: multiple approaches green: {owners}")
    return result


def _phase_groups(cfg):
    """Return four exclusive phases; never combine green approaches."""

    return (
        (0,),
        (1,),
        (2,),
        (3,)
    )


def _lane_from_vehicle_id(vehicle_id):
    try:
        if vehicle_id.startswith("v") and "_" in vehicle_id:
            lane = int(
                vehicle_id[1:].split("_", 1)[0]
            )

            return lane if 0 <= lane < 4 else -1

    except (TypeError, ValueError):
        pass

    return -1


def _read_tripinfo(path):
    trips = []

    if not os.path.isfile(path):
        return trips

    try:
        root = ET.parse(path).getroot()

        for trip in root.findall("tripinfo"):
            arrival = float(
                trip.get("arrival", "-1")
            )

            vehicle_id = trip.get("id", "")

            trips.append({
                "id": vehicle_id,
                "arrival": arrival,
                "depart": float(trip.get("depart", "-1")),
                "waiting": float(
                    trip.get("waitingTime", "0")
                ),
                "depart_delay": float(
                    trip.get("departDelay", "0")
                ),
                "duration": float(
                    trip.get("duration", "0")
                ),
                "lane": _lane_from_vehicle_id(
                    vehicle_id
                ),
                "completed": arrival >= 0,
            })

    except (ET.ParseError, ValueError):
        return []

    return trips


def run_scenario(
    project,
    out,
    cfg,
    route_path,
    scenario,
    controller_mode,
    gui,
    cycles,
    groups,
    gui_delay_ms=100
):
    tools_path = ensure_sumo_tools()
    try:
        import traci
    except ImportError as exc:
        raise RuntimeError(
            "Python cannot import SUMO TraCI. Set SUMO_HOME to your SUMO "
            "installation folder. Expected its tools\\traci package; "
            f"searched standard Windows locations too. Last tools path: {tools_path}"
        ) from exc
    from network import build_network

    net = build_network(project)

    duration = float(
        cfg["simulation_duration_seconds"]
    )

    drain_limit = float(
        cfg["sumo_drain_limit_seconds"]
    )

    step_length = float(
        cfg["sumo_step_length"]
    )

    detection_interval = float(
        cfg["detection_interval_seconds"]
    )

    yellow_seconds = float(
        cfg["yellow_seconds"]
    )

    all_red_seconds = float(
        cfg["all_red_seconds"]
    )

    extension_seconds = float(
        cfg["sumo_green_extension_seconds"]
    )

    cycle_length = duration / cycles

    sumocfg = os.path.join(
        out,
        f"{scenario}.sumocfg"
    )

    tripinfo_path = os.path.join(
        out,
        f"{scenario}_tripinfo.xml"
    )

    Path(sumocfg).write_text(
        f'<configuration><input><net-file value="{net}"/>'
        f'<route-files value="{route_path}"/></input>'
        f'<time><begin value="0"/>'
        f'<end value="{duration + drain_limit}"/>'
        f'<step-length value="{step_length}"/>'
        f'</time></configuration>',
        encoding="utf-8"
    )

    executable = find_sumo(gui)

    if not executable:
        raise RuntimeError(
            "SUMO executable not found. Add SUMO bin to PATH "
            "or set SUMO_HOME correctly."
        )

    command = [
        executable,
        "-c",
        sumocfg,
        "--seed",
        str(cfg["seed"]),
        "--no-step-log",
        "true",
        "--tripinfo-output",
        tripinfo_path,
        "--tripinfo-output.write-unfinished",
        "true",
        "--tripinfo-output.write-undeparted",
        "true",
        "--waiting-time-memory",
        str(duration + drain_limit + 1),
        "--time-to-teleport",
        "-1",
        "--log",
        os.path.join(out, f"{scenario}_sumo.log"),
        "--error-log",
        os.path.join(out, f"{scenario}_sumo_error.log"),
    ]
    if gui:
        command.extend(["--delay", str(int(gui_delay_ms))])

    traci.start(command)
    view_id = resolve_gui_view_id(traci)
    camera_bounds = (float(cfg["sumo_view_min_x"]), float(cfg["sumo_view_min_y"]),
                     float(cfg["sumo_view_max_x"]), float(cfg["sumo_view_max_y"]))
    view_bounds = camera_bounds
    if gui:
        maximize_sumo_window()
        try:
            traci.gui.setSchema(view_id, "real world")
            traci.gui.setBoundary(view_id, *camera_bounds)
            traci.gui.setOffset(view_id, 120.0, 120.0)
            traci.gui.setZoom(view_id, float(cfg.get("sumo_zoom", "500")))
            lower, upper = traci.gui.getBoundary(view_id)
            view_bounds = (float(lower[0]), float(lower[1]),
                           float(upper[0]), float(upper[1]))
            print(
                f"[SUMO GUI] Full-screen view; real-world scheme; "
                f"zoom={traci.gui.getZoom(view_id):.0f}; bounds={view_bounds}",
                flush=True
            )
        except Exception as exc:
            print(f"[SUMO GUI] Could not fully apply presentation view: {exc}", flush=True)
    controller = AdaptiveController(
        cfg,
        groups=groups
    )

    lane_links = []

    controlled_links = (
        traci.trafficlight.getControlledLinks("center")
    )

    for lane_index, edge in enumerate(IN_EDGES):
        straight_edge = STRAIGHT_OUT_EDGES[lane_index]

        indexes = []

        for index, group in enumerate(controlled_links):
            if group and any(
                link[0].startswith(edge + "_")
                for link in group
            ):
                indexes.append(index)

        lane_links.append(indexes)

    if any(not indexes for indexes in lane_links):
        traci.close()

        raise RuntimeError(
            "Could not map all four incoming lanes to "
            f"traffic-light links: {lane_links}"
        )

    link_count = len(controlled_links)

    traci.trafficlight.setRedYellowGreenState(
        "center",
        "r" * link_count
    )

    signal_rows = []

    density_sum = [
        [0.0] * 4
        for _ in range(cycles)
    ]

    density_samples = [0] * cycles

    queue_sum = [
        [0.0] * 4
        for _ in range(cycles)
    ]
    queue_samples = [0] * cycles

    max_queue_by_lane = [0] * 4
    max_oldest_wait_by_lane = [0.0] * 4

    active_group = None
    active_lanes = ()

    active_green = 0.0
    active_signal_row = None

    phase_state = "idle"
    phase_end = 0.0
    next_decision = 0.0
    last_density_observations = None

    sim_end_cap = duration + drain_limit
    waiting_window = sim_end_cap + 1.0

    final_sim_time = 0.0

    try:
        while should_continue_simulation(
            traci.simulation.getTime(),
            duration,
            drain_limit,
            traci.simulation.getMinExpectedNumber(),
        ):

            now = traci.simulation.getTime()

            if (
                phase_state == "green"
                and now + 1e-9 >= phase_end
            ):
                exact_obs = lane_observations(
                    traci,
                    cfg,
                    waiting_window
                )

                if controller_mode == "smart":
                    extend, extension_reason = controller.should_extend(
                        active_group,
                        exact_obs,
                        active_green,
                        yellow_seconds,
                        all_red_seconds
                    )
                else:
                    extend = False
                    extension_reason = "fixed green complete"

                if extend:
                    active_green += extension_seconds
                    phase_end += extension_seconds

                    if active_signal_row is not None:
                        active_signal_row[2] = phase_end
                        active_signal_row[4] = active_green

                        active_signal_row[5] = (
                            f"{active_signal_row[5]}; "
                            f"{extension_reason}"
                        )

                else:
                    traci.trafficlight.setRedYellowGreenState(
                        "center",
                        signal_state(
                            link_count,
                            lane_links,
                            active_lanes,
                            "y"
                        )
                    )

                    phase_state = "yellow"
                    phase_end = now + yellow_seconds

                    if active_signal_row is not None:
                        active_signal_row[2] = now
                        active_signal_row[4] = active_green

            elif (
                phase_state == "yellow"
                and now + 1e-9 >= phase_end
            ):
                traci.trafficlight.setRedYellowGreenState(
                    "center",
                    "r" * link_count
                )

                phase_state = "all_red"
                phase_end = now + all_red_seconds

            elif (
                phase_state == "all_red"
                and now + 1e-9 >= phase_end
            ):
                controller.mark_served(
                    active_group,
                    now
                )

                active_group = None
                active_lanes = ()
                active_signal_row = None

                phase_state = "idle"
                next_decision = now

            if (
                phase_state == "idle"
                and now + 1e-9 >= next_decision
            ):
                exact_obs = lane_observations(
                    traci,
                    cfg,
                    waiting_window
                )

                chosen_obs = exact_obs

                last_density_observations = chosen_obs

                selected_group, green_seconds, reason = (
                    controller.choose(
                        chosen_obs,
                        now,
                        controller_mode
                    )
                )

                if selected_group is None:
                    next_decision = (
                        now + detection_interval
                    )

                else:
                    active_group = selected_group
                    active_lanes = groups[selected_group]

                    active_green = float(
                        green_seconds
                    )

                    phase_start = now
                    phase_end = now + active_green
                    phase_state = "green"

                    label = "+".join(
                        LANES[i]
                        for i in active_lanes
                    )

                    traci.trafficlight.setRedYellowGreenState(
                        "center",
                        signal_state(
                            link_count,
                            lane_links,
                            active_lanes,
                            "G"
                        )
                    )

                    active_signal_row = [
                        scenario,
                        phase_start,
                        phase_end,
                        label,
                        active_green,
                        reason
                    ]

                    signal_rows.append(
                        active_signal_row
                    )

            exact_now = lane_observations(
                traci,
                cfg,
                waiting_window
            )

            if now < duration:
                bucket = min(
                    cycles - 1,
                    max(0, int(now / cycle_length))
                )

                density_observations = (
                    last_density_observations
                    if last_density_observations is not None
                    else exact_now
                )
                for lane_index in range(4):
                    density_sum[bucket][lane_index] += (
                        density_observations[lane_index]["density_pcu"]
                    )

                    max_queue_by_lane[lane_index] = max(
                        max_queue_by_lane[lane_index],
                        exact_now[lane_index]["queue_count"]
                    )

                    max_oldest_wait_by_lane[lane_index] = max(
                        max_oldest_wait_by_lane[lane_index],
                        exact_now[lane_index]["oldest_wait_seconds"]
                    )

                    queue_sum[bucket][lane_index] += (
                        exact_now[lane_index]["queue_count"]
                    )

                density_samples[bucket] += 1
                queue_samples[bucket] += 1

            traci.simulationStep()

    finally:
        try:
            final_sim_time = float(
                traci.simulation.getTime()
            )
        except Exception:
            final_sim_time = 0.0

        if (
            active_signal_row is not None
            and phase_state == "green"
        ):
            actual_green = max(
                0.0,
                final_sim_time - float(active_signal_row[1])
            )

            active_signal_row[2] = final_sim_time
            active_signal_row[4] = actual_green

            active_signal_row[5] = (
                f"{active_signal_row[5]}; "
                "simulation ended during green"
            )

        try:
            traci.close()
        except Exception:
            pass

    trips = _read_tripinfo(
        tripinfo_path
    )

    completed = sum(
        1 for trip in trips
        if trip["completed"]
    )

    unfinished = len(trips) - completed

    drain_seconds = max(0.0, final_sim_time - duration)

    return {
        "scenario": scenario,
        "signals": signal_rows,
        "trips": trips,
        "completed": completed,
        "unfinished": unfinished,
        "drain_seconds": drain_seconds,
        "max_queue_by_lane": max_queue_by_lane,
        "max_oldest_wait_by_lane": max_oldest_wait_by_lane,
        "density": [
            [
                value / density_samples[i]
                if density_samples[i]
                else 0.0
                for value in density_sum[i]
            ]
            for i in range(cycles)
        ],
        "queue_length": [
            [
                value / queue_samples[i]
                if queue_samples[i]
                else 0.0
                for value in queue_sum[i]
            ]
            for i in range(cycles)
        ],
    }


def should_continue_simulation(sim_time, duration, drain_limit, min_expected):
    """Continue through demand generation, then drain active/pending vehicles.

    The drain is bounded by ``duration + drain_limit``. It is deliberately
    excluded from per-minute demand/queue sampling, but allows complete trip
    delays to be written to tripinfo for a fair final-minute comparison.
    """
    return (
        float(sim_time) < float(duration) + float(drain_limit)
        and (
            float(sim_time) < float(duration)
            or int(min_expected) > 0
        )
    )


def cycle_metrics(trips, cycles, duration):
    """Calculate cohort-based total queue delay for every vehicle that departed.

    Vehicles are assigned to the minute they entered the network, not the
    minute they completed their trip. Unfinished trips are retained so a
    controller cannot appear better merely because its longest-waiting
    vehicles have not reached their destinations yet. Total queue delay
    includes both stopped waitingTime and departDelay.
    """
    width = duration / cycles
    by_cycle = [[] for _ in range(cycles)]

    for trip in trips:
        depart = float(trip.get("depart", -1.0))
        if not math.isfinite(depart) or depart < 0 or depart >= duration:
            continue
        idx = min(cycles - 1, max(0, int(depart / width)))
        total_delay = max(0.0, float(trip.get("waiting", 0.0))) + max(
            0.0, float(trip.get("depart_delay", 0.0))
        )
        by_cycle[idx].append(total_delay)

    result = []
    cumulative_wait = 0.0
    cumulative_count = 0
    for bucket in by_cycle:
        cumulative_wait += sum(bucket)
        cumulative_count += len(bucket)
        result.append({
            "average": sum(bucket) / len(bucket) if bucket else None,
            "cumulative": cumulative_wait / cumulative_count if cumulative_count else None,
            "throughput": len(bucket),
        })
    return result


def _percentile(values, percentile):
    if not values:
        return None

    ordered = sorted(values)

    index = max(
        0,
        min(
            len(ordered) - 1,
            math.ceil(
                (percentile / 100.0) * len(ordered)
            ) - 1
        )
    )

    return ordered[index]


def _fmt(value):
    return (
        "N/A"
        if value is None
        else f"{value:.2f} s"
    )


def write_outputs(
    out,
    results,
    cycles,
    duration,
    groups,
    cfg
):
    by_name = {
        result["scenario"]: result
        for result in results
    }

    fixed_result = by_name.get("fixed")
    fixed = (
        cycle_metrics(fixed_result["trips"], cycles, duration)
        if fixed_result else [
            {"average": None, "cumulative": None, "throughput": 0}
            for _ in range(cycles)
        ]
    )

    smart_exact = cycle_metrics(
        by_name["smart_exact"]["trips"],
        cycles,
        duration
    )

    selected_smart = smart_exact

    header = [
        "Cycle",
        "Fixed_Average_Wait_Seconds",
        "SmartFlow_Average_Wait_Seconds",
        "SCOOT_Average_Wait_Seconds",
        "Fixed_Cycle_Average_Wait_Seconds",
        "SmartFlow_Cycle_Average_Wait_Seconds",
        "SCOOT_Cycle_Average_Wait_Seconds",
        "Fixed_Cumulative_Average_Wait_Seconds",
        "SmartFlow_Cumulative_Average_Wait_Seconds",
        "SCOOT_Cumulative_Average_Wait_Seconds",
        "Fixed_Throughput",
        "SmartFlow_Throughput",
        "SCOOT_Throughput",
        "Fixed_Green_Seconds",
        "SmartFlow_SUMO_Observation_Average_Wait_Seconds"
    ]

    with open(
        os.path.join(out, "comparison.csv"),
        "w",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.writer(file)
        writer.writerow(header)

        for i in range(cycles):
            f = fixed[i]
            s = smart_exact[i]
            selected = selected_smart[i]

            writer.writerow([
                i + 1,

                f["cumulative"]
                if f["cumulative"] is not None
                else "N/A",

                selected["cumulative"]
                if selected["cumulative"] is not None
                else "N/A",

                "N/A",

                f["average"]
                if f["average"] is not None
                else "N/A",

                selected["average"]
                if selected["average"] is not None
                else "N/A",

                "N/A",

                f["cumulative"]
                if f["cumulative"] is not None
                else "N/A",

                selected["cumulative"]
                if selected["cumulative"] is not None
                else "N/A",

                "N/A",

                f["throughput"] if fixed_result else "N/A",
                selected["throughput"],
                "N/A",
                45 if fixed_result else "N/A",

                s["average"]
                if s["average"] is not None
                else "N/A"
            ])
    fixed_queue = (
        fixed_result["queue_length"] if fixed_result else [[float("nan")] * 4 for _ in range(cycles)]
    )
    smart_queue = by_name["smart_exact"]["queue_length"]

    with open(
        os.path.join(out, "queue_length.csv"),
        "w",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            ["Cycle"]
            + [f"Fixed_Lane{lane}_Queue_Length" for lane in range(1, 5)]
            + [f"SmartFlow_Lane{lane}_Queue_Length" for lane in range(1, 5)]
        )
        for i in range(cycles):
            writer.writerow(
                [i + 1]
                + [round(value, 3) for value in fixed_queue[i]]
                + [round(value, 3) for value in smart_queue[i]]
            )

    density_result = by_name["smart_exact"]["density"]

    with open(
        os.path.join(out, "density.csv"),
        "w",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.writer(file)

        writer.writerow([
            "Cycle",
            "Lane1_PCU",
            "Lane2_PCU",
            "Lane3_PCU",
            "Lane4_PCU",
            "Winner"
        ])

        for i, values in enumerate(density_result):
            winner = (
                LANES[max(range(4), key=lambda j: values[j])]
                if max(values) > 0
                else "N/A"
            )

            writer.writerow([
                i + 1,
                *[round(value, 3) for value in values],
                winner
            ])

    with open(
        os.path.join(out, "density_cpp_compatible.csv"),
        "w",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.writer(file)
        writer.writerow([
            "Simulation",
            "Lane1_PCU",
            "Lane2_PCU",
            "Lane3_PCU",
            "Lane4_PCU",
            "Winner"
        ])
        for i, values in enumerate(density_result):
            winner_index = max(range(4), key=lambda j: values[j])
            winner = str(winner_index + 1) if max(values) > 0 else "N/A"
            writer.writerow([
                i + 1,
                *[round(value, 3) for value in values],
                winner
            ])

    with open(
        os.path.join(out, "signal_log.csv"),
        "w",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.writer(file)

        writer.writerow([
            "scenario",
            "phase_start",
            "phase_end",
            "lane",
            "green_seconds",
            "selection_reason"
        ])

        for result in results:
            writer.writerows(
                result["signals"]
            )

    group_labels = [
        "+".join(LANES[i] for i in group)
        for group in groups
    ]

    report_lines = [
        "SMARTFLOW SUMO MODE REPORT",
        "==========================",

        f"Traffic generation horizon: {duration:.0f} seconds",

        f"Maximum drain period: "
        f"{float(cfg['sumo_drain_limit_seconds']):.0f} seconds",

        f"Reporting intervals (one per minute): {cycles}",

        "Per-minute average waiting uses total queue delay (SUMO waitingTime + departDelay). "
        "Vehicles are grouped by departure minute; unfinished departed vehicles are included.",

        "Comparison uses two sequential SUMO executions with the same generated route demand: "
        "fixed-time baseline first, then SmartFlow.",

        f"Signal groups: {', '.join(group_labels)}",

        f"Green settings: "
        f"min={cfg['sumo_minimum_green_seconds']}s, "
        f"max={cfg['sumo_maximum_green_seconds']}s, "
        f"extension={cfg['sumo_green_extension_seconds']}s",

        f"Waiting-time priority target: "
        f"{cfg['sumo_starvation_threshold_seconds']}s "
        "(target, not a guaranteed bound under oversaturated demand)",

        "Exactly one approach lane receives green at a time; "
        "opposing approaches are never paired.",

        ""
    ]

    for result in results:
        trips = result["trips"]

        completed_trips = [
            trip for trip in trips
            if trip["completed"]
        ]

        unfinished_trips = [
            trip for trip in trips
            if not trip["completed"]
        ]

        waits_all = [
            trip["waiting"]
            for trip in trips
        ]

        waits_completed = [
            trip["waiting"]
            for trip in completed_trips
        ]

        depart_delays = [
            trip["depart_delay"]
            for trip in trips
        ]

        total_queue_delays = [
            trip["waiting"] + trip["depart_delay"]
            for trip in trips
        ]

        lane_counts = [0, 0, 0, 0]
        lane_waits = [[] for _ in range(4)]
        lane_total_delays = [[] for _ in range(4)]

        for trip in trips:
            lane = trip["lane"]

            if 0 <= lane < 4:
                if trip["completed"]:
                    lane_counts[lane] += 1

                lane_waits[lane].append(
                    trip["waiting"]
                )

                lane_total_delays[lane].append(
                    trip["waiting"] + trip["depart_delay"]
                )

        fairness_den = (
            4 * sum(x * x for x in lane_counts)
        )

        fairness = (
            sum(lane_counts) ** 2 / fairness_den
            if fairness_den
            else 0.0
        )

        greens = [
            row[4]
            for row in result["signals"]
        ]

        report_lines += [
            f"Scenario: {result['scenario']}",

            f"Completed vehicles (throughput): "
            f"{len(completed_trips)}",

            f"Unfinished vehicles at simulation cap: "
            f"{len(unfinished_trips)}",

            f"Drain time used after arrivals stopped: "
            f"{result['drain_seconds']:.0f} seconds",

            f"Average stopped waiting time (all reported vehicles): "
            f"{_fmt(sum(waits_all) / len(waits_all) if waits_all else None)}",

            f"Average stopped waiting time (completed only): "
            f"{_fmt(sum(waits_completed) / len(waits_completed) if waits_completed else None)}",

            f"95th percentile stopped waiting time: "
            f"{_fmt(_percentile(waits_all, 95))}",

            f"Maximum individual stopped waiting time: "
            f"{_fmt(max(waits_all) if waits_all else None)}",

            f"Average departure delay before insertion: "
            f"{_fmt(sum(depart_delays) / len(depart_delays) if depart_delays else None)}",

            f"Average total queue delay (waiting + departure delay): "
            f"{_fmt(sum(total_queue_delays) / len(total_queue_delays) if total_queue_delays else None)}",

            f"95th percentile total queue delay (waiting + departure delay): "
            f"{_fmt(_percentile(total_queue_delays, 95))}",

            f"Maximum total queue delay (waiting + departure delay): "
            f"{_fmt(max(total_queue_delays) if total_queue_delays else None)}",

            f"Actual green phases logged: {len(greens)}",

            f"Average green duration: "
            f"{_fmt(sum(greens) / len(greens) if greens else None)}",

            f"Jain throughput fairness across approaches: "
            f"{fairness:.3f}"
        ]

        for i, lane_name in enumerate(LANES):
            lane_avg = (
                sum(lane_waits[i]) / len(lane_waits[i])
                if lane_waits[i]
                else None
            )

            lane_p95 = _percentile(
                lane_waits[i],
                95
            )

            lane_total_avg = (
                sum(lane_total_delays[i]) / len(lane_total_delays[i])
                if lane_total_delays[i]
                else None
            )

            report_lines.append(
                f"  {lane_name}: "
                f"completed={lane_counts[i]}, "
                f"avg_stopped_wait={_fmt(lane_avg)}, "
                f"p95_stopped_wait={_fmt(lane_p95)}, "
                f"avg_total_queue_delay={_fmt(lane_total_avg)}, "
                f"max_queue={result['max_queue_by_lane'][i]}, "
                f"max_observed_oldest_wait="
                f"{_fmt(result['max_oldest_wait_by_lane'][i])}"
            )

        report_lines.append("")

    fixed_trips = by_name.get("fixed", {}).get("trips", [])
    smart_trips = by_name.get("smart_exact", {}).get("trips", [])

    def overall_delay(trips):
        eligible = [
            max(0.0, float(t.get("waiting", 0.0)))
            + max(0.0, float(t.get("depart_delay", 0.0)))
            for t in trips
            if float(t.get("depart", -1.0)) >= 0
        ]
        return (sum(eligible) / len(eligible), len(eligible)) if eligible else (None, 0)

    fixed_overall, fixed_n = overall_delay(fixed_trips)
    smart_overall, smart_n = overall_delay(smart_trips)
    report_lines.append("")
    if fixed_overall is not None and smart_overall is not None and fixed_overall > 0:
        saved_pct = ((fixed_overall - smart_overall) / fixed_overall) * 100.0
        report_lines.append(
            f"Overall vehicle-weighted average queue delay: fixed={fixed_overall:.2f}s "
            f"({fixed_n} vehicles), SmartFlow={smart_overall:.2f}s ({smart_n} vehicles)."
        )
        report_lines.append(
            f"Time saved vs fixed-time: {saved_pct:.2f}% "
            "(negative means SmartFlow had higher average delay)."
        )
    else:
        report_lines.append(
            "Overall time-saved percentage: N/A (insufficient valid vehicle data)."
        )

    report_lines.append(
        "SCOOT is not implemented in SUMO mode; SCOOT columns are N/A."
    )

    Path(
        os.path.join(out, "report.txt")
    ).write_text(
        "\n".join(report_lines) + "\n",
        encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--minutes",
        type=int,
        required=True,
        help="Exact simulated duration in minutes"
    )

    parser.add_argument(
        "--out",
        required=True
    )

    parser.add_argument(
        "--render",
        choices=["gui", "headless"],
        default="gui",
        help="Run SUMO with its GUI or without a GUI"
    )
    parser.add_argument(
        "--delay-ms",
        type=int,
        default=100,
        help="SUMO GUI delay in milliseconds (default: 100)"
    )

    args = parser.parse_args()
    if args.delay_ms < 0:
        parser.error("--delay-ms cannot be negative")

    if not 1 <= args.minutes <= 240:
        parser.error("--minutes must be between 1 and 240")

    project = str(
        Path(__file__).resolve().parents[2]
    )

    out = os.path.abspath(args.out)

    os.makedirs(
        out,
        exist_ok=True
    )

    cfg = load_config(
        os.path.join(project, "config.ini")
    )

    duration = float(args.minutes * 60)
    cfg["simulation_duration_seconds"] = str(duration)
    reporting_buckets = args.minutes  

    groups = _phase_groups(cfg)

    route_path = os.path.join(
        out,
        "traffic.rou.xml"
    )

    generated = make_routes(
        cfg,
        route_path
    )

    print(
        f"Generated {generated} vehicles across four approaches."
    )

    print(
        "Signal groups: "
        + ", ".join(
            "+".join(LANES[i] for i in group)
            for group in groups
        )
    )

    scenarios = [("fixed", "fixed"), ("smart_exact", "smart")]

    results = []

    for scenario, controller_mode in scenarios:
        print(f"Running {scenario} using SUMO TraCI observations...")
        results.append(
            run_scenario(
                project,
                out,
                cfg,
                route_path,
                scenario,
                controller_mode,
                args.render == "gui",
                reporting_buckets,
                groups,
                args.delay_ms
            )
        )

    write_outputs(
        out,
        results,
        reporting_buckets,
        duration,
        groups,
        cfg
    )

    print(
        "SUMO run completed. Review report.txt, "
        "signal_log.csv, comparison.csv and density.csv."
    )


if __name__ == "__main__":
    main()