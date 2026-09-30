#pragma once
// Tiny DSP helpers for the microphone path (no dependencies — unit-testable on the host).
#include <cmath>

namespace roomkey {

// RBJ-cookbook biquad, transposed direct form II.
struct Biquad {
  float b0 = 1, b1 = 0, b2 = 0, a1 = 0, a2 = 0, z1 = 0, z2 = 0;

  // 2nd-order Butterworth high-pass. 120 Hz at 16 kHz removes table knocks, handling
  // noise and DC while leaving the speech band (≈150 Hz – 3.4 kHz) untouched.
  static Biquad highpass(float fc, float fs, float q = 0.7071f) {
    const float w = 2.0f * 3.14159265f * fc / fs, cw = cosf(w), alpha = sinf(w) / (2.0f * q), a0 = 1.0f + alpha;
    Biquad f;
    f.b0 = (1.0f + cw) / 2.0f / a0;
    f.b1 = -(1.0f + cw) / a0;
    f.b2 = (1.0f + cw) / 2.0f / a0;
    f.a1 = -2.0f * cw / a0;
    f.a2 = (1.0f - alpha) / a0;
    return f;
  }

  float process(float x) {
    float y = b0 * x + z1;
    z1 = b1 * x - a1 * y + z2;
    z2 = b2 * x - a2 * y;
    return y;
  }
};

// Peak limiter for the mic stream (int16 scale): instant attack, ~120 ms release. Loud speech
// close to the mic is turned down smoothly instead of being clipped (clipping costs words).
struct Limiter {
  float env = 0.0f;
  float ceiling = 0.8f * 32767.0f;  // ≈ −2 dBFS
  float process(float v) {
    float a = v < 0 ? -v : v;
    env = a > env ? a : env * 0.9995f + a * 0.0005f;
    return env > ceiling ? v * (ceiling / env) : v;
  }
};

}  // namespace roomkey
