#include "../include/SignalController.h"
#include <algorithm>

SignalController::SignalController(double threshold)
    : starvationThresholdSeconds(threshold) {
}

int SignalController::selectLane(
    const std::vector<Lane>& lanes,
    int previousLane
) const {
    int selected = -1;
    double oldest = -1.0;
    double highestScore = -1.0;

    for (int i = 0; i < static_cast<int>(lanes.size()); ++i) {
        if (lanes[i].getVehicleCount() == 0 || i == previousLane) {
            continue;
        }

        if (
            lanes[i].getStarvationTime() >= starvationThresholdSeconds &&
            lanes[i].getStarvationTime() > oldest
        ) {
            selected = i;
            oldest = lanes[i].getStarvationTime();
        }
    }

    if (selected >= 0) {
        return selected;
    }

    for (int i = 0; i < static_cast<int>(lanes.size()); ++i) {
        if (lanes[i].getVehicleCount() == 0 || i == previousLane) {
            continue;
        }

        double score = lanes[i].getTotalPCU()
                     + 5.0 * lanes[i].getStarvationTime();

        if (score > highestScore) {
            highestScore = score;
            selected = i;
        }
    }

    if (selected >= 0) {
        return selected;
    }

    for (int i = 0; i < static_cast<int>(lanes.size()); ++i) {
        if (lanes[i].getVehicleCount() > 0) {
            return i;
        }
    }

    return -1;
}
