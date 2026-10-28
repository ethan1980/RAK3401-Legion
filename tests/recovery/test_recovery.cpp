// Exercise RecoveryStore and legionParseBackup from the actual prepared firmware.
// A reset at any 32-bit flash-program boundary must leave a complete old or new generation,
// including deletion and restoration markers. This guards snapshot loss, resurrection after
// acknowledged deletion, malformed targeting, schema rollback and endless recovery retries.
#include "mesh/LegionRecoveryPolicy.h"
#include "mesh/LegionRecoveryRunner.h"
#include "mesh/LegionRecoveryStore.h"
#include <array>
#include <cassert>
#include <iostream>
#include <string>

using namespace legion;

struct Flash : RecoveryFlash {
    std::array<RecoveryPage, 2> pages;
    size_t cut = sizeof(RecoveryPage);
    bool unsafe = false;
    bool unreadable = false;
    unsigned writes = 0;
    Flash() { std::memset(pages.data(), 0xff, sizeof(pages)); }
    bool read(uint8_t slot, RecoveryPage &out) override
    {
        if (unreadable)
            return false;
        out = pages.at(slot);
        return true;
    }
    bool write(uint8_t slot, const RecoveryPage &page) override
    {
        if (unsafe)
            return false;
        ++writes;
        auto &destination = pages.at(slot);
        std::memset(&destination, 0xff, sizeof(destination));
        std::memcpy(&destination, &page, cut);
        return cut == sizeof(page);
    }
};

RecoveryPage armed()
{
    RecoveryPage page{};
    page.phase = RecoveryPhase::Armed;
    page.node = 0xa1b2c3d4;
    page.device[0] = 42;
    page.device[1] = 43;
    page.payloadSize = 1234;
    std::memset(page.payload, 0x53, page.payloadSize);
    return page;
}

void test_every_flash_word_preserves_a_complete_generation()
{
    Flash original;
    RecoveryStore store(original);
    auto page = armed();
    assert(store.commit(page));
    for (const auto phase : {RecoveryPhase::Armed, RecoveryPhase::Restoring, RecoveryPhase::NoticePending,
                             RecoveryPhase::NoticeSent, RecoveryPhase::Deleted}) {
        for (size_t cut = 0; cut <= sizeof(RecoveryPage); cut += 4) {
            Flash flash = original;
            RecoveryStore interrupted(flash);
            RecoveryPage before;
            assert(interrupted.load(before) == RecoveryRead::Valid);
            auto next = before;
            next.phase = phase;
            next.payload[17] ^= 1;
            if (phase == RecoveryPhase::Deleted) {
                next.payloadSize = 0;
                std::memset(next.payload, 0, sizeof(next.payload));
            }
            flash.cut = cut;
            const bool success = interrupted.commit(next);
            RecoveryStore reboot(flash);
            RecoveryPage recovered;
            assert(reboot.load(recovered) == RecoveryRead::Valid);
            assert(recovered.generation == 1 || recovered.generation == 2);
            assert(recovered.payloadSize == 0 || recovered.payload[17] == (recovered.generation == 1 ? 0x53 : 0x52));
            if (success)
                assert(recovered.phase == phase && recovered.generation == 2);
            else
                assert(recovered.generation == 1);
        }
    }
}

void test_first_snapshot_is_never_armed_partially()
{
    for (size_t cut = 0; cut < sizeof(RecoveryPage); cut += 4) {
        Flash flash;
        flash.cut = cut;
        RecoveryStore store(flash);
        auto page = armed();
        assert(!store.commit(page));
        RecoveryPage result;
        RecoveryStore reboot(flash);
        assert(reboot.load(result) == RecoveryRead::Empty);
        assert(reboot.hasStoredData() == (cut != 0));
    }
}

void test_unavailable_flash_is_not_an_absent_backup()
{
    Flash flash;
    RecoveryStore store(flash);
    RecoveryPage page;
    assert(store.load(page) == RecoveryRead::Empty && !store.hasStoredData());
    flash.unreadable = true;
    assert(store.load(page) == RecoveryRead::Unavailable);
    assert(flash.writes == 0);
}

