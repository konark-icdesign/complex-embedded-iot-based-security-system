# Rev-A electrical hardware simulation

This is the first circuit-level hardware pass for the UNO R4 security node. It is deliberately separate from the earlier random/synthetic sensor-fusion simulations.

The executable model is `hardware/electrical_interface_sim.py`. It uses datasheet electrical limits and lumped circuit equations. It is **not** a vendor transistor-level SPICE model and it is **not** a physical bench measurement.

## Parts frozen for this simulation

- Arduino UNO R4 WiFi / Renesas RA4M1 at the 5 V GPIO domain
- HC-SR501-class PIR output: 0 / 3.3 V
- Hi-Link LD2410B/C-class radar OUT: 0 / 3.3 V
- HC-SR04 ultrasonic module: 5 V, 10 us trigger, 5 V TTL Echo
- TI SN74AHCT14, 5 V, Schmitt-trigger logic conditioner
- AOS AO3400A N-channel MOSFET for the alarm output

The exact PIR/radar modules physically purchased still have to be checked against these assumptions before wiring.

## Why the original direct D2/D3 wiring was not acceptable

The UNO R4 uses 5 V RA4M1 GPIO. For ordinary input pins, the RA4M1 datasheet specifies:

```text
VIH(min) = 0.8 * VCC
VIL(max) = 0.2 * VCC
```

At 5.0 V:

```text
guaranteed HIGH >= 4.0 V
guaranteed LOW  <= 1.0 V
```

The HC-SR501-class PIR and LD2410B/C-class OUT signals are 3.3 V logic.

Therefore:

```text
3.3 V < 4.0 V
```

Direct connection may appear to work on a particular board, but it is not guaranteed by the RA4M1 electrical specification.

## Rev-A PIR/radar input circuit

Each 3.3 V sensor output gets this interface:

```text
sensor OUT
   |
  10k
   |
   +--------> SN74AHCT14 gate A -> gate B -> UNO R4 D2/D3
   |
  10nF
   |
  GND

input node
   |
 100k
   |
  GND
```

Two inverter gates preserve signal polarity.

The 100 kOhm pulldown makes a disconnected sensor read LOW. The 10 kOhm / 10 nF network rejects very short wiring spikes. SN74AHCT14 was chosen because it has Schmitt-trigger, TTL-compatible inputs and a 4.5-5.5 V supply range.

### Simulated result

With a 3.3 V sensor HIGH:

```text
filtered steady-state HIGH = 3.00 V
worst AHCT positive threshold used = 2.10 V
input margin = 0.90 V
```

The filter time constant is about:

```text
90.91 us
```

The input reaches the worst-case 2.1 V Schmitt threshold after:

```text
109.45 us
```

This is negligible compared with PIR/radar presence signals, which are much slower than 0.1 ms.

For a LOW-line positive glitch, the circuit-equation model gives:

| Glitch width | RC node peak |
|---:|---:|
| 1 us | 0.033 V |
| 5 us | 0.161 V |
| 10 us | 0.312 V |
| 20 us | 0.592 V |
| 30 us | 0.843 V |
| 35 us | 0.959 V |
| 50 us | 1.269 V |
| 100 us | 2.001 V |

Using the minimum possible SN74AHCT14 positive threshold of 0.9 V, pulses shorter than about **32.4 us** are guaranteed to remain below the switching threshold in this model.

On the output side, the AHCT14 datasheet guarantees at least 4.4 V at a 50 uA high-level load with VCC=4.5 V. The RA4M1 input leakage is at most about 1 uA, so this is a conservative receiving condition.

At a 5 V RA4M1 threshold of 4.0 V, the conservative high-state margin is therefore at least:

```text
4.4 - 4.0 = 0.4 V
```

The low-state margin is about 0.9 V using 0.1 V AHCT VOL and 1.0 V RA4M1 VIL.

## HC-SR04 interface

Proposed wiring:

```text
UNO D4 ---- 220R ---- TRIG

ECHO ---- 1k ----+---- UNO D5
                 |
                100pF
                 |
                GND

D5 node ---- 100k ---- GND
```

The UNO R4 GPIO domain itself is 5 V, so the HC-SR04 5 V TTL Echo does not need a 5-to-3.3 V divider as it would on a 3.3 V-only MCU.

The 1 kOhm / 100 pF / 100 kOhm network gives:

```text
steady HIGH at D5 = 4.9505 V
RC time constant = 99.0 ns
time to guaranteed 4.0 V HIGH = 163 ns
worst DC drop from 1 uA MCU input leakage across 1k = 1 mV
```

The shortest valid HC-SR04 echo pulse is orders of magnitude longer than this, so this conditioner does not materially change distance timing.

The HC-SR04 guide recommends more than 60 ms between measurements. The firmware uses 100 ms, so the current sample period is compatible with that recommendation.

## New ultrasonic issue found: temperature error

The current firmware uses a fixed speed of sound of 343 m/s.

Using:

```text
c(T) ~= 331.3 + 0.606*T  m/s
```

a true 1.8 m target is reported as:

| Air temperature | Firmware result for true 1.8 m |
|---:|---:|
| -15 C | 1.916 m |
| 0 C | 1.864 m |
| 20 C | 1.798 m |
| 40 C | 1.737 m |
| 60 C | 1.679 m |

Therefore the current hard `1.8 m` near/far decision does **not** represent the same physical distance across temperature.

At -15 C a person at a true 1.8 m can be classified outside the 1.8 m threshold. This needs either temperature compensation, a deliberately conservative threshold, or removal of ultrasonic distance as a hard all-or-nothing security condition.

