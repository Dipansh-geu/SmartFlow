#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <random>
#include <string>
#include <vector>

#include "../include/Vehicle.h"

struct Config {
    int laneCount = 4;
    int fixedGreen = 45;
    int minGreen = 20;
    int maxGreen = 90;
    int yellow = 5;
    int allRed = 3;

    double starvationThreshold = 180.0;
    double horizon = 3600.0;

    std::vector<double> rates{0.12, 0.16, 0.10, 0.14};

    double pcuBike = 0.5;
    double pcuCar = 1;
    double pcuBus = 3;
    double pcuTruck = 3;

    int timeBike = 1;
    int timeCar = 2;
    int timeBus = 4;
    int timeTruck = 5;

    unsigned seed = 0;
};

static std::string trim(std::string s) {
    const char* ws = " \t\r\n";

    s.erase(0, s.find_first_not_of(ws));
    s.erase(s.find_last_not_of(ws) + 1);

    return s;
}

Config readConfig(const std::string& path) {
    Config c;
    std::ifstream f(path);
    std::string line;

    while (std::getline(f, line)) {
        line = trim(line);

        if (line.empty() || line[0] == '#' ||
            line[0] == ';' || line[0] == '[') {
            continue;
        }

        auto pos = line.find('=');

        if (pos == std::string::npos) {
            continue;
        }

        std::string k = trim(line.substr(0, pos));
        std::string v = trim(line.substr(pos + 1));

        try {
            if (k == "lanes") {
                c.laneCount = std::stoi(v);
            } else if (k == "fixed_green_seconds") {
                c.fixedGreen = std::stoi(v);
            } else if (k == "minimum_green_seconds") {
                c.minGreen = std::stoi(v);
            } else if (k == "maximum_green_seconds") {
                c.maxGreen = std::stoi(v);
            } else if (k == "yellow_seconds") {
                c.yellow = std::stoi(v);
            } else if (k == "all_red_seconds") {
                c.allRed = std::stoi(v);
            } else if (k == "starvation_threshold_seconds") {
                c.starvationThreshold = std::stod(v);
            } else if (k == "simulation_duration_seconds") {
                c.horizon = std::stod(v);
            } else if (k.rfind("arrival_rate_lane", 0) == 0) {
                int i = std::stoi(k.substr(17)) - 1;

                if (i >= 0 && i < 100) {
                    if (i >= static_cast<int>(c.rates.size())) {
                        c.rates.resize(i + 1, 0.12);
                    }

                    c.rates[i] = std::stod(v);
                }
            } else if (k == "pcu_bike") {
                c.pcuBike = std::stod(v);
            } else if (k == "pcu_car") {
                c.pcuCar = std::stod(v);
            } else if (k == "pcu_bus") {
                c.pcuBus = std::stod(v);
            } else if (k == "pcu_truck") {
                c.pcuTruck = std::stod(v);
            } else if (k == "crossing_bike_seconds") {
                c.timeBike = std::stoi(v);
            } else if (k == "crossing_car_seconds") {
                c.timeCar = std::stoi(v);
            } else if (k == "crossing_bus_seconds") {
                c.timeBus = std::stoi(v);
            } else if (k == "crossing_truck_seconds") {
                c.timeTruck = std::stoi(v);
            } else if (k == "seed") {
                c.seed = static_cast<unsigned>(std::stoul(v));
            }
        } catch (...) {
            std::cerr << "Invalid config value for " << k
                      << "; retaining default.\n";
        }
    }

    c.laneCount = std::max(1, c.laneCount);
    c.horizon = std::max(1.0, c.horizon);
    c.minGreen = std::max(1, c.minGreen);
    c.maxGreen = std::max(c.minGreen, c.maxGreen);

    c.rates.resize(c.laneCount, 0.12);

    return c;
}

Vehicle makeVehicle(
    std::mt19937& rng,
    const Config& c,
    double arrival
) {
    std::discrete_distribution<int> d({0.45, 0.35, 0.10, 0.10});
    int t = d(rng);

    if (t == 0) {
        return Vehicle("Bike", c.pcuBike, c.timeBike, arrival);
    }

    if (t == 1) {
        return Vehicle("Car", c.pcuCar, c.timeCar, arrival);
    }

    if (t == 2) {
        return Vehicle("Bus", c.pcuBus, c.timeBus, arrival);
    }

    return Vehicle("Truck", c.pcuTruck, c.timeTruck, arrival);
}

struct Traffic {
    std::vector<std::vector<Vehicle>> lanes;
};

