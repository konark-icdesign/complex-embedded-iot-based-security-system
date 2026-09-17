#include "../csrc/detection.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>

int main(void) {
    double audio[ROOM_N] = {0}, x[9], center[9] = {0}, scale[9];
    assert(room_features(audio, x) == 0);
    for (unsigned i = 0; i < ROOM_N; ++i) audio[i] = .1*sin(i*.17);
    assert(room_features(audio, x) == 1);
    for (unsigned i = 0; i < 9; ++i) { assert(isfinite(x[i])); scale[i] = 1; }
    assert(isfinite(room_score(x, center, scale)));
    audio[0] = NAN;
    assert(room_features(audio, x) == -1);
    double score;
    assert(!room_confirm(1, &score));
    assert(room_confirm(1U|4U|8U, &score));
    assert(score == 5.5);
    puts("C core boundary checks passed");
    return 0;
}
