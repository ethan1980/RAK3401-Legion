#pragma once
extern bool powerSafe;
inline bool powerHAL_isPowerLevelSafe() { return powerSafe; }
