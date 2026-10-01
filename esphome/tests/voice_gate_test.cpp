// Host test for roomkey::VoiceGate (src/roomkey_dsp.h): "is somebody talking?" from levels alone.
//   g++ -std=c++17 -Wall -Wextra -I esphome/src esphome/tests/voice_gate_test.cpp -o t && ./t
#include <cstdint>
#include <cstdio>
#include "roomkey_dsp.h"

using roomkey::VoiceGate;
static int fails = 0, checks = 0;
#define CHECK(c, what)                                \
  do {                                                \
    checks++;                                         \
    if (!(c)) fails++, printf("  FAIL: %s\n", what);  \
  } while (0)

// feed `ms` of blocks (20 ms each) at a level given per block
template<typename F> static uint32_t feed(VoiceGate &g, uint32_t t, uint32_t ms, F level) {
  for (uint32_t k = 0; k < ms / 20; k++, t += 20) g.note(level(k), t);
  return t;
}

int main() {
  {
    VoiceGate g;
    uint32_t t = feed(g, 1000, 3000, [](uint32_t) { return -50.0f; });
    CHECK(!g.voiced_since(0), "steady street noise is not speech");
    t = feed(g, t, 1000, [](uint32_t k) { return (k / 5) % 2 ? -46.0f : -52.0f; });
    CHECK(!g.voiced_since(0), "noise that wobbles by 6 dB is not speech");
  }
  {
    VoiceGate g;
    uint32_t t = feed(g, 1000, 1000, [](uint32_t) { return -50.0f; });
    const uint32_t t_speech = t;
    t = feed(g, t, 2000, [](uint32_t k) { return (k / 8) % 3 == 2 ? -48.0f : -28.0f; });   // words with gaps
    CHECK(g.voiced_since(t_speech), "words with gaps over noise are speech");
    CHECK(g.quiet_ms(t) < 300, "quiet time is short while talking");
    t = feed(g, t, 4000, [](uint32_t) { return -50.0f; });
    CHECK(g.quiet_ms(t) >= 3500, "after the talk the quiet time grows");
    CHECK(!g.voiced_since(t - 3000), "nothing said in the last 3 s");
  }
  {
    VoiceGate g;
    uint32_t t = feed(g, 1000, 1500, [](uint32_t) { return -50.0f; });
    g.note(-15.0f, t);   // one knock
    t = feed(g, t + 20, 1000, [](uint32_t) { return -50.0f; });
    CHECK(!g.voiced_since(0), "a single knock is not speech");
  }
  {
    VoiceGate g;
    uint32_t t = feed(g, 1000, 1000, [](uint32_t) { return -120.0f; });   // muted mic start
    t = feed(g, t, 1000, [](uint32_t) { return -50.0f; });
    CHECK(!g.voiced_since(0), "muted blocks don't lower the floor (no false speech after a muted start)");
  }
  {
    VoiceGate g;
    uint32_t t = feed(g, 1000, 1000, [](uint32_t) { return -95.0f; });
    t = feed(g, t, 1000, [](uint32_t k) { return k % 4 == 3 ? -95.0f : -80.0f; });
    CHECK(!g.voiced_since(0), "whisper-quiet levels (< -75 dBFS) are not speech");
  }
  {
    VoiceGate g;                                                       // millis() wraps after 49.7 days
    uint32_t t0 = 0xFFFFF800u;                                         // 2 s before the wrap
    uint32_t t = feed(g, t0, 1000, [](uint32_t) { return -50.0f; });
    t = feed(g, t, 2000, [](uint32_t k) { return (k / 8) % 3 == 2 ? -48.0f : -28.0f; });
    CHECK(t < t0 && g.voiced_since(t0), "voiced_since works across the millis() wrap");
  }
  {  // door mic, voice v2 live test 01.10.: dropouts (partly empty blocks) pulled the old minimum floor far down
    VoiceGate g;
    feed(g, 1000, 6000, [](uint32_t k) { return k % 40 == 7 ? -85.0f : (k % 3 ? -40.0f : -41.5f); });
    CHECK(!g.voiced_since(0), "dropouts (1 block in 40 at -85 dBFS) don't turn the noise into speech");
  }
  {
    VoiceGate g;
    feed(g, 1000, 6000, [](uint32_t k) { return k % 6 == 0 ? -24.0f : -40.0f; });
    CHECK(!g.voiced_since(0), "single loud blocks (cracks, 8 per second) are not speech");
  }
  {
    VoiceGate g;
    feed(g, 1000, 6000, [](uint32_t k) { return k % 40 < 2 ? -20.0f : -40.0f; });
    CHECK(!g.voiced_since(0), "two loud blocks in a row are not speech either");
  }
  printf("%d checks, %d failed\n", checks, fails);
  return fails ? 1 : 0;
}
