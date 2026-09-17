"""Scenario inputs and labels used by the simulation and evaluator."""

from dataclasses import dataclass, field
import numpy as np
from .dsp import background, add_event, FS


@dataclass
class Case:
    name: str
    group: str = "normal"
    intrusion: bool = False
    audio: str = "none"
    video: str = "normal"
    physical: str = "none"
    context: str = "dry"
    gain: float = 1.0
    internet_outage: bool = False
    server_outage: bool = False
    usb_outage: bool = False
    event_start: float = 8.0
    video_start: float = 8.0
    note: str = ""


def cases():
    # IDs 1-42 preserve the uploaded brief's ordering.
    specs = [
        Case("01_quiet"),
        Case("02_fan"),
        Case("03_traffic"),
        Case("04_sensor_noise"),
        Case("05_gain", gain=3.0),
        Case("06_camera_noise"),
        Case("07_light_on", "environment", video="light_on"),
        Case("08_light_off", "environment", video="light_off"),
        Case("09_rain", "environment", context="rain"),
        Case("10_thunder", "environment", audio="thunder", context="rain"),
        Case("11_wind", "environment", audio="wind"),
        Case("12_door_slam", "environment", audio="impact"),
        Case("13_object_falls", "environment", audio="glass"),
        Case("14_bad_echo", "fault", physical="echo_glitch"),
        Case("15_pir_glitch", "fault", physical="pir_glitch"),
        Case("16_radar_glitch", "fault", physical="mm_glitch"),
        Case("17_mic_transient", "fault", audio="click"),
        Case("18_frame_drop", "fault", video="drop"),
        Case("19_camera_disconnect", "fault", video="disconnect"),
        Case("20_camera_covered", "fault", video="black"),
        Case(
            "21_wifi_outage",
            "fault",
            True,
            "steps",
            "person",
            "all",
            internet_outage=True,
        ),
        Case(
            "22_server_offline",
            "fault",
            True,
            "steps",
            "person",
            "all",
            server_outage=True,
        ),
        Case("23_walk_in", "intrusion", True, "steps", "person", "all"),
        Case("24_quiet_entry", "intrusion", True, "none", "person", "all"),
        Case(
            "25_early_steps",
            "intrusion",
            True,
            "steps",
            "person",
            "all",
            video_start=10.8,
        ),
        Case("26_avoids_camera", "intrusion", True, "steps", "normal", "all"),
        Case("27_blocks_camera", "intrusion", True, "steps", "black", "all"),
        Case("28_stops_moving", "intrusion", True, "steps", "person", "stationary"),
        Case("29_near", "intrusion", True, "soft_steps", "normal", "all"),
        Case("30_far", "intrusion", True, "steps", "person", "pm"),
        Case(
            "31_audio_pir_only",
            "intrusion",
            True,
            "steps",
            "normal",
            "p",
            note="Deliberately insufficient for RED",
        ),
        Case(
            "32_audio_radar_only",
            "intrusion",
            True,
            "steps",
            "normal",
            "m",
            note="Deliberately insufficient for RED",
        ),
        Case("33_camera_pir", "intrusion", True, "none", "person", "p"),
        Case("34_camera_ultrasonic", "intrusion", True, "none", "person", "u"),
        Case("35_camera_unavailable", "intrusion", True, "none", "disconnect", "all"),
        Case(
            "36_delayed_camera",
            "intrusion",
            True,
            "steps",
            "person",
            "p",
            video_start=11.2,
        ),
        Case("37_curtain", "challenge", video="curtain"),
        Case(
            "38_warm_moving_object",
            "challenge",
            False,
            "none",
            "warm",
            "p",
            note="Common cause can fool vision+PIR",
        ),
        Case("39_small_animal", "challenge", False, "soft_steps", "small", "p"),
        Case("40_strong_thunder", "challenge", audio="thunder"),
        Case("41_rain_impacts", "challenge", audio="impact", context="rain"),
        Case(
            "42_outside_door",
            "challenge",
            False,
            "impact",
            "normal",
            "pm",
            note="Models bad sensor placement/cross-boundary response",
        ),
        Case("43_us_timeout", "fault", physical="timeout"),
        Case("44_silent_mic", "fault", audio="silence"),
        Case("45_clipped_mic", "fault", audio="clipped"),
        Case("46_frozen_camera", "fault", video="freeze"),
        Case("47_nonuniform_light", "challenge", video="nonuniform"),
        Case("48_saturated_camera", "fault", video="saturation"),
        Case(
            "49_usb_lost_intrusion",
            "fault",
            True,
            "steps",
            "normal",
            "all",
            usb_outage=True,
        ),
        Case(
            "50_rain_intrusion",
            "intrusion",
            True,
            "soft_steps",
            "person",
            "all",
            context="rain",
        ),
        Case(
            "51_blind_silent_far",
            "intrusion",
            True,
            "none",
            "normal",
            "m",
            note="Insufficient observability; intentional blind spot",
        ),
        Case("52_stuck_radar", "fault", physical="stuck_mm"),
    ]
    return specs


def waveform(case, seed, duration=24.0):
    x = background(duration, seed, case.context, traffic=("traffic" in case.name))
    if case.audio == "silence":
        x[int(case.event_start * FS) :] = 0
    elif case.audio == "clipped":
        x = np.clip(x * 1000, -1, 1)
    else:
        x = add_event(x, case.audio, case.event_start, 5.0, seed + 99)
    # Gain is flat scaling, unlike real AGC/clipping; stress those separately.
    return np.clip(x * case.gain, -1, 1)


def physical(case, t, rng):
    on = case.event_start <= t < 14.0
    p = False
    m = False
    d = 3.0 + rng.normal(0, 0.02)
    mode = case.physical
    if on:
        if mode in ("all", "p", "pm", "stationary"):
            p = True
        if mode in ("all", "m", "pm", "stationary"):
            m = True
        if mode in ("all", "u", "stationary"):
            d = 1.2 + rng.normal(0, 0.025)
        if mode == "stationary" and t > 9.5:
            p = False
    if mode == "echo_glitch" and 8.0 <= t < 8.1:
        d = 0.35
    if mode == "pir_glitch" and 8.0 <= t < 8.1:
        p = True
    if mode == "mm_glitch" and 8.0 <= t < 8.1:
        m = True
    if mode == "timeout" and t >= 8.0:
        d = float("nan")
    if mode == "stuck_mm" and t >= 8.0:
        m = True
    return p, m, d
