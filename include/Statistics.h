#ifndef STATISTICS_H
#define STATISTICS_H

#include <vector>
#include <fstream>

#include "Lane.h"

class Statistics
{
private:
    std::ofstream report;

    int fixedWaitingTime;
    int smartWaitingTime;

public:

    Statistics();

    ~Statistics();

    void logSimulation(
        int simulationNo,
        std::vector<Lane>& lanes,
        int selectedLane
    );

    void addFixed(int value);

    void addSmart(int value);

    void saveComparisonCSV(
        int simulationNo,
        int fixedTime,
        int smartTime
    );

    void saveDensityCSV(
        int simulationNo,
        std::vector<Lane>& lanes,
        int winner
    );

    void printReport(int simulations);
};

#endif