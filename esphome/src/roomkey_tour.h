#pragma once
// Scripted "tour" through every UI state.
//  • Simulator: RK_TOUR=1 → LVGL snapshots saved as BMP to $RK_SHOTS (default ./shots),
//    RK_TOUR_EXIT=1 quits when done.
//  • Device: build with -DRK_TOUR_ON_BOOT → runs once after boot and logs frame
//    timing, as a performance check for animations on the C6.
#if defined(USE_HOST) || defined(RK_TOUR_ON_BOOT)
#ifdef USE_HOST
#include <sys/stat.h>
#endif

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

#include "roomkey_ui.h"

namespace roomkey {
namespace sim {

#ifdef USE_HOST
inline bool write_bmp(const std::string &path) {
  lv_obj_t *scr = lv_screen_active();
  lv_obj_update_layout(scr);
  lv_draw_buf_t *buf = lv_snapshot_take(scr, LV_COLOR_FORMAT_RGB888);
  if (buf == nullptr) return false;
  const int w = buf->header.w, h = buf->header.h, stride = buf->header.stride;
  const int row = (w * 3 + 3) & ~3;
  const uint32_t size = 54 + row * h;
  uint8_t hdr[54] = {'B', 'M'};
  auto put32 = [&](int off, uint32_t v) {
    for (int i = 0; i < 4; i++) hdr[off + i] = (v >> (8 * i)) & 0xFF;
  };
  put32(2, size);
  put32(10, 54);
  put32(14, 40);
  put32(18, w);
  put32(22, h);
  hdr[26] = 1;
  hdr[28] = 24;
  put32(34, row * h);
  FILE *f = fopen(path.c_str(), "wb");
  if (f == nullptr) {
    lv_draw_buf_destroy(buf);
    return false;
  }
  fwrite(hdr, 1, 54, f);
  std::vector<uint8_t> line(row, 0);
  for (int y = h - 1; y >= 0; y--) {  // RGB888 in LVGL memory is B,G,R — same as BMP
    memcpy(line.data(), buf->data + y * stride, w * 3);
    fwrite(line.data(), 1, row, f);
  }
  fclose(f);
  lv_draw_buf_destroy(buf);
  return true;
}
#else
inline bool write_bmp(const std::string &) { return true; }
#endif

struct Step {
  uint32_t wait_ms;          // delay before this step runs
  std::function<void()> fn;  // optional action
  const char *shot;          // optional snapshot name
};

class Tour {
 public:
  void start() {
#ifdef USE_HOST
    const char *dir = getenv("RK_SHOTS");
    dir_ = dir ? dir : "shots";
    mkdir(dir_.c_str(), 0755);
#else
    dir_ = "device";
#endif
    // Lambdas call ctl() directly: capturing a local reference by reference dangles on GCC.
    auto key = [](bool d) { return [d]() { ctl().key(d); }; };
    steps_ = {
        {600, []() { ctl().clock_locked = true; ctl().set_time(21, 47, true); ctl().set_lights(0); ctl().set_alarm(Alarm::DISARMED); }, "01_home_lights_off"},
        {400, key(true), nullptr},
        {420, nullptr, "02_home_hold_for_menu"},
        {400, key(false), "03_menu"},
        {300, key(true), nullptr},
        {80, key(false), nullptr},
        {300, key(true), nullptr},
        {80, key(false), "04_menu_select_test_ring"},
        {200, key(true), nullptr},
        {650, key(false), nullptr},
        {1100, nullptr, "05_doorbell_ringing"},
        {300, []() { ctl().set_visitor("Paketdienst · DHL"); ctl().set_visitor_role("parcel"); }, "05b_visitor_parcel"},
        {300, []() { ctl().set_visitor("Polizei"); ctl().set_visitor_role("police"); }, "05c_visitor_self_declared"},
        {300, []() { ctl().set_visitor("Anna Schmitz"); ctl().set_visitor_role("name"); ctl().set_visitor_urgent("True"); },
         "05d_visitor_urgent"},
        {200, key(true), nullptr},
        {700, nullptr, "06_call_talking_hold"},
        {400, key(false), nullptr},
        {900, nullptr, "07_call_listening"},
        {300, []() {
           using M = Controller::ChatMsg;
           std::vector<M> chat;
           M a; a.id = "door-1"; a.door = true; a.who = "Paketdienst · DHL"; a.role = "parcel";
           a.text = "Guten Tag, ich habe ein Paket für Sie, passt nicht in den Briefkasten."; chat.push_back(a);
           M b; b.id = "room-1"; b.who = "Jonas"; b.text = "Ich komme gleich runter."; chat.push_back(b);
           M c; c.id = "door-2"; c.door = true; c.who = "Paketdienst · DHL"; c.role = "parcel"; c.lang = "Polish";
           c.text = "Alles klar, ich warte."; chat.push_back(c);
           ctl().set_chat(chat);
           ctl().set_live_text("Kann ich es auch beim Nachbarn");
         }, nullptr},
        {2500, nullptr, "07c_call_chat"},
        {200, key(true), nullptr},
        {90, key(false), nullptr},
        {700, nullptr, "07d_chat_older"},
        {200, key(true), nullptr},
        {90, key(false), nullptr},
        {700, nullptr, "07e_chat_oldest_then_newest"},
        {11000, nullptr, "07b_call_over_after_silence"},   // R17.8: "Call silence end" 10 s without speech
        {200, key(true), nullptr},
        {90, key(false), nullptr},
        {500, key(true), nullptr},
        {90, key(false), "08_home_lights_on"},
        {400, []() { ctl().set_alarm(Alarm::ARMED_NIGHT); }, "09_home_armed_night"},
        {300, key(true), nullptr},
        {850, nullptr, "10_home_hold_to_disarm"},
        {900, nullptr, "11_disarming"},
        {200, key(false), nullptr},
        {650, nullptr, "12_disarmed_flash"},
        {1500, []() { ctl().set_alarm(Alarm::PENDING); }, nullptr},
        {1450, nullptr, "13_alarm_entry_delay"},
        {300, []() { ctl().set_alarm(Alarm::TRIGGERED); }, nullptr},
        {390, nullptr, "14_alarm_triggered"},
        {300, []() { ctl().set_alarm(Alarm::DISARMED); ctl().open_info(); }, "15_room_info"},
        {300, []() { ctl().key(true); ctl().key(false); ctl().set_demo(false); ctl().set_online(false); }, nullptr},
        {300, key(true), nullptr},
        {90, key(false), nullptr},
        {300, nullptr, "16_offline_toast"},
        // R21: a call nobody rang for (another room started it) → the same offer, titled "Call at the door"
        {2000, []() { ctl().set_online(true); ctl().end_call_for_tour(); ctl().set_door_call(false); ctl().set_door_call(true); }, nullptr},
        {400, nullptr, "16b_call_nobody_rang_for_join"},
        {200, []() { ctl().set_door_call(false); }, nullptr},
        // R19: it rings, another room answers → this key offers to join; one press joins (listening, chat)
        {2000, []() { ctl().set_online(true); ctl().ring_start(); }, nullptr},
        {1100, nullptr, "17_ringing_again"},
        {300, []() { ctl().set_door_call(true); ctl().ring_stop(false); }, nullptr},
        {600, nullptr, "18_answered_elsewhere_join"},
        {200, key(true), nullptr},
        {90, key(false), nullptr},
        {800, nullptr, "19_joined_chat_touch"},
        // a hold the timer never saw (the loop was late): key down and up in one go, 400 ms apart → still talk/join
        {300, []() { ctl().end_call_for_tour(); }, nullptr},
        {300, []() { ctl().key_at(true, esphome::millis() - 400); ctl().key(false); }, nullptr},
        {200, nullptr, "21b_late_hold_joined"},
        // live text: a Whisper revision of words already shown appears at once (no retyping from the start)
        {300, []() { ctl().set_live_text("Alice klar, ich habe hier ein Paket für Sie, es passt leider nicht in den Briefkasten."); }, nullptr},
        {4000, nullptr, nullptr},
        {100, []() { ctl().set_live_text("Alles klar, ich habe hier ein Paket für Sie, es passt leider nicht in den Briefkasten. Kann"); }, nullptr},
        {120, nullptr, "22_live_revision_shown_at_once"},
        // T12: the talk clock runs only while talking and starts at 0:00 on every hold, also within one call
        {300, []() { ctl().set_floor_busy(false); ctl().end_call_for_tour(); ctl().set_door_call(false); }, nullptr},
        {300, key(true), nullptr},
        {2600, nullptr, "T12a_talking_clock_runs"},
        {100, key(false), nullptr},
        {600, nullptr, "T12b_listening_no_clock"},
        {5000, key(true), nullptr},
        {500, nullptr, "T12c_talking_again_from_0"},
        {100, key(false), nullptr},
        // R17.14: holding while another room has the floor → "besetzt", nothing is sent
        {200, []() { ctl().set_floor_busy(true); }, nullptr},
        {200, key(true), nullptr},
        {900, nullptr, "20_busy_another_room_talks"},
        {200, []() { ctl().set_floor_busy(false); }, nullptr},
        {300, nullptr, "21_floor_free_talking"},
        {200, key(false), nullptr},
    };
    timer_ = lv_timer_create(&Tour::tick_cb_, 20, this);
    next_at_ = esphome::millis() + 1500;  // let the UI settle
    ESP_LOGI("tour", "tour started, %d steps → %s/", (int) steps_.size(), dir_.c_str());
  }

