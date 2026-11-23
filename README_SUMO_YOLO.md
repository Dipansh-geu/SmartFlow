# SmartFlow

Adaptive traffic-signal simulation with two execution modes:

- **Non-virtual C++ simulation:** Poisson arrivals, PCU-weighted queues, and fixed/SmartFlow/SCOOT-inspired controller comparisons.
- **Virtual SUMO simulation:** SUMO traffic with TraCI vehicle and queue observations. The active runner uses exact TraCI observations; YOLO utilities remain optional dataset/training tools and are not part of the active control loop.

## Configuration

Edit `config.ini`. The configured minimum green times are:

- C++: `minimum_green_seconds=20`
- SUMO: `sumo_minimum_green_seconds=15`

Both modes use 5 seconds yellow, 3 seconds all-red, and a 180-second starvation threshold. `startup_buffer_seconds` has been removed and is not applied.

## Build the C++ engine

From the project root:

```bash
g++ -std=c++17 -O2 -Iinclude src/main.cpp src/Lane.cpp src/SignalController.cpp src/Statistics.cpp src/Vehicle.cpp -o smartflow
```

On Windows with MinGW, use `smartflow.exe` as the output name.

## Run the GUI

Install dependencies from `requirements.txt`, install SUMO separately for virtual mode, then run:

```bash
python python/gui.py
```

The GUI compiles the C++ engine for non-virtual mode. SUMO mode requires SUMO and its Python TraCI modules to be available.

## Outputs

Each run is saved in a separate folder under `records/`. The engine writes CSV/report outputs and the Python graph scripts create PNG/HTML visualizations.

## Virtual-mode run behavior

One GUI launch starts one comparison batch. The runner generates one shared route-demand file, then executes one fixed-time baseline scenario and one SmartFlow-controlled scenario before writing the comparison CSVs and generating the graphs. Graph generation does not launch additional SUMO simulations. The average-waiting-time output is a single grouped bar chart comparing per-minute average total queue delay (`waitingTime + departDelay`).

The SmartFlow controller enforces `sumo_minimum_green_seconds=15`: even when the selected lane has very few vehicles, its initial green phase is at least 15 seconds (unless the simulation itself reaches its configured end time). The fixed-time baseline continues to use `fixed_green_seconds`.

### Virtual-mode comparison and final-minute waiting-time accuracy

Virtual mode stops generating demand at the selected simulation duration, then
continues running the signal controller for up to `sumo_drain_limit_seconds`
while vehicles remain in the network. Drain-period samples are excluded from
the minute-by-minute traffic graphs, but vehicles are allowed to finish so the
final-minute trip-delay comparison is not cut off at the demand horizon. The
fixed-time bars in the average-wait comparison graph are red; SmartFlow bars
remain blue. A negative time-saved result is still possible when measured
SmartFlow delay is genuinely higher than the fixed-time baseline.
