// The real LegionDcdc.cpp must enable REG1 once through the SoftDevice API after startup.
// A missing SoftDevice or failed API/readback must not loop, reset, or touch REG0.
// Register values and SVC execution are stubbed here; compiled SVC identity is checked separately.
#include "platform/nrf52/LegionDcdc.h"
#include <cassert>
#include <cstring>
#include <iostream>
FakePower power;
uint32_t queryResult = 0, setResult = 0, setCalls = 0, setArgument = 0;
uint8_t sdEnabled = 1;
bool readbackFails = false;
int main(int argc, char **argv)
{
    assert(argc == 2);
    const bool queryFails = !std::strcmp(argv[1], "query_failure");
    const bool disabled = !std::strcmp(argv[1], "disabled");
    const bool setFails = !std::strcmp(argv[1], "api_failure");
    readbackFails = !std::strcmp(argv[1], "readback_failure");
    if (queryFails)
        queryResult = 17;
    if (disabled)
        sdEnabled = 0;
    if (setFails)
        setResult = 18;
    power.DCDCEN0 = 73;
    legionEnableDcdcReg1();
    legionEnableDcdcReg1();
    assert(setCalls == (queryFails || disabled ? 0u : 1u));
    assert(power.DCDCEN0 == 73);
    if (setCalls)
        assert(setArgument == 1);
    assert(power.DCDCEN == (queryFails || disabled || setFails || readbackFails ? 0u : 1u));
    std::cout << "REG1 " << argv[1] << " passed\n";
}