Traffic generateTraffic(const Config& c, unsigned seed) {
    Traffic t;
    t.lanes.resize(c.laneCount);

    std::mt19937 rng(seed);

    for (int lane = 0; lane < c.laneCount; ++lane) {
        const double rate = c.rates[lane];

        if (rate <= 0) {
            continue;
        }

        std::exponential_distribution<double> gap(rate);

        for (double time = gap(rng); time < c.horizon; time += gap(rng)) {
            t.lanes[lane].push_back(makeVehicle(rng, c, time));
        }
    }

    return t;
}

enum class Mode {
    Fixed,
    Smart,
    Scoot
};
struct GreenPhase {
    int lane;
    double start;
    double end;
};
struct Result {
    std::vector<GreenPhase> greenPhases;
    std::vector<double> cycleAvg;
    std::vector<double> cumulativeAvg;

    std::vector<double> redCycleAvg;

    std::vector<long> throughputHistory;
std::vector<std::vector<double>> greenTimeByLaneCycle;

std::vector<std::vector<long>> queueLengthByLaneCycle;

    long throughput = 0;
    long phases = 0;

    double totalWait = 0;
};

int greenFor(
    const std::vector<Vehicle>& q,
    size_t head,
    double now,
    const Config& c,
    Mode mode
) {
    if (mode == Mode::Fixed) {
        return c.fixedGreen;
    }

    double crossing = 0;
    double pcu = 0;

    for (
        size_t j = head;
        j < q.size() && q[j].getArrivalTime() <= now;
        ++j
    ) {
        crossing += q[j].getCrossingTime();
        pcu += q[j].getPCU();
    }

    int demand = static_cast<int>(std::ceil(crossing));

    if (mode == Mode::Scoot) {
        demand = static_cast<int>(
            std::ceil(std::min(crossing, pcu * 2.0))
        );
    }

    return std::max(
        c.minGreen,
        std::min(c.maxGreen, demand)
    );
}

