#pragma once
class AdminModule
{
  public:
    bool editing = false;
    bool isEditingSettings() const { return editing; }
};
extern AdminModule *adminModule;
