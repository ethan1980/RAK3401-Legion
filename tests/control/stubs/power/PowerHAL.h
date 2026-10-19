#pragma once
extern bool flashSafe;
inline bool powerHAL_isPowerLevelSafe()
{
    return flashSafe;
}
