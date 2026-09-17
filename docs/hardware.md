# Hardware mapping and bench bring-up

This is a wiring plan, not a record of hardware testing. The actual board, sensors and their electrical specifications must be checked before connection. An EK-labelled board is not automatically pin-, firmware- or voltage-equivalent to the official UNO R4 WiFi.

The official UNO R4 WiFi uses a 5 V RA4M1 host MCU, with a separate 3.3 V ESP32-S3 radio. The compiled firmware runs on the RA4M1. The simulation does not put camera or audio processing into its 32 KB SRAM. Source: https://docs.arduino.cc/hardware/uno-r4-wifi .

| Connection | Sketch pin | Note |
|---|---:|---|
| PIR output | D2 | Verify output voltage and module warm-up; use external pulldown if required |
| LD2410-class presence OUT | D3 | Verify exact module logic level and UNO input-high requirement; use proper 3.3-to-5 V translation where required |
| Ultrasonic trigger | D4 | The sketch assumes an HC-SR04-like trigger/echo interface |
| Ultrasonic echo | D5 | Verify echo level; the official UNO R4 main GPIO is a 5 V domain |
| Green LED | D6 | Series current-limiting resistor |
| Yellow LED | D7 | Series current-limiting resistor |
| Red LED | D8 | Series current-limiting resistor |
| Active buzzer control | D9 | Use a suitable transistor driver and correct supply; do not draw buzzer power directly from GPIO |
| Local reset button | D10 to GND | INPUT_PULLUP; clears local alarm latch |
| PC connection | USB-C | Serial data at 115200 baud |
| Shared reference | GND | All low-voltage sensor grounds need a common reference |

Pinout and supply requirements vary across LD2410, LD2410B, LD2410C and clones. The chosen firmware reads only OUT, not UART. It therefore cannot verify radar frame freshness, configure distance gates, or reliably distinguish a wire stuck low from no presence. Test and document this limitation. Consult the exact module manual from its manufacturer before wiring: https://www.hlktech.net/ .

## Power arrangement

For first bench work, use USB power and explicitly accept that fallback ends when USB power disappears. For the later PC-failure demonstration, give the Arduino an independent supported power source using the board manufacturer's guidance. Do not connect arbitrary external 5 V and USB supplies together without verifying the board's power-selection arrangement. Use a normal approved low-voltage supply; no mains wiring is part of the project.

## What the sketch actually does

- It does not block waiting for a PC serial terminal.
- It polls at a nominal 100 ms cadence.
- Echo timeout is bounded at 25 ms. A missing echo is invalid, not a valid zero-metre object.
- PIR and radar need three consecutive active samples.
- Range uses a five-sample median plus three consecutive near results.
- The first 60 seconds inhibit alarms while sensors settle.
- `HB` renews the PC heartbeat; `ALARM` latches the local buzzer. Commands are newline-terminated and length-bounded.
- Missing heartbeat for more than two seconds enables physical fallback.
- A sample gap above 250 ms clears accumulated persistence.
- The official Renesas watchdog is enabled for four seconds and refreshed by the loop.
- Local button reset clears the alarm; it is not an authenticated access-control system.

Output line:

```text
S,sequence,board_millis,pir_filtered,radar_filtered,range_metres,range_valid,alarm,armed
```

`range_metres` may be `nan`. The PC must honor `range_valid`. Opening a port can reset some boards; after reconnection, flush old bytes, establish a new session and remap the board clock. The supplied serial bench tool only displays these fields and sends heartbeats. It is not the complete continuous acquisition/fusion service.

## Small bench sequence

1. Compile and upload with sensors disconnected; confirm boot, status LEDs, serial messages and warm-up.
2. Verify each input separately with a meter/known stimulus. Connect one sensor at a time.
3. Log raw and filtered range while presenting a flat target at measured distances. Record invalid-echo frequency.
4. Measure PIR hold time and retrigger behavior. These depend on the module settings, not just the 0.3-second software persistence.
5. Measure radar responses to empty room, moving fan/curtain, stationary person and activity outside the room.
6. Verify `ALARM` and the local reset button using a low-volume buzzer.
7. Disconnect the PC data link while the board remains powered. Present all three physical stimuli and measure fallback latency.
8. Test board power loss separately. The RAM latch and history do not survive it; the current design cannot claim otherwise.

The recorded target compile used 53,724 bytes of flash and 6,904 bytes of global RAM. Stack usage, electrical behavior, real-time deadlines and watchdog recovery were not measured on a physical board. Compiler success does not establish any of them.