 protected:
  static void tick_cb_(lv_timer_t *t) { ((Tour *) lv_timer_get_user_data(t))->tick_(); }
  void tick_() {
    uint32_t now = esphome::millis();
    if (last_tick_ && now - last_tick_ > worst_gap_) worst_gap_ = now - last_tick_;
    last_tick_ = now;
    if (now < next_at_) return;
    if (idx_ >= steps_.size()) {
      ESP_LOGI("tour", "tour done — worst LVGL timer gap %u ms", (unsigned) worst_gap_);
      lv_timer_delete(timer_);
#ifdef USE_HOST
      if (getenv("RK_TOUR_EXIT")) exit(0);
#endif
      return;
    }
    Step &s = steps_[idx_++];
    if (s.fn) s.fn();
    if (s.shot) {
      lv_refr_now(nullptr);
      std::string p = dir_ + "/" + s.shot + ".bmp";
      ESP_LOGI("tour", "%s %s (worst gap so far %u ms)", write_bmp(p) ? "shot" : "FAILED", p.c_str(),
               (unsigned) worst_gap_);
      worst_gap_ = 0;
    }
    next_at_ = esphome::millis() + (idx_ < steps_.size() ? steps_[idx_].wait_ms : 0);
  }
  std::vector<Step> steps_;
  size_t idx_ = 0;
  uint32_t next_at_ = 0, last_tick_ = 0, worst_gap_ = 0;
  lv_timer_t *timer_ = nullptr;
  std::string dir_;
};

inline void maybe_start_tour() {
#ifdef USE_HOST
  if (getenv("RK_TOUR") == nullptr) return;
#endif
  static Tour tour;
  tour.start();
}

}  // namespace sim
}  // namespace roomkey
#endif  // USE_HOST || RK_TOUR_ON_BOOT
