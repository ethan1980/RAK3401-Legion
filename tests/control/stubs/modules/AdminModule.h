#pragma once
struct AdminModule {
    bool editing = false;
    bool isEditingSettings() const { return editing; }
};
extern AdminModule *adminModule;
