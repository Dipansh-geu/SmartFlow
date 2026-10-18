#ifndef SIGNALCONTROLLER_H
#define SIGNALCONTROLLER_H

#include <vector>
#include "Lane.h"

class SignalController
{
public:
    int selectLane(std::vector<Lane>& lanes);
};

#endif
