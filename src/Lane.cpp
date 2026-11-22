#include "../include/Lane.h"
#include <algorithm>

Lane::Lane(int id)
    : laneID(id), starvationTimeSeconds(0.0) {
}

void Lane::addVehicle(const Vehicle& v) {
    vehicles.push_back(v);
}

void Lane::removeVehicles() {
    vehicles.clear();
}

double Lane::getTotalPCU() const {
    double total = 0;

    for (const auto& v : vehicles) {
        total += v.getPCU();
    }

    return total;
}

int Lane::getTotalCrossingTime() const {
    int total = 0;

    for (const auto& v : vehicles) {
        total += v.getCrossingTime();
    }

    return total;
}

int Lane::getVehicleCount() const {
    return static_cast<int>(vehicles.size());
}

void Lane::increaseStarvation(double seconds) {
    if (!vehicles.empty() && seconds > 0) {
        starvationTimeSeconds += seconds;
    } else if (vehicles.empty()) {
        starvationTimeSeconds = 0;
    }
}

void Lane::resetStarvation() {
    starvationTimeSeconds = 0;
}

double Lane::getStarvationTime() const {
    return starvationTimeSeconds;
}

int Lane::getLaneID() const {
    return laneID;
}

const std::vector<Vehicle>& Lane::getVehicles() const {
    return vehicles;
}

int Lane::clearVehiclesWithin(
    int greenSeconds,
    double serviceTime,
    double& waitingTotal,
    int& throughput
) {
    int cleared = 0;
    double used = 0.0;

    while (!vehicles.empty()) {
        const Vehicle& v = vehicles.front();

        double crossing = static_cast<double>(v.getCrossingTime());

        if (used + crossing > greenSeconds) {
            break;
        }

        used += crossing;

        waitingTotal += std::max(
            0.0,
            serviceTime + used - crossing - v.getArrivalTime()
        );

        vehicles.erase(vehicles.begin());

        ++cleared;
        ++throughput;
    }

    return cleared;
}