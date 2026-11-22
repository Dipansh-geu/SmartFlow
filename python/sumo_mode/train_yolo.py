"""Train the four-class SmartFlow detector and install best.pt automatically."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main():
    project = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Train SmartFlow's bike/car/bus/truck YOLO model.")
    parser.add_argument("--data", default=str(project / "dataset" / "data.yaml"))
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--imgsz", type=int, default=960)
    parser.add_argument("--model", default="yolov8n.pt")
    parser.add_argument("--batch", type=int, default=8)
    args = parser.parse_args()

    data_yaml = Path(args.data).resolve()
    if not data_yaml.is_file():
        raise SystemExit(f"Dataset config not found: {data_yaml}. Run collect_dataset.py first.")
    if args.epochs < 1 or args.imgsz < 320 or args.batch < 1:
        parser.error("epochs/batch must be positive and imgsz must be at least 320")

    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit("Ultralytics is missing. Run: py -m pip install ultralytics") from exc

    runs_dir = project / "python" / "sumo_mode" / "training_runs"
    model = YOLO(args.model)
    result = model.train(
        data=str(data_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project=str(runs_dir),
        name="smartflow_4class",
        exist_ok=True,
    )
    model.val(data=str(data_yaml), imgsz=args.imgsz)

    best = Path(model.trainer.save_dir) / "weights" / "best.pt"
    if not best.is_file():
        raise SystemExit(f"Training finished but best.pt was not found at {best}")

    weights_dir = project / "python" / "sumo_mode" / "weights"
    weights_dir.mkdir(parents=True, exist_ok=True)
    destination = weights_dir / "best.pt"
    shutil.copy2(best, destination)
    print(f"\nSmartFlow YOLO weights installed: {destination}")
    print("You can now run SUMO mode with --source yolo.")


if __name__ == "__main__":
    main()
