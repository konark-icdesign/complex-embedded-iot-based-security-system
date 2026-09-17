// Bench firmware. Confirm the board and electrical levels in docs/hardware.md.
// 60 s sensor warm-up. USB serial avoids putting Wi-Fi between sensors and HP.
#include <Arduino.h>
#include "core.h"
#if defined(ARDUINO_ARCH_RENESAS_UNO)
#include <WDT.h>
#endif

constexpr uint8_t PIR_PIN = 2, RADAR_PIN = 3, TRIG_PIN = 4, ECHO_PIN = 5;
constexpr uint8_t GREEN_PIN = 6, YELLOW_PIN = 7, RED_PIN = 8, BUZZER_PIN = 9, RESET_PIN = 10;
security::Core controller;
security::LineBuffer commandLine;
uint32_t startMs = 0, lastSample = 0, sequence = 0;

float readDistance() {
    digitalWrite(TRIG_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG_PIN, LOW);
    // Bounded blocking, at most 25 ms; acceptable inside a 100 ms prototype loop.
    const unsigned long width = pulseIn(ECHO_PIN, HIGH, 25000UL);
    return width == 0UL ? NAN : static_cast<float>(width) * .0001715F;
}
void processServerMessage(uint32_t now) {
    // Bound work per loop; malformed serial traffic must not starve sampling.
    for (uint8_t n = 0; n < 64U && Serial.available() > 0; ++n) {
        commandLine.feed(static_cast<char>(Serial.read()), controller, now);
    }
}
void updateAlarmOutputs(const security::Output &out, bool armed) {
    digitalWrite(GREEN_PIN, armed && !out.degraded && !out.range_fault && !out.alarm && !out.investigating);
    digitalWrite(YELLOW_PIN, !out.alarm && (!armed || out.degraded || out.range_fault || out.investigating));
    digitalWrite(RED_PIN, out.alarm);
    digitalWrite(BUZZER_PIN, out.alarm); // Drive a transistor, not a high-current buzzer directly.
}
void publishSensorData(uint32_t now, const security::Output &out, bool armed) {
    // Only send if buffer space exists; disconnected USB must not block fallback.
    if (Serial.availableForWrite() < 64) {
        return;
    }
    Serial.print("S,");
    Serial.print(sequence++);
    Serial.print(',');
    Serial.print(now);
    Serial.print(',');
    Serial.print(out.pir);
    Serial.print(',');
    Serial.print(out.radar);
    Serial.print(',');
    Serial.print(out.metres, 3);
    Serial.print(',');
    Serial.print(!out.range_fault);
    Serial.print(',');
    Serial.print(out.alarm);
    Serial.print(',');
    Serial.println(armed);
}
void setup() {
    pinMode(PIR_PIN, INPUT);
    pinMode(RADAR_PIN, INPUT);
    pinMode(ECHO_PIN, INPUT);
    pinMode(TRIG_PIN, OUTPUT);
    pinMode(RESET_PIN, INPUT_PULLUP);
    for (uint8_t pin = GREEN_PIN; pin <= BUZZER_PIN; ++pin) {
        pinMode(pin, OUTPUT);
        digitalWrite(pin, LOW);
    }
    Serial.begin(115200);
    startMs = millis(); // Never wait indefinitely for Serial.
#if defined(ARDUINO_ARCH_RENESAS_UNO)
    WDT.begin(4000);
#endif
}
void loop() {
    const uint32_t now = millis();
    processServerMessage(now);
    if (security::elapsed(now, lastSample) >= 100U) {
        lastSample = now;
        const bool armed = security::elapsed(now, startMs) >= 60000U;
        if (digitalRead(RESET_PIN) == LOW) {
            controller.reset();
        }
        const auto out = controller.tick(now, digitalRead(PIR_PIN) == HIGH,
                                         digitalRead(RADAR_PIN) == HIGH, readDistance(), armed);
        updateAlarmOutputs(out, armed);
        publishSensorData(now, out, armed);
    }
#if defined(ARDUINO_ARCH_RENESAS_UNO)
    WDT.refresh();
#endif
}
