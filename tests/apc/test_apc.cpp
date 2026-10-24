// Exercise ApcController/ApcObserver from the prepared firmware, with clocked voltage
// traces and independent airtime limits. These checks guard transient-driven state
// changes, stale measurements suppressing relays, shadow mode mutating traffic,
// unbounded token accumulation, and rollover breaking persistence or recovery.
#include "modules/LegionApcController.h"
#include "modules/LegionApcPolicy.h"
#include <cassert>
#include <iostream>

using namespace legion;

uint32_t advance(ApcController &controller, uint32_t &now, uint32_t duration, uint16_t battery, bool usb = false,
                 uint32_t generation = 7)
{
    for (uint32_t elapsed = 0; elapsed < duration; elapsed += 5000) {
        now += 5000;
        controller.sample(now, battery, 3300, usb, generation);
    }
    return now;
}
void enter(ApcController &controller, uint32_t &now, ApcMode mode, uint16_t battery, ApcState state)
{
    controller.setMode(mode, 7);
    controller.sample(now, battery, 3300, false, 7);
    advance(controller, now, 30 * 60000, battery);
    assert(controller.copy(now).state == state && controller.copy(now).hold == ApcHold::None);
}

void test_filter_persistence_and_hysteresis()
{
    ApcController controller;
    uint32_t now = 0;
    assert(controller.copy(now).mode == ApcMode::Off);
    controller.setMode(ApcMode::Shadow, 7);
    controller.sample(now, 3851, 3300, false, 7);
    assert(controller.copy(now).hold == ApcHold::Warmup);
    advance(controller, now, 3600000, 3851);
    controller.sample(now += 5000, 2979, 3300, false, 7);
    advance(controller, now, 3600000, 3851);
    assert(controller.copy(now).state == ApcState::Normal);
    advance(controller, now, 600000, 3790);
    assert(controller.copy(now).state == ApcState::Normal);
    advance(controller, now, 600000, 3790);
    assert(controller.copy(now).state == ApcState::Conserve);
    advance(controller, now, 1200000, 3860);
    assert(controller.copy(now).state == ApcState::Conserve);
    advance(controller, now, 1200000, 3920);
    assert(controller.copy(now).state == ApcState::Normal);
    advance(controller, now, 600000, 3620);
    assert(controller.copy(now).state == ApcState::Reserve);
    advance(controller, now, 1200000, 3700);
    assert(controller.copy(now).state == ApcState::Reserve);
    advance(controller, now, 1200000, 3770);
    assert(controller.copy(now).state == ApcState::Conserve);
    advance(controller, now, 1200000, 3920);
    assert(controller.copy(now).state == ApcState::Normal);
}

void test_sustained_battery_during_warmup_is_not_immediate_conservation()
{
    ApcController controller;
    uint32_t now = 0;
    controller.setMode(ApcMode::On, 7);
    controller.sample(now, 3600, 3300, false, 7);
    advance(controller, now, APC_WARMUP_MS - 5000, 3600);
    assert(controller.copy(now).state == ApcState::Normal && controller.copy(now).hold == ApcHold::Warmup);
    advance(controller, now, 5000, 3600);
    assert(controller.copy(now).state == ApcState::Normal && controller.copy(now).requiredSec == 300);
    advance(controller, now, APC_RESERVE_MS - 5000, 3600);
    assert(controller.copy(now).state == ApcState::Normal);
    advance(controller, now, 5000, 3600);
    assert(controller.copy(now).state == ApcState::Reserve);
}

