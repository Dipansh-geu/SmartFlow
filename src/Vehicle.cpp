#include "../include/Vehicle.h"

Vehicle::Vehicle(int time)
{
    arrivalTime = time;
}

int Vehicle::getArrivalTime()
{
    return arrivalTime;
}
