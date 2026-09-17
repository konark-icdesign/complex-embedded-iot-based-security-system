#include "../firmware/night_security/core.h"
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include <string>

int main() {
    using security::Core;
    {
        Core c;
        security::Output o;
        for (uint32_t t = 0; t < 2000; t += 100) {
            c.heartbeat(t);
            o = c.tick(t, false, false, t == 1000 ? .35F : 3.F);
            assert(!o.near);
            assert(!o.alarm);
        }
        puts("PASS isolated echo rejected");
    }
    {
        Core c;
        security::Output o;
        for (uint32_t t = 0; t < 2000; t += 100) {
            c.heartbeat(t);
            o = c.tick(t, false, false, 1.2F);
        }
        assert(o.near);
        assert(!o.alarm);
        puts("PASS sustained range accepted without single-sensor alarm");
        o = c.tick(2000, false, false, NAN);
        assert(!o.near && o.range_fault);
        puts("PASS invalid range invalidates old evidence");
    }
    {
        Core c;
        security::Output o;
        for (uint32_t t = 0; t < 5000; t += 100) {
            o = c.tick(t, true, true, 1.2F);
        }
        assert(o.alarm && o.degraded);
        c.heartbeat(5000);
        o = c.tick(5000, false, false, 3.F);
        assert(o.alarm);
        c.reset();
        o = c.tick(5100, false, false, 3.F);
        assert(!o.alarm);
        puts("PASS offline fallback latches until explicit reset");
    }
    {
        Core c;
        security::Output o;
        for (uint32_t t = 0; t < 5000; t += 100) {
            c.heartbeat(t);
            o = c.tick(t, true, true, 1.2F);
            assert(!o.alarm);
        }
        c.serverAlarm();
        o = c.tick(5000, false, false, 3.F);
        assert(o.alarm);
        puts("PASS healthy host controls central alarm");
    }
    {
        Core c;
        c.heartbeat(UINT32_MAX - 1000U);
        auto o = c.tick(500, false, false, 3.F);
        assert(!o.degraded);
        o = c.tick(1500, false, false, 3.F);
        assert(o.degraded);
        puts("PASS millis wraparound");
    }
    {
        Core c;
        security::LineBuffer b;
        std::string bad(300, 'x');
        bad += "ALARM\n";
        for (char x : bad) {
            b.feed(x, c, 0);
        }
        assert(!c.tick(0, false, false, 3.F).alarm);
        for (char x : std::string("ALARM\n")) {
            b.feed(x, c, 100);
        }
        assert(c.tick(100, false, false, 3.F).alarm);
        puts("PASS bounded command parser rejects overflow tails");
    }
    {
        Core c;
        security::Output o;
        for (uint32_t t = 0; t < 1000; t += 100) {
            o = c.tick(t, true, true, 1.2F);
        }
        o = c.tick(5000, true, true, 1.2F);
        assert(!o.near && !o.alarm);
        puts("PASS sample gap resets persistence");
    }
    {
        Core c;
        for (uint32_t t = 0; t < 5000; t += 100) {
            assert(!c.tick(t, true, true, 1.2F, false).alarm);
        }
        puts("PASS warm-up inhibits alarm");
    }
    puts("ALL EMBEDDED HOST TESTS PASSED");
}
