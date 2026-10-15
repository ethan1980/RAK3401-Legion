#pragma once
#include "configuration.h"
class NodeDB
{
  public:
    uint32_t getNodeNum() const { return ownNode; }
};
extern NodeDB *nodeDB;
