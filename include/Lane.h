#ifndef LANE_H
#define LANE_H

#include <vector>
#include "Vehicle.h"

class Lane
{
private:
    int laneID;
    std::vector<Vehicle> vehicles;
    int starvationCount;

public:
    Lane(int id);

    void addVehicle(Vehicle v);

    void removeVehicles();

    int getDensityScore();

    int getTotalCrossingTime();

    int getVehicleCount();

    void increaseStarvation();

    void resetStarvation();

    int getStarvationCount();

    int getLaneID();
};

#endif