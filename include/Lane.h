#ifndef LANE_H
#define LANE_H

#include <vector>
#include "Vehicle.h"

class Lane {
private:
    int laneID;
    std::vector<Vehicle> vehicles;
    double starvationTimeSeconds;

public:
    explicit Lane(int id);

    void addVehicle(const Vehicle& v);
    void removeVehicles();

    double getTotalPCU() const;
    int getTotalCrossingTime() const;
    int getVehicleCount() const;

    void increaseStarvation(double elapsedSeconds);
    void resetStarvation();
    double getStarvationTime() const;

    int getLaneID() const;
    const std::vector<Vehicle>& getVehicles() const;

    int clearVehiclesWithin(
        int greenSeconds,
        double serviceTime,
        double& waitingTotal,
        int& throughput
    );
};

#endif