#pragma once
#include <stdint.h>
#include <stddef.h>
#include <math.h>
#include <string.h>

namespace security {
inline uint32_t elapsed(uint32_t now,uint32_t then) { return now-then; }
struct Output {
    bool pir=false, radar=false, near=false, range_fault=true;
    bool degraded=true, alarm=false;
    float metres=NAN;
};
class Core {
    float ranges_[5] = {};
    uint8_t used_=0, cursor_=0, p_=0, m_=0, u_=0, agree_=0;
    uint32_t heartbeat_=0, last_tick_=0;
    bool heartbeat_seen_=false, sampled_=false, latch_=false;
public:
    void heartbeat(uint32_t now) { heartbeat_=now; heartbeat_seen_=true; }
    void serverAlarm() { latch_=true; }
    void reset() { latch_=false; agree_=0; }
    bool command(const char* line,uint32_t now) {
        if (strcmp(line,"HB")==0) { heartbeat(now); return true; }
        if (strcmp(line,"ALARM")==0) { serverAlarm(); return true; }
        // Alarm reset requires a physical reset button; no unauthenticated remote reset.
        return false;
    }
    Output tick(uint32_t now,bool p,bool m,float distance,bool armed=true) {
        if (sampled_ && elapsed(now,last_tick_)>250U) {
            used_=0;p_=0;m_=0;u_=0;agree_=0;
        }
        sampled_=true;last_tick_=now;
        p_=p ? static_cast<uint8_t>(p_<3U ? p_+1U : 3U) : 0U;
        m_=m ? static_cast<uint8_t>(m_<3U ? m_+1U : 3U) : 0U;
        Output o;
        o.pir=p_>=3U; o.radar=m_>=3U;
        o.range_fault=!isfinite(distance)||distance<.02F||distance>4.F;
        if (o.range_fault) { used_=0;cursor_=0;u_=0; }
        else {
            ranges_[cursor_]=distance;cursor_=static_cast<uint8_t>((cursor_+1U)%5U);
            if (used_<5U) { ++used_; }
            float a[5]={};
            for (uint8_t i=0;i<used_;++i) { a[i]=ranges_[i]; }
            for (uint8_t i=1;i<used_;++i) {
                const float value=a[i]; uint8_t j=i;
                while (j>0U && a[j-1U]>value) { a[j]=a[j-1U]; --j; }
                a[j]=value;
            }
            o.metres=a[used_/2U];
            const bool near=used_==5U && o.metres<1.8F;
            u_=near ? static_cast<uint8_t>(u_<3U ? u_+1U : 3U) : 0U;
            o.near=u_>=3U;
        }
        o.degraded=!heartbeat_seen_||elapsed(now,heartbeat_)>2000U;
        const bool fallback=armed&&o.degraded&&o.pir&&o.radar&&o.near;
        agree_=fallback ? static_cast<uint8_t>(agree_<10U ? agree_+1U : 10U) : 0U;
        if (agree_>=10U) { latch_=true; }
        o.alarm=armed&&latch_;
        return o;
    }
};

// Bounded serial line collector. Discard an entire oversized line, not its tail.
class LineBuffer {
    char data_[32]={}; size_t n_=0; bool overflow_=false;
public:
    bool feed(char c,Core& core,uint32_t now) {
        if (c=='\r') { return false; }
        if (c=='\n') {
            bool accepted=false;
            if (!overflow_) { data_[n_]='\0';accepted=core.command(data_,now); }
            n_=0;overflow_=false;return accepted;
        }
        if (overflow_) { return false; }
        if (n_+1U>=sizeof(data_)) { overflow_=true;return false; }
        data_[n_++]=c;return false;
    }
};
}