void test_delete_survives_reboot_and_the_next_interrupted_create()
{
    Flash flash;
    RecoveryStore store(flash);
    auto page = armed();
    assert(store.commit(page));
    page.phase = RecoveryPhase::Deleted;
    page.payloadSize = 0;
    assert(store.commit(page));
    RecoveryStore reboot(flash);
    assert(reboot.load(page) == RecoveryRead::Valid && page.phase == RecoveryPhase::Deleted);
    auto next = armed();
    next.generation = page.generation;
    flash.cut = 60;
    assert(!reboot.commit(next));
    assert(reboot.load(page) == RecoveryRead::Valid && page.phase == RecoveryPhase::Deleted);
}

void test_unsafe_power_and_corrupt_new_page_keep_previous_snapshot()
{
    Flash flash;
    RecoveryStore store(flash);
    auto page = armed();
    assert(store.commit(page));
    flash.unsafe = true;
    assert(!store.commit(page) && flash.writes == 1);
    flash.unsafe = false;
    assert(store.commit(page));
    flash.pages[1].payload[8] ^= 1;
    assert(store.load(page) == RecoveryRead::Valid && page.generation == 1);
}

void test_newer_unsupported_schema_never_falls_back_to_old_snapshot()
{
    Flash flash;
    RecoveryStore store(flash);
    auto page = armed();
    assert(store.commit(page));
    assert(store.commit(page));
    flash.pages[1].schema++;
    flash.pages[1].crc = recoveryCrc(flash.pages[1]);
    assert(store.load(page) == RecoveryRead::Incompatible);
}

void test_persisted_retry_budget_and_generation_limits()
{
    Flash flash;
    RecoveryStore store(flash);
    auto page = armed();
    assert(store.commit(page));
    page.phase = RecoveryPhase::Restoring;
    for (uint32_t attempt = 1; attempt <= RECOVERY_MAX_ATTEMPTS; ++attempt) {
        page.restoreAttempts = attempt;
        assert(store.commit(page));
        RecoveryStore reboot(flash);
        assert(reboot.load(page) == RecoveryRead::Valid && page.restoreAttempts == attempt);
    }
    page.restoreAttempts++;
    assert(!store.commit(page));
    page.restoreAttempts = 0;
    page.generation = UINT32_MAX - 1;
    assert(!store.commit(page));
}

void test_only_the_exact_target_accepts_backup_operations()
{
    for (const auto &verb : {std::string(""), std::string("status "), std::string("replace "), std::string("delete ")}) {
        const std::string command = " /backup " + verb + "!A1B2C3D4\r\n";
        for (uint32_t node : {0xa1b2c3d4u, 0x11111111u, 0x22222222u, 0x33333333u}) {
            const auto parsed = legionParseBackup(reinterpret_cast<const uint8_t *>(command.data()), command.size(), node);
            assert((parsed != LegionBackupCommand::None) == (node == 0xa1b2c3d4u));
        }
    }
    for (const auto &text : {"/backup", "/backup status", "/backup !a1b2c3d", "/backup !a1b2c3d45", "/backup !a1b2c3dz",
                             "/backup !a1b2c3d4 extra", "/backupx !a1b2c3d4", "/backup erase !a1b2c3d4"})
        assert(legionParseBackup(reinterpret_cast<const uint8_t *>(text), std::strlen(text), 0xa1b2c3d4) ==
               LegionBackupCommand::None);
    assert(legionParseBackup(nullptr, 8, 42) == LegionBackupCommand::None);
}

