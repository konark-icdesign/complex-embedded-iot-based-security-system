# DSP mathematics, from samples to an investigation

## 1. A microphone produces samples

At 16,000 samples per second, the program sees 16,000 numbers every second. These are digital signal values, not calibrated sound pressure. RMS expressed as dBFS is relative to digital full scale, **not dB SPL**.

One frame has 2048 samples, so it spans 2048/16000 = 0.128 seconds. A new frame begins after 1024 samples, or 0.064 seconds. The frames overlap. Their detections are statistically dependent; two overlapping abnormal frames are persistence, not two independent witnesses.

## 2. Remove the DC offset

For each frame, subtract its mean: y[n] = x[n] - mean(x).

A microphone offset should not appear as room sound. The remaining values fluctuate around zero.

RMS = sqrt(sum(y[n]^2)/N). It measures amplitude. If microphone gain becomes three times larger, RMS also becomes three times larger. A detector based only on RMS confuses gain adjustment with a new event.

Crest factor = max(abs(y))/RMS. A short impact can have a large peak compared with average energy. The implementation uses its natural logarithm as one bounded-scale feature.

## 3. Window and FFT

The symmetric Hann window is w[n] = 0.5 - 0.5*cos(2*pi*n/(N-1)). Multiplying y by w reduces artificial spectral spreading at the frame boundaries. The FFT then maps the windowed samples into frequency bins.

Bin spacing is fs/N = 7.8125 Hz. Only 0 to 8 kHz is representable at this sampling rate. Compute one-sided power, doubling bins except DC and Nyquist. Normalize the power by its sum, so p[k] represents the fraction of frame spectral power in bin k.

A gain change g multiplies spectral power by g^2. Dividing by total power cancels that factor. This is why the normalized features are invariant to constant gain in the no-clipping numerical test. Real automatic gain control can vary within a frame and change the features. Saturation destroys information; it is treated as a fault, not cured by normalization.

## 4. Nine shape features

| Feature | Calculation / interpretation |
|---|---|
| Four band fractions | Sum p[k] in 0-250, 250-1000, 1000-4000 and 4000-8000 Hz |
| Normalized centroid | Sum(f[k]*p[k]) / (fs/2); center of spectral power |
| Flatness | Geometric mean of p divided by arithmetic mean; diffuse versus tonal spectrum |
| Zero crossing rate | Fraction of adjacent sample pairs whose product is negative |
| Log crest factor | Log(peak/RMS); prominence of peaks |
| Within-frame energy variation | Divide the frame into 8 pieces, take their RMS values, then population standard deviation / mean |

RMS and dBFS are logged separately. They are not added to the gain-normalized anomaly score. Invalid silence and more than 1% full-scale clipping are flagged as health problems. The thresholds are practical numerical checks, not certified microphone diagnostics.

## 5. Learn an approved baseline

The model is fitted on baseline data and frozen. For each feature i:

center_i = median(training feature i)

scale_i = max(1.4826 * median(abs(feature i - center_i)), floor_i)

The median and median absolute deviation reduce the influence of isolated outliers. The floor prevents division by a nearly zero scale. The 1.4826 factor is a conventional Gaussian consistency scaling; the data are not claimed Gaussian.

Separate training and calibration recordings are used. Synthetic training seeds are 11-14; calibration seeds are 101-102; evaluation seeds start at 1000. No evaluation traces train the deployed model. Dry and rain models are kept separate, with a supplied context label in the synthetic experiment. There is no weather API in this version.

## 6. Score a new frame

z_i = (new_feature_i - center_i) / scale_i

D = sqrt(mean(min(z_i^2, 400)))

Each standardized deviation is capped in magnitude at 20 before averaging its squared value. A single extreme numerical feature therefore cannot become unbounded. This score does not account for feature covariance: the four band fractions sum to one and are correlated. Do not call it a calibrated statistical likelihood or count each feature as separate evidence.

The threshold is max(3.5, 1.2 * calibration 99.5th percentile). The synthetic dry and rain models both used 3.5 in the executed experiment. Different real background recordings produced different thresholds. Two of the last three frames must exceed the threshold. A valid frame with D above twice the threshold and crest factor above 8 can start YELLOW immediately.

Illustrative arithmetic, not a measured recording: if center = 0.20, scale = 0.05 and a new band fraction = 0.40, then z = (0.40-0.20)/0.05 = 4. That is a large deviation in that feature; it still is not proof of a human.

## 7. Median filtering on the Arduino

Example echo sequence, metres: 3.00, 3.02, 0.35, 2.99, 3.01. Sort it: 0.35, 2.99, 3.00, 3.01, 3.02. The median is 3.00. An isolated short echo is rejected.

A sustained near target eventually occupies at least three positions in the five-sample window. Require three successive near medians before asserting proximity. At 10 Hz, the simulated 3.0-to-1.2 m step asserts near evidence after 0.4 seconds when a full far baseline already exists. Invalid/no echo clears the filter; old near distances must not remain valid forever.

Ultrasonic distance is approximated by d = c*t_echo/2, with c = 343 m/s in the sketch. The division by two accounts for the outward and return path. Air conditions, target shape, angle, range and acoustic interference affect a real echo. The simulator models noisy distances, not sound propagation through the room.

## 8. Camera illumination compensation

Naive motion: count pixels for which abs(current - previous) > 12.

Corrected motion: fit current ~= a*previous + b on the majority of pixels, trim high-residual local changes, then count residuals above 12. The fit estimates both multiplicative exposure change a and additive brightness offset b.

The clean synthetic global +60 brightness test changes 100% of pixels by naive subtraction and 0% after compensation. A local 50x30 region in a 160x120 frame changes 1500/19200 = 7.8125% of image area and remains detectable. These figures describe this constructed image test, not expected field performance. A shadow affecting half the picture is not a global illumination change and remains an unresolved visual anomaly.

## 9. Why this is not a PID project

The system estimates conditions and triggers events. It does not regulate a physical variable to a setpoint through a feedback actuator. A PID controller would not solve the classification problem. The relevant subjects are DSP, embedded programming, sensor physics, timing, fault handling and experimental measurement.

## Five questions you should be able to answer

1. Why do RMS-only alarms fail when gain changes?
2. Why does normalized power survive constant gain but not clipping?
3. Why do two abnormal audio frames count as persistence rather than two sensors?
4. Why does an invalid echo have to invalidate old proximity evidence?
5. Why can a mathematically correct fusion rule still alert on a harmless heated object?
