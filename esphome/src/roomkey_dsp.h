#pragma once
// Tiny DSP helpers for the microphone path (no dependencies — unit-testable on the host).
#include <algorithm>
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

// One call per audio block (any block size of about 10–30 ms), with the block's level in dBFS.
// Speech = VOICE_DB above the noise floor, for at least a third of the last SUSTAIN_MS:
//   floor     a low percentile (FLOOR_PERCENTILE) of the block levels of the last WINDOW_MS, not the single quietest
//             block: a few dropouts or glitches (partly empty blocks, e.g. I2S) would pull a minimum far down and make
//             all ordinary noise look like speech (found on the door mic, voice v2 live test 01.10.)
//   sustained syllables are loud for 100 ms and more; cracks and clicks for one block. A single loud block is no speech.
// Same as aikos_voice level.h (aikos-home/aikos). Tuned on 67 real key recordings against Whisper (all 50 with speech found, gaps between detections like before) and
// on noise with dropouts and cracks (no false speech); see the PR.
// Muted blocks (< −100 dBFS, e.g. a mic that is just starting) don't count; < MIN_DB is never speech. A steady tone
// without gaps for longer than WINDOW_MS (a whistle, a beeping truck) raises the floor to its own level and stops
// counting after about 1.5 s; that is wanted for words, which always have gaps.
// Thread use: note() from one task (mic or network), the getters from another; the two fields they share are atomic.
class VoiceGate {
 public:
  static constexpr int N = 96;                     // ≥ 1.5 s of 16 ms mic blocks or 20 ms RTP packets
  static constexpr float VOICE_DB = 11.0f;         // above the floor
  static constexpr float MIN_DB = -75.0f;          // quieter than this is never speech
  static constexpr uint32_t WINDOW_MS = 1500;
  static constexpr float FLOOR_PERCENTILE = 0.05f; // the floor ignores the quietest 5 % of the window,
  static constexpr int FLOOR_SKIP = 2;             //   and at least its 2 quietest blocks once it holds a few
  static constexpr uint32_t SUSTAIN_MS = 120;      // at least a third of this loud (and at least 3 blocks seen)

  void note(float db, uint32_t now) {
    if (db < -100.0f)
      return;
    float win[N + 1];
    int n = 0;
    for (int i = 0; i < count_; i++)
      if (now - ms_[i] < WINDOW_MS)
        win[n++] = db_[i];
    win[n++] = db;
    const int k = std::max((int) (FLOOR_PERCENTILE * (float) (n - 1)), n > 8 ? FLOOR_SKIP : 0);
    std::nth_element(win, win + k, win + n);
    floor_ = win[k];
    smooth_ = smooth_ < -100.0f ? db : smooth_ * 0.7f + db * 0.3f;
    const bool loud = smooth_ > floor_ + VOICE_DB && db > MIN_DB;
    db_[i_] = db;
    ms_[i_] = now;
    loud_[i_] = loud;
    i_ = (i_ + 1) % N;
    if (count_ < N)
      count_++;
    int seen = 0, high = 0;
    for (int i = 0; i < count_; i++)
      if (now - ms_[i] < SUSTAIN_MS) {
        seen++;
        high += loud_[i];
      }
    if (loud && n > 8 && seen >= 3 && 3 * high >= seen) {   // n > 8: no verdict before the floor has some history
      last_.store(now, std::memory_order_relaxed);
      voice_.store(true, std::memory_order_release);
    }
  }
  // speech since t0 (wrap-safe for millis())
  bool voiced_since(uint32_t t0) const {
    return voice_.load(std::memory_order_acquire) && (int32_t) (last_.load(std::memory_order_relaxed) - t0) >= 0;
  }
  uint32_t quiet_ms(uint32_t now) const { return now - last_voice_ms(); }  // meaningful once voiced_since() was true
  uint32_t last_voice_ms() const { return last_.load(std::memory_order_relaxed); }
  float floor_db() const { return floor_; }
  void reset() {
    voice_.store(false, std::memory_order_release);
    smooth_ = -120.0f;
  }

 protected:
  float db_[N] = {0};
  uint32_t ms_[N] = {0};
  bool loud_[N] = {false};
  int i_ = 0, count_ = 0;
  float floor_ = 0.0f, smooth_ = -120.0f;
  std::atomic<bool> voice_{false};
  std::atomic<uint32_t> last_{0};
};

}  // namespace roomkey
