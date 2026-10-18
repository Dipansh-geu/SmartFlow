import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("comparison.csv")

plt.figure(figsize=(10,6))

plt.plot(df["Simulation"], df["Fixed"], marker="o", label="Fixed")
plt.plot(df["Simulation"], df["SmartFlow"], marker="o", label="SmartFlow")

plt.xlabel("Simulation")
plt.ylabel("Waiting Time")
plt.title("Fixed vs SmartFlow")

plt.legend()

plt.savefig("comparison.png")

plt.savefig("comparison.png")
plt.close()
