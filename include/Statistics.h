#ifndef STATISTICS_H
#define STATISTICS_H

#include <fstream>
#include <vector>
#include "Lane.h"

class Statistics {
private:
    std::ofstream report;
    double fixedGreenSecondsTotal;
    double smartGreenSecondsTotal;

public:
    Statistics();
    ~Statistics();

    void logSimulation(
        int simulationNo,
        const std::vector<Lane>& lanes,
        int selectedLane,
        int smartGreenSeconds
    );

    void addFixed(double seconds);
    void addSmart(double seconds);

    void saveComparisonCSV(
        int simulationNo,
        double fixedSeconds,
        double smartSeconds
    );

    void saveDensityCSV(
        int simulationNo,
        const std::vector<Lane>& lanes,
        int winner
    );

    void printReport(int completedSimulations);
};

#endif
