#!/usr/bin/env python3
"""Deterministic datasheet-based electrical simulation for the first hardware revision.

This is a lumped-element circuit simulation, not a statistical sensor/fusion simulation.
It models voltages, RC time constants, Schmitt thresholds, GPIO drive, MOSFET gate
charge/on-resistance, ultrasonic time-of-flight, and simple ground-return stress cases.

It is not a transistor-level vendor SPICE model of the RA4M1 or sensor modules.
"""
import json
import math

VCC_R4 = 5.0
R4_VIH = 0.8 * VCC_R4
R4_VIL = 0.2 * VCC_R4
R4_CIN = 15e-12
R4_IIN_MAX = 1e-6

AHCT_VTPLUS_MAX = 2.1
AHCT_VTPLUS_MIN = 0.9
AHCT_VTMINUS_MAX = 1.7
AHCT_VOH_LIGHT_MIN = 4.4
AHCT_VOL_LIGHT_MAX = 0.1
AHCT_TPD_MAX = 8e-9

# PIR/radar front end:
# 0/3.3V source -> 10k series -> input node
# input node -> 100k pulldown + 10nF to GND
# input node -> two SN74AHCT14 inverters -> UNO R4 input
SENSOR_HIGH = 3.3
R_SER = 10e3
R_PULL = 100e3
C_FILTER = 10e-9
R_TH = R_SER * R_PULL / (R_SER + R_PULL)
TAU_FILTER = R_TH * C_FILTER
V_FILTER_FINAL = SENSOR_HIGH * R_PULL / (R_SER + R_PULL)

def charge(vfinal, tau, t):
    return vfinal * (1.0 - math.exp(-t / tau))

def t_to_level(vfinal, tau, level):
    return -tau * math.log(1.0 - level / vfinal)

# HC-SR04 Echo conditioner:
# Echo -> 1k -> D5 node; 100k to GND; 100pF to GND.
ECHO_SRC = 5.0
R_ECHO = 1e3
R_ECHO_PD = 100e3
C_ECHO = 100e-12
R_ECHO_TH = R_ECHO * R_ECHO_PD / (R_ECHO + R_ECHO_PD)
TAU_ECHO = R_ECHO_TH * C_ECHO
V_ECHO_FINAL = ECHO_SRC * R_ECHO_PD / (R_ECHO + R_ECHO_PD)

# AO3400A alarm output.
# RA4M1: VOH >= VCC-0.8V at 4mA for middle-drive "other output pins".
RA4_ROUT_WORST = 0.8 / 0.004
R_GATE = 1500.0
AO3400_QG = 6e-9
AO3400_RDS_MAX = 32e-3
GATE_C_EFFECTIVE = AO3400_QG / 4.5
TAU_GATE = (RA4_ROUT_WORST + R_GATE) * GATE_C_EFFECTIVE

def c_air(temp_c):
    return 331.3 + 0.606 * temp_c

def echo_time(distance_m, temp_c):
    return 2.0 * distance_m / c_air(temp_c)

def firmware_distance(distance_m, temp_c):
    return echo_time(distance_m, temp_c) * 343.0 / 2.0

noise_widths_us = [0.1, 1, 5, 10, 20, 30, 35, 50, 100, 200]
noise_peaks = {
    str(w): charge(V_FILTER_FINAL, TAU_FILTER, w * 1e-6)
    for w in noise_widths_us
}

sensor_rise_to_worst_threshold = t_to_level(
    V_FILTER_FINAL, TAU_FILTER, AHCT_VTPLUS_MAX
)
guaranteed_reject_width = t_to_level(
    V_FILTER_FINAL, TAU_FILTER, AHCT_VTPLUS_MIN
)
echo_cross_vih = t_to_level(V_ECHO_FINAL, TAU_ECHO, R4_VIH)

gate_t90 = -TAU_GATE * math.log(0.1)
gate_peak_current = VCC_R4 / (RA4_ROUT_WORST + R_GATE)

