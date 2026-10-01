#pragma once
// Tiny DSP helpers for the microphone path (no dependencies — unit-testable on the host).
#include <atomic>
#include <cmath>
#include <cstdint>

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

// "Is somebody talking?" from levels alone (one call per audio block, any block size ~10–30 ms).
// Speech = VOICE_DB above the noise floor, the quietest block of the last WINDOW_MS: speech has gaps between
// words, steady noise (street, fan) does not. A single loud block is not speech (smoothed). Muted blocks
// (< −100 dB) don't count. Time comes in as `now` (ms), so it runs on a PC for tests. A steady tone without gaps
// for more than WINDOW_MS raises the floor and stops counting (wanted: words always have gaps).
// Same as aikos_voice level.h (aikos-home/aikos).
struct VoiceGate {
  static constexpr int N = 96;              // ≥ 1.5 s of 16 ms mic blocks or 20 ms RTP packets
  static constexpr float VOICE_DB = 12.0f;
  static constexpr uint32_t WINDOW_MS = 1500;
  void note(float db, uint32_t now) {
    if (db < -100.0f) return;
    db_[i_] = db;
    ms_[i_] = now;
    i_ = (i_ + 1) % N;
    float floor = db;
    for (int i = 0; i < N; i++)
      if (now - ms_[i] < WINDOW_MS && db_[i] < floor) floor = db_[i];
    floor_ = floor;
    smooth_ = smooth_ < -100.0f ? db : smooth_ * 0.7f + db * 0.3f;
    if (smooth_ > floor + VOICE_DB && db > -75.0f) {
      last_.store(now, std::memory_order_relaxed);
      voice_.store(true, std::memory_order_release);
    }
  }
  bool voiced_since(uint32_t t0) const {   // wrap-safe
    return voice_.load(std::memory_order_acquire) && (int32_t) (last_.load(std::memory_order_relaxed) - t0) >= 0;
  }
  uint32_t quiet_ms(uint32_t now) const { return now - last_voice_ms(); }
  uint32_t last_voice_ms() const { return last_.load(std::memory_order_relaxed); }
  float floor_db() const { return floor_; }
  void reset() { voice_.store(false, std::memory_order_release), smooth_ = -120.0f; }

 private:
  float db_[N] = {0};
  uint32_t ms_[N] = {0};
  int i_ = 0;
  float floor_ = 0.0f, smooth_ = -120.0f;
  std::atomic<bool> voice_{false};   // written by the audio task, read by the main loop
  std::atomic<uint32_t> last_{0};
};

}  // namespace roomkey
