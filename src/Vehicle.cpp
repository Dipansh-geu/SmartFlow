#include "../include/Vehicle.h"

Vehicle::Vehicle(std::string type,int weight,int crossingTime)
{
    this->type=type;
    this->weight=weight;
    this->crossingTime=crossingTime;
}

int Vehicle::getWeight()
{
    return weight;
}

int Vehicle::getCrossingTime()
{
    return crossingTime;
}

std::string Vehicle::getType()
{
    return type;
}
