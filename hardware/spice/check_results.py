#!/usr/bin/env python3
"""Fail CI when the SPICE circuits violate the intended electrical envelope."""
from pathlib import Path
import math
import re

ROOT = Path("results/spice")


def measurement(log_name, key):
    text = (ROOT / log_name).read_text(encoding="utf-8", errors="replace")
    match = re.search(
        rf"(?mi)^\s*{re.escape(key)}\s*=\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?)",
        text,
    )
    if not match:
        raise SystemExit(f"missing SPICE measurement {key} in {log_name}")
    value = float(match.group(1))
    if not math.isfinite(value):
        raise SystemExit(f"non-finite SPICE measurement {key}={value}")
    return value


sensor_cross = measurement("sensor_interface.log", "t_filter_cross")
sensor_out = measurement("sensor_interface.log", "t_out_cross")
sensor_high = measurement("sensor_interface.log", "filtered_high")
logic_high = measurement("sensor_interface.log", "output_high")

echo_cross = measurement("echo_interface.log", "t_echo_4v")
echo_high = measurement("echo_interface.log", "d5_high")

gate_cross = measurement("alarm_driver.log", "gate_4p5")
load_current = abs(measurement("alarm_driver.log", "load_current_on"))
drain_on = measurement("alarm_driver.log", "drain_on")
drain_peak = measurement("alarm_driver.log", "drain_peak")

# All pulse sources rise at t=1 ms in these netlists.
sensor_delay = sensor_cross - 1e-3
sensor_logic_delay = sensor_out - 1e-3
echo_delay = echo_cross - 1e-3
gate_delay = gate_cross - 1e-3

checks = {
    "sensor_filtered_high_2p8_to_3p05_V": 2.8 <= sensor_high <= 3.05,
    "conditioned_R4_logic_high_above_4V": logic_high >= 4.0,
    "sensor_RC_crossing_80_to_150_us": 80e-6 <= sensor_delay <= 150e-6,
    "conditioned_output_crossing_under_160_us": 0 <= sensor_logic_delay <= 160e-6,
    "echo_high_above_R4_VIH": echo_high >= 4.0,
    "echo_4V_crossing_under_1_us": 0 <= echo_delay <= 1e-6,
    "alarm_gate_4p5_under_10_us": 0 <= gate_delay <= 10e-6,
    "alarm_current_about_0p5A": 0.45 <= load_current <= 0.55,
    "alarm_MOSFET_on_drop_under_100mV": 0 <= drain_on <= 0.100,
    "flyback_peak_under_15V_in_model": 0 <= drain_peak <= 15.0,
}

print("SPICE acceptance measurements")
print(f"sensor RC 2.1V crossing delay: {sensor_delay * 1e6:.3f} us")
print(f"conditioned output 4V delay:    {sensor_logic_delay * 1e6:.3f} us")
print(f"filtered sensor HIGH:           {sensor_high:.4f} V")
print(f"conditioned logic HIGH:         {logic_high:.4f} V")
print(f"HC-SR04 D5 4V delay:            {echo_delay * 1e9:.1f} ns")
print(f"HC-SR04 D5 HIGH:                {echo_high:.4f} V")
print(f"alarm gate 4.5V delay:          {gate_delay * 1e6:.3f} us")
print(f"alarm load current:             {load_current:.4f} A")
print(f"alarm MOSFET drain ON:          {drain_on * 1e3:.2f} mV")
print(f"flyback drain peak:             {drain_peak:.3f} V")

failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(f"{'PASS' if ok else 'FAIL'} {name}")
if failed:
    raise SystemExit("SPICE electrical acceptance failed: " + ", ".join(failed))

print("ALL SPICE ELECTRICAL ACCEPTANCE CHECKS PASSED")
