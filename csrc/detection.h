#ifndef ROOM_DETECTION_H
#define ROOM_DETECTION_H
#define ROOM_N 2048
#define ROOM_FEATURES 9
/* Host-side C numerical core, not intended for UNO audio processing. */
int room_features(const double *audio, double *out);
double room_score(const double *x, const double *center, const double *scale);
int room_confirm(unsigned mask, double *score);
void room_detect(const double *x, const int *valid, unsigned rows,
                 const double *center, const double *scale, double threshold,
                 double *scores, int *flags);
#endif