void test_normal_boot_and_temporary_or_unsupported_files_never_restore()
{
    for (const auto result : {PreferenceRead::Valid, PreferenceRead::Temporary, PreferenceRead::Unsupported}) {
        Flash flash;
        RecoveryStore store(flash);
        auto page = armed();
        assert(store.commit(page));
        bool restored = false;
        auto outcome = runRecovery(
            store, page, [&]() { return result; },
            [&]() {
                restored = true;
                return true;
            },
            []() {});
        assert(!restored && flash.writes == 1);
        assert(outcome == (result == PreferenceRead::Valid ? LegionBootRecovery::None : LegionBootRecovery::Blocked));
    }
}

void test_inconsistent_loss_evidence_does_not_overwrite_preferences()
{
    Flash flash;
    RecoveryStore store(flash);
    auto page = armed();
    assert(store.commit(page));
    unsigned reads = 0;
    auto outcome = runRecovery(
        store, page, [&]() { return reads++ ? PreferenceRead::Valid : PreferenceRead::Corrupt; },
        []() {
            assert(false);
            return false;
        },
        []() {});
    assert(outcome == LegionBootRecovery::Blocked && flash.writes == 1);
}

void test_cut_after_each_preference_segment_resumes_one_transaction()
{
    for (unsigned cut = 0; cut <= 4; ++cut) {
        Flash flash;
        RecoveryStore store(flash);
        auto page = armed();
        assert(store.commit(page));
        unsigned files = 0;
        auto outcome = runRecovery(
            store, page, []() { return PreferenceRead::Missing; },
            [&]() {
                files = cut;
                return false;
            },
            []() {});
        assert(outcome == LegionBootRecovery::Blocked);
        RecoveryStore reboot(flash);
        assert(reboot.load(page) == RecoveryRead::Valid && page.phase == RecoveryPhase::Restoring);
        // Four valid files are still incomplete until fixed position and the transaction commit land.
        outcome = runRecovery(
            reboot, page, [&]() { return files == 4 ? PreferenceRead::Valid : PreferenceRead::Missing; },
            [&]() {
                files = 4;
                return true;
            },
            []() {});
        assert(outcome == LegionBootRecovery::Restored && page.restoreAttempts == 2);
        page.phase = RecoveryPhase::NoticePending;
        assert(reboot.commit(page));
        RecoveryStore finished(flash);
        assert(finished.load(page) == RecoveryRead::Valid);
        assert(runRecovery(
                   finished, page, []() { return PreferenceRead::Valid; },
                   []() {
                       assert(false);
                       return false;
                   },
                   []() {}) == LegionBootRecovery::None);
    }
}

void test_failed_restore_budget_is_persistent_and_bounded()
{
    Flash flash;
    auto page = armed();
    RecoveryStore initial(flash);
    assert(initial.commit(page));
    unsigned restores = 0;
    for (unsigned boot = 0; boot < 10; ++boot) {
        RecoveryStore store(flash);
        assert(store.load(page) == RecoveryRead::Valid);
        assert(runRecovery(
                   store, page, []() { return PreferenceRead::Corrupt; },
                   [&]() {
                       ++restores;
                       return false;
                   },
                   []() {}) == LegionBootRecovery::Blocked);
    }
    assert(restores == RECOVERY_MAX_ATTEMPTS && flash.writes == 1 + RECOVERY_MAX_ATTEMPTS);
}

int main()
{
    test_unavailable_flash_is_not_an_absent_backup();
    test_every_flash_word_preserves_a_complete_generation();
    test_first_snapshot_is_never_armed_partially();
    test_delete_survives_reboot_and_the_next_interrupted_create();
    test_unsafe_power_and_corrupt_new_page_keep_previous_snapshot();
    test_newer_unsupported_schema_never_falls_back_to_old_snapshot();
    test_persisted_retry_budget_and_generation_limits();
    test_only_the_exact_target_accepts_backup_operations();
    test_normal_boot_and_temporary_or_unsupported_files_never_restore();
    test_inconsistent_loss_evidence_does_not_overwrite_preferences();
    test_cut_after_each_preference_segment_resumes_one_transaction();
    test_failed_restore_budget_is_persistent_and_bounded();
    std::cout << "Recovery journal: every flash-word interruption boundary and restore policy checks passed\n";
}
