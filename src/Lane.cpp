#include "../include/Lane.h"

void Lane::addVehicle(int id)
{
    vehicles.push(id);
}

void Lane::removeVehicle()
{
    if(!vehicles.empty())
        vehicles.pop();
}

int Lane::getVehicleCount()
{
    return vehicles.size();
}