Result runController(
    const Traffic& traffic,
    const Config& c,
    int cycles,
    Mode mode
) {
    const auto& q = traffic.lanes;

    std::vector<size_t> head(c.laneCount, 0);

std::vector<double> starvation(c.laneCount, 0.0);

std::vector<int> skippedPhases(c.laneCount, 0);

    Result r;

    const double nan = std::numeric_limits<double>::quiet_NaN();

    r.cycleAvg.assign(cycles, nan);
    r.cumulativeAvg.assign(cycles, nan);
    r.redCycleAvg.assign(cycles, nan);
    r.throughputHistory.assign(cycles, 0);
    r.greenTimeByLaneCycle.assign(
    c.laneCount, std::vector<double>(cycles, 0.0)
);

r.queueLengthByLaneCycle.assign(
    c.laneCount, std::vector<long>(cycles, 0)
);

const double notServed = std::numeric_limits<double>::quiet_NaN();

std::vector<std::vector<double>> serviceStartByVehicle(c.laneCount);

for (int lane = 0; lane < c.laneCount; ++lane) {
    serviceStartByVehicle[lane].assign(q[lane].size(), notServed);
}

    std::vector<std::vector<double>> redWaitByVehicle(c.laneCount);
    for (int lane = 0; lane < c.laneCount; ++lane) {
        redWaitByVehicle[lane].assign(q[lane].size(), 0.0);
    }

    std::vector<double> cohortWait(cycles, 0.0);
    std::vector<double> redCohortWait(cycles, 0.0);
    std::vector<long> cohortCount(cycles, 0);
    std::vector<long> departedIn(cycles, 0);

    const double interval = c.horizon / cycles;

    auto bucket = [&](double t) {
        return std::min(
            cycles - 1,
            std::max(0, static_cast<int>(t / interval))
        );
    };

    for (const auto& lane : q) {
        for (const auto& v : lane) {
            ++cohortCount[bucket(v.getArrivalTime())];
        }
    }

    double clock = 0;
    int previous = -1;
    double totalWaitSoFar = 0;

    auto waiting = [&](int lane, double now) {
        return head[lane] < q[lane].size() &&
               q[lane][head[lane]].getArrivalTime() <= now;
    };

    while (clock < c.horizon) {
        int chosen = -1;

        if (mode == Mode::Fixed) {
            for (int step = 1; step <= c.laneCount; ++step) {
                int idx = (previous + step) % c.laneCount;

                if (waiting(idx, clock)) {
                    chosen = idx;
                    break;
                }
            }
        } else {
            double best = -1e30;

            for (int lane = 0; lane < c.laneCount; ++lane) {
                if (!waiting(lane, clock) || lane == previous) {
                    continue;
                }

                double pcu = 0;
                double cross = 0;

                for (
                    size_t j = head[lane];
                    j < q[lane].size() &&
                    q[lane][j].getArrivalTime() <= clock;
                    ++j
                ) {
                    pcu += q[lane][j].getPCU();
                    cross += q[lane][j].getCrossingTime();
                }

                double score = mode == Mode::Smart
    ? pcu + 5.0 * skippedPhases[lane]
    : pcu + 0.25 * cross;

if (starvation[lane] >= c.starvationThreshold) {
    score += 1e9 + starvation[lane];
}

                if (score > best) {
                    best = score;
                    chosen = lane;
                }
            }

            if (chosen < 0) {
                for (int lane = 0; lane < c.laneCount; ++lane) {
                    if (waiting(lane, clock)) {
                        chosen = lane;
                        break;
                    }
                }
            }
        }

        if (chosen < 0) {
            double next = c.horizon;

            for (int lane = 0; lane < c.laneCount; ++lane) {
                if (head[lane] < q[lane].size()) {
                    next = std::min(
                        next,
                        q[lane][head[lane]].getArrivalTime()
                    );
                }
            }

            clock = std::max(clock + 1e-6, next);
            continue;
        }

        const int green = greenFor(
            q[chosen],
            head[chosen],
            clock,
            c,
            mode
        );
if (mode == Mode::Smart) {
    r.greenPhases.push_back({
        chosen + 1,
        clock,
        std::min(clock + green, c.horizon)
    });
}

        const double phaseEnd = clock + green + c.yellow + c.allRed;
const double greenEnd = std::min(clock + green, c.horizon);

for (int cycle = 0; cycle < cycles; ++cycle) {
    const double cycleStart = cycle * interval;
    const double cycleEnd = (cycle + 1) * interval;

    const double overlap = std::max(
        0.0,
        std::min(greenEnd, cycleEnd) -
        std::max(clock, cycleStart)
    );

    r.greenTimeByLaneCycle[chosen][cycle] += overlap;
}
        double servingEnd = clock;

        while (
            head[chosen] < q[chosen].size() &&
            q[chosen][head[chosen]].getArrivalTime() <= servingEnd
        ) {
            const Vehicle& v = q[chosen][head[chosen]];

            if (servingEnd + v.getCrossingTime() > clock + green) {
                break;
            }

            const double departure = servingEnd + v.getCrossingTime();

            if (departure > c.horizon) {
                break;
            }

            const double wait = std::max(
                0.0,
                departure - v.getArrivalTime() - v.getCrossingTime()
            );
            serviceStartByVehicle[chosen][head[chosen]] = servingEnd;

            totalWaitSoFar += wait;
            cohortWait[bucket(v.getArrivalTime())] += wait;

            ++departedIn[bucket(departure)];
            ++r.throughput;

            servingEnd = departure;
            ++head[chosen];
        }

        const double redPhaseEnd = std::min(phaseEnd, c.horizon);
        const double selectedLaneRedStart = clock + green + c.yellow;

        for (int lane = 0; lane < c.laneCount; ++lane) {
            const double redStart = (lane == chosen)
                ? selectedLaneRedStart
                : clock;

            const double redEnd = redPhaseEnd;
            if (redEnd <= redStart) {
                continue;
            }

            for (size_t j = head[lane]; j < q[lane].size(); ++j) {
                const double arrival = q[lane][j].getArrivalTime();
                const double overlapStart = std::max(redStart, arrival);

                if (redEnd > overlapStart) {
                    redWaitByVehicle[lane][j] += redEnd - overlapStart;
                }
            }
        }

        for (int lane = 0; lane < c.laneCount; ++lane) {

    if (lane == chosen) {
        starvation[lane] = 0.0;
        skippedPhases[lane] = 0;
        continue;
    }

    if (waiting(lane, clock)) {
        skippedPhases[lane]++;
    }

    if (waiting(lane, phaseEnd)) {

        if (waiting(lane, clock)) {
            starvation[lane] += phaseEnd - clock;
        } else {
            double arrival = q[lane][head[lane]].getArrivalTime();
            starvation[lane] += phaseEnd - arrival;
        }

    } else {
        starvation[lane] = 0.0;
        skippedPhases[lane] = 0;
    }
}

        previous = chosen;
        clock = phaseEnd;
        ++r.phases;
    }

    double pending = 0;

    for (int lane = 0; lane < c.laneCount; ++lane) {
        for (size_t j = head[lane]; j < q[lane].size(); ++j) {
            double wait = std::max(
                0.0,
                c.horizon - q[lane][j].getArrivalTime()
            );

            pending += wait;
            cohortWait[bucket(q[lane][j].getArrivalTime())] += wait;
        }
    }

    r.totalWait = totalWaitSoFar + pending;
for (int cycle = 0; cycle < cycles; ++cycle) {

    const double sampleTime = std::min(
        c.horizon,
        (cycle + 1) * interval
    );

    for (int lane = 0; lane < c.laneCount; ++lane) {

        long queued = 0;

        for (size_t j = 0; j < q[lane].size(); ++j) {

            const double arrival = q[lane][j].getArrivalTime();
            const double serviceStart = serviceStartByVehicle[lane][j];

            if (
                arrival <= sampleTime &&
                (!std::isfinite(serviceStart) ||
                 serviceStart > sampleTime)
            ) {
                ++queued;
            }
        }

        r.queueLengthByLaneCycle[lane][cycle] = queued;
    }
}

    for (int lane = 0; lane < c.laneCount; ++lane) {
        for (size_t j = 0; j < q[lane].size(); ++j) {
            const int arrivalBucket = bucket(q[lane][j].getArrivalTime());
            redCohortWait[arrivalBucket] += redWaitByVehicle[lane][j];
        }
    }

    double cw = 0;
    long cc = 0;
    long passed = 0;

    for (int i = 0; i < cycles; ++i) {
        if (cohortCount[i] > 0) {
            r.cycleAvg[i] = cohortWait[i] / cohortCount[i];
            r.redCycleAvg[i] = redCohortWait[i] / cohortCount[i];
        }

        cw += cohortWait[i];
        cc += cohortCount[i];

        if (cc > 0) {
            r.cumulativeAvg[i] = cw / cc;
        }

        passed += departedIn[i];
        r.throughputHistory[i] = passed;
    }

    return r;
}