void test_shadow_budget_matches_active_without_suppression()
{
    for (const auto voltage : {uint16_t(3700), uint16_t(3600)}) {
        ApcController shadow, active;
        uint32_t shadowNow = 0, activeNow = 0;
        const auto state = voltage == 3700 ? ApcState::Conserve : ApcState::Reserve;
        enter(shadow, shadowNow, ApcMode::Shadow, voltage, state);
        enter(active, activeNow, ApcMode::On, voltage, state);
        unsigned admitted = 0;
        for (unsigned i = 0; i < 120; ++i) {
            advance(shadow, shadowNow, 5000, voltage);
            advance(active, activeNow, 5000, voltage);
            assert(shadow.allowRelay(shadowNow, 7, true, true, 300));
            admitted += active.allowRelay(activeNow, 7, true, true, 300);
        }
        const auto s = shadow.copy(shadowNow), a = active.copy(activeNow);
        assert(s.eligible == 120 && a.eligible == 120 && s.wouldSkip == a.wouldSkip && s.wouldSkip > 0);
        assert(s.skipped == 0 && a.skipped == a.wouldSkip && a.skipped + admitted == 120);
        assert(a.skippedMs == uint64_t(a.skipped) * 300 && s.wouldSkipMs == a.skippedMs);
        const auto budget = state == ApcState::Conserve ? APC_CONSERVE_BUDGET_MS : APC_RESERVE_BUDGET_MS;
        assert(admitted * 300 <= 10 * budget + APC_BURST_MS);
        for (unsigned i = 0; i < 100; ++i)
            assert(active.allowRelay(activeNow, 7, true, false, 300));
        assert(active.allowRelay(activeNow, 7, true, true, APC_BURST_MS + 1));
        assert(active.allowRelay(activeNow, 7, true, true, 0));
        assert(active.copy(activeNow).protectedRelays == 102);
    }
}

void test_stale_invalid_usb_and_context_fail_open()
{
    ApcController controller;
    uint32_t now = 0;
    enter(controller, now, ApcMode::On, 3600, ApcState::Reserve);
    assert(controller.allowRelay(now, 7, false, true, 300));
    now += APC_SAMPLE_MAX_MS + 1;
    assert(controller.copy(now).hold == ApcHold::Sample && controller.allowRelay(now, 7, true, true, 300));
    controller.sample(now, 3600, 3300, false, 7);
    assert(controller.copy(now).hold == ApcHold::Warmup && controller.copy(now).state == ApcState::Normal);
    advance(controller, now, 600000, 3600);
    assert(controller.copy(now).state == ApcState::Reserve);
    controller.sample(now += 5000, 3600, 2999, false, 7);
    assert(controller.copy(now).hold == ApcHold::Sample && controller.allowRelay(now, 7, true, true, 300));
    advance(controller, now, 1200000, 3600);
    controller.sample(now += 5000, 3600, 3300, true, 7);
    assert(controller.copy(now).hold == ApcHold::Usb && controller.copy(now).state == ApcState::Normal);
    advance(controller, now, 3600000, 3600, true);
    assert(controller.allowRelay(now, 7, true, true, 300));
    controller.sample(now += 5000, 3600, 3300, false, 7);
    assert(controller.copy(now).hold == ApcHold::Warmup);
    advance(controller, now, 1200000, 3600);
    assert(controller.copy(now).state == ApcState::Reserve);
    assert(controller.allowRelay(now, 8, true, true, 300));
    assert(controller.copy(now).mode == ApcMode::Off);
}

void test_idempotency_mode_changes_and_rollover()
{
    ApcController controller;
    uint32_t now = UINT32_MAX - 100000;
    enter(controller, now, ApcMode::Shadow, 3700, ApcState::Conserve);
    const auto filtered = controller.copy(now).filtered;
    assert(!controller.setMode(ApcMode::Shadow, 7) && controller.copy(now).filtered == filtered);
    assert(controller.setMode(ApcMode::On, 7));
    assert(controller.copy(now).hold == ApcHold::Sample && controller.allowRelay(now, 7, true, true, 300));
    advance(controller, now, 1800000, 3700);
    assert(controller.copy(now).state == ApcState::Conserve);
    controller.disarm();
    assert(controller.copy(now).mode == ApcMode::Off && controller.allowRelay(now, 7, true, true, 300));
    controller.setMode(ApcMode::Observe, 7);
    advance(controller, now, 3600000, 3600);
    assert(controller.copy(now).hold == ApcHold::Observe && controller.copy(now).state == ApcState::Normal);
    assert(controller.allowRelay(now, 7, true, true, 300));
}

