#pragma once
#include <cstdint>
void flash_nrf5x_flush();
int flash_nrf5x_write(uint32_t address, const void *source, uint32_t size);
