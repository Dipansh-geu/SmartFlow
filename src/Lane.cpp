#include "../include/Lane.h"

Lane::Lane(int id)
{
    laneID=id;
    starvationCount=0;
}

void Lane::addVehicle(Vehicle v)
{
    vehicles.push_back(v);
}

void Lane::removeVehicles()
{
    vehicles.clear();
}

int Lane::getDensityScore()
{
    int score=0;

    for(auto &v:vehicles)
        score+=v.getWeight();

    return score;
}

int Lane::getTotalCrossingTime()
{
    int total=0;

    for(auto &v:vehicles)
        total+=v.getCrossingTime();

    return total;
}

int Lane::getVehicleCount()
{
    return vehicles.size();
}

void Lane::increaseStarvation()
{
    starvationCount++;
}

void Lane::resetStarvation()
{
    starvationCount=0;
}

int Lane::getStarvationCount()
{
    return starvationCount;
}

int Lane::getLaneID()
{
    return laneID;
}