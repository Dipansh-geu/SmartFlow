"""Build SmartFlow's four-arm SUMO network for left-hand traffic (India)."""
from pathlib import Path
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET


def build_network(project):
    sumo_dir = Path(project) / "sumo"
    net = sumo_dir / "intersection.net.xml"
    exe = shutil.which("netconvert")
    if not exe:
        home = os.environ.get("SUMO_HOME", "")
        candidates = [
            Path(home) / "bin" / ("netconvert.exe" if os.name == "nt" else "netconvert"),
            Path(r"C:\Program Files (x86)\SUMO\bin\netconvert.exe"),
            Path(r"C:\Program Files\Eclipse\Sumo\bin\netconvert.exe"),
        ]
        exe = next((str(x) for x in candidates if x.is_file()), None)
    if not exe:
        raise RuntimeError("netconvert not found. Install SUMO or set SUMO_HOME.")

    cmd = [exe, "--node-files", str(sumo_dir / "nodes.nod.xml"),
           "--edge-files", str(sumo_dir / "edges.edg.xml"),
           "--output-file", str(net), "--tls.default-type", "static",
           "--no-turnarounds", "true", "--lefthand", "true"]
    subprocess.run(cmd, check=True, cwd=str(project))

    tree = ET.parse(net)
    root = tree.getroot()
    for logic in root.findall("tlLogic"):
        for phase in list(logic.findall("phase")):
            logic.remove(phase)

        links_by_approach = {edge: [] for edge in ("n_in", "e_in", "s_in", "w_in")}
        max_index = -1
        for connection in root.findall("connection"):
            if connection.get("tl") != logic.get("id"):
                continue
            edge = connection.get("from")
            if edge in links_by_approach:
                index = int(connection.get("linkIndex", "-1"))
                if index >= 0:
                    links_by_approach[edge].append(index)
                    max_index = max(max_index, index)

        state_length = max_index + 1
        if state_length <= 0:
            state_length = 16

        for edge in ("n_in", "e_in", "s_in", "w_in"):
            green = ["r"] * state_length
            yellow = ["r"] * state_length
            for index in links_by_approach[edge]:
                green[index] = "G"
                yellow[index] = "y"
            ET.SubElement(logic, "phase", {
                "duration": "1",
                "state": "".join(green),
                "name": f"SmartFlow fallback green {edge}",
            })
            ET.SubElement(logic, "phase", {
                "duration": "1",
                "state": "".join(yellow),
                "name": f"SmartFlow fallback yellow {edge}",
            })
    tree.write(net, encoding="utf-8", xml_declaration=True)
    return str(net)
