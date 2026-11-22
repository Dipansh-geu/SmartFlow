"""Single grouped-bar comparison of average queue delay per reporting minute."""
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CSV_FILE = "comparison.csv"
OUTPUT_FILE = "average_wait_comparison.png"


def main():
    df = pd.read_csv(CSV_FILE)
    if "Cycle" not in df.columns:
        raise ValueError("comparison.csv is missing Cycle.")
    df["Cycle"] = pd.to_numeric(df["Cycle"], errors="coerce")
    df = df.dropna(subset=["Cycle"]).copy()
    if df.empty:
        raise ValueError("No valid reporting intervals found.")

    smart_col = "SmartFlow_Cycle_Average_Wait_Seconds"
    fixed_col = "Fixed_Cycle_Average_Wait_Seconds"
    if smart_col not in df.columns:
        raise ValueError(f"comparison.csv is missing {smart_col}.")

    smart = pd.to_numeric(df[smart_col], errors="coerce")
    fixed = pd.to_numeric(df[fixed_col], errors="coerce") if fixed_col in df.columns else pd.Series(float("nan"), index=df.index)
    x = range(len(df))
    width = 0.38 if fixed.notna().any() else 0.62

    fig, ax = plt.subplots(figsize=(13, 6), constrained_layout=True)
    if fixed.notna().any():
        ax.bar([i - width / 2 for i in x], fixed, width=width, label="Fixed-time", color="#E53935")
        ax.bar([i + width / 2 for i in x], smart, width=width, label="SmartFlow", color="#2980B9")
    else:
        ax.bar(x, smart, width=width, label="SmartFlow", color="#2980B9")
        ax.text(0.5, 0.96, "Fixed-time baseline unavailable in this run", transform=ax.transAxes, ha="center", va="top", fontsize=10)

    ax.set_title("Average Waiting Time: Fixed-time vs SmartFlow", pad=16, fontweight="bold")
    ax.set_xlabel("Simulation minute")
    ax.set_ylabel("Average queue delay (seconds per vehicle)")
    ax.set_xticks(list(x))
    ax.set_xticklabels([str(int(v)) for v in df["Cycle"]], rotation=0)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)
    ax.legend(loc="best")
    ax.margins(x=0.03, y=0.15)
    fig.savefig(OUTPUT_FILE, dpi=200, bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)
    print(f"Created {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
