#include <iostream>
#include <vector>
#include <cstdlib>
#include <ctime>

#include "../include/Vehicle.h"
#include "../include/Lane.h"
#include "../include/SignalController.h"
#include "../include/Statistics.h"

using namespace std;

Vehicle randomVehicle()
{
    int x = rand() % 4;

    if(x == 0)
        return Vehicle("Bike",1,1);

    if(x == 1)
        return Vehicle("Car",3,2);

    if(x == 2)
        return Vehicle("Bus",6,4);

    return Vehicle("Truck",8,5);
}

int main()
{
    srand(time(0));

    int simulations;

    cout<<"Enter number of simulations: ";
    cin>>simulations;

    Statistics stats;

    Lane lane1(1);
    Lane lane2(2);
    Lane lane3(3);
    Lane lane4(4);

    vector<Lane> lanes =
    {
        lane1,
        lane2,
        lane3,
        lane4
    };


    for(int i=0;i<4;i++)
    {
        int vehicleCount =
        rand()%10 + 1;

        for(int j=0;j<vehicleCount;j++)
        {
            lanes[i].addVehicle(
                randomVehicle()
            );
        }
    }

    SignalController controller;

    for(int sim=1;sim<=simulations;sim++)
    {
        int winner =
        controller.selectLane(lanes);

        int smartTime =
        lanes[winner].getTotalCrossingTime() + 2;

        int fixedTime =
        lanes[winner].getVehicleCount() * 5;

        stats.logSimulation(
            sim,
            lanes,
            winner
        );

        stats.saveDensityCSV(
        sim,
        lanes,
        winner
        );

        stats.addFixed(fixedTime);
        stats.addSmart(smartTime);

        stats.saveComparisonCSV(
            sim,
            fixedTime,
            smartTime
        );

        cout
        << "\nSimulation "
        << sim
        << endl;

        cout
        << "Selected Lane : "
        << lanes[winner].getLaneID()
        << endl;

        lanes[winner].removeVehicles();

        for(int i=0;i<lanes.size();i++)
        {
            if(i==winner)
                lanes[i].resetStarvation();
            else
                lanes[i].increaseStarvation();
        }

        for(int i=0;i<4;i++)
        {
            int arrivals =
            rand()%5 + 1;

            for(int j=0;j<arrivals;j++)
            {
                lanes[i].addVehicle(
                    randomVehicle()
                );
            }
        }
    }

    stats.printReport(simulations);

    cout
    << "\nSimulation Complete"
    << endl;

    return 0;
}