mosfet_cases = {}
for current in (0.1, 0.5, 1.0):
    mosfet_cases[str(current)] = {
        "vds_drop_V": current * AO3400_RDS_MAX,
        "conduction_W": current * current * AO3400_RDS_MAX,
    }

temps = [-15, 0, 20, 40, 60]
ultrasonic = {}
for temp in temps:
    ultrasonic[str(temp)] = {
        "sound_speed_m_s": c_air(temp),
        "echo_4m_ms": echo_time(4.0, temp) * 1e3,
        "true_1p8m_reported_m_with_fixed_343": firmware_distance(1.8, temp),
        "true_distance_at_firmware_1p8m_threshold_m":
            1.8 * c_air(temp) / 343.0,
    }

ground_bounce = {
    str(r): 0.5 * r
    for r in (0.02, 0.05, 0.1, 0.25, 0.5)
}

results = {
    "logic": {
        "R4_VIH_guaranteed_V": R4_VIH,
        "R4_VIL_guaranteed_V": R4_VIL,
        "direct_3p3_to_R4_guaranteed": SENSOR_HIGH >= R4_VIH,
        "AHCT_input_final_high_V": V_FILTER_FINAL,
        "AHCT_worst_rising_threshold_V": AHCT_VTPLUS_MAX,
        "AHCT_input_high_margin_V": V_FILTER_FINAL - AHCT_VTPLUS_MAX,
        "AHCT_double_inverter_output_high_min_V": AHCT_VOH_LIGHT_MIN,
        "R4_high_margin_after_buffer_V": AHCT_VOH_LIGHT_MIN - R4_VIH,
        "R4_low_margin_after_buffer_V": R4_VIL - AHCT_VOL_LIGHT_MAX,
        "filter_tau_us": TAU_FILTER * 1e6,
        "rise_to_worst_AHCT_threshold_us":
            sensor_rise_to_worst_threshold * 1e6,
        "guaranteed_reject_pulse_shorter_than_us":
            guaranteed_reject_width * 1e6,
        "noise_pulse_peak_V": noise_peaks,
        "two_gate_max_prop_delay_ns": 2 * AHCT_TPD_MAX * 1e9,
    },
    "ultrasonic_echo_interface": {
        "conditioned_high_V": V_ECHO_FINAL,
        "RC_tau_ns": TAU_ECHO * 1e9,
        "time_to_R4_VIH_ns": echo_cross_vih * 1e9,
        "DC_drop_from_1uA_input_leakage_mV":
            R_ECHO * R4_IIN_MAX * 1e3,
        "recommended_trigger_period_ms": 100.0,
        "sensor_guide_min_cycle_ms": 60.0,
    },
    "ultrasonic_temperature": ultrasonic,
    "alarm_mosfet": {
        "RA4_output_effective_R_worst_ohm": RA4_ROUT_WORST,
        "gate_series_R_ohm": R_GATE,
        "initial_gate_current_mA": gate_peak_current * 1e3,
        "effective_gate_tau_us": TAU_GATE * 1e6,
        "gate_90_percent_us": gate_t90 * 1e6,
        "AO3400A_Rds_on_max_ohm_at_4p5V": AO3400_RDS_MAX,
        "load_cases": mosfet_cases,
    },
    "ground_return": {
        "alarm_current_A": 0.5,
        "shared_ground_bounce_V_by_return_resistance_ohm":
            ground_bounce,
    },
}

assert not results["logic"]["direct_3p3_to_R4_guaranteed"]
assert results["logic"]["AHCT_input_high_margin_V"] > 0.5
assert results["logic"]["R4_high_margin_after_buffer_V"] > 0.3
assert results["ultrasonic_echo_interface"]["conditioned_high_V"] > R4_VIH
assert results["ultrasonic_echo_interface"]["recommended_trigger_period_ms"] >= 60
assert results["alarm_mosfet"]["initial_gate_current_mA"] < 4.0
assert results["alarm_mosfet"]["load_cases"]["1.0"]["conduction_W"] < 0.05

print(json.dumps(results, indent=2))
