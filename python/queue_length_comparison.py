import os
import pandas as pd

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt

CSV_FILE = "comparison.csv"
SUMO_CSV_FILE = "queue_length.csv"
OUTPUT_FILE = "queue_length_comparison.png"


def main():
    source_file = SUMO_CSV_FILE if os.path.isfile(SUMO_CSV_FILE) else CSV_FILE
    df = pd.read_csv(source_file)

    if "Cycle" not in df.columns:
        raise ValueError(f"{source_file} is missing Cycle.")

    df["Cycle"] = pd.to_numeric(df["Cycle"], errors="coerce")
    df = df.dropna(subset=["Cycle"])

    if df.empty:
        raise ValueError("No valid cycle data found.")

    lane_columns = []

    for lane in range(1, 5):
        fixed_col = f"Fixed_Lane{lane}_Queue_Length"
        smart_col = f"SmartFlow_Lane{lane}_Queue_Length"

        if smart_col in df.columns or fixed_col in df.columns:
            lane_columns.append(lane)

    if not lane_columns:
        raise ValueError(f"Queue-length columns are missing from {source_file}.")

    fig, axes = plt.subplots(
        2, 2,
        figsize=(14, 9),
        sharex=True,
        constrained_layout=True
    )

    axes = axes.flatten()
    has_fixed_any = False

    for idx, lane in enumerate(lane_columns):
        ax = axes[idx]

        smart_col = f"SmartFlow_Lane{lane}_Queue_Length"
        fixed_col = f"Fixed_Lane{lane}_Queue_Length"

        if smart_col in df.columns:
            smart = pd.to_numeric(df[smart_col], errors="coerce")

            if smart.notna().any():
                ax.plot(
                    df["Cycle"],
                    smart,
                    marker="s",
                    linewidth=2,
                    label="SmartFlow"
                )

        if fixed_col in df.columns:
            fixed = pd.to_numeric(df[fixed_col], errors="coerce")

            if fixed.notna().any():
                ax.plot(
                    df["Cycle"],
                    fixed,
                    marker="o",
                    linewidth=2,
                    label="Fixed Green"
                )

                has_fixed_any = True

        ax.set_title(f"Lane {lane}")
        ax.set_ylabel("Vehicles queued")
        ax.grid(axis="both", linestyle="--", alpha=0.4)
        ax.legend()

    for idx in range(len(lane_columns), len(axes)):
        axes[idx].set_visible(False)

    for ax in axes[-2:]:
        if ax.get_visible():
            ax.set_xlabel("Simulation minute")

    title = (
        "Queue Length Over Time: Fixed Green vs SmartFlow"
        if has_fixed_any
        else "SmartFlow Queue Length Over Time"
    )

    fig.suptitle(title, fontsize=15)

    fig.savefig(
        OUTPUT_FILE,
        dpi=200,
        bbox_inches="tight",
        pad_inches=0.3
    )

    plt.close(fig)

    print(f"Created {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
