// Deterministic policy tests. Hardware PA output and RF reach are not measured here.
#include "modules/LegionGuardPolicy.h"
#include "modules/LegionRfPolicy.h"
#include <cassert>
#include <iostream>
using namespace legion;
static SpamIdentity peer(uint32_t node, bool verified = false, uint8_t key = 1)
{
    SpamIdentity i;
    i.node = node; i.verified = verified; i.key[0] = key;
    return i;
}
static void repeated(GuardPolicy &g, SpamIdentity i, uint32_t now, bool enforced)
{
    for (unsigned n = 1; n <= 6; ++n)
        assert(g.receive(now, i, n, 44) == (!enforced || n < 6));
}
void test_modes_duplicates_and_fixed_expiry()
{
    GuardPolicy g;
    const auto a = peer(42);
    assert(g.snapshot(0).mode == GuardMode::Observe);
    repeated(g, a, 0, false);
    assert(g.snapshot(0).active == 1 && g.snapshot(0).dropped == 0 && g.snapshot(0).wouldDrop == 1);
    assert(g.setMode(GuardMode::On));
    for (unsigned n=1; n<=100; ++n) assert(g.receive(100, a, 1, 44));
    assert(g.snapshot(100).duplicates == 99 && !g.snapshot(100).active);
    for (unsigned n=2; n<=6; ++n) assert(g.receive(100, a, n, 44) == (n<6));
    assert(!g.setMode(GuardMode::On));
    assert(!g.receive(599999, a, 999, 45)); // Does not extend the original expiry at 600100.
    assert(g.snapshot(600099).active == 1);
    assert(g.snapshot(600100).active == 0);
    assert(g.receive(600100, a, 1000, 1));
    assert(g.receive(600100, a, 1001, 2));
    assert(!g.receive(600100, a, 1002, 3)); // Two tokens on probation.
    assert(g.receive(605100, a, 1003, 4));
    g.clear(42, 605100);
    for(unsigned n=0;n<8;++n) assert(g.receive(605100,a,2000+n,100+n));
    assert(!g.receive(605100,a,2008,108));
    g.contextChanged();
    assert(g.snapshot(605100).mode == GuardMode::Off && g.snapshot(605100).active == 0);
    for(unsigned n=0;n<100;++n) assert(g.receive(605100,a,3000+n,1));
}
void test_rate_identity_capacity_and_rollover()
{
    GuardPolicy g; g.setMode(GuardMode::On);
    for(unsigned n=1;n<=12;++n) assert(g.receive(0,peer(1),n,n) == (n<=8));
    assert(g.snapshot(0).active == 1);
    assert(!g.allowPending(1,peer(1),1));
    assert(g.receive(1,peer(1,true),99,55)); // Unsigned spoof cannot quarantine signed identity.
    repeated(g,peer(1,true),2,true);
    assert(g.receive(2,peer(1,true,2),1,55)); // Key change has a separate domain.
    SpamEntry entries[8];
    assert(g.list(2,entries,8)==2);
    g.clear(1,3);
    assert(g.snapshot(3).active==0);
    GuardPolicy full;full.setMode(GuardMode::On);
    for(unsigned node=1;node<=SPAM_QUARANTINES;++node) repeated(full,peer(node),10,true);
    assert(full.snapshot(10).active==8);
    // More senders cannot evict existing quarantines; fresh senders pass under memory pressure.
    for(unsigned node=9;node<30;++node) assert(full.receive(10,peer(node),1,node));
    assert(!full.allowPending(100000,peer(1),1));
    assert(full.snapshot(100000).full>0);
    for(unsigned node=30;node<50;++node) full.receive(100000,peer(node),1,node);
    assert(full.snapshot(600010).active==0);
    assert(full.receive(600010,peer(1),99,99));
    assert(full.receive(600010,peer(1),100,100));
    assert(!full.receive(600010,peer(1),101,101));
    GuardPolicy wrap;wrap.setMode(GuardMode::On);
    const uint32_t start=UINT32_MAX-1000;
    repeated(wrap,peer(1),start,true);
    assert(wrap.snapshot(start+599999).active==1);
    assert(wrap.snapshot(start+600000).active==0);
    GuardPolicy copies;copies.setMode(GuardMode::On);
    for(unsigned node=1;node<=6;++node) assert(copies.receive(0,peer(node),node,99));
    assert(copies.snapshot(0).active==0); // Six legitimate senders are not one repeating origin.
}
void test_rf_matrix_and_completed_nodeinfo()
{
    RfPolicy rf; ApcControlStats a;
    a.mode=ApcMode::On;a.hold=ApcHold::None;a.state=ApcState::Conserve;
    assert(rf.target(a,RelayKind::Routine,1,1,0,27,0)==24);
    a.state=ApcState::Reserve;
    assert(rf.target(a,RelayKind::Routine,1,1,0,27,0)==21);
    for(auto kind:{RelayKind::Text,RelayKind::Opaque}) assert(rf.target(a,kind,1,1,0,27,0)==24);
    assert(rf.target(a,RelayKind::Protected,1,1,0,27,0)==27);
    assert(rf.target(a,RelayKind::Routine,1,1,0,18,0)==18);
    assert(rf.target(a,RelayKind::Routine,1,1,0,23,0)==21);
    assert(rf.target(a,RelayKind::NodeInfo,1,1,55,27,0)==27);
    rf.nodeInfoDone(1,55,0);
    assert(rf.target(a,RelayKind::NodeInfo,1,2,55,27,1)==21);
    assert(rf.target(a,RelayKind::NodeInfo,1,2,56,27,1)==27);
    rf.started(a,1,2,27,21,21,1);
    assert(rf.target(a,RelayKind::Routine,1,2,0,27,2)==27);
    assert(rf.target(a,RelayKind::Routine,1,2,0,27,120002)==21);
    assert(rf.snapshot().reduced==1);
    a.mode=ApcMode::Shadow;
    rf.started(a,1,3,27,21,27,3);
    assert(rf.snapshot().wouldReduce==1 && rf.snapshot().nominal==1);
    for(auto hold:{ApcHold::Off,ApcHold::Observe,ApcHold::Sample,ApcHold::Warmup,ApcHold::Usb,ApcHold::Context}) {
        a.hold=hold; assert(rf.target(a,RelayKind::Routine,1,4,0,27,4)==27);
    }
    a.hold=ApcHold::None;
    rf.programmed(15,false);rf.programmed(15,true);
    assert(rf.snapshot().fault && rf.snapshot().errors==1 && rf.snapshot().valid);
    assert(rf.target(a,RelayKind::Routine,1,4,0,27,4)==27);
    rf.resetFault();assert(rf.target(a,RelayKind::Routine,1,4,0,27,4)==21);
    rf.contextChanged();assert(rf.target(a,RelayKind::NodeInfo,1,4,55,27,4)==27);
    a.mode=ApcMode::Off;assert(rf.target(a,RelayKind::Routine,1,4,0,27,4)==27);
    a.mode=ApcMode::Observe;assert(rf.target(a,RelayKind::Routine,1,4,0,27,4)==27);
    a.mode=ApcMode::On;a.state=ApcState::Normal;assert(rf.target(a,RelayKind::Routine,1,4,0,27,4)==27);
}
int main()
{
    test_modes_duplicates_and_fixed_expiry();
    test_rate_identity_capacity_and_rollover();
    test_rf_matrix_and_completed_nodeinfo();
    std::cout << "Traffic policy: modes, duplicate accounting, rate/repetition, identities, capacity, expiry/rollover, S2 matrix/NodeInfo/faults passed\n";
}