static void putNum(std::ostream& o, double x) {
    if (std::isfinite(x)) {
        o << x;
    } else {
        o << "N/A";
    }
}

int main() {
    Config c = readConfig("config.ini");
    int minutes = 0;

    std::cout << "Enter simulation duration in minutes: ";

    if (!(std::cin >> minutes) || minutes <= 0 || minutes > 240) {
        std::cerr << "Duration must be between 1 and 240 minutes.\n";
        return 1;
    }

    c.horizon = static_cast<double>(minutes) * 60.0;
    const int reportingBuckets = minutes;

    unsigned seed = c.seed ? c.seed : std::random_device{}();

    Traffic arrivals = generateTraffic(c, seed);

    Result fixed = runController(arrivals, c, reportingBuckets, Mode::Fixed);
    Result smart = runController(arrivals, c, reportingBuckets, Mode::Smart);
    Result scoot = runController(arrivals, c, reportingBuckets, Mode::Scoot);

    std::ofstream greenPhasesFile("smartflow_green_phases.csv");

if (!greenPhasesFile) {
    std::cerr << "Cannot create smartflow_green_phases.csv\n";
    return 1;
}

greenPhasesFile << "Lane,Start_Seconds,End_Seconds\n";
greenPhasesFile << std::fixed << std::setprecision(2);

for (const auto& phase : smart.greenPhases) {
    greenPhasesFile
        << phase.lane << ","
        << phase.start << ","
        << phase.end << "\n";
}

greenPhasesFile.close();

    std::ofstream density("density.csv");
    std::ofstream comparison("comparison.csv");
    std::ofstream report("report.txt");

    if (!density || !comparison || !report) {
        std::cerr << "Cannot write output files in the working folder.\n";
        return 1;
    }

    density << "Cycle";

    for (int i = 0; i < c.laneCount; ++i) {
        density << ",Lane" << i + 1 << "_PCU";
    }

    density << ",Winner\n";

    comparison
        << "Cycle,"
        << "Fixed_RedLight_Cycle_Average_Wait_Seconds,"
        << "SmartFlow_RedLight_Cycle_Average_Wait_Seconds,"
        << "SCOOT_RedLight_Cycle_Average_Wait_Seconds,"
        << "Fixed_Cycle_Average_Wait_Seconds,"
        << "SmartFlow_Cycle_Average_Wait_Seconds,"
        << "SCOOT_Cycle_Average_Wait_Seconds,"
        << "Fixed_Cumulative_Average_Wait_Seconds,"
        << "SmartFlow_Cumulative_Average_Wait_Seconds,"
        << "SCOOT_Cumulative_Average_Wait_Seconds,"
        << "Fixed_Throughput,"
        << "SmartFlow_Throughput,"
        << "SCOOT_Throughput,"
        << "Fixed_Green_Seconds";

for (int lane = 0; lane < c.laneCount; ++lane) {
    comparison
        << ",Fixed_Lane" << lane + 1 << "_Green_Seconds"
        << ",SmartFlow_Lane" << lane + 1 << "_Green_Seconds";
}

for (int lane = 0; lane < c.laneCount; ++lane) {
    comparison
        << ",Fixed_Lane" << lane + 1 << "_Queue_Length"
        << ",SmartFlow_Lane" << lane + 1 << "_Queue_Length";
}

comparison << '\n';

    comparison << std::fixed << std::setprecision(2);
    density << std::fixed << std::setprecision(2);

    const double interval = c.horizon / reportingBuckets;

    std::vector<std::vector<double>> pcuBy(
        c.laneCount,
        std::vector<double>(reportingBuckets, 0.0)
    );

    double generatedPCU = 0;
    long generatedVehicles = 0;

    for (int lane = 0; lane < c.laneCount; ++lane) {
        for (const auto& v : arrivals.lanes[lane]) {
            int b = std::min(
                reportingBuckets - 1,
                static_cast<int>(v.getArrivalTime() / interval)
            );

            pcuBy[lane][b] += v.getPCU();
            generatedPCU += v.getPCU();

            ++generatedVehicles;
        }
    }

    for (int i = 0; i < reportingBuckets; ++i) {
        density << i + 1;

        for (int lane = 0; lane < c.laneCount; ++lane) {
            density << ',' << pcuBy[lane][i];
        }

        density << ",N/A\n";

        comparison << i + 1;

        const double cols[9] = {
            fixed.redCycleAvg[i],
            smart.redCycleAvg[i],
            scoot.redCycleAvg[i],

            fixed.cycleAvg[i],
            smart.cycleAvg[i],
            scoot.cycleAvg[i],

            fixed.cumulativeAvg[i],
            smart.cumulativeAvg[i],
            scoot.cumulativeAvg[i]
        };

        for (double x : cols) {
            comparison << ',';
            putNum(comparison, x);
        }

        comparison
            << ',' << fixed.throughputHistory[i]
<< ',' << smart.throughputHistory[i]
<< ',' << scoot.throughputHistory[i]
<< ',' << c.fixedGreen;

for (int lane = 0; lane < c.laneCount; ++lane) {
    comparison
        << ',' << fixed.greenTimeByLaneCycle[lane][i]
        << ',' << smart.greenTimeByLaneCycle[lane][i];
}

for (int lane = 0; lane < c.laneCount; ++lane) {
    comparison
        << ',' << fixed.queueLengthByLaneCycle[lane][i]
        << ',' << smart.queueLengthByLaneCycle[lane][i];
}

comparison << '\n';
    }

    report
        << "SMARTFLOW TRAFFIC REPORT\n"
        << "PCU = Passenger Car Unit. All times are in seconds.\n"
        << "Cycle average and cumulative average are queue waiting time: arrival until crossing starts.\n"
        << "Red-light cycle average counts only time when the vehicle's signal is red; yellow is excluded.\n"
        << "Seed: " << seed
        << "\nReporting intervals (one per minute): " << reportingBuckets
        << "\nSimulation duration: " << c.horizon << " seconds\n\n"
        << "Generated vehicles: " << generatedVehicles
        << "\nGenerated total PCU: " << generatedPCU
        << "\n\nSummary\n"
        << "Fixed-time total wait seconds: " << fixed.totalWait
        << "\nSmartFlow total wait seconds: " << smart.totalWait
        << "\nSCOOT-inspired total wait seconds: " << scoot.totalWait
        << "\nFixed-time throughput: " << fixed.throughput
        << "\nSmartFlow throughput: " << smart.throughput
        << "\nSCOOT-inspired throughput: " << scoot.throughput
        << "\nGreen phases run (Fixed/SmartFlow/SCOOT): "
        << fixed.phases << "/"
        << smart.phases << "/"
        << scoot.phases << "\n";

    std::cout
        << "Completed " << minutes
        << " simulated minutes (" << c.horizon
        << " seconds). CSV and report files written.\n";

    return 0;
}