At 4 m and -15 C the modeled echo is about 24.83 ms. The original 25 ms `pulseIn` timeout left only about 0.17 ms of margin, so Rev-A increases the timeout to 30 ms. That remains well below the 100 ms sample period while reducing avoidable cold/clone timeout risk.

## Alarm driver

Do not drive a buzzer/siren load directly from D9.

Rev-A output:

```text
UNO D9
   |
 1.5k
   |
AO3400A gate
   |
100k to GND

12 V ---- fuse ---- alarm +
alarm - ------------ AO3400A drain
AO3400A source ----- GND

SS34 across alarm load for inductive load protection
(cathode to +12 V, anode to MOSFET drain)
```

The RA4M1 output model used here is conservative: its guaranteed high can lose 0.8 V at 4 mA, equivalent to a 200 Ohm source resistance bound.

With that source resistance plus a 1.5 kOhm gate resistor:

```text
initial gate current = 2.94 mA
effective gate 90% charge time ~= 5.22 us
```

This stays below the 4 mA condition used for the output-voltage guarantee and is easily fast enough for an alarm switch.

AO3400A maximum RDS(on) at VGS=4.5 V is 32 mOhm. Conduction estimates:

| Alarm current | MOSFET drop | MOSFET conduction loss |
|---:|---:|---:|
| 0.1 A | 3.2 mV | 0.32 mW |
| 0.5 A | 16 mV | 8 mW |
| 1.0 A | 32 mV | 32 mW |

This means conduction loss is not the limiting issue at these currents. The remaining constraints are the actual alarm load, connector/wire current, fuse rating, supply capacity and switching transients.

## Ground return issue

A 0.5 A alarm current through a shared ground return creates:

| Shared return resistance | Ground shift |
|---:|---:|
| 20 mOhm | 10 mV |
| 50 mOhm | 25 mV |
| 100 mOhm | 50 mV |
| 250 mOhm | 125 mV |
| 500 mOhm | 250 mV |

The siren/MOSFET return must therefore go directly to the supply ground/star point instead of flowing through the microphone/sensor ground path. This becomes much more important when the analog microphone front-end is added.

## Proposed Rev-A wiring

```text
                         +5 V sensor rail
                               |
        +----------------------+----------------------+
        |                      |                      |
    HC-SR501               LD2410B/C              HC-SR04
        | OUT 3.3 V            | OUT 3.3 V            |
        v                      v                       |
 10k/10nF/100k          10k/10nF/100k                |
        |                      |                       |
  AHCT14 x2              AHCT14 x2                    |
        |                      |                       |
       D2                     D3                  Echo->D5
                                                   Trig<-D4

D9 -> 1.5k -> AO3400A -> external alarm load
```

Place a 100 nF ceramic decoupling capacitor directly at the SN74AHCT14 VCC/GND pins.

## ngspice circuit execution

The three Rev-A netlists are also executed by **ngspice 42** in GitHub Actions:

- `hardware/spice/sensor_interface.cir`
- `hardware/spice/echo_interface.cir`
- `hardware/spice/alarm_driver.cir`

The CI run performs transient circuit analysis and then checks the measured values against explicit acceptance bounds. The recorded passing run produced:

| SPICE measurement | Result |
|---|---:|
| Sensor RC delay to 2.1 V | 109.450 us |
| Conditioned output delay to 4.0 V | 109.490 us |
| Filtered 3.3 V sensor HIGH | 2.9877 V |
| Conditioned logic HIGH | 5.0000 V |
| HC-SR04 D5 delay to 4.0 V | 190 ns |
| HC-SR04 conditioned HIGH | 4.9495 V |
| Alarm gate delay to 4.5 V | 5.490 us |
| Representative alarm current | 0.4942 A |
| MOSFET drain voltage while ON | 14.07 mV |
| Drain peak during inductive turn-off | 12.393 V |

All ten electrical acceptance checks passed.

This is a real SPICE transient solve, but model fidelity still matters. The AHCT gates are represented as datasheet-threshold behavioral Schmitt stages rather than TI transistor-level silicon models. The AO3400A is an approximate MOS model fitted to the relevant 4.5 V on-resistance region rather than the AOS proprietary device model. The resistor/capacitor networks and transient load are directly solved by ngspice.

Therefore these results validate the **Rev-A circuit topology and first-order electrical margins**, not final production behavior under every process, temperature, wiring-parasitic or EMC condition.

## What this simulation proves

It is enough to reject the old direct 3.3 V -> 5 V RA4M1 input design and to define a defensible first electrical interface.

It establishes that, under the cited datasheet limits:

- the proposed AHCT14 interface gives valid logic margins,
- the RC filter is slow enough to reject very short spikes but extremely fast relative to human-presence signals,
- the HC-SR04 Echo conditioner does not distort range timing significantly,
- the proposed MOSFET gate drive does not require excessive GPIO current,
- the AO3400A has very low conduction loss for the intended alarm-current range,
- the fixed ultrasonic speed-of-sound assumption creates a real temperature-dependent threshold error.

## What is still not proved

This is **not** physical validation and it is not a transistor-level vendor SPICE simulation of every module.

Before soldering the final PCB, still measure/verify:

- exact purchased HC-SR501 output HIGH/LOW,
- exact LD2410 variant and OUT electrical level,
- actual HC-SR04 echo waveform and missed-echo rate,
- UNO R4 5 V rail under the intended supply,
- alarm current and inductive behavior,
- oscilloscope edge/ringing on long sensor wires,
- real microphone analog front end,
- real power supply and ground transients.

The next circuit-level block should be the microphone analog front-end and power filtering after the exact microphone and power source are selected.
