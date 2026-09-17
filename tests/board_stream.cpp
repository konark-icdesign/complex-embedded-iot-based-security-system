#include "../firmware/night_security/core.h"
#include <iostream>
#include <string>

int main() {
    security::Core core;
    uint32_t now;
    int p, m, ready, connected, reset;
    float distance;
    std::string command;
    while (std::cin >> now >> p >> m >> distance >> ready >> connected >> reset >> command) {
        if (reset) core.reset(); // Simulated physical button, not a serial command.
        if (connected) {
            core.heartbeat(now);
            core.command(command.c_str(), now);
        }
        const auto out = core.tick(now, p != 0, m != 0, distance, ready != 0);
        std::cout << out.pir << ' ' << out.radar << ' ' << out.near << ' '
                  << out.range_fault << ' ' << out.degraded << ' ' << out.alarm << ' '
                  << out.investigating << ' ' << out.fallback_alarm << std::endl;
    }
}
