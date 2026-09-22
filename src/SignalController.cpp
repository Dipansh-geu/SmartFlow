#include "../include/SignalController.h"

int SignalController::getGreenSignal(int north, int south, int east, int west)
{
    int maxLane = north;

    if(south > maxLane)
        maxLane = south;

    if(east > maxLane)
        maxLane = east;

    if(west > maxLane)
        maxLane = west;

    return maxLane;
}