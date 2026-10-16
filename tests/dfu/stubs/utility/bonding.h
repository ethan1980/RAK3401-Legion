#pragma once
#include <bluefruit.h>
struct bond_keys_t {
    ble_gap_enc_key_t own_enc;
    struct {
        ble_gap_addr_t id_addr_info;
        ble_gap_irk_t id_info;
    } peer_id;
};
bool bond_load_keys(uint8_t, ble_gap_addr_t *, bond_keys_t *);
