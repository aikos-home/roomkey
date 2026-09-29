#pragma once
// Microphone bring-up helper (dev tool, used by mic_test.yaml).
// Logs level / peak / zero-crossing pitch / stuck-bit masks every 250 ms, then records
// a clip and dumps it over the log as base64 so the host can rebuild a WAV.
#include <cmath>
#include <cstdint>
#include <cstdlib>

#include "esphome/core/hal.h"
#include "esphome/core/log.h"

namespace mictest {

static const char *const TAG = "mictest";
constexpr int RATE = 16000;
constexpr int CAP_SAMPLES = RATE * 5;

enum State { WARMUP, CAPTURING, DUMPING, DONE };

struct Stats {
  double sumsq = 0;
  int32_t peak = 0, zc = 0, n = 0, zeros = 0;
  uint32_t or_bits = 0, and_bits = 0xFFFFFFFF;
  int32_t prev = 0;
};

inline Stats g_stats;
inline volatile State g_state = WARMUP;
inline int16_t *g_cap = nullptr;
inline volatile int g_cap_n = 0;
inline int g_dump_pos = 0;

// mic task
inline void on_data(const std::vector<uint8_t> &x) {
  const size_t n = x.size() / 4;
  const int32_t *s = reinterpret_cast<const int32_t *>(x.data());
  Stats &st = g_stats;
  for (size_t i = 0; i < n; i++) {
    int32_t v = s[i];
    double f = v / 2147483648.0;
    st.sumsq += f * f;
    int32_t a = v < 0 ? -(v >> 8) : (v >> 8);
    if (a > st.peak) st.peak = a;
    if ((v < 0) != (st.prev < 0)) st.zc++;
    st.prev = v;
    if (v == 0) st.zeros++;
    st.or_bits |= (uint32_t) v;
    st.and_bits &= (uint32_t) v;
    st.n++;
    if (g_state == CAPTURING && g_cap && g_cap_n < CAP_SAMPLES) g_cap[g_cap_n++] = (int16_t) (v >> 16);
  }
  if (g_state == CAPTURING && g_cap_n >= CAP_SAMPLES) g_state = DUMPING;
}

// main loop, every 250 ms
inline void report() {
  Stats st = g_stats;
  g_stats = Stats{};
  g_stats.prev = st.prev;
  if (st.n == 0) {
    ESP_LOGW(TAG, "no samples received (mic task not delivering data)");
    return;
  }
  double db = 10.0 * log10(st.sumsq / st.n + 1e-12);
  double peak_db = 20.0 * log10(st.peak / 8388608.0 + 1e-9);
  int hz = (int) (st.zc / 2.0 / (st.n / (double) RATE));
  ESP_LOGI(TAG, "LEVEL rms=%.1f dBFS peak=%.1f dBFS pitch~%d Hz zeros=%d%% or=%08X and=%08X n=%d", db, peak_db, hz,
           (int) (100L * st.zeros / st.n), (unsigned) st.or_bits, (unsigned) st.and_bits, (int) st.n);
}

inline void start_capture() {
  if (!g_cap) g_cap = (int16_t *) malloc(CAP_SAMPLES * sizeof(int16_t));
  if (!g_cap) { ESP_LOGE(TAG, "no RAM for capture"); return; }
  g_cap_n = 0;
  g_dump_pos = 0;
  ESP_LOGI(TAG, "CAPTURE ARMED %d samples @ %d Hz", CAP_SAMPLES, RATE);
  g_state = CAPTURING;
}

// main loop, every 10 ms: emit a few base64 lines
inline void dump_some() {
  if (g_state != DUMPING) return;
  static const char *B = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  const uint8_t *bytes = reinterpret_cast<const uint8_t *>(g_cap);
  const int total = CAP_SAMPLES * 2;
  for (int line = 0; line < 6 && g_dump_pos < total; line++) {
    char out[260];
    int o = 0, end = g_dump_pos + 192 < total ? g_dump_pos + 192 : total;
    for (int i = g_dump_pos; i < end; i += 3) {
      uint32_t v = bytes[i] << 16 | (i + 1 < end ? bytes[i + 1] << 8 : 0) | (i + 2 < end ? bytes[i + 2] : 0);
      out[o++] = B[(v >> 18) & 63];
      out[o++] = B[(v >> 12) & 63];
      out[o++] = i + 1 < end ? B[(v >> 6) & 63] : '=';
      out[o++] = i + 2 < end ? B[v & 63] : '=';
    }
    out[o] = 0;
    ESP_LOGI(TAG, "B64 %d %s", g_dump_pos, out);
    g_dump_pos = end;
  }
  if (g_dump_pos >= total) {
    ESP_LOGI(TAG, "CAPTURE END bytes=%d", total);
    g_state = DONE;
  }
}

}  // namespace mictest
