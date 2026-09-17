#include "detection.h"
#include <math.h>
#include <stddef.h>

static const double pi = 3.14159265358979323846;

int room_features(const double *audio, double *out) {
    double re[ROOM_N], im[ROOM_N] = {0}, sub[8] = {0};
    double mean = 0, energy = 0, peak = 0;
    unsigned clipped = 0, crossing = 0;
    for (unsigned i = 0; i < ROOM_N; ++i) {
        if (!isfinite(audio[i])) return -1;
        mean += audio[i];
        clipped += fabs(audio[i]) >= .999;
    }
    mean /= ROOM_N;
    for (unsigned i = 0; i < ROOM_N; ++i) {
        const double x = audio[i] - mean;
        energy += x*x;
        sub[i / 256] += x*x / 256;
        if (fabs(x) > peak) peak = fabs(x);
        if (i > 0 && x * (audio[i-1] - mean) < 0) ++crossing;
        re[i] = x * (.5 - .5*cos(2*pi*i/(ROOM_N-1)));
    }
    /* In-place radix-two FFT with bit-reversed input. */
    for (unsigned i = 1, j = 0; i < ROOM_N; ++i) {
        unsigned bit = ROOM_N >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) { const double temp = re[i]; re[i] = re[j]; re[j] = temp; }
    }
    for (unsigned length = 2; length <= ROOM_N; length <<= 1) {
        for (unsigned start = 0; start < ROOM_N; start += length) {
            for (unsigned j = 0; j < length/2; ++j) {
                const double angle = -2*pi*j/length;
                const double wr = cos(angle), wi = sin(angle);
                const unsigned a = start+j, b = a+length/2;
                const double tr = re[b]*wr - im[b]*wi;
                const double ti = re[b]*wi + im[b]*wr;
                re[b] = re[a]-tr; im[b] = im[a]-ti;
                re[a] += tr; im[a] += ti;
            }
        }
    }
    double total = 0;
    for (unsigned i = 0; i <= ROOM_N/2; ++i) {
        re[i] = (re[i]*re[i] + im[i]*im[i]) * ((i && i < ROOM_N/2) ? 2 : 1);
        total += re[i];
    }
    for (unsigned i = 0; i < ROOM_FEATURES; ++i) out[i] = 0;
    double logsum = 0;
    for (unsigned i = 0; i <= ROOM_N/2; ++i) {
        const double p = re[i] / fmax(total, 1e-30);
        const double hz = i * 16000.0 / ROOM_N;
        const unsigned band = hz < 250 ? 0 : hz < 1000 ? 1 : hz < 4000 ? 2 : 3;
        out[band] += p;
        out[4] += p * hz / 8000;
        logsum += log(fmax(p, 1e-30));
    }
    out[5] = exp(logsum/1025)*1025;
    out[6] = crossing / 2047.0;
    const double rms = sqrt(energy/ROOM_N);
    out[7] = log(fmax(peak/fmax(rms, 1e-15), 1));
    double sm = 0, variance = 0;
    for (unsigned i = 0; i < 8; ++i) { sub[i] = sqrt(sub[i]); sm += sub[i]/8; }
    for (unsigned i = 0; i < 8; ++i) variance += (sub[i]-sm)*(sub[i]-sm)/8;
    out[8] = sqrt(variance)/fmax(sm, 1e-15);
    return rms > 1e-7 && clipped <= ROOM_N*.01;
}

double room_score(const double *x, const double *center, const double *scale) {
    double sum = 0;
    for (unsigned i = 0; i < ROOM_FEATURES; ++i) {
        if (!(scale[i] > 0) || !isfinite(scale[i])) return NAN;
        const double z = (x[i]-center[i])/scale[i];
        sum += fmin(z*z, 400);
    }
    return sqrt(sum/ROOM_FEATURES);
}

int room_confirm(unsigned mask, double *score) {
    const double weights[5] = {1.5, 3, 2, 2, 2}; /* A V P M U */
    unsigned physical = 0;
    *score = 0;
    for (unsigned i = 0; i < 5; ++i) {
        if (mask & (1U << i)) { *score += weights[i]; if (i >= 2) ++physical; }
    }
    return *score >= 5 && (((mask & 2U) && physical >= 1) || physical >= 3
                           || ((mask & 1U) && physical >= 2));
}

void room_detect(const double *x, const int *valid, unsigned rows,
                 const double *center, const double *scale, double threshold,
                 double *scores, int *flags) {
    unsigned recent = 0;
    for (unsigned i = 0; i < rows; ++i) {
        scores[i] = room_score(x + i*ROOM_FEATURES, center, scale);
        recent = ((recent << 1) | (unsigned)(valid[i] && scores[i] > threshold)) & 7U;
        const unsigned count = (recent & 1U) + ((recent >> 1) & 1U) + ((recent >> 2) & 1U);
        flags[i] = valid[i] && (count >= 2 || (scores[i] > 2*threshold
                                && x[i*ROOM_FEATURES+7] > log(8)));
    }
}
