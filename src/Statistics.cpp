#include "../include/Statistics.h"
#include <iomanip>
#include <iostream>

Statistics::Statistics()
    : fixedGreenSecondsTotal(0.0),
      smartGreenSecondsTotal(0.0)
{
    report.open("report.txt");

    report << "=====================================\n"
           << "SMARTFLOW TRAFFIC REPORT\n"
           << "=====================================\n\n"
           << "PCU = Passenger Car Unit. Green durations are recorded in seconds.\n";
}

Statistics::~Statistics()
{
    if (report.is_open())
    {
        report.close();
    }
}

void Statistics::addFixed(double seconds)
{
    fixedGreenSecondsTotal += seconds;
}

void Statistics::addSmart(double seconds)
{
    smartGreenSecondsTotal += seconds;
}

void Statistics::logSimulation(
    int simulationNo,
    const std::vector<Lane>& lanes,
    int selectedLane,
    int smartGreenSeconds
)
{
    report << "\n=====================================\nSimulation "
           << simulationNo << "\n=====================================\n";

    for (const auto& lane : lanes)
    {
        report << "\nLane " << lane.getLaneID() << "\n"
               << "Vehicles : " << lane.getVehicleCount() << "\n"
               << "Traffic Demand : " << lane.getTotalPCU() << " PCU\n"
               << "Total Crossing Time : " << lane.getTotalCrossingTime() << " seconds\n"
               << "Starvation Time : " << lane.getStarvationTime() << " seconds\n";
    }

    report << "\nSelected Lane : " << lanes[selectedLane].getLaneID() << "\n"
           << "Green Duration : " << smartGreenSeconds << " seconds\n"
           << "Selection Rule : Starvation override (if triggered), otherwise highest PCU; no consecutive lane when alternatives exist.\n";
}

void Statistics::saveComparisonCSV(
    int simulationNo,
    double fixedSeconds,
    double smartSeconds
)
{
    std::ofstream file(
        simulationNo == 1 ? "comparison.csv" : "comparison.csv",
        simulationNo == 1 ? std::ios::out : std::ios::app
    );

    if (simulationNo == 1)
    {
        file << "Simulation,Fixed,SmartFlow\n";
    }

    file << simulationNo << ','
         << fixedSeconds << ','
         << smartSeconds << '\n';
}

void Statistics::saveDensityCSV(
    int simulationNo,
    const std::vector<Lane>& lanes,
    int winner
)
{
    std::ofstream file(
        simulationNo == 1 ? "density.csv" : "density.csv",
        simulationNo == 1 ? std::ios::out : std::ios::app
    );

    if (simulationNo == 1)
    {
        file << "Simulation,Lane1_PCU,Lane2_PCU,Lane3_PCU,Lane4_PCU,Winner\n";
    }

    file << simulationNo << ','
         << lanes[0].getTotalPCU() << ','
         << lanes[1].getTotalPCU() << ','
         << lanes[2].getTotalPCU() << ','
         << lanes[3].getTotalPCU() << ','
         << lanes[winner].getLaneID() << '\n';
}

void Statistics::printReport(int completedSimulations)
{
    if (completedSimulations <= 0)
    {
        std::cout << "No simulations were completed.\n";
        report << "\nNo simulations were completed.\n";
        return;
    }

    const double fixedAverage =
        fixedGreenSecondsTotal / completedSimulations;

    const double smartAverage =
        smart
