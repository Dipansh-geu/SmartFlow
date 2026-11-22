"""Compile and smoke-test SmartFlow's C++ engine using a temporary output directory."""

import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]

SOURCES = [
    "src/main.cpp",
    "src/Lane.cpp",
    "src/SignalController.cpp",
    "src/Statistics.cpp",
    "src/Vehicle.cpp"
]

with tempfile.TemporaryDirectory(prefix="smartflow_test_") as temp:

    temp = pathlib.Path(temp)
    binary = temp / "smartflow_test"

    subprocess.run(
        ["g++", "-std=c++17", "-Iinclude", *SOURCES, "-o", str(binary)],
        cwd=ROOT,
        check=True
    )

    (temp / "config.ini").write_text(
        (ROOT / "config.ini").read_text(encoding="utf-8"),
        encoding="utf-8"
    )

    result = subprocess.run(
        [str(binary)],
        input="5\n",
        cwd=temp,
        text=True,
        capture_output=True,
        check=True
    )

    assert "Completed 5 cycles" in result.stdout

    density = (temp / "density.csv").read_text(
        encoding="utf-8"
    ).splitlines()

    comparison = (temp / "comparison.csv").read_text(
        encoding="utf-8"
    ).splitlines()

    assert density[0] == "Cycle,Lane1_PCU,Lane2_PCU,Lane3_PCU,Lane4_PCU,Winner"

    assert len(density) == 6

    assert comparison[0].startswith(
        "Cycle,Fixed_RedLight_Cycle_Average_Wait_Seconds,SmartFlow_RedLight_Cycle_Average_Wait_Seconds"
    )

    assert len(comparison) == 6

    assert (temp / "report.txt").is_file()

print("SmartFlow C++ smoke test passed.")
