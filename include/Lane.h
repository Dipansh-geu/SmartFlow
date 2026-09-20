#ifndef LANE_H
#define LANE_H

#include <queue>
using namespace std;

class Lane
{
private:
    queue<int> vehicles;

public:
    void addVehicle(int id);
    void removeVehicle();
    int getVehicleCount();
};

#endif