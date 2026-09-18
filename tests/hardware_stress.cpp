#include "../firmware/night_security/core.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <initializer_list>

static uint32_t nextRandom(uint32_t &state) {
    state = state * 1664525U + 1013904223U;
    return state;
}

struct DetectionResult {
    int detected = 0;
    double latency_sum = 0.0;
};

int main() {
    constexpr int trials = 5000;
    constexpr int ticks = 100; // 10 s at the intended 100 ms cadence.

    puts("Synthetic hardware-behaviour stress test; this is not physical sensor validation.");

    for (int dropout_percent : {0, 1, 5, 10, 20}) {
        DetectionResult result;
        for (int trial = 0; trial < trials; ++trial) {
            security::Core core;
            uint32_t random = 20260919U + static_cast<uint32_t>(trial) * 17U;
            for (int tick = 0; tick < ticks; ++tick) {
                const bool lost_echo =
                    static_cast<int>(nextRandom(random) % 100U) < dropout_percent;
                const auto output = core.tick(
                    static_cast<uint32_t>(tick) * 100U,
                    true,
                    true,
                    lost_echo ? NAN : 1.0F,
                    true);
                if (output.alarm) {
                    ++result.detected;
                    result.latency_sum += tick * 0.1;
                    break;
                }
            }
        }
        const double rate = 100.0 * result.detected / trials;
        const double mean_latency =
            result.detected ? result.latency_sum / result.detected : 0.0;
        printf("echo_dropout=%d%% detection_10s=%.2f%% mean_latency=%.3fs\n",
               dropout_percent, rate, mean_latency);
        if (dropout_percent <= 10) {
            assert(rate > 99.0);
        }
    }

    // False-near outliers while the real target remains far. The median and
    // persistence filter should reject moderate isolated range glitches.
    for (int glitch_percent : {1, 5, 10, 20, 30}) {
        int alarms = 0;
        for (int trial = 0; trial < trials; ++trial) {
            security::Core core;
            uint32_t random = 12345U + static_cast<uint32_t>(trial) * 31U;
            for (int tick = 0; tick < ticks; ++tick) {
                const bool near_glitch =
                    static_cast<int>(nextRandom(random) % 100U) < glitch_percent;
                const auto output = core.tick(
                    static_cast<uint32_t>(tick) * 100U,
                    true,
                    true,
                    near_glitch ? 0.5F : 3.0F,
                    true);
                if (output.alarm) {
                    ++alarms;
                    break;
                }
            }
        }
        const double false_alarm_rate = 100.0 * alarms / trials;
        printf("false_near_glitch=%d%% alarm_10s=%.2f%%\n",
               glitch_percent, false_alarm_rate);
        if (glitch_percent <= 10) {
            assert(false_alarm_rate == 0.0);
        }
    }

    // Long loop stalls reset persistence. This deliberately stresses the
    // 250 ms timing-gap rule rather than modelling measured UNO R4 timing.
    for (int stall_percent : {1, 5, 10}) {
        int detected = 0;
        for (int trial = 0; trial < trials; ++trial) {
            security::Core core;
            uint32_t random = 98765U + static_cast<uint32_t>(trial) * 13U;
            uint32_t now = 0;
            for (int tick = 0; tick < ticks; ++tick) {
                const bool stalled =
                    static_cast<int>(nextRandom(random) % 100U) < stall_percent;
                now += stalled ? 300U : 100U;
                const auto output = core.tick(now, true, true, 1.0F, true);
                if (output.alarm) {
                    ++detected;
                    break;
                }
            }
        }
        const double rate = 100.0 * detected / trials;
        printf("loop_stall_300ms=%d%% detection_10s=%.2f%%\n",
               stall_percent, rate);
    }

    puts("HARDWARE-BEHAVIOUR STRESS TEST PASSED");
}
