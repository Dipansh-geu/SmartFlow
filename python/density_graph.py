import pandas as pd

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt


CSV_FILE = "density.csv"
OUTPUT_FILE = "density.png"


LANE_COLORS = [
    "#3498DB",
    "#E74C3C",
    "#2ECC71",
    "#F1C40F"
]


def main():
    df = pd.read_csv(CSV_FILE)

    lane_columns = sorted(
        [
            col for col in df.columns
            if col.startswith("Lane") and col.endswith("_PCU")
        ],
        key=lambda col: int(col[4:-4])
    )

    if not lane_columns:
        raise ValueError(
            "No lane PCU columns found in density.csv"
        )

    if "Cycle" not in df.columns:
        raise ValueError(
            "Missing Cycle column in density.csv"
        )

    df["Cycle"] = pd.to_numeric(
        df["Cycle"], errors="raise"
    )

    df[lane_columns] = df[lane_columns].apply(
        pd.to_numeric,
        errors="coerce"
    ).fillna(0)

    lane_count = len(lane_columns)

    fig, axes = plt.subplots(
        lane_count,
        1,
        figsize=(13, max(3.2 * lane_count, 7)),
        sharex=True,
        sharey=True,
        constrained_layout=True
    )

    if lane_count == 1:
        axes = [axes]

    max_value = df[lane_columns].to_numpy().max()
    y_limit = max(1, max_value * 1.25)

    for index, column in enumerate(lane_columns):

        ax = axes[index]
        values = df[column]

        lane_name = (
            column.replace("_PCU", "")
            .replace("Lane", "Lane ")
        )

        bars = ax.bar(
            df["Cycle"],
            values,
            width=0.65,
            color=LANE_COLORS[index % len(LANE_COLORS)],
            label=lane_name
        )

        for bar, value in zip(bars, values):
            ax.annotate(
                f"{value:.2f}",
                xy=(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height()
                ),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8
            )

        ax.set_title(
            lane_name,
            loc="left",
            fontsize=11,
            fontweight="bold"
        )

        ax.set_ylabel("PCU")
        ax.set_ylim(0, y_limit)

        ax.grid(
            axis="y",
            linestyle="--",
            alpha=0.4
        )

        ax.set_axisbelow(True)

    axes[-1].set_xlabel("Simulation Minute")

    fig.suptitle(
        "SmartFlow - PCU Demand Per Lane",
        fontsize=15,
        fontweight="bold"
    )

    fig.tight_layout(
        rect=[0, 0, 1, 0.97]
    )

    plt.savefig(
        OUTPUT_FILE,
        dpi=200,
        bbox_inches="tight"
    )

    plt.close(fig)

    print(f"Graph saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
