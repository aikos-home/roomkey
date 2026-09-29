#pragma once
// ─────────────────────────────────────────────────────────────────────────────
// RoomKey audio link (WIP) — half-duplex intercom media over UDP.
//
//   Format   RTP (RFC 3550) · L16 big-endian (RFC 3551) · 16 kHz · mono ·
//            dynamic payload type 96 · 20 ms / 320 samples per packet
//   Port     local UDP 5004 (configurable)
//   Peer     set explicitly (action set_intercom_peer) or *latched*: the first
//            host that streams to us becomes the peer (symmetric RTP) — so the
//            door station only needs to know the key's IP.
//
// Signalling (who talks when) is NOT here: it goes through Home Assistant
// (events answer / talk_start / talk_stop / hangup, action call_state).
// Threading: push_*() is called from the microphone task and only writes a
// lock-free SPSC ring; loop() runs in the main loop and owns the socket.
// ─────────────────────────────────────────────────────────────────────────────

#include <atomic>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <functional>
#include <string>

#include "esphome/core/hal.h"
#include "esphome/core/log.h"

#ifdef USE_HOST
#include <arpa/inet.h>
#include <fcntl.h>
#include <netdb.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>
#else
#include "lwip/netdb.h"
#include "lwip/sockets.h"
#endif

namespace roomkey {

class AudioLink {
 public:
  static constexpr int RATE = 16000;
  static constexpr int FRAME = 320;  // 20 ms
  static constexpr uint8_t PT_L16 = 96;

  bool begin(uint16_t port) {
    if (sock_ >= 0) return true;
    sock_ = ::socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock_ < 0) { ESP_LOGE(TAG, "socket() failed"); return false; }
    sockaddr_in a{};
    a.sin_family = AF_INET;
    a.sin_port = htons(port);
    a.sin_addr.s_addr = htonl(INADDR_ANY);
    if (::bind(sock_, (sockaddr *) &a, sizeof(a)) < 0) {
      ESP_LOGE(TAG, "bind(%u) failed", port);
      ::close(sock_);
      sock_ = -1;
      return false;
    }
    int fl = ::fcntl(sock_, F_GETFL, 0);
    ::fcntl(sock_, F_SETFL, fl | O_NONBLOCK);
    ssrc_ = 0x524B0000u ^ (uint32_t) esphome::millis();  // "RK" + noise
    port_ = port;
    ESP_LOGI(TAG, "RTP/L16 16 kHz listening on UDP %u", port);
    return true;
  }

  void set_peer(const std::string &host, uint16_t port) {
    sockaddr_in a{};
    a.sin_family = AF_INET;
    a.sin_port = htons(port);
    if (::inet_aton(host.c_str(), &a.sin_addr) == 0) {
      addrinfo hints{}, *res = nullptr;
      hints.ai_family = AF_INET;
      hints.ai_socktype = SOCK_DGRAM;
      if (::getaddrinfo(host.c_str(), nullptr, &hints, &res) != 0 || res == nullptr) {
        ESP_LOGW(TAG, "cannot resolve peer %s", host.c_str());
        return;
      }
      a.sin_addr = ((sockaddr_in *) res->ai_addr)->sin_addr;
      ::freeaddrinfo(res);
    }
    peer_ = a;
    has_peer_ = true;
    latched_ = false;
    ESP_LOGI(TAG, "peer set to %s:%u", ::inet_ntoa(a.sin_addr), port);
  }
  void clear_peer() { has_peer_ = false; latched_ = false; }
  // End of a call: forget a latched peer so the next caller can latch.
  void end_session() {
    set_tx(false);
    if (latched_) clear_peer();
  }
  // Accept incoming audio only while a call is active. Outside a call every packet is
  // dropped unheard and nobody can latch — otherwise any device on the LAN could play
  // sound in a bedroom.
  void set_accept(bool on) {
    if (accept_ && !on && latched_) clear_peer();
    accept_ = on;
  }
  // Where received audio goes (the speaker). Unset = received audio is only metered.
  std::function<void(const int16_t *, size_t)> sink;

  // Transmit gate (push-to-talk). Frames are only sent while on.
  void set_tx(bool on) {
    tx_ = on;
    tail_.store(head_.load(std::memory_order_acquire));  // consumer-side drop of stale samples
  }
  bool tx() const { return tx_; }

  // Producer side (microphone task): Q31 samples, optional gain.
  void push_q31(const int32_t *s, size_t n, float gain = 4.0f) {
    if (!tx_) return;
    for (size_t i = 0; i < n; i++) {
      float v = (s[i] >> 16) * gain;
      put_((int16_t) (v > 32767.f ? 32767 : v < -32768.f ? -32768 : v));
    }
  }
  void push_s16(const int16_t *s, size_t n) {
    if (!tx_) return;
    for (size_t i = 0; i < n; i++) put_(s[i]);
  }

