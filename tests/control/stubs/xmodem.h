#pragma once
struct XModem {
    bool busy = false;
    bool isBusy() const { return busy; }
};
extern XModem xModem;
