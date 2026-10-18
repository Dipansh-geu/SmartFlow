#include "../include/SignalController.h"

int SignalController::selectLane(std::vector<Lane>& lanes)
{
    int bestLane=0;
    int bestScore=-1;

    for(int i=0;i<lanes.size();i++)
    {
        int score=
        lanes[i].getDensityScore()
        +
        lanes[i].getStarvationCount()*5;

        if(score>bestScore)
        {
            bestScore=score;
            bestLane=i;
        }
    }

    return bestLane;
}
