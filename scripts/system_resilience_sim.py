"""Synthetic resilience simulation for the remaining system-level cases.

This is not physical hardware validation. It stress-tests the state logic with
synthetic sensor scores, missing sensors, benign multi-sensor activity and
network outages.

Run:
    python scripts/system_resilience_sim.py
"""

import numpy as np
import pandas as pd


SEED = 20260919
TRIALS = 12000
SENSORS = ["audio", "radar", "ultra", "pir", "camera"]


def main() -> None:
    rng = np.random.default_rng(SEED)

    scenarios = np.array(
        [
            "normal",
            "benign",
            "authorized",
            "intrusion",
            "sensor_fault",
            "outage_intrusion",
        ]
    )
    probabilities = np.array([0.32, 0.18, 0.16, 0.18, 0.08, 0.08])
    scenario = rng.choice(scenarios, TRIALS, p=probabilities)

    means = {
        "normal": [0.10, 0.08, 0.08, 0.06, 0.08],
        "benign": [0.40, 0.28, 0.30, 0.35, 0.30],
        "authorized": [0.45, 0.65, 0.60, 0.70, 0.70],
        "intrusion": [0.72, 0.80, 0.74, 0.78, 0.82],
        "sensor_fault": [0.16, 0.14, 0.14, 0.12, 0.14],
        "outage_intrusion": [0.72, 0.80, 0.74, 0.78, 0.82],
    }
    stddev = {
        "normal": [0.08, 0.07, 0.06, 0.08, 0.07],
        "benign": [0.18, 0.16, 0.16, 0.20, 0.18],
        "authorized": [0.18, 0.14, 0.15, 0.16, 0.14],
        "intrusion": [0.16, 0.12, 0.14, 0.14, 0.12],
        "sensor_fault": [0.12, 0.11, 0.10, 0.12, 0.11],
        "outage_intrusion": [0.16, 0.12, 0.14, 0.14, 0.12],
    }

    samples = np.zeros((TRIALS, len(SENSORS)))
    for i, name in enumerate(scenario):
        samples[i] = np.clip(rng.normal(means[name], stddev[name]), 0, 1)

    missing = np.zeros_like(samples, dtype=bool)
    for i, name in enumerate(scenario):
        if name == "sensor_fault":
            failed = rng.integers(0, len(SENSORS))
            degraded = (failed + rng.integers(1, len(SENSORS))) % len(SENSORS)
            missing[i, failed] = True
            samples[i, degraded] = np.clip(
                samples[i, degraded] + rng.normal(0, 0.25), 0, 1
            )
        else:
            missing[i] = rng.random(len(SENSORS)) < 0.01

    masked = samples.copy()
    masked[missing] = np.nan

    weights = np.array([0.20, 0.24, 0.18, 0.14, 0.24])
    available_weights = np.where(np.isnan(masked), 0, weights)
    fusion = np.nansum(masked * available_weights, axis=1) / np.maximum(
        available_weights.sum(axis=1), 1e-9
    )

    strong_count = np.nansum(masked >= 0.65, axis=1)
    fusion = np.clip(fusion + 0.05 * np.maximum(strong_count - 1, 0), 0, 1)

    state = np.full(TRIALS, "GREEN", dtype=object)
    state[(fusion >= 0.35) & (fusion < 0.68)] = "YELLOW"
    state[fusion >= 0.68] = "RED"

    # Valid local authorization suppresses escalation in this synthetic model.
    state[(scenario == "authorized") & (state == "RED")] = "YELLOW"

    truth = np.isin(scenario, ["intrusion", "outage_intrusion"])
    predicted_red = state == "RED"

    tp = np.sum(predicted_red & truth)
    fn = np.sum((~predicted_red) & truth)
    fp = np.sum(predicted_red & (~truth))
    tn = np.sum((~predicted_red) & (~truth))

    recall = tp / (tp + fn)
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    false_positive_rate = fp / (fp + tn)

    benign_red_rate = np.mean(predicted_red[scenario == "benign"])
    outage_detection_rate = np.mean(
        predicted_red[scenario == "outage_intrusion"]
    )
    sensor_fault_safe_rate = np.mean(state[scenario == "sensor_fault"] != "RED")

    outage_count = np.sum(scenario == "outage_intrusion")
    outage_duration = rng.uniform(10, 180, outage_count)
    retry_period = 5.0
    delivery_delay = (
        np.ceil(outage_duration / retry_period) * retry_period
        + rng.uniform(0.2, 1.2, outage_count)
    )

    summary = pd.DataFrame(
        {
            "Metric": [
                "Threat detection recall",
                "RED precision",
                "Overall false-positive rate",
                "Benign multi-sensor RED rate",
                "Outage intrusion locally detected",
                "Sensor-fault cases avoiding RED",
                "Median buffered-event delivery",
                "95th percentile buffered-event delivery",
            ],
            "Result": [
                f"{recall * 100:.2f}%",
                f"{precision * 100:.2f}%",
                f"{false_positive_rate * 100:.2f}%",
                f"{benign_red_rate * 100:.2f}%",
                f"{outage_detection_rate * 100:.2f}%",
                f"{sensor_fault_safe_rate * 100:.2f}%",
                f"{np.median(delivery_delay):.1f} s",
                f"{np.percentile(delivery_delay, 95):.1f} s",
            ],
        }
    )

    print(f"Synthetic remaining-system simulation: {TRIALS:,} trials")
    print(f"Seed: {SEED}\n")
    print(summary.to_string(index=False))

    distribution = (
        pd.crosstab(scenario, state, normalize="index") * 100
    ).round(2)
    print("\nPer-scenario states (%):")
    print(distribution.to_string())


if __name__ == "__main__":
    main()
