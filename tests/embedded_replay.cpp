#include "../firmware/night_security/core.h"
#include <iostream>
#include <sstream>
#include <string>
#include <cstdlib>
int main() {
    std::string line, lastCase;
    security::Core core;
    while (std::getline(std::cin, line)) {
        std::stringstream s(line);
        std::string name, ts, ps, ms, ds, hs;
        if (!std::getline(s, name, ',') || !std::getline(s, ts, ',') || !std::getline(s, ps, ',') ||
            !std::getline(s, ms, ',') || !std::getline(s, ds, ',') || !std::getline(s, hs, ',')) {
            return 2;
        }
        if (name != lastCase) {
            core = security::Core();
            lastCase = name;
        }
        const uint32_t t = static_cast<uint32_t>(std::stoul(ts));
        if (hs == "1") {
            core.heartbeat(t);
        }
        const auto out = core.tick(t, ps == "1", ms == "1", std::stof(ds));
        std::cout << name << ',' << t << ',' << out.pir << ',' << out.radar << ',' << out.near
                  << ',' << out.alarm << '\n';
    }
    return 0;
}