  // Main loop: send complete frames, receive packets into `sink`.
  void loop() {
    if (sock_ < 0) return;
    // ── transmit ──
    while (tx_ && has_peer_ && avail_() >= FRAME) {
      uint8_t pkt[12 + FRAME * 2];
      pkt[0] = 0x80;
      pkt[1] = PT_L16 | (first_ ? 0x80 : 0);  // marker bit on the first packet of a talk spurt
      first_ = false;
      pkt[2] = seq_ >> 8; pkt[3] = seq_ & 0xFF;
      pkt[4] = ts_ >> 24; pkt[5] = ts_ >> 16; pkt[6] = ts_ >> 8; pkt[7] = ts_;
      pkt[8] = ssrc_ >> 24; pkt[9] = ssrc_ >> 16; pkt[10] = ssrc_ >> 8; pkt[11] = ssrc_;
      for (int i = 0; i < FRAME; i++) {
        int16_t v = get_();
        pkt[12 + 2 * i] = (uint16_t) v >> 8;  // L16 is network byte order
        pkt[13 + 2 * i] = v & 0xFF;
      }
      ::sendto(sock_, pkt, sizeof(pkt), 0, (sockaddr *) &peer_, sizeof(peer_));
      seq_++;
      ts_ += FRAME;
      tx_pkts++;
    }
    if (!tx_) first_ = true;
    // ── receive ──
    for (int guard = 0; guard < 16; guard++) {
      uint8_t buf[1500];
      sockaddr_in from{};
      socklen_t fl = sizeof(from);
      int n = ::recvfrom(sock_, buf, sizeof(buf), 0, (sockaddr *) &from, &fl);
      if (n <= 12) break;
      if (!accept_) { rx_dropped++; continue; }                        // no call → drop unheard
      if ((buf[0] >> 6) != 2 || (buf[1] & 0x7F) != PT_L16) continue;  // RTP v2, L16 only
      int hdr = 12 + 4 * (buf[0] & 0x0F);
      if (n <= hdr) continue;
      if (!has_peer_) {  // symmetric RTP: answer whoever talks to us
        peer_ = from;
        has_peer_ = latched_ = true;
        ESP_LOGI(TAG, "latched peer %s:%u", ::inet_ntoa(from.sin_addr), ntohs(from.sin_port));
      }
      size_t count = (n - hdr) / 2;
      int16_t pcm[(1500 - 12) / 2];
      float acc = 0;
      for (size_t i = 0; i < count; i++) {
        pcm[i] = (int16_t) ((buf[hdr + 2 * i] << 8) | buf[hdr + 2 * i + 1]);
        float f = pcm[i] / 32768.f;
        acc += f * f;
      }
      float db = 10.f * log10f(acc / (count ? count : 1) + 1e-12f);
      float lvl = (db + 60.f) / 50.f;
      rx_level = lvl < 0 ? 0 : lvl > 1 ? 1 : lvl;
      rx_pkts++;
      last_rx_ms_ = esphome::millis();
      if (!tx_ && sink) sink(pcm, count);  // half-duplex: never play while talking
    }
    if (rx_level > 0 && esphome::millis() - last_rx_ms_ > 300) rx_level = 0;
  }

  bool active() const { return sock_ >= 0; }
  uint32_t tx_pkts = 0, rx_pkts = 0, rx_dropped = 0;
  float rx_level = 0;

 protected:
  static constexpr const char *TAG = "roomkey.audio";
  static constexpr uint32_t RING = 4096;  // 256 ms
  void put_(int16_t v) {
    uint32_t h = head_.load(std::memory_order_relaxed);
    if (h - tail_.load(std::memory_order_acquire) >= RING) return;  // full: drop
    ring_[h % RING] = v;
    head_.store(h + 1, std::memory_order_release);
  }
  int16_t get_() {
    uint32_t t = tail_.load(std::memory_order_relaxed);
    int16_t v = ring_[t % RING];
    tail_.store(t + 1, std::memory_order_release);
    return v;
  }
  uint32_t avail_() const { return head_.load(std::memory_order_acquire) - tail_.load(std::memory_order_relaxed); }

  int sock_ = -1;
  uint16_t port_ = 0;
  sockaddr_in peer_{};
  bool has_peer_ = false, latched_ = false, first_ = true, accept_ = false;
  volatile bool tx_ = false;
  uint16_t seq_ = 0;
  uint32_t ts_ = 0, ssrc_ = 0, last_rx_ms_ = 0;
  int16_t ring_[RING];
  std::atomic<uint32_t> head_{0}, tail_{0};
};

inline AudioLink &audio() {
  static AudioLink a;
  return a;
}

}  // namespace roomkey
