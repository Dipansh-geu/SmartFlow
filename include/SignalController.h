#ifndef SIGNALCONTROLLER_H
#define SIGNALCONTROLLER_H

#include <vector>
#include "Lane.h"

class SignalController {
public:
    explicit SignalController(double starvationThreshold = 180.0);

    int selectLane(
        const std::vector<Lane>& lanes,
        int previousLane
    ) const;

private:
    double starvationThresholdSeconds;
};

#endif
