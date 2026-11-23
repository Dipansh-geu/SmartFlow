#include "../include/Vehicle.h"

Vehicle::Vehicle(
    const std::string& type,
    double pcu,
    int crossingTime,
    double arrivalTime
)
    : type(type),
      pcu(pcu),
      crossingTime(crossingTime),
      arrivalTime(arrivalTime)
{
}

double Vehicle::getPCU() const
{
    return pcu;
}

int Vehicle::getCrossingTime() const
{
    return crossingTime;
}

const std::string& Vehicle::getType() const
{
    return type;
}

double Vehicle::getArrivalTime() const
{
    return arrivalTime;
}
