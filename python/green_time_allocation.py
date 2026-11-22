import os
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import plotly.graph_objects as go


CSV_FILE = "smartflow_green_phases.csv"
PNG_FILE = "green_time_allocation.png"
HTML_FILE = "green_time_allocation.html"

LANE_COLORS = {
    1: "#3498DB",
    2: "#E76F51",
    3: "#2A9D8F",
    4: "#9467BD"
}


def load_phases():
    if not os.path.isfile(CSV_FILE):
        raise FileNotFoundError(
            f"{CSV_FILE} was not found in: {os.getcwd()}"
        )

    df = pd.read_csv(CSV_FILE)

    required = ["Lane", "Start_Seconds", "End_Seconds"]
    missing = [column for column in required if column not in df.columns]

    if missing:
        raise ValueError(f"{CSV_FILE} is missing columns: {missing}")

    for column in required:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(subset=required)
    df = df[
        (df["Lane"] > 0) &
        (df["End_Seconds"] > df["Start_Seconds"])
    ].copy()

    if df.empty:
        raise ValueError("No valid SmartFlow green phases found.")

    df["Lane"] = df["Lane"].astype(int)
    df["Duration"] = df["End_Seconds"] - df["Start_Seconds"]

    return df.sort_values("Start_Seconds").reset_index(drop=True)


def create_png(df):
    """Create the static dashboard preview using Matplotlib."""
    fig, axis = plt.subplots(figsize=(14, 4.5), constrained_layout=True)

    for _, phase in df.iterrows():
        lane = int(phase["Lane"])
        start = float(phase["Start_Seconds"])
        end = float(phase["End_Seconds"])
        duration = end - start

        axis.broken_barh(
            [(start, duration)],
            (0.25, 0.5),
            facecolors=LANE_COLORS.get(lane, "#808080"),
            edgecolors="white",
            linewidth=1
        )

        if duration >= 8:
            axis.text(
                start + duration / 2,
                0.5,
                f"{duration:.0f}s",
                ha="center",
                va="center",
                fontsize=8,
                fontweight="bold",
                color="white"
            )

    used_lanes = sorted(df["Lane"].unique())
    handles = [
        plt.Rectangle(
            (0, 0), 1, 1,
            facecolor=LANE_COLORS.get(lane, "#808080"),
            label=f"Lane {lane}"
        )
        for lane in used_lanes
    ]

    total_time = max(float(df["End_Seconds"].max()), 1.0)

    axis.set_xlim(0, total_time)
    axis.set_ylim(0, 1)
    axis.set_yticks([])
    axis.set_xlabel("Simulation Time (seconds)")
    axis.set_title("SmartFlow - Green Signal Sequence", fontweight="bold")
    axis.grid(axis="x", linestyle="--", alpha=0.35)
    axis.set_axisbelow(True)

    for spine in ("top", "right", "left"):
        axis.spines[spine].set_visible(False)

    if handles:
        axis.legend(
            handles=handles,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.22),
            ncol=max(1, len(handles)),
            frameon=False
        )

    fig.savefig(PNG_FILE, dpi=200, bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)

    print(f"Created {PNG_FILE}")


def create_html(df):
    """Create the interactive Plotly version; do not open it automatically."""
    fig = go.Figure()

    for index, phase in df.iterrows():
        lane = int(phase["Lane"])
        start = float(phase["Start_Seconds"])
        end = float(phase["End_Seconds"])
        duration = end - start

        fig.add_trace(
            go.Bar(
                x=[duration],
                y=["Green Signal"],
                base=[start],
                orientation="h",
                width=0.55,
                marker=dict(
                    color=LANE_COLORS.get(lane, "#808080"),
                    line=dict(color="white", width=1)
                ),
                text=[f"{duration:.0f}s" if duration >= 8 else ""],
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(color="white", size=11),
                name=f"Lane {lane}",
                legendgroup=f"lane{lane}",
                showlegend=lane not in df.iloc[:index]["Lane"].values,
                customdata=[[lane, start, end, duration]],
                hovertemplate=(
                    "<b>Lane %{customdata[0]}</b><br>"
                    "Start: %{customdata[1]:.1f} seconds<br>"
                    "End: %{customdata[2]:.1f} seconds<br>"
                    "Green duration: %{customdata[3]:.1f} seconds"
                    "<extra></extra>"
                )
            )
        )

    total_time = max(float(df["End_Seconds"].max()), 1.0)

    fig.update_layout(
        title=dict(
            text="SmartFlow - Interactive Green Signal Timeline",
            x=0.5,
            font=dict(size=20)
        ),
        barmode="overlay",
        height=480,
        xaxis=dict(
            title="Simulation Time (seconds)",
            range=[0, total_time],
            rangeslider=dict(visible=True, thickness=0.12),
            showgrid=True,
            gridcolor="rgba(150,150,150,0.2)",
            zeroline=False
        ),
        yaxis=dict(
            showticklabels=False,
            showgrid=False,
            fixedrange=True
        ),
        legend=dict(
            title="Traffic Lanes",
            orientation="h",
            y=1.12,
            x=0.5,
            xanchor="center"
        ),
        dragmode="pan",
        hovermode="closest",
        margin=dict(l=80, r=40, t=100, b=100),
        template="plotly_white"
    )

    fig.write_html(
        HTML_FILE,
        include_plotlyjs=True,
        config={
            "scrollZoom": True,
            "displayModeBar": True,
            "displaylogo": False,
            "modeBarButtonsToRemove": ["select2d", "lasso2d"]
        }
    )

    print(f"Created {HTML_FILE}")


def main():
    df = load_phases()
    create_png(df)
    create_html(df)


if __name__ == "__main__":
    main()