void test_bucket_credit_cap_and_refill_rollover()
{
    ApcController controller;
    uint32_t now = UINT32_MAX - 1900000;
    enter(controller, now, ApcMode::On, 3700, ApcState::Conserve);
    unsigned admitted = 0;
    for (unsigned i = 0; i < 120; ++i) {
        advance(controller, now, 5000, 3700);
        admitted += controller.allowRelay(now, 7, true, true, 300);
    }
    assert(admitted * 300 <= 10 * APC_CONSERVE_BUDGET_MS + APC_BURST_MS);
    advance(controller, now, 3600000, 3700);
    admitted = 0;
    for (unsigned i = 0; i < 100; ++i)
        admitted += controller.allowRelay(now, 7, true, true, 300);
    assert(admitted == APC_BURST_MS / 300);
    assert(!controller.allowRelay(now, 7, true, true, 300));
}

void test_long_uptime_does_not_restart_warmup()
{
    ApcController controller;
    uint32_t now = 0;
    enter(controller, now, ApcMode::On, 3700, ApcState::Conserve);
    advance(controller, now, 25u * 24 * 60 * 60 * 1000, 3700);
    assert(controller.copy(now).hold == ApcHold::None && controller.copy(now).state == ApcState::Conserve);
    advance(controller, now, 25u * 24 * 60 * 60 * 1000, 3700);
    assert(controller.copy(now).hold == ApcHold::None && controller.copy(now).state == ApcState::Conserve);
}

void test_observer_accounting_and_sample_sum()
{
    ApcObserver observer;
    observer.sample(0, 4100, 3300, false, 0);
    assert(observer.copy().samples == 0);
    assert(observer.observe(20, 42, 3) && !observer.observe(30, 43, 4));
    observer.sample(UINT32_MAX - 4000, 4100, 3300, false, 3);
    observer.sample(999, 3900, 3290, true, 3);
    observer.sample(22000, 3800, 3280, false, 4);
    observer.started(UINT32_MAX - 49, 1, 1, true, 100);
    observer.ended(50, true, true);
    observer.ended(150, true, true);
    observer.started(200, 2, 2, false, 90);
    observer.ended(240, false, false);
    observer.startError();
    const auto s = observer.copy();
    assert(s.samples == 3 && s.batterySum == 11800 && s.minimum == 3800 && s.maximum == 4100);
    assert(s.usbSamples == 1 && s.gaps == 1 && s.configChanges == 1 && s.vddMin == 3280);
    assert(s.own.started == 1 && s.own.done == 1 && s.own.irqTimed == 1 && s.own.irqMs == 100);
    assert(s.relay.interrupted == 1 && s.startErrors == 1 && s.unfinished == 0);
    observer.off(200);
    observer.sample(30000, 1000, 1000, false, 4);
    assert(observer.copy().samples == 3 && observer.copy().stopSec == 200);
}

int main()
{
#define RUN(test)                                                                                                                \
    test();                                                                                                                      \
    std::cout << #test << " passed\n"
    RUN(test_filter_persistence_and_hysteresis);
    RUN(test_sustained_battery_during_warmup_is_not_immediate_conservation);
    RUN(test_shadow_budget_matches_active_without_suppression);
    RUN(test_stale_invalid_usb_and_context_fail_open);
    RUN(test_idempotency_mode_changes_and_rollover);
    RUN(test_bucket_credit_cap_and_refill_rollover);
    RUN(test_long_uptime_does_not_restart_warmup);
    RUN(test_observer_accounting_and_sample_sum);
}
