#ifndef VEHICLE_H
#define VEHICLE_H

#include <string>

class Vehicle
{
private:
    std::string type;
    int weight;
    int crossingTime;

public:
    Vehicle(std::string type,int weight,int crossingTime);

    int getWeight();
    int getCrossingTime();
    std::string getType();
};

#endif
