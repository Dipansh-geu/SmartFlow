#ifndef VEHICLE_H
#define VEHICLE_H

#include <string>

class Vehicle {
private:
    std::string type;
    double pcu;
    int crossingTime;
    double arrivalTime;

public:
    Vehicle(
        const std::string& type,
        double pcu,
        int crossingTime,
        double arrivalTime = 0.0
    );

    double getPCU() const;
    int getCrossingTime() const;

    const std::string& getType() const;
    double getArrivalTime() const;
};

#endif
