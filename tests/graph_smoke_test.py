"""Smoke-test the graph generators with the Phase 1 CSV schema."""
import pathlib
import sys
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]

with tempfile.TemporaryDirectory(prefix="smartflow_graph_test_") as temp:
    temp = pathlib.Path(temp)

    (temp / "comparison.csv").write_text(
        "Cycle,Fixed_Average_Wait_Seconds,SmartFlow_Average_Wait_Seconds,SCOOT_Average_Wait_Seconds,Fixed_Cycle_Average_Wait_Seconds,SmartFlow_Cycle_Average_Wait_Seconds,SCOOT_Cycle_Average_Wait_Seconds,Fixed_Cumulative_Average_Wait_Seconds,SmartFlow_Cumulative_Average_Wait_Seconds,SCOOT_Cumulative_Average_Wait_Seconds,Fixed_Throughput,SmartFlow_Throughput,SCOOT_Throughput,Fixed_Green_Seconds\n"
        "1,22.5,18.1,17.2,22.5,18.1,17.2,22.5,18.1,17.2,10,12,13,45\n2,35.0,26.4,24.9,35.0,26.4,24.9,35.0,26.4,24.9,8,11,12,45\n",
        encoding="utf-8"
    )

    (temp / "density.csv").write_text(
        "Cycle,Lane1_PCU,Lane2_PCU,Lane3_PCU,Lane4_PCU,Winner\n"
        "1,3.5,6.0,2.0,4.5,2\\n2,7.0,1.5,4.0,3.0,3\n",
        encoding="utf-8"
    )

    subprocess.run([sys.executable, str(ROOT / "python/graph.py")], cwd=temp, check=True)
    subprocess.run([sys.executable, str(ROOT / "python/density_graph.py")], cwd=temp, check=True)
    subprocess.run([sys.executable, str(ROOT / "python/average_wait_cycle.py")], cwd=temp, check=True)
    subprocess.run([sys.executable, str(ROOT / "python/cumulative_average.py")], cwd=temp, check=True)
    subprocess.run([sys.executable, str(ROOT / "python/vehicles_passed.py")], cwd=temp, check=True)

    assert (temp / "comparison.png").stat().st_size > 1000
    assert (temp / "density.png").stat().st_size > 1000

    for graph in ("average_wait_cycle.png", "cumulative_average.png", "vehicles_passed.png"):
        assert (temp / graph).stat().st_size > 1000

print("SmartFlow graph smoke tests passed.")
