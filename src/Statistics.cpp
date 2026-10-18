#include "../include/Statistics.h"

#include <string>

#include <iostream>

using namespace std;

Statistics::Statistics()
{
    fixedWaitingTime = 0;
    smartWaitingTime = 0;

    report.open("report.txt");

    report
    << "=====================================\n";

    report
    << "SMARTFLOW TRAFFIC REPORT\n";

    report
    << "=====================================\n\n";
}

Statistics::~Statistics()
{
    report.close();
}

void Statistics::addFixed(int value)
{
    fixedWaitingTime += value;
}

void Statistics::addSmart(int value)
{
    smartWaitingTime += value;
}

void Statistics::logSimulation(
    int simulationNo,
    vector<Lane>& lanes,
    int selectedLane
)
{
    report
    << "\n=====================================\n";

    report
    << "Simulation "
    << simulationNo
    << "\n";

    report
    << "=====================================\n";

    for(auto &lane : lanes)
    {
        report
        << "\nLane "
        << lane.getLaneID()
        << "\n";

        report
        << "Vehicles : "
        << lane.getVehicleCount()
        << "\n";

        report
        << "Density Score : "
        << lane.getDensityScore()
        << "\n";

        report
        << "Crossing Time : "
        << lane.getTotalCrossingTime()
        << "\n";

        report
        << "Starvation Count : "
        << lane.getStarvationCount()
        << "\n";
    }

    report
    << "\nSelected Lane : "
    << lanes[selectedLane].getLaneID()
    << "\n";

    report
    << "Reason : Highest Priority Score\n";
}

void Statistics::printReport(int simulations)
{
    double improvement =
    (
        (fixedWaitingTime - smartWaitingTime)
        * 100.0
        /
        fixedWaitingTime
    );

    cout
    << "\n===== FINAL REPORT =====\n";

    cout
    << "Simulations : "
    << simulations
    << endl;

    cout
    << "Average Fixed Waiting Time : "
    << fixedWaitingTime / simulations
    << endl;

    cout
    << "Average Smart Waiting Time : "
    << smartWaitingTime / simulations
    << endl;

    cout
    << "Improvement : "
    << improvement
    << "%"
    << endl;

    report
    << "\n\n=====================================\n";

    report
    << "FINAL ANALYSIS\n";

    report
    << "=====================================\n";

    report
    << "Simulations : "
    << simulations
    << "\n";

    report
    << "Average Fixed Waiting Time : "
    << fixedWaitingTime / simulations
    << "\n";

    report
    << "Average Smart Waiting Time : "
    << smartWaitingTime / simulations
    << "\n";

    report
    << "Improvement : "
    << improvement
    << "%\n";
}

void Statistics::saveComparisonCSV(
    int simulationNo,
    int fixedTime,
    int smartTime
)
{
    ofstream file;

    if(simulationNo == 1)
    {
        file.open("comparison.csv");

        file
        << "Simulation,"
        << "Fixed,"
        << "SmartFlow\n";
    }
    else
    {
        file.open(
            "comparison.csv",
            ios::app
        );
    }

    file
    << simulationNo
    << ","
    << fixedTime
    << ","
    << smartTime
    << "\n";

    file.close();
}
void Statistics::saveDensityCSV(
    int simulationNo,
    std::vector<Lane>& lanes,
    int winner
)
{
    ofstream file;

    if(simulationNo == 1)
    {
        file.open("density.csv");

        file
        << "Simulation,"
        << "Lane1,"
        << "Lane2,"
        << "Lane3,"
        << "Lane4,"
        << "Winner\n";
    }
    else
    {
        file.open(
            "density.csv",
            ios::app
        );
    }

    file
    << simulationNo << ","
    << lanes[0].getDensityScore() << ","
    << lanes[1].getDensityScore() << ","
    << lanes[2].getDensityScore() << ","
    << lanes[3].getDensityScore() << ","
    << lanes[winner].getLaneID()
    << "\n";

    file.close();
}