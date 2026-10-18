import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("density.csv")

plt.figure(figsize=(12,6))

plt.bar(
    df["Simulation"],
    df["Lane1"],
    label="Lane 1"
)

plt.bar(
    df["Simulation"],
    df["Lane2"],
    bottom=df["Lane1"],
    label="Lane 2"
)

plt.bar(
    df["Simulation"],
    df["Lane3"],
    bottom=df["Lane1"] + df["Lane2"],
    label="Lane 3"
)

plt.bar(
    df["Simulation"],
    df["Lane4"],
    bottom=df["Lane1"] + df["Lane2"] + df["Lane3"],
    label="Lane 4"
)

plt.xlabel("Simulation Number")
plt.ylabel("Density Score")
plt.title("Traffic Density Distribution Across Simulations")

plt.legend()
plt.grid(axis="y", linestyle="--", alpha=0.5)

plt.tight_layout()

plt.savefig("density.png")

plt.savefig("density.png")
plt.close()
