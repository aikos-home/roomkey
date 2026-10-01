#pragma once
// ─────────────────────────────────────────────────────────────────────────────
// RoomKey — per-room key for lights · alarm · doorbell · intercom
//
// This header owns the UI, the input grammar and the interaction state machine.
// It knows nothing about GPIOs or Home Assistant: YAML feeds it state
// (set_lights, set_alarm, ring_start, …) and receives intents through Hooks
// (toggle_lights, disarm, answer, talk, …).
//
// Input grammar (works key-only; touch is an optional extra layer):
//   PRESS  (click)  → the obvious thing for the current screen
//   HOLD   (≥ t)    → the deliberate thing (disarm, menu, push-to-talk)
//   A mechanical press always starts as a touch → a key-down cancels the touch
//   gesture in progress, so one physical press never fires twice.
// ─────────────────────────────────────────────────────────────────────────────

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <functional>
#include <string>
#include <vector>

#include "esphome/core/hal.h"
#include "esphome/core/log.h"
#include "lvgl.h"

#ifdef USE_HOST
#include <cstdlib>
#endif

namespace roomkey {

using esphome::millis;
static const char *const TAG = "roomkey";

// ── Palette ──────────────────────────────────────────────────────────────────
namespace pal {
constexpr uint32_t BG = 0x0A0C0F;
constexpr uint32_t SURFACE = 0x15181D;
constexpr uint32_t RAISED = 0x1F232A;
constexpr uint32_t LINE = 0x2C313A;
constexpr uint32_t TEXT = 0xEEF1F5;
constexpr uint32_t MUTED = 0x8B93A1;
constexpr uint32_t FAINT = 0x4B525E;
constexpr uint32_t AMBER = 0xFFB547;   // light
constexpr uint32_t CYAN = 0x3CC8E8;    // door / intercom
constexpr uint32_t GREEN = 0x39D98A;   // talking / ok
constexpr uint32_t RED = 0xFF4D57;     // alarm
constexpr uint32_t ORANGE = 0xFF8A3D;  // entry / exit delay
}  // namespace pal

// ── Icons (Material Design Icons, same names as mdi: in Home Assistant) ──────
// Every codepoint here must also be listed in the icon font glyphs (YAML).
namespace icon {
constexpr const char *BULB = "\U000F0335";          // mdi:lightbulb
constexpr const char *BULB_OUTLINE = "\U000F0336";  // mdi:lightbulb-outline
constexpr const char *BELL_RING = "\U000F009E";     // mdi:bell-ring
constexpr const char *SHIELD_HOME = "\U000F068A";   // mdi:shield-home
constexpr const char *SHIELD_LOCK = "\U000F099D";   // mdi:shield-lock
constexpr const char *SHIELD_CHECK = "\U000F0565";  // mdi:shield-check
constexpr const char *SHIELD_ALERT = "\U000F0ECC";  // mdi:shield-alert
constexpr const char *SHIELD_MOON = "\U000F1828";   // mdi:shield-moon
constexpr const char *SHIELD_AWAY = "\U000F06BB";   // mdi:shield-airplane
constexpr const char *ALARM_LIGHT = "\U000F078F";   // mdi:alarm-light
constexpr const char *MIC = "\U000F036C";           // mdi:microphone
constexpr const char *EAR = "\U000F07C5";           // mdi:ear-hearing
constexpr const char *HANGUP = "\U000F03F5";        // mdi:phone-hangup
constexpr const char *PHONE_TALK = "\U000F03F6";    // mdi:phone-in-talk (md + lg fonts)
constexpr const char *CLOUD_OFF = "\U000F0164";     // mdi:cloud-off-outline
constexpr const char *CHECK = "\U000F0E1E";         // mdi:check-bold
constexpr const char *CLOSE = "\U000F1398";         // mdi:close-thick
constexpr const char *INFO = "\U000F02FD";          // mdi:information-outline
constexpr const char *TIMER = "\U000F051F";         // mdi:timer-sand
constexpr const char *DOOR = "\U000F081A";          // mdi:door

// Visitor types (speaker_role from the door transcriber; aikos features/sprechen.md §2c). Small icon font only.
inline const char *visitor(const std::string &role) {
  static const struct { const char *role, *glyph; } MAP[] = {
      {"emergency", "\U000F0026"},       // alert
      {"parcel", "\U000F03D7"},          // package-variant-closed
      {"mail", "\U000F01F0"},            // email-outline
      {"food", "\U000F025A"},            // food
      {"shopping", "\U000F0111"},        // cart-outline
      {"pharmacy", "\U000F03F1"},        // mortar-pestle-plus (MDI has no "pharmacy" any more)
      {"flowers", "\U000F024A"},         // flower
      {"freight", "\U000F053D"},         // truck
      {"police", "\U000F1167"},          // police-badge
      {"fire", "\U000F08AB"},            // fire-truck
      {"ambulance", "\U000F002F"},       // ambulance
      {"officials", "\U000F0991"},       // office-building
      {"utility", "\U000F1A57"},         // meter-electric
      {"telecom", "\U000F0469"},         // router-wireless
      {"trades", "\U000F1323"},          // hammer-wrench
      {"chimney", "\U000F112B"},         // home-roof
      {"waste", "\U000F0A7A"},           // trash-can-outline
      {"care", "\U000F06EF"},            // medical-bag
      {"property", "\U000F1574"},        // key-chain
      {"household_help", "\U000F00E2"},  // broom
      {"neighbour", "\U000F0826"},       // home-account
      {"family", "\U000F02D1"},          // heart
      {"kids_friend", "\U000F02E7"},     // human-child
      {"taxi", "\U000F04FF"},            // taxi
      {"sales", "\U000F0A38"},           // clipboard-text-outline
      {"religion", "\U000F14F7"},        // book-open-variant
      {"seasonal", "\U000F0AE2"},        // star-four-points
      {"campaign", "\U000F0A1F"},        // vote
      {"name", "\U000F0004"},            // account
  };
  for (const auto &m : MAP)
    if (role == m.role) return m.glyph;
  return "\U000F12E6";  // doorbell: nobody said who they are
}
// Types people claim at the door to get in ("laut Besucher"): shown with a "?" (§2c)
inline bool self_declared(const std::string &role) {
  return role == "police" || role == "officials" || role == "utility" || role == "trades";
}
}  // namespace icon

// ── Strings ──────────────────────────────────────────────────────────────────
struct Strings {
  const char *press, *hold;
  const char *lights_on, *lights_off, *lights_unknown;
  const char *a_lights, *a_menu, *a_disarm, *a_answer, *a_talk, *a_end, *a_next, *a_select, *a_back, *a_cancel, *a_older;
  const char *doorbell, *listening, *talking, *connecting;
  const char *alarm, *entry_delay, *hold_to_disarm, *disarming, *disarmed, *not_confirmed;
  const char *armed_home, *armed_away, *armed_night, *armed_vacation, *armed_custom, *arming;
  const char *m_title, *m_talk, *m_info, *m_test_ring, *m_test_alarm, *m_close;
  const char *offline, *missed, *demo, *ha_on, *ha_off, *not_sent;
  const char *tap_hint;
  const char *speaks;  // printf: the visitor's language
  const char *answered, *join_hint, *a_join, *hold_here;  // another room answered (R19); touch: hold below the chat
  const char *busy;                                       // another room has the floor (R17.14)
  const char *door_call;                                  // a call at the door this key is not in (R21)
};

static const Strings STR_EN = {
    "PRESS", "HOLD",
    "Lights on", "Lights off", "Lights",
    "Lights", "Menu", "Disarm", "Answer", "Talk", "End", "Next", "Select", "Back", "Cancel", "Older",
    "Doorbell", "Listening", "Talking", "Connecting",
    "ALARM", "ENTRY DELAY", "Hold to disarm", "Disarming", "Disarmed", "Not confirmed",
    "Armed · Home", "Armed · Away", "Armed · Night", "Armed · Vacation", "Armed", "Arming",
    "MENU", "Talk to door", "Room info", "Test doorbell", "Test alarm", "Close",
    "Offline", "missed", "Demo mode", "connected", "offline", "Offline · not sent",
    "Press the key for lights",
    "Speaks %s",
    "Answered", "Press to listen in", "Listen", "Hold here to talk",
    "Busy · another room talks",
    "Call at the door",
};

static const Strings STR_DE = {
    "DRÜCKEN", "HALTEN",
    "Licht an", "Licht aus", "Licht",
    "Licht", "Menü", "Unscharf", "Annehmen", "Sprechen", "Auflegen", "Weiter", "Wählen", "Zurück", "Abbruch", "Früher",
    "Klingel", "Hören", "Sprechen", "Verbinde",
    "ALARM", "VORALARM", "Halten = entschärfen", "Entschärfe", "Entschärft", "Nicht bestätigt",
    "Scharf · Zuhause", "Scharf · Abwesend", "Scharf · Nacht", "Scharf · Urlaub", "Scharf", "Schärfe",
    "MENÜ", "Mit Tür sprechen", "Rauminfo", "Klingel testen", "Alarm testen", "Schließen",
    "Offline", "verpasst", "Demo-Modus", "verbunden", "offline", "Offline · nicht gesendet",
    "Taste drücken für Licht",
    "Spricht %s",
    "Angenommen", "Drücken: mithören", "Mithören", "Hier halten: sprechen",
    "Besetzt · anderer Raum spricht",
    "Gespräch an der Tür",
};

// ── Model ────────────────────────────────────────────────────────────────────
enum class Alarm : uint8_t {
  UNKNOWN, DISARMED, ARMING, ARMED_HOME, ARMED_AWAY, ARMED_NIGHT, ARMED_VACATION, ARMED_CUSTOM, PENDING, TRIGGERED
};
enum class View : uint8_t { HOME, MENU, INFO, RING, CALL, ALARM };
enum class Screen : uint8_t { ACTIVE, DIM, OFF };

inline Alarm parse_alarm(const std::string &s) {
  if (s == "disarmed") return Alarm::DISARMED;
  if (s == "arming") return Alarm::ARMING;
  if (s == "armed_home") return Alarm::ARMED_HOME;
  if (s == "armed_away") return Alarm::ARMED_AWAY;
  if (s == "armed_night") return Alarm::ARMED_NIGHT;
  if (s == "armed_vacation") return Alarm::ARMED_VACATION;
  if (s == "armed_custom_bypass") return Alarm::ARMED_CUSTOM;
  if (s == "pending") return Alarm::PENDING;
  if (s == "triggered") return Alarm::TRIGGERED;
  return Alarm::UNKNOWN;
}
inline bool is_armed(Alarm a) { return a >= Alarm::ARMED_HOME && a <= Alarm::ARMED_CUSTOM; }

struct Fonts {
  const lv_font_t *small = nullptr;    // 13 px  hints, status, captions
  const lv_font_t *body = nullptr;     // 17 px  list items, clock
  const lv_font_t *title = nullptr;    // 22 px  screen titles
  const lv_font_t *big = nullptr;      // 34 px  call timer
  const lv_font_t *icon_sm = nullptr;  // 16 px  status bar
  const lv_font_t *icon_md = nullptr;  // 24 px  menu
  const lv_font_t *icon_lg = nullptr;  // 60 px  hero icon
};

// Everything the controller asks the outside world to do.
struct Hooks {
  std::function<void()> toggle_lights;             // → HA light.toggle
  std::function<void()> disarm;                    // → HA disarm script
  std::function<void()> answer;                    // ring answered in this room
  std::function<void()> dismiss;                   // ring silenced in this room
  std::function<void()> call_door;                 // outgoing intercom session
  std::function<void()> hangup;                    // end intercom session
  std::function<void(bool)> talk;                  // push-to-talk edge
  std::function<void(bool)> ringtone;              // start / stop ring sound
  std::function<void(float)> backlight;            // 0..1
  std::function<void(uint32_t, const char *)> led; // colour, effect: off|solid|pulse|strobe
  std::function<void(const char *)> gesture;       // raw input log → HA event entity
  std::function<void(bool)> mic;                   // start / stop microphone capture
};

struct Config {
  std::string room = "Room";
  std::string door = "Front door";
  bool has_touch = false;
  bool demo = true;
  float bright = 1.0f;
  float bright_dim = 0.35f;           // perceptual level (the light applies gamma 2.2 → ≈10 % duty)
  uint32_t dim_after_ms = 0;          // 0 = never dim (set from HA: "Dim after")
  uint32_t off_after_ms = 0;          // 0 = never switch fully off
  uint32_t ring_timeout_ms = 40000;
  uint32_t call_max_ms = 1800000;   // safety net only: a conversation normally ends after 2 min without audio
  uint32_t disarm_hold_ms = 1500;
  uint32_t menu_hold_ms = 600;
  uint32_t talk_hold_ms = 220;
};

// ─────────────────────────────────────────────────────────────────────────────
class Controller {
 public:
  Fonts fonts;
  Hooks hooks;
  Config cfg;
  const Strings *S = &STR_EN;

  void set_language(const std::string &lang) { S = (lang == "de") ? &STR_DE : &STR_EN; }

  // ── state inputs (from HA / demo) ─────────────────────────────────────────
  void set_lights(int on) {  // -1 unknown, 0 off, 1 on
    if (lights_pending_until_ && millis() < lights_pending_until_ && on != lights_) return;  // keep optimistic value briefly
    lights_pending_until_ = 0;
    lights_ = on;
    render();
  }
  void set_lights_state(const std::string &s) {
    if (cfg.demo) return;
    set_lights(s == "on" ? 1 : s == "off" ? 0 : -1);
  }
  void set_alarm(Alarm a) {
    Alarm prev = alarm_;
    alarm_ = a;
    if (a == Alarm::PENDING && prev != Alarm::PENDING) pending_since_ = millis();
    if (disarming_ && a == Alarm::DISARMED) {
      disarming_ = false;
      flash(icon::SHIELD_CHECK, S->disarmed, pal::GREEN, 1400);
      if (hooks.led) hooks.led(pal::GREEN, "solid");
      led_hold_until_ = millis() + 1400;
    }
    if (a == Alarm::PENDING || a == Alarm::TRIGGERED) wake();
    render();
  }
  void set_alarm_state(const std::string &s) {
    if (cfg.demo || test_alarm_) return;
    set_alarm(parse_alarm(s));
  }
  void ring_start() {
    if (in_call_) return;  // already talking to the door
    answered_elsewhere_ = false;
    if (!ringing_) visitor_.clear(), visitor_lang_.clear(), visitor_role_.clear(), visitor_urgent_ = false,
                   live_text_.clear(), live_shown_ = 0;  // a new visitor
    ringing_ = true;
    ring_since_ = millis();
    menu_open_ = info_open_ = false;
    if (hooks.ringtone) hooks.ringtone(true);
    wake();
    render();
  }
  // missed = the ring timed out; otherwise another room answered (HA) and this key may join (R19)
  void ring_stop(bool missed = false) {
    if (!ringing_) return;
    ringing_ = false;
    if (hooks.ringtone) hooks.ringtone(false);
    answered_elsewhere_ = !missed && !in_call_;
    answered_ms_ = millis();
    if (missed) {
      missed_++;
      snprintf(missed_at_, sizeof(missed_at_), "%02d:%02d", hh_, mm_);
    }
    render();
  }
  void call_state(const std::string &s) {  // from the door station / HA: "active" | "ended"
    if (s == "active") {
      if (ringing_) ring_stop();
      begin_call_();
    } else if (s == "ended") {
      end_call_(false);
    }
  }
  void set_online(bool on) { online_ = on; render_status_(); render_info_(); }
  void set_demo(bool on) {
    cfg.demo = on;
    render_info_();
    render_status_();
  }
  bool clock_locked = false;  // simulator tour pins the clock for stable screenshots
  void set_time(int hh, int mm, bool force = false) {
    if (clock_locked && !force) return;
    if (hh == hh_ && mm == mm_) return;
    hh_ = hh;
    mm_ = mm;
    render_status_();
  }
  void set_net(const std::string &ip, int rssi) { ip_ = ip; rssi_ = rssi; render_info_(); }
  void set_level(float lvl) {  // 0..1, incoming audio (listening)
    level_in_ = lvl;
    if (lvl > 0.05f) call_seen_ms_ = millis();   // the door speaks: show the call
  }
  // Called from the microphone task: store numbers only, never touch LVGL here.
  void set_mic_level(float lvl, float db) { mic_level_ = lvl; mic_db_ = db; }
  void set_brightness(float b) { cfg.bright = b; apply_screen_(true); }
  void set_dim_after(uint32_t ms) { cfg.dim_after_ms = ms; wake(); }
  void toast(const std::string &text, uint32_t ms = 1800) { show_toast_(text.c_str(), ms); }

  // ── raw inputs ────────────────────────────────────────────────────────────
  // simulator tour only: a key-down that happened at `at` (to test a late loop)
  void key_at(bool down, uint32_t at) {
    key(down);
    if (down) key_down_ms_ = at;
  }
  void end_call_for_tour() { end_call_(false); }
  void key(bool down) {
    uint32_t now = millis();
    ESP_LOGD(TAG, "key %s in %s (held %u ms)", down ? "down" : "up", view_name(), (unsigned) (now - key_down_ms_));
    if (down) {
      if (key_down_) return;
      key_down_ = true;
      key_down_ms_ = now;
      double_ = pending_press_ && age_(pending_press_ms_) < (int32_t) DOUBLE_MS;   // second press of a double press
      pending_press_ = false;
      hold_fired_ = false;
      key_consumed_ = false;
      cancel_touch_();  // the finger that pressed the key must not also "tap"
      bool was_dark = screen_ != Screen::ACTIVE;
      wake();
      if (hooks.gesture) hooks.gesture("key_down");
      press_anim_(true);
      View v = view();
      if (v == View::RING) {  // answer on key-DOWN: instant, and a continued hold becomes talk
        answer_();
        key_consumed_ = true;
      }
      (void) was_dark;  // the key always acts, even on a dark screen (blind operation)
    } else {
      if (!key_down_) return;
      key_down_ = false;
      press_anim_(false);
      set_hold_progress_(0);
      // A hold the timer never saw (the loop was late, e.g. a busy simulator): where holding means talk, it still
      // counts as a hold, so the key joins as on time. Never for disarming, where a stretched press must not count.
      const bool talk_hold = (view() == View::HOME && !(is_armed(alarm_) || alarm_ == Alarm::ARMING)) || view() == View::CALL;
      if (!hold_fired_ && !key_consumed_ && talk_hold && now - key_down_ms_ >= hold_ms_()) {
        ESP_LOGD(TAG, "late hold in %s", view_name());
        on_hold_();
        hold_fired_ = true;
      }
      if (hold_fired_) {
        on_hold_release_();
      } else if (!key_consumed_) {
        if (hooks.gesture) hooks.gesture("press");
        on_press_();
      }
    }
  }

  // Called by the LVGL timer (~30 Hz).
  void tick() {
    uint32_t now = millis();
    // hold progress
    if (key_down_ && !hold_fired_) {
      uint32_t need = hold_ms_();
      if (need) {
        uint32_t held = now - key_down_ms_;
        if (view() != View::CALL) set_hold_progress_(held < 140 ? 0 : (int) ((held - 140) * 1000 / (need - 140)));
        if (held >= need) {
          hold_fired_ = true;
          set_hold_progress_(0);
          if (hooks.gesture) hooks.gesture("hold");
          on_hold_();
        }
      }
    }
    if (built_ && view() != shown_) render();   // e.g. the call view hides 8 s after the last activity
    if (built_ && live_shown_ < live_text_.size()) {   // type the live text in; catch up when far behind
      int steps = 2 + (int) (live_text_.size() - live_shown_) / 12;
      for (int k = 0; k < steps && live_shown_ < live_text_.size(); k++) {
        live_shown_++;
        while (live_shown_ < live_text_.size() && ((uint8_t) live_text_[live_shown_] & 0xC0) == 0x80) live_shown_++;
      }
      if (in_call_) call_seen_ms_ = millis();
      render_live_();
    }
    if (pending_press_ && age_(pending_press_ms_) >= (int32_t) DOUBLE_MS) {   // no second press came: lights
      pending_press_ = false;
      if (view() == View::HOME) toggle_lights_();
    }
    // timeouts — age_() re-reads the clock: the hold handler above may have just stamped
    // a timestamp *after* `now`, and unsigned `now - later` would underflow.
    if (ringing_ && age_(ring_since_) > (int32_t) cfg.ring_timeout_ms) ring_stop(true);
    if (in_call_ && !talking_ && age_(call_since_) > (int32_t) cfg.call_max_ms) end_call_(false);
    if (chat_back_ > 0 && age_(chat_back_ms_) > 8000) {   // scrolled back: return to the newest message
      chat_back_ = 0;
      scroll_chat_(true);
    }
    if (menu_open_ && age_(last_input_ms_) > 9000) { ESP_LOGD(TAG, "menu timeout"); menu_open_ = false; render(); }
    if (info_open_ && age_(last_input_ms_) > 15000) { info_open_ = false; render(); }
    if (disarming_ && age_(disarm_since_) > 8000) {
      disarming_ = false;
      flash(icon::CLOSE, S->not_confirmed, pal::RED, 1600);
      render();
    }
    now = millis();
    if (flash_until_ && now > flash_until_) { flash_until_ = 0; lv_obj_add_flag(v_flash_, LV_OBJ_FLAG_HIDDEN); }
    if (toast_until_ && now > toast_until_) { toast_until_ = 0; lv_obj_add_flag(toast_, LV_OBJ_FLAG_HIDDEN); }
    if (led_hold_until_ && now > led_hold_until_) { led_hold_until_ = 0; apply_led_(); }
    run_demo_(now);
    // per-second refresh
    if (now - last_second_ >= 1000) {
      last_second_ = now;
      if (in_call_) render_call_();
      if (alarm_ == Alarm::PENDING) render_alarm_();
    }
    if (in_call_) animate_meter_(now);
    if (info_open_ && now - last_mic_ui_ > 150) { last_mic_ui_ = now; render_mic_row_(); }
    apply_screen_(false);
  }

  // ── build ─────────────────────────────────────────────────────────────────
  void build(lv_obj_t *scr) {
    scr_ = scr;
    lv_obj_set_style_bg_color(scr, lv_color_hex(pal::BG), 0);
    lv_obj_set_style_bg_opa(scr, LV_OPA_COVER, 0);
    lv_obj_remove_flag(scr, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_add_event_cb(scr, &Controller::on_gesture_cb_, LV_EVENT_GESTURE, this);

    build_status_();
    build_home_();
    build_menu_();
    build_info_();
    build_ring_();
    build_call_();
    build_alarm_();
    build_hints_();
    build_flash_();
    build_toast_();

    timer_ = lv_timer_create(&Controller::tick_cb_, 33, this);
    last_input_ms_ = millis();
    built_ = true;
    render();
    ESP_LOGI(TAG, "UI built (touch=%s, demo=%s, brightness=%.0f%%, dim after=%us)", cfg.has_touch ? "yes" : "no",
             cfg.demo ? "on" : "off", cfg.bright * 100, (unsigned) (cfg.dim_after_ms / 1000));
  }

  View view() const {
    if (alarm_ == Alarm::PENDING || alarm_ == Alarm::TRIGGERED || disarming_) return View::ALARM;
    // The conversation stays open 2 min after the last audio (the door's answer must get through), but the
    // screen shows it only while something happens: talking, door audio arriving, or just now.
    if (in_call_ && (talking_ || age_(call_seen_ms_) < (int32_t) CALL_SHOW_MS)) return View::CALL;
    if (ringing_ || joinable_()) return View::RING;   // ringing, or answered elsewhere and this room may join (R19)
    if (menu_open_) return View::MENU;
    if (info_open_) return View::INFO;
    return View::HOME;
  }
  const char *view_name() const {
    static const char *const N[] = {"home", "menu", "info", "ring", "call", "alarm"};
    return N[(int) view()];
  }

  // Public for the simulator tour.
  void open_menu() { menu_open_ = true; menu_sel_ = 0; last_input_ms_ = millis(); render(); }
  void set_menu_sel(int i) { menu_sel_ = i; render_menu_(); }
  void open_info() { info_open_ = true; render(); }
  void test_alarm() { start_test_alarm_(); }
  void set_talk_level(float l) { level_in_ = l; }
  bool ringing() const { return ringing_; }
  // TEST ONLY (WIP): keeps the microphone on for a timed test recording and says so on screen.
  void set_test_recording(bool on, uint32_t max_secs = 15) {
    if (on == test_rec_) return;
    test_rec_ = on;
    if (on) show_toast_("Mic test: speak now", max_secs * 1000);
    else show_toast_("Mic test: sent", 1200);
    render();
  }
  bool test_recording() const { return test_rec_; }
  // Who is at the door, as the visitor introduced themselves ("Anna", "Paketdienst · DHL"), from the
  // door-side transcript. Shown instead of the door name while ringing / in the call; not verified.
  void set_visitor(const std::string &who) {
    if (who.empty() || who == "unknown" || who == "unavailable") return;  // keep the last one said
    if (!ringing_ && !in_call_) return;                                     // old news
    visitor_ = who;
    render_door_labels_();
  }
  const std::string &visitor() const { return visitor_; }
  // The visitor's type (speaker_role: "parcel", "police", "name", …) for the icon in front of the name.
  void set_visitor_role(const std::string &role) {
    if (role.empty() || role == "unknown" || role == "unavailable") return;  // keep the last one said
    if (!ringing_ && !in_call_) return;
    visitor_role_ = role;
    render_door_labels_();
  }
  // An emergency was said ("Hilfe", "Notfall", …): the visitor line turns red until this visitor is gone.
  void set_visitor_urgent(const std::string &v) {
    if (v != "True" && v != "true" && v != "on") return;
    if (!ringing_ && !in_call_) return;
    visitor_urgent_ = true;
    wake();
    render_door_labels_();
  }
  // What the visitor is saying, while they say it (door transcriber, partial texts ~1/s, then the final one).
  // Shown in place of the bell / ear, typed in letter by letter.
  void set_live_text(const std::string &t) {
    if (t.empty() || t == "unknown" || t == "unavailable") return;
    if (!ringing_ && !in_call_) return;
    // Every update carries the whole utterance so far. Whisper revises earlier words now and then: show a revision of
    // what is already on screen at once and type only the new words (retyping from the first changed letter made a
    // long utterance look as if it streamed in again). A new utterance (live_utterance) types from the start.
    if (t != live_text_) visitor_text_n_++;
    live_text_ = t;
    size_t keep = std::min(live_shown_, t.size());
    while (keep > 0 && keep < t.size() && ((uint8_t) t[keep] & 0xC0) == 0x80) keep--;  // UTF-8 boundary
    live_shown_ = keep;
    if (in_call_) call_seen_ms_ = millis();
    if (built_) render();
  }
  // A new utterance at the door (the live sensor's state = when it started): its text types in from the start.
  void live_utterance(const std::string &started) {
    if (started.empty() || started == "unknown" || started == "unavailable" || started == live_started_) return;
    live_started_ = started;
    live_shown_ = 0;
  }
  // The language the visitor speaks, when it is not German ("Chinese"), from the same transcript.
  void set_visitor_language(const std::string &lang) {
    if (lang.empty() || lang == "unknown" || lang == "unavailable" || lang == "German" || lang == "Deutsch") return;
    if (!ringing_ && !in_call_) return;
    visitor_lang_ = lang;
    render_door_labels_();
    if (built_) render_ring_();
  }
  // The conversation as a chat (aikos sensor.aikos_call_log, R17.6): the last CHAT_N messages, oldest first.
  struct ChatMsg {
    std::string id, who, role, text, lang;
    bool door = false, urgent = false;
  };
  static constexpr size_t CHAT_N = 10;
  // R22: never the last call's chat, not even for a moment. aikos' call log counts only while it says a call is
  // active, and the key empties it itself when the door's call changes or ends, whatever HA still holds.
  void set_chat(std::vector<ChatMsg> msgs) {
    chat_in_ = std::move(msgs);
    show_chat_();
  }
  void set_chat_active(bool on) {
    if (on == chat_active_) return;
    chat_active_ = on;
    if (!on) chat_in_.clear();
    show_chat_();
  }
  void door_call_id(uint32_t id) {   // from the door's broadcast: a new id (or 0) = a new call (or none)
    if (call_id_known_ && id != call_id_) clear_chat_();
    call_id_ = id;
    call_id_known_ = true;
  }
  void show_chat_() {
    std::vector<ChatMsg> msgs = chat_active_ ? chat_in_ : std::vector<ChatMsg>{};
    if (msgs.size() > CHAT_N) msgs.erase(msgs.begin(), msgs.end() - CHAT_N);
    bool same = msgs.size() == chat_.size();
    for (size_t i = 0; same && i < msgs.size(); i++)
      same = msgs[i].id == chat_[i].id && msgs[i].text == chat_[i].text && msgs[i].who == chat_[i].who &&
             msgs[i].lang == chat_[i].lang;
    if (same) return;
    const bool grew = !msgs.empty() && (chat_.empty() || msgs.back().id != chat_.back().id);
    chat_ = std::move(msgs);
    if (in_call_ && grew) {
      call_seen_ms_ = millis();                                   // a new message brings the call view back
      if (chat_.back().door) live_text_.clear(), live_shown_ = 0;  // the visitor's final words are in the chat now
    }
    chat_back_ = 0;
    if (built_) {
      build_chat_();
      render();
    }
  }
  // From the door (voice v2): someone answered (R19: no more listening before an answer) and another key has the
  // floor ("besetzt": this key's hold sends nothing until the floor is free).
  void set_door_answered(bool on) { door_answered_ = on; }
  bool door_answered() const { return door_answered_; }
  void set_floor_busy(bool busy) {
    if (busy == floor_busy_) return;
    floor_busy_ = busy;
    if (!busy && talking_) talk_since_ms_ = millis();   // the floor came free: the talk clock starts now
    if (built_) render();
  }
  bool floor_busy() const { return floor_busy_; }
  bool sends() const { return talking_ && !floor_busy_; }   // the mic goes to the door and the transcriber only then
  // The door has a call (aikos binary_sensor.aikos_intercom_talk_in_call; with voice v2 straight from the door).
  void set_door_call(bool on) {
    if (on && door_call_ != 1) join_dismissed_ = false;          // a new call at the door: offer to join again
    door_call_ = on ? 1 : 0;
    if (!on) answered_elsewhere_ = false, door_answered_ = false, floor_busy_ = false, join_dismissed_ = false;
    if (built_) render();
  }
  bool in_call() const { return in_call_; }
  bool talking() const { return talking_; }
  bool visitor_urgent() const { return visitor_urgent_; }
  uint32_t visitor_text_count() const { return visitor_text_n_; }   // grows whenever the visitor's text changes (= they spoke)

 protected:
  // ── helpers ───────────────────────────────────────────────────────────────
  static int32_t age_(uint32_t t) { return (int32_t) (millis() - t); }  // wrap-safe; negative if t is in the future
  static lv_obj_t *box_(lv_obj_t *parent) {
    lv_obj_t *o = lv_obj_create(parent);
    lv_obj_remove_style_all(o);
    lv_obj_remove_flag(o, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_remove_flag(o, LV_OBJ_FLAG_CLICKABLE);
    return o;
  }
  lv_obj_t *label_(lv_obj_t *parent, const lv_font_t *font, uint32_t color, const char *text = "") {
    lv_obj_t *l = lv_label_create(parent);
    if (font) lv_obj_set_style_text_font(l, font, 0);
    lv_obj_set_style_text_color(l, lv_color_hex(color), 0);
    lv_label_set_text(l, text);
    return l;
  }
  lv_obj_t *view_box_() {
    lv_obj_t *v = box_(scr_);
    lv_obj_set_size(v, 172, 320);
    lv_obj_set_pos(v, 0, 0);
    lv_obj_add_flag(v, LV_OBJ_FLAG_HIDDEN);
    lv_obj_add_flag(v, LV_OBJ_FLAG_GESTURE_BUBBLE);
    return v;
  }
  // The round "hero" disc every screen is built around (mirrors the keycap).
  lv_obj_t *hero_(lv_obj_t *parent, int cy, lv_obj_t **icon_out, lv_obj_t **arc_out) {
    lv_obj_t *arc = lv_arc_create(parent);
    lv_obj_set_size(arc, 138, 138);
    lv_obj_align(arc, LV_ALIGN_TOP_MID, 0, cy - 69);
    lv_arc_set_bg_angles(arc, 0, 360);
    lv_arc_set_rotation(arc, 270);
    lv_arc_set_range(arc, 0, 1000);
    lv_arc_set_value(arc, 0);
    lv_obj_remove_style(arc, nullptr, LV_PART_KNOB);
    lv_obj_remove_flag(arc, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_set_style_arc_width(arc, 5, LV_PART_MAIN);
    lv_obj_set_style_arc_width(arc, 5, LV_PART_INDICATOR);
    lv_obj_set_style_arc_opa(arc, LV_OPA_TRANSP, LV_PART_MAIN);
    lv_obj_set_style_arc_rounded(arc, true, LV_PART_INDICATOR);
    lv_obj_add_flag(arc, LV_OBJ_FLAG_HIDDEN);
    if (arc_out) *arc_out = arc;

    lv_obj_t *disc = box_(parent);
    lv_obj_set_size(disc, 118, 118);
    lv_obj_align(disc, LV_ALIGN_TOP_MID, 0, cy - 59);
    lv_obj_set_style_radius(disc, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_bg_opa(disc, LV_OPA_COVER, 0);
    lv_obj_set_style_bg_color(disc, lv_color_hex(pal::SURFACE), 0);
    lv_obj_set_style_border_width(disc, 2, 0);
    lv_obj_set_style_border_color(disc, lv_color_hex(pal::LINE), 0);
    lv_obj_set_style_outline_pad(disc, 5, 0);
    lv_obj_set_style_outline_width(disc, 4, 0);
    lv_obj_set_user_data(disc, (void *) (intptr_t) cy);  // centre y, for the press animation
    lv_obj_add_flag(disc, LV_OBJ_FLAG_GESTURE_BUBBLE);

    lv_obj_t *ic = label_(disc, fonts.icon_lg, pal::MUTED, icon::BULB_OUTLINE);
    lv_obj_center(ic);
    if (icon_out) *icon_out = ic;
    return disc;
  }
  static void style_disc_(lv_obj_t *disc, lv_obj_t *ic, uint32_t accent, lv_opa_t fill, int border, bool glow) {
    lv_obj_set_style_bg_color(disc, fill ? lv_color_mix(lv_color_hex(accent), lv_color_hex(pal::SURFACE), fill)
                                         : lv_color_hex(pal::SURFACE), 0);
    lv_obj_set_style_border_color(disc, lv_color_hex(fill || border > 2 ? accent : pal::LINE), 0);
    lv_obj_set_style_border_width(disc, border, 0);
    // "Glow" = translucent outline halo; LVGL software shadows are far too slow here.
    lv_obj_set_style_outline_color(disc, lv_color_hex(accent), 0);
    lv_obj_set_style_outline_opa(disc, glow ? LV_OPA_30 : LV_OPA_TRANSP, 0);
    if (ic) lv_obj_set_style_text_color(ic, lv_color_hex(fill || border > 2 ? accent : pal::MUTED), 0);
  }

  // ── build: status bar ─────────────────────────────────────────────────────
  void build_status_() {
    status_ = box_(scr_);
    // The 1.47" panel has rounded corners: corner elements sit in a safe area (≥ 16 px in, 4 px down).
    lv_obj_set_size(status_, 172, 30);
    lv_obj_set_pos(status_, 0, 0);
    st_time_ = label_(status_, fonts.body, pal::TEXT, "--:--");
    lv_obj_align(st_time_, LV_ALIGN_LEFT_MID, 16, 3);
    st_alarm_ = label_(status_, fonts.icon_sm, pal::MUTED, icon::SHIELD_CHECK);
    lv_obj_align(st_alarm_, LV_ALIGN_RIGHT_MID, -15, 3);
    st_net_ = label_(status_, fonts.icon_sm, pal::ORANGE, icon::CLOUD_OFF);
    lv_obj_align(st_net_, LV_ALIGN_RIGHT_MID, -37, 3);
    st_missed_ = label_(status_, fonts.small, pal::CYAN, "");
    lv_obj_align(st_missed_, LV_ALIGN_RIGHT_MID, -59, 3);
    st_demo_ = label_(status_, fonts.small, pal::FAINT, "DEMO");
    lv_obj_align(st_demo_, LV_ALIGN_LEFT_MID, 66, 4);
  }

  // ── build: home ───────────────────────────────────────────────────────────
  void build_home_() {
    v_home_ = view_box_();
    banner_ = box_(v_home_);
    lv_obj_set_size(banner_, 150, 24);
    lv_obj_align(banner_, LV_ALIGN_TOP_MID, 0, 32);
    lv_obj_set_style_radius(banner_, 12, 0);
    lv_obj_set_style_bg_opa(banner_, LV_OPA_COVER, 0);
    banner_icon_ = label_(banner_, fonts.icon_sm, pal::RED, icon::SHIELD_LOCK);
    lv_obj_align(banner_icon_, LV_ALIGN_LEFT_MID, 9, 0);
    banner_text_ = label_(banner_, fonts.small, pal::RED, "");
    lv_obj_align(banner_text_, LV_ALIGN_LEFT_MID, 30, 0);

    home_disc_ = hero_(v_home_, 140, &home_icon_, &home_arc_);
    lv_obj_add_flag(home_disc_, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_add_event_cb(home_disc_, &Controller::on_tap_cb_, LV_EVENT_CLICKED, this);

    home_title_ = label_(v_home_, fonts.title, pal::TEXT, "");
    lv_obj_align(home_title_, LV_ALIGN_TOP_MID, 0, 208);
    home_sub_ = label_(v_home_, fonts.small, pal::MUTED, cfg.room.c_str());
    lv_obj_align(home_sub_, LV_ALIGN_TOP_MID, 0, 236);
  }

  // ── build: menu ───────────────────────────────────────────────────────────
  void build_menu_() {
    v_menu_ = view_box_();
    lv_obj_t *t = label_(v_menu_, fonts.small, pal::MUTED, S->m_title);
    lv_obj_set_style_text_letter_space(t, 2, 0);
    lv_obj_align(t, LV_ALIGN_TOP_MID, 0, 32);
    static const char *const ICONS[MENU_N] = {icon::PHONE_TALK, icon::INFO, icon::BELL_RING, icon::SHIELD_ALERT,
                                              icon::CLOSE};
    const char *texts[MENU_N] = {S->m_talk, S->m_info, S->m_test_ring, S->m_test_alarm, S->m_close};
    for (int i = 0; i < MENU_N; i++) {
      lv_obj_t *row = box_(v_menu_);
      lv_obj_set_size(row, 156, 38);
      lv_obj_align(row, LV_ALIGN_TOP_MID, 0, 54 + i * 41);
      lv_obj_set_style_radius(row, 12, 0);
      lv_obj_set_style_bg_color(row, lv_color_hex(pal::RAISED), 0);
      lv_obj_add_flag(row, LV_OBJ_FLAG_CLICKABLE);
      lv_obj_add_flag(row, LV_OBJ_FLAG_GESTURE_BUBBLE);
      lv_obj_set_user_data(row, (void *) (intptr_t) i);
      lv_obj_add_event_cb(row, &Controller::on_menu_tap_cb_, LV_EVENT_CLICKED, this);
      lv_obj_t *ic = label_(row, fonts.icon_md, pal::MUTED, ICONS[i]);
      lv_obj_align(ic, LV_ALIGN_LEFT_MID, 10, 0);
      lv_obj_t *tx = label_(row, fonts.body, pal::TEXT, texts[i]);
      lv_obj_align(tx, LV_ALIGN_LEFT_MID, 42, 0);
      menu_rows_[i] = row;
      menu_icons_[i] = ic;
      menu_texts_[i] = tx;
    }
  }

  // ── build: info ───────────────────────────────────────────────────────────
  void build_info_() {
    v_info_ = view_box_();
    lv_obj_t *t = label_(v_info_, fonts.title, pal::TEXT, cfg.room.c_str());
    lv_obj_align(t, LV_ALIGN_TOP_LEFT, 14, 34);
    static const char *const KEYS[INFO_N] = {"Home Assistant", "Wi-Fi", "IP", "Alarm", "Mode", "Firmware", "Mic"};
    for (int i = 0; i < INFO_N; i++) {
      lv_obj_t *k = label_(v_info_, fonts.small, pal::MUTED, KEYS[i]);
      lv_obj_align(k, LV_ALIGN_TOP_LEFT, 14, 72 + i * 26);
      info_val_[i] = label_(v_info_, fonts.small, pal::TEXT, "");
      lv_obj_align(info_val_[i], LV_ALIGN_TOP_RIGHT, -14, 72 + i * 26);
      if (i) {
        lv_obj_t *line = box_(v_info_);
        lv_obj_set_size(line, 144, 1);
        lv_obj_align(line, LV_ALIGN_TOP_MID, 0, 72 + i * 26 - 7);
        lv_obj_set_style_bg_opa(line, LV_OPA_COVER, 0);
        lv_obj_set_style_bg_color(line, lv_color_hex(pal::SURFACE), 0);
      }
    }
    // live mic level bar next to the dBFS value
    mic_bar_bg_ = box_(v_info_);
    lv_obj_set_size(mic_bar_bg_, 44, 6);
    lv_obj_align(mic_bar_bg_, LV_ALIGN_TOP_LEFT, 48, 72 + 6 * 26 + 6);
    lv_obj_set_style_radius(mic_bar_bg_, 3, 0);
    lv_obj_set_style_bg_opa(mic_bar_bg_, LV_OPA_COVER, 0);
    lv_obj_set_style_bg_color(mic_bar_bg_, lv_color_hex(pal::RAISED), 0);
    mic_bar_ = box_(mic_bar_bg_);
    lv_obj_set_size(mic_bar_, 2, 6);
    lv_obj_set_style_radius(mic_bar_, 3, 0);
    lv_obj_set_style_bg_opa(mic_bar_, LV_OPA_COVER, 0);
    lv_obj_set_style_bg_color(mic_bar_, lv_color_hex(pal::GREEN), 0);
  }
  void render_mic_row_() {
    if (mic_level_ < 0) {
      lv_label_set_text(info_val_[6], hooks.mic ? "no data" : "not fitted");
      lv_obj_set_width(mic_bar_, 2);
      return;
    }
    char t[16];
    snprintf(t, sizeof(t), "%d dB", (int) roundf(mic_db_));
    lv_label_set_text(info_val_[6], t);
    lv_obj_set_width(mic_bar_, 2 + (int) (mic_level_ * 42));
  }

  // ── build: ring ───────────────────────────────────────────────────────────
  void build_ring_() {
    v_ring_ = view_box_();
    for (int i = 0; i < 2; i++) {  // expanding ripples behind the disc
      lv_obj_t *r = box_(v_ring_);
      lv_obj_set_size(r, 118, 118);
      lv_obj_align(r, LV_ALIGN_TOP_MID, 0, 140 - 59);
      lv_obj_set_style_radius(r, LV_RADIUS_CIRCLE, 0);
      lv_obj_set_style_border_width(r, 3, 0);
      lv_obj_set_style_border_color(r, lv_color_hex(pal::CYAN), 0);
      ripples_[i] = r;
    }
    lv_obj_t *t = ring_door_ = door_label_(v_ring_, ring_row_, 36);
    lv_obj_set_style_text_letter_space(t, 1, 0);
    layout_row_(ring_row_, cfg.door, nullptr, false, pal::CYAN);
    ring_disc_ = hero_(v_ring_, 140, &ring_icon_, nullptr);
    lv_label_set_text(ring_icon_, icon::BELL_RING);
    lv_obj_set_style_transform_pivot_x(ring_icon_, 30, 0);
    lv_obj_set_style_transform_pivot_y(ring_icon_, 8, 0);
    style_disc_(ring_disc_, ring_icon_, pal::CYAN, LV_OPA_20, 3, false);
    lv_obj_add_flag(ring_disc_, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_add_event_cb(ring_disc_, &Controller::on_tap_cb_, LV_EVENT_CLICKED, this);
    ring_live_ = live_label_(v_ring_, 64, 136);
    ring_title_ = label_(v_ring_, fonts.title, pal::TEXT, S->doorbell);
    lv_obj_align(ring_title_, LV_ALIGN_TOP_MID, 0, 208);
    ring_sub_ = label_(v_ring_, fonts.small, pal::MUTED, "");
    lv_obj_align(ring_sub_, LV_ALIGN_TOP_MID, 0, 236);
    if (cfg.has_touch) {
      lv_obj_t *x = label_(v_ring_, fonts.icon_md, pal::MUTED, icon::CLOSE);
      lv_obj_align(x, LV_ALIGN_TOP_RIGHT, -6, 4);
      lv_obj_add_flag(x, LV_OBJ_FLAG_CLICKABLE);
      lv_obj_set_ext_click_area(x, 12);
      lv_obj_add_event_cb(x, &Controller::on_dismiss_cb_, LV_EVENT_CLICKED, this);
    }
  }

  // ── build: call ───────────────────────────────────────────────────────────
  void build_call_() {
    v_call_ = view_box_();
    call_door_ = door_label_(v_call_, call_row_, 32);
    call_timer_ = label_(v_call_, fonts.big, pal::TEXT, "0:00");
    lv_obj_align(call_timer_, LV_ALIGN_TOP_MID, 0, 48);
    call_disc_ = hero_(v_call_, 152, &call_icon_, nullptr);
    // the chat (R17.6) replaces the ear while listening; the visitor's words in progress are its last row
    chat_box_ = box_(v_call_);
    lv_obj_set_size(chat_box_, 164, 160);
    lv_obj_align(chat_box_, LV_ALIGN_TOP_MID, 0, 58);
    lv_obj_add_flag(chat_box_, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_scrollbar_mode(chat_box_, LV_SCROLLBAR_MODE_OFF);
    lv_obj_set_scroll_dir(chat_box_, LV_DIR_VER);
    lv_obj_add_flag(chat_box_, LV_OBJ_FLAG_HIDDEN);
    if (cfg.has_touch) {   // R18: swipe through the chat like on a phone
      lv_obj_add_flag(chat_box_, LV_OBJ_FLAG_CLICKABLE);
      lv_obj_add_event_cb(chat_box_, &Controller::on_chat_scroll_cb_, LV_EVENT_SCROLL, this);
    }
    call_live_ = live_label_(chat_box_, 0, 0);
    lv_obj_align(call_live_, LV_ALIGN_TOP_LEFT, 0, 0);
    if (cfg.has_touch) {  // press-and-hold the disc = talk (same as the key)
      lv_obj_add_flag(call_disc_, LV_OBJ_FLAG_CLICKABLE);
      lv_obj_add_event_cb(call_disc_, &Controller::on_call_disc_cb_, LV_EVENT_ALL, this);
      lv_obj_t *x = label_(v_call_, fonts.icon_md, pal::RED, icon::HANGUP);
      lv_obj_align(x, LV_ALIGN_TOP_RIGHT, -8, 4);
      lv_obj_add_flag(x, LV_OBJ_FLAG_CLICKABLE);
      lv_obj_set_ext_click_area(x, 12);
      lv_obj_add_event_cb(x, &Controller::on_hangup_cb_, LV_EVENT_CLICKED, this);
    }
    for (int i = 0; i < METER_N; i++) {
      lv_obj_t *b = box_(v_call_);
      lv_obj_set_size(b, 8, 6);
      lv_obj_align(b, LV_ALIGN_TOP_MID, (i - METER_N / 2) * 13, 228);
      lv_obj_set_style_radius(b, 4, 0);
      lv_obj_set_style_bg_opa(b, LV_OPA_COVER, 0);
      lv_obj_set_style_bg_color(b, lv_color_hex(pal::CYAN), 0);
      meter_[i] = b;
    }
    call_state_ = label_(v_call_, fonts.small, pal::MUTED, "");
    lv_obj_align(call_state_, LV_ALIGN_TOP_MID, 0, 244);
    if (cfg.has_touch) {   // the chat hides the disc: the meter strip below it is the press-and-hold talk button then
      talk_zone_ = box_(v_call_);
      lv_obj_set_size(talk_zone_, 150, 46);
      lv_obj_align(talk_zone_, LV_ALIGN_TOP_MID, 0, 220);
      lv_obj_set_style_radius(talk_zone_, 23, 0);
      lv_obj_set_style_border_width(talk_zone_, 1, 0);
      lv_obj_set_style_border_color(talk_zone_, lv_color_hex(pal::LINE), 0);
      lv_obj_add_flag(talk_zone_, LV_OBJ_FLAG_CLICKABLE);
      lv_obj_add_event_cb(talk_zone_, &Controller::on_call_disc_cb_, LV_EVENT_ALL, this);
      lv_obj_add_flag(talk_zone_, LV_OBJ_FLAG_HIDDEN);
    }
  }

  // ── build: alarm ──────────────────────────────────────────────────────────
  void build_alarm_() {
    v_alarm_ = view_box_();
    // Pulsing frame made of four edge bars: animating a full-screen tint would force a
    // full redraw every frame (~100 ms on the C6); bars only invalidate the edges.
    static const int16_t EDGE[4][4] = {{0, 0, 172, 7}, {0, 313, 172, 7}, {0, 7, 7, 306}, {165, 7, 7, 306}};
    for (int i = 0; i < 4; i++) {
      lv_obj_t *e = box_(v_alarm_);
      lv_obj_set_pos(e, EDGE[i][0], EDGE[i][1]);
      lv_obj_set_size(e, EDGE[i][2], EDGE[i][3]);
      lv_obj_set_style_bg_opa(e, LV_OPA_TRANSP, 0);
      lv_obj_set_style_bg_color(e, lv_color_hex(pal::RED), 0);
      alarm_edge_[i] = e;
    }
    alarm_head_ = label_(v_alarm_, fonts.small, pal::RED, S->alarm);
    lv_obj_set_style_text_letter_space(alarm_head_, 2, 0);
    lv_obj_align(alarm_head_, LV_ALIGN_TOP_MID, 0, 34);
    alarm_disc_ = hero_(v_alarm_, 140, &alarm_icon_, &alarm_arc_);
    alarm_title_ = label_(v_alarm_, fonts.title, pal::TEXT, "");
    lv_obj_align(alarm_title_, LV_ALIGN_TOP_MID, 0, 208);
    alarm_sub_ = label_(v_alarm_, fonts.small, pal::MUTED, "");
    lv_obj_align(alarm_sub_, LV_ALIGN_TOP_MID, 0, 236);
  }

  // ── build: hint bar ───────────────────────────────────────────────────────
  void build_hints_() {
    hints_ = box_(scr_);
    lv_obj_set_size(hints_, 156, 52);
    lv_obj_align(hints_, LV_ALIGN_BOTTOM_MID, 0, -6);
    lv_obj_set_style_radius(hints_, 14, 0);
    lv_obj_set_style_bg_opa(hints_, LV_OPA_COVER, 0);
    lv_obj_set_style_bg_color(hints_, lv_color_hex(pal::SURFACE), 0);
    for (int i = 0; i < 2; i++) {
      lv_obj_t *glyph = box_(hints_);  // ● for press, ▬ for hold — the shape is the gesture
      lv_obj_set_size(glyph, i == 0 ? 8 : 20, 8);
      lv_obj_align(glyph, LV_ALIGN_TOP_LEFT, i == 0 ? 18 : 12, i == 0 ? 11 : 33);
      lv_obj_set_style_radius(glyph, 4, 0);
      lv_obj_set_style_bg_opa(glyph, LV_OPA_COVER, 0);
      lv_obj_set_style_bg_color(glyph, lv_color_hex(pal::MUTED), 0);
      hint_glyph_[i] = glyph;
      lv_obj_t *verb = label_(hints_, fonts.small, pal::FAINT, i == 0 ? S->press : S->hold);
      lv_obj_set_style_text_letter_space(verb, 1, 0);
      lv_obj_align(verb, LV_ALIGN_TOP_LEFT, 40, i == 0 ? 6 : 28);
      hint_verb_[i] = verb;
      lv_obj_t *act = label_(hints_, fonts.small, pal::TEXT, "");
      lv_obj_align(act, LV_ALIGN_TOP_RIGHT, -14, i == 0 ? 6 : 28);
      hint_act_[i] = act;
    }
  }

  void build_flash_() {
    v_flash_ = box_(scr_);
    lv_obj_set_size(v_flash_, 172, 320);
    lv_obj_set_style_bg_opa(v_flash_, LV_OPA_COVER, 0);
    lv_obj_set_style_bg_color(v_flash_, lv_color_hex(pal::BG), 0);
    flash_disc_ = hero_(v_flash_, 140, &flash_icon_, nullptr);
    flash_text_ = label_(v_flash_, fonts.title, pal::TEXT, "");
    lv_obj_align(flash_text_, LV_ALIGN_TOP_MID, 0, 214);
    lv_obj_add_flag(v_flash_, LV_OBJ_FLAG_HIDDEN);
  }

  void build_toast_() {
    toast_ = box_(scr_);
    lv_obj_set_size(toast_, 160, 52);
    lv_obj_align(toast_, LV_ALIGN_TOP_MID, 0, 204);
    lv_obj_set_style_radius(toast_, 12, 0);
    lv_obj_set_style_bg_opa(toast_, LV_OPA_COVER, 0);
    lv_obj_set_style_bg_color(toast_, lv_color_hex(pal::RAISED), 0);
    lv_obj_set_style_border_width(toast_, 1, 0);
    lv_obj_set_style_border_color(toast_, lv_color_hex(pal::LINE), 0);
    lv_obj_set_style_pad_all(toast_, 0, 0);
    toast_text_ = label_(toast_, fonts.small, pal::TEXT, "");
    lv_obj_set_width(toast_text_, 140);
    lv_obj_center(toast_text_);
    lv_obj_set_style_text_align(toast_text_, LV_TEXT_ALIGN_CENTER, 0);
    lv_label_set_long_mode(toast_text_, LV_LABEL_LONG_MODE_WRAP);
    lv_obj_add_flag(toast_, LV_OBJ_FLAG_HIDDEN);
  }

  // ── render ────────────────────────────────────────────────────────────────
 public:
  void render() {
    if (!built_) return;
    View v = view();
    if (v != shown_) {
      lv_obj_t *views[] = {v_home_, v_menu_, v_info_, v_ring_, v_call_, v_alarm_};
      for (int i = 0; i < 6; i++) {
        if (i == (int) v) lv_obj_remove_flag(views[i], LV_OBJ_FLAG_HIDDEN);
        else lv_obj_add_flag(views[i], LV_OBJ_FLAG_HIDDEN);
      }
      shown_ = v;
      ESP_LOGD(TAG, "view -> %s", view_name());
    }
    // (Re)start animations whenever the view or its sub-state changes.
    int sig = (int) v * 8 + (disarming_ ? 2 : 0) + (alarm_ == Alarm::TRIGGERED ? 1 : 0);
    if (sig != anim_sig_) {
      stop_anims_();
      start_anims_(v);
      anim_sig_ = sig;
    }
    // status bar is part of the calm screens only
    bool calm = (v == View::HOME || v == View::MENU || v == View::INFO);
    if (calm) lv_obj_remove_flag(status_, LV_OBJ_FLAG_HIDDEN);
    else lv_obj_add_flag(status_, LV_OBJ_FLAG_HIDDEN);
    render_status_();
    switch (v) {
      case View::HOME: render_home_(); break;
      case View::MENU: render_menu_(); break;
      case View::INFO: render_info_(); break;
      case View::RING: render_ring_(); break;
      case View::CALL: render_call_(); break;
      case View::ALARM: render_alarm_(); break;
    }
    render_hints_(v);
    bool want_mic = v == View::INFO || talking_ || test_rec_;
    if (want_mic != mic_on_ && hooks.mic) {
      mic_on_ = want_mic;
      hooks.mic(want_mic);
    }
    lv_obj_move_foreground(hints_);
    lv_obj_move_foreground(v_flash_);
    lv_obj_move_foreground(toast_);
    apply_led_();
    apply_screen_(true);
  }

 protected:
  void render_status_() {
    if (!built_) return;
    char t[8];
    if (hh_ >= 0) snprintf(t, sizeof(t), "%02d:%02d", hh_, mm_);
    else snprintf(t, sizeof(t), "--:--");
    lv_label_set_text(st_time_, t);
    lv_obj_set_style_text_color(st_time_, lv_color_hex(hh_ >= 0 ? pal::TEXT : pal::FAINT), 0);  // grey = no time yet
    // alarm glyph
    const char *ai = icon::SHIELD_CHECK;
    uint32_t ac = pal::FAINT;
    switch (alarm_) {
      case Alarm::ARMED_HOME: case Alarm::ARMED_CUSTOM: ai = icon::SHIELD_HOME; ac = pal::RED; break;
      case Alarm::ARMED_AWAY: case Alarm::ARMED_VACATION: ai = icon::SHIELD_AWAY; ac = pal::RED; break;
      case Alarm::ARMED_NIGHT: ai = icon::SHIELD_MOON; ac = pal::RED; break;
      case Alarm::ARMING: ai = icon::TIMER; ac = pal::ORANGE; break;
      case Alarm::PENDING: case Alarm::TRIGGERED: ai = icon::SHIELD_ALERT; ac = pal::RED; break;
      case Alarm::UNKNOWN: ai = icon::SHIELD_CHECK; ac = pal::LINE; break;
      default: break;
    }
    lv_label_set_text(st_alarm_, ai);
    lv_obj_set_style_text_color(st_alarm_, lv_color_hex(ac), 0);
    bool offline = !online_ && !cfg.demo;
    if (offline) lv_obj_remove_flag(st_net_, LV_OBJ_FLAG_HIDDEN);
    else lv_obj_add_flag(st_net_, LV_OBJ_FLAG_HIDDEN);
    if (cfg.demo) lv_obj_remove_flag(st_demo_, LV_OBJ_FLAG_HIDDEN);
    else lv_obj_add_flag(st_demo_, LV_OBJ_FLAG_HIDDEN);
    if (missed_ > 0) {
      lv_obj_set_style_text_font(st_missed_, fonts.icon_sm, 0);
      lv_label_set_text(st_missed_, icon::BELL_RING);
      lv_obj_align(st_missed_, LV_ALIGN_RIGHT_MID, offline ? -59 : -37, 3);
      lv_obj_remove_flag(st_missed_, LV_OBJ_FLAG_HIDDEN);
    } else {
      lv_obj_add_flag(st_missed_, LV_OBJ_FLAG_HIDDEN);
    }
  }

  void render_home_() {
    // armed banner
    bool armed = is_armed(alarm_);
    if (armed || alarm_ == Alarm::ARMING) {
      uint32_t c = alarm_ == Alarm::ARMING ? pal::ORANGE : pal::RED;
      const char *txt = S->armed_custom;
      const char *ic = icon::SHIELD_LOCK;
      switch (alarm_) {
        case Alarm::ARMED_HOME: txt = S->armed_home; ic = icon::SHIELD_HOME; break;
        case Alarm::ARMED_AWAY: txt = S->armed_away; ic = icon::SHIELD_AWAY; break;
        case Alarm::ARMED_NIGHT: txt = S->armed_night; ic = icon::SHIELD_MOON; break;
        case Alarm::ARMED_VACATION: txt = S->armed_vacation; ic = icon::SHIELD_AWAY; break;
        case Alarm::ARMING: txt = S->arming; ic = icon::TIMER; break;
        default: break;
      }
      lv_obj_set_style_bg_color(banner_, lv_color_mix(lv_color_hex(c), lv_color_hex(pal::BG), LV_OPA_20), 0);
      lv_label_set_text(banner_icon_, ic);
      lv_obj_set_style_text_color(banner_icon_, lv_color_hex(c), 0);
      lv_label_set_text(banner_text_, txt);
      lv_obj_set_style_text_color(banner_text_, lv_color_hex(c), 0);
      lv_obj_remove_flag(banner_, LV_OBJ_FLAG_HIDDEN);
    } else {
      lv_obj_add_flag(banner_, LV_OBJ_FLAG_HIDDEN);
    }
    // hero
    if (lights_ == 1) {
      lv_label_set_text(home_icon_, icon::BULB);
      style_disc_(home_disc_, home_icon_, pal::AMBER, LV_OPA_20, 3, true);
      lv_label_set_text(home_title_, S->lights_on);
      lv_obj_set_style_text_color(home_title_, lv_color_hex(pal::AMBER), 0);
    } else {
      lv_label_set_text(home_icon_, icon::BULB_OUTLINE);
      style_disc_(home_disc_, home_icon_, pal::AMBER, 0, 2, false);
      lv_label_set_text(home_title_, lights_ == 0 ? S->lights_off : S->lights_unknown);
      lv_obj_set_style_text_color(home_title_, lv_color_hex(lights_ == 0 ? pal::TEXT : pal::MUTED), 0);
    }
    lv_label_set_text(home_sub_, cfg.room.c_str());
    bool disarm_mode = armed || alarm_ == Alarm::ARMING;
    lv_obj_set_style_arc_color(home_arc_, lv_color_hex(disarm_mode ? pal::RED : pal::CYAN), LV_PART_INDICATOR);
  }

  void render_menu_() {
    for (int i = 0; i < MENU_N; i++) {
      bool sel = i == menu_sel_;
      lv_obj_set_style_bg_opa(menu_rows_[i], sel ? LV_OPA_COVER : LV_OPA_TRANSP, 0);
      lv_obj_set_style_border_width(menu_rows_[i], sel ? 2 : 0, 0);
      lv_obj_set_style_border_color(menu_rows_[i], lv_color_hex(pal::CYAN), 0);
      lv_obj_set_style_text_color(menu_icons_[i], lv_color_hex(sel ? pal::CYAN : pal::FAINT), 0);
      lv_obj_set_style_text_color(menu_texts_[i], lv_color_hex(sel ? pal::TEXT : pal::MUTED), 0);
    }
  }

  void render_info_() {
    if (!built_) return;

    const char *alarm_txt = "—";
    switch (alarm_) {
      case Alarm::DISARMED: alarm_txt = "disarmed"; break;
      case Alarm::ARMING: alarm_txt = "arming"; break;
      case Alarm::ARMED_HOME: alarm_txt = "armed_home"; break;
      case Alarm::ARMED_AWAY: alarm_txt = "armed_away"; break;
      case Alarm::ARMED_NIGHT: alarm_txt = "armed_night"; break;
      case Alarm::ARMED_VACATION: alarm_txt = "armed_vacation"; break;
      case Alarm::ARMED_CUSTOM: alarm_txt = "armed_custom"; break;
      case Alarm::PENDING: alarm_txt = "pending"; break;
      case Alarm::TRIGGERED: alarm_txt = "triggered"; break;
      default: break;
    }
    char rssi[16];
    snprintf(rssi, sizeof(rssi), rssi_ ? "%d dBm" : "—", rssi_);
    const char *vals[INFO_N] = {online_ ? S->ha_on : S->ha_off, rssi, ip_.empty() ? "—" : ip_.c_str(), alarm_txt,
                                cfg.demo ? "demo" : "live", "0.1.0"};
    for (int i = 0; i < 6; i++) lv_label_set_text(info_val_[i], vals[i]);
    render_mic_row_();
    lv_obj_set_style_text_color(info_val_[0], lv_color_hex(online_ ? pal::GREEN : pal::ORANGE), 0);

  }

  // The visitor line at the top of the ring and call views: [type icon] "Front door" or who is there [?]
  struct DoorRow {
    lv_obj_t *icon = nullptr, *text = nullptr, *badge = nullptr;
    int y = 0;
  };
  lv_obj_t *door_label_(lv_obj_t *parent, DoorRow &row, int y) {
    row.y = y;
    row.icon = label_(parent, fonts.icon_sm, pal::CYAN, "");
    lv_obj_t *l = row.text = label_(parent, fonts.small, pal::CYAN, cfg.door.c_str());
    lv_label_set_long_mode(l, LV_LABEL_LONG_DOT);
    lv_obj_set_style_text_align(l, LV_TEXT_ALIGN_LEFT, 0);
    lv_obj_t *b = row.badge = box_(parent);           // "?": the visitor says so, nobody checked (§2c)
    lv_obj_set_size(b, 14, 14);
    lv_obj_set_style_radius(b, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_bg_opa(b, LV_OPA_COVER, 0);
    lv_obj_set_style_bg_color(b, lv_color_hex(pal::AMBER), 0);
    lv_obj_t *q = label_(b, fonts.small, pal::BG, "?");
    lv_obj_center(q);
    lv_obj_add_flag(b, LV_OBJ_FLAG_HIDDEN);
    layout_row_(row, cfg.door, nullptr, false, pal::CYAN);
    return l;
  }
  // Centre icon + text + badge as one line; the text is cut with "…" when it does not fit.
  void layout_row_(DoorRow &r, const std::string &text, const char *glyph, bool badge, uint32_t color) {
    const int ICON_W = glyph ? 20 : 0, BADGE_W = badge ? 18 : 0, MAX_W = 164;
    lv_point_t sz;
    lv_text_get_size(&sz, text.c_str(), fonts.small, lv_obj_get_style_text_letter_space(r.text, LV_PART_MAIN), 0, LV_COORD_MAX,
                     LV_TEXT_FLAG_NONE);
    const int tw = std::min<int>(sz.x + 2, MAX_W - ICON_W - BADGE_W);
    const int x0 = (172 - (ICON_W + tw + BADGE_W)) / 2;
    lv_label_set_text(r.icon, glyph ? glyph : "");
    lv_obj_set_style_text_color(r.icon, lv_color_hex(color), 0);
    lv_obj_align(r.icon, LV_ALIGN_TOP_LEFT, x0, r.y - 2);
    lv_label_set_text(r.text, text.c_str());
    lv_obj_set_style_text_color(r.text, lv_color_hex(color), 0);
    lv_obj_set_width(r.text, tw);
    lv_obj_align(r.text, LV_ALIGN_TOP_LEFT, x0 + ICON_W, r.y);
    lv_obj_align(r.badge, LV_ALIGN_TOP_LEFT, x0 + ICON_W + tw + 4, r.y + 1);
    if (badge) lv_obj_remove_flag(r.badge, LV_OBJ_FLAG_HIDDEN); else lv_obj_add_flag(r.badge, LV_OBJ_FLAG_HIDDEN);
  }
  void render_door_labels_() {
    if (!built_) return;
    const std::string t = visitor_.empty() ? cfg.door : visitor_;
    // an icon once the transcriber said something about the visitor; a red line for an emergency
    const bool known = !visitor_role_.empty() || visitor_urgent_;
    const std::string role = visitor_urgent_ && (visitor_role_.empty() || visitor_role_ == "name") ? "emergency" : visitor_role_;
    const char *glyph = known ? icon::visitor(role) : nullptr;
    const bool badge = icon::self_declared(visitor_role_);
    const uint32_t color = visitor_urgent_ ? pal::RED : pal::CYAN;
    layout_row_(ring_row_, t, glyph, badge, color);
    layout_row_(call_row_, visitor_lang_.empty() ? t : t + " · " + visitor_lang_, glyph, badge, color);
  }

  lv_obj_t *live_label_(lv_obj_t *parent, int y, int h) {
    lv_obj_t *l = label_(parent, fonts.small, pal::TEXT, "");
    lv_obj_set_width(l, 156);                     // fixed width, lines wrap; live_tail_() keeps it within h
    lv_label_set_long_mode(l, LV_LABEL_LONG_WRAP);
    (void) h;
    lv_obj_set_style_text_align(l, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_align(l, LV_ALIGN_TOP_MID, 0, y);
    lv_obj_add_flag(l, LV_OBJ_FLAG_HIDDEN);
    return l;
  }
  // The visible part: the last ~120 characters (start at a word), with "..." in front when cut.
  std::string live_tail_() const {
    std::string t = live_text_.substr(0, live_shown_);
    const size_t MAX = 120;
    if (t.size() <= MAX) return t;
    size_t cut = t.size() - MAX;
    while (cut < t.size() && t[cut] != ' ') cut++;
    return "..." + t.substr(cut);
  }
  void render_live_() {
    if (!built_) return;
    bool show = !live_text_.empty();
    std::string tail = live_tail_();
    for (lv_obj_t *l : {ring_live_, call_live_}) lv_label_set_text(l, tail.c_str());
    // ring view: the text replaces the bell; call view: the chat + text in progress replace the ear (the mic
    // still shows while you talk)
    bool ring_text = show, call_text = (show || !chat_rows_.empty()) && !talking_;
    if (ring_text) lv_obj_remove_flag(ring_live_, LV_OBJ_FLAG_HIDDEN); else lv_obj_add_flag(ring_live_, LV_OBJ_FLAG_HIDDEN);
    for (lv_obj_t *o : {ring_disc_, ripples_[0], ripples_[1]}) {
      if (ring_text) lv_obj_add_flag(o, LV_OBJ_FLAG_HIDDEN); else lv_obj_remove_flag(o, LV_OBJ_FLAG_HIDDEN);
    }
    if (show) lv_obj_remove_flag(call_live_, LV_OBJ_FLAG_HIDDEN); else lv_obj_add_flag(call_live_, LV_OBJ_FLAG_HIDDEN);
    lv_obj_set_style_text_align(call_live_, chat_rows_.empty() ? LV_TEXT_ALIGN_CENTER : LV_TEXT_ALIGN_LEFT, 0);
    if (call_text) lv_obj_remove_flag(chat_box_, LV_OBJ_FLAG_HIDDEN); else lv_obj_add_flag(chat_box_, LV_OBJ_FLAG_HIDDEN);
    if (call_text) lv_obj_add_flag(call_disc_, LV_OBJ_FLAG_HIDDEN); else lv_obj_remove_flag(call_disc_, LV_OBJ_FLAG_HIDDEN);
    if (talk_zone_) {   // touch: talk below the chat while the disc is hidden (and while talking, to release it there)
      bool zone = call_text || (talking_ && !lv_obj_has_flag(talk_zone_, LV_OBJ_FLAG_HIDDEN));
      if (zone) lv_obj_remove_flag(talk_zone_, LV_OBJ_FLAG_HIDDEN); else lv_obj_add_flag(talk_zone_, LV_OBJ_FLAG_HIDDEN);
    }
    if (call_text && chat_back_ == 0) scroll_chat_(false);
  }

  // One bubble per message, laid out by hand (no flex in this LVGL build): visitor left with type icon + who
  // (cyan), this house right (green), red frame for an emergency; the words in progress follow below.
  void build_chat_() {
    for (lv_obj_t *r : chat_rows_) lv_obj_delete(r);
    chat_rows_.clear();
    const int W = 156, TEXT_MAX = 134, PAD_X = 6, PAD_Y = 3, HEAD_H = 16, GAP = 5;
    int y = 0;
    for (const ChatMsg &m : chat_) {
      const uint32_t col = m.urgent ? pal::RED : m.door ? pal::CYAN : pal::GREEN;
      const std::string who = m.who + (m.lang.empty() ? "" : " · " + m.lang);
      lv_point_t ts, ws;
      lv_text_get_size(&ts, m.text.c_str(), fonts.small, 0, 0, TEXT_MAX, LV_TEXT_FLAG_NONE);
      lv_text_get_size(&ws, who.c_str(), fonts.small, 0, 0, LV_COORD_MAX, LV_TEXT_FLAG_NONE);
      const int icon_w = m.door ? 19 : 0;
      const int who_w = std::min<int>(ws.x + 2, TEXT_MAX - icon_w);
      const int inner_w = std::max<int>(std::min<int>(ts.x + 2, TEXT_MAX), icon_w + who_w);
      const int bw = inner_w + 2 * PAD_X, bh = HEAD_H + ts.y + 2 * PAD_Y;
      lv_obj_t *b = box_(chat_box_);
      lv_obj_set_size(b, bw, bh);
      lv_obj_set_pos(b, m.door ? 0 : W - bw, y);
      lv_obj_set_style_radius(b, 8, 0);
      lv_obj_set_style_bg_opa(b, LV_OPA_COVER, 0);
      lv_obj_set_style_bg_color(b, lv_color_hex(m.door ? pal::RAISED : pal::SURFACE), 0);
      if (m.urgent) {
        lv_obj_set_style_border_width(b, 1, 0);
        lv_obj_set_style_border_color(b, lv_color_hex(pal::RED), 0);
      }
      if (m.door) {
        lv_obj_t *ic = label_(b, fonts.icon_sm, col,
                              icon::visitor(m.urgent && (m.role.empty() || m.role == "name") ? "emergency" : m.role));
        lv_obj_set_pos(ic, PAD_X, PAD_Y - 1);
      }
      lv_obj_t *w = label_(b, fonts.small, col, who.c_str());
      lv_label_set_long_mode(w, LV_LABEL_LONG_DOT);
      lv_obj_set_size(w, who_w, HEAD_H);   // one line, "…" when too long
      lv_obj_set_pos(w, PAD_X + icon_w, PAD_Y);
      lv_obj_t *t = label_(b, fonts.small, pal::TEXT, m.text.c_str());
      lv_label_set_long_mode(t, LV_LABEL_LONG_WRAP);
      lv_obj_set_width(t, std::min<int>(ts.x + 2, TEXT_MAX));
      lv_obj_set_pos(t, PAD_X, PAD_Y + HEAD_H);
      chat_rows_.push_back(b);
      y += bh + GAP;
    }
    chat_end_y_ = y;
    lv_obj_align(call_live_, LV_ALIGN_TOP_LEFT, 0, y);   // the words in progress below the last message
  }
  void scroll_chat_(bool anim) {   // to the newest: the words in progress, else the last message
    lv_obj_update_layout(chat_box_);
    lv_obj_t *target = !lv_obj_has_flag(call_live_, LV_OBJ_FLAG_HIDDEN) ? call_live_
                       : chat_rows_.empty() ? nullptr : chat_rows_.back();
    if (target) lv_obj_scroll_to_view(target, anim ? LV_ANIM_ON : LV_ANIM_OFF);
  }

  void render_ring_() {
    render_live_();
    lv_label_set_text(ring_icon_, ringing_ ? icon::BELL_RING : icon::PHONE_TALK);
    if (!ringing_) for (lv_obj_t *r : ripples_) lv_obj_add_flag(r, LV_OBJ_FLAG_HIDDEN);   // no ringing waves
    lv_label_set_text(ring_title_, ringing_ ? S->doorbell : answered_elsewhere_ ? S->answered : S->door_call);
    if (!ringing_) {   // answered in another room (R19) or a call nobody rang for (R21): press = listen in, hold = talk
      lv_label_set_text(ring_sub_, S->join_hint);
      return;
    }
    char sub[48];
    if (!visitor_lang_.empty()) snprintf(sub, sizeof(sub), S->speaks, visitor_lang_.c_str());   // "Speaks Chinese"
    else snprintf(sub, sizeof(sub), "%02d:%02d", hh_, mm_);
    lv_label_set_text(ring_sub_, (hh_ >= 0 || !visitor_lang_.empty()) ? sub : "");
  }

  void render_call_() {
    render_live_();
    // Walkie-talkie, not a phone call: the clock shows how long you are talking right now, nothing while listening
    // (a conversation stays open for minutes in the background; its total length would look like a long call).
    char t[12] = "";
    if (talking_ && !floor_busy_) {   // busy: nothing goes out, so no talk clock
      uint32_t s = (millis() - talk_since_ms_) / 1000;
      snprintf(t, sizeof(t), "%u:%02u", (unsigned) (s / 60), (unsigned) (s % 60));
    }
    lv_label_set_text(call_timer_, t);
    if (talking_ && floor_busy_) {   // holding, but another room has the floor: nothing is sent (R17.14)
      lv_label_set_text(call_icon_, icon::MIC);
      style_disc_(call_disc_, call_icon_, pal::ORANGE, LV_OPA_20, 3, false);
      lv_label_set_text(call_state_, S->busy);
      lv_obj_set_style_text_color(call_state_, lv_color_hex(pal::ORANGE), 0);
    } else if (talking_) {
      lv_label_set_text(call_icon_, icon::MIC);
      style_disc_(call_disc_, call_icon_, pal::GREEN, LV_OPA_30, 4, true);
      lv_label_set_text(call_state_, S->talking);
      lv_obj_set_style_text_color(call_state_, lv_color_hex(pal::GREEN), 0);
    } else {
      lv_label_set_text(call_icon_, icon::EAR);
      style_disc_(call_disc_, call_icon_, pal::CYAN, LV_OPA_10, 3, false);
      const bool chat_shown = !lv_obj_has_flag(chat_box_, LV_OBJ_FLAG_HIDDEN);
      lv_label_set_text(call_state_, talk_zone_ && chat_shown ? S->hold_here : S->listening);
      lv_obj_set_style_text_color(call_state_, lv_color_hex(pal::CYAN), 0);
    }
    for (int i = 0; i < METER_N; i++)
      lv_obj_set_style_bg_color(meter_[i], lv_color_hex(talking_ ? (floor_busy_ ? pal::ORANGE : pal::GREEN) : pal::CYAN), 0);
  }

  void render_alarm_() {
    bool trig = alarm_ == Alarm::TRIGGERED;
    uint32_t c = trig ? pal::RED : (alarm_ == Alarm::PENDING ? pal::ORANGE : pal::RED);
    lv_label_set_text(alarm_head_, trig ? S->alarm : (alarm_ == Alarm::PENDING ? S->entry_delay : S->alarm));
    lv_obj_set_style_text_color(alarm_head_, lv_color_hex(c), 0);
    lv_label_set_text(alarm_icon_, trig ? icon::ALARM_LIGHT : icon::SHIELD_ALERT);
    style_disc_(alarm_disc_, alarm_icon_, c, LV_OPA_20, 3, false);
    lv_obj_set_style_arc_color(alarm_arc_, lv_color_hex(disarming_ ? pal::MUTED : c), LV_PART_INDICATOR);
    for (lv_obj_t *e : alarm_edge_) lv_obj_set_style_bg_color(e, lv_color_hex(c), 0);
    if (disarming_) {
      lv_label_set_text(alarm_title_, S->disarming);
      lv_label_set_text(alarm_sub_, "…");
    } else {
      lv_label_set_text(alarm_title_, S->hold_to_disarm);
      if (alarm_ == Alarm::PENDING) {
        uint32_t s = (millis() - pending_since_) / 1000;
        char t[24];
        snprintf(t, sizeof(t), "%u s", (unsigned) s);
        lv_label_set_text(alarm_sub_, t);
      } else {
        lv_label_set_text(alarm_sub_, cfg.room.c_str());
      }
    }
    lv_obj_set_style_text_font(alarm_title_, disarming_ ? fonts.title : fonts.body, 0);
  }

  void render_hints_(View v) {
    const char *press = nullptr, *hold = nullptr;
    uint32_t hold_col = pal::TEXT;
    bool armed = is_armed(alarm_) || alarm_ == Alarm::ARMING;
    switch (v) {
      case View::HOME:
        press = S->a_lights;
        hold = armed ? S->a_disarm : S->a_talk;
        if (armed) hold_col = pal::RED;
        break;
      case View::MENU: press = S->a_next; hold = S->a_select; break;
      case View::INFO: press = S->a_back; break;
      case View::RING: press = ringing_ ? S->a_answer : S->a_join; hold = S->a_talk; hold_col = pal::GREEN; break;
      case View::CALL:   // push-to-talk only: no hang-up
        press = chat_rows_.empty() ? nullptr : S->a_older;
        hold = S->a_talk;
        hold_col = pal::GREEN;
        break;
      case View::ALARM: hold = disarming_ ? nullptr : S->a_disarm; hold_col = pal::RED; break;
    }
    const char *acts[2] = {press, hold};
    uint32_t cols[2] = {pal::TEXT, hold_col};
    for (int i = 0; i < 2; i++) {
      bool on = acts[i] != nullptr;
      lv_label_set_text(hint_act_[i], on ? acts[i] : "—");
      lv_obj_set_style_text_color(hint_act_[i], lv_color_hex(on ? cols[i] : pal::FAINT), 0);
      lv_obj_set_style_bg_color(hint_glyph_[i], lv_color_hex(on ? pal::MUTED : pal::LINE), 0);
      lv_obj_set_style_text_color(hint_verb_[i], lv_color_hex(on ? pal::MUTED : pal::LINE), 0);
    }
  }

  // ── actions ───────────────────────────────────────────────────────────────
  void on_press_() {
    switch (view()) {
      case View::HOME:   // press = lights, double press = menu (so a single press waits DOUBLE_MS)
        if (double_) open_menu();
        else { pending_press_ = true; pending_press_ms_ = millis(); }
        break;
      case View::MENU:
        menu_sel_ = (menu_sel_ + 1) % MENU_N;
        render_menu_();
        break;
      case View::INFO: info_open_ = false; render(); break;
      case View::RING: answer_(); break;
      case View::CALL:  // push-to-talk only, no hang-up. A press scrolls the chat one message back.
        if (!chat_rows_.empty()) {
          lv_obj_update_layout(chat_box_);
          chat_back_ = lv_obj_get_scroll_top(chat_box_) > 0;   // at the oldest already: back to the newest
          chat_back_ms_ = millis();
          call_seen_ms_ = millis();
          if (chat_back_) lv_obj_scroll_by_bounded(chat_box_, 0, 100, LV_ANIM_ON);
          else scroll_chat_(true);
        }
        break;
      case View::ALARM:
        if (!disarming_) { shake_(alarm_disc_); show_toast_(S->hold_to_disarm, 1400); }
        break;
    }
  }
  uint32_t hold_ms_() {
    switch (view()) {
      case View::HOME: return (is_armed(alarm_) || alarm_ == Alarm::ARMING) ? cfg.disarm_hold_ms : cfg.talk_hold_ms;
      case View::MENU: return 500;
      case View::CALL: return cfg.talk_hold_ms;
      case View::ALARM: return disarming_ ? 0 : cfg.disarm_hold_ms;
      default: return 0;
    }
  }
  void on_hold_() {
    ESP_LOGD(TAG, "hold fired in %s", view_name());
    switch (view()) {
      case View::HOME:   // hold = talk to the door, always (decided 01.10.); armed: hold = disarm
        if (is_armed(alarm_) || alarm_ == Alarm::ARMING) disarm_();
        else { begin_call_(); set_talk_(true); }
        break;
      case View::MENU: menu_select_(menu_sel_); break;
      case View::CALL: set_talk_(true); break;
      case View::ALARM: disarm_(); break;
      default: break;
    }
  }
  void on_hold_release_() {
    if (talking_) set_talk_(false);
  }

  void toggle_lights_() {
    if (!cfg.demo && !online_) { show_toast_(S->not_sent, 1600); shake_(home_disc_); return; }
    lights_ = lights_ == 1 ? 0 : 1;  // optimistic — HA will confirm or correct
    lights_pending_until_ = cfg.demo ? 0 : millis() + 2500;
    if (!cfg.demo && hooks.toggle_lights) hooks.toggle_lights();
    render_home_();
  }
  void disarm_() {
    disarming_ = true;
    disarm_since_ = millis();
    if (test_alarm_ || cfg.demo) {
      demo_disarm_at_ = millis() + 900;
    } else if (!online_) {
      disarming_ = false;
      show_toast_(S->not_sent, 1600);
    } else if (hooks.disarm) {
      hooks.disarm();
    }
    render();
  }
  void answer_() {
    ringing_ = false;
    if (hooks.ringtone) hooks.ringtone(false);
    if (hooks.answer && !cfg.demo) hooks.answer();
    begin_call_();
  }
  void dismiss_ring_() {   // the user waved the ring (or the join offer) away: no join view for this call
    ring_stop();
    answered_elsewhere_ = false;
    join_dismissed_ = true;
    render();
  }
  // The join offer ("Drücken: mithören"): a call runs at the door and this key is not in it. R19: it rang here and another
  // room answered; R21: a call nobody rang for (another room started it). Door state unknown after an answer: 2 min.
  bool joinable_() const {
    if (in_call_ || join_dismissed_) return false;
    if (door_call_ == 1) return true;
    return answered_elsewhere_ && door_call_ != 0 && age_(answered_ms_) < (int32_t) JOIN_UNKNOWN_MS;
  }
  void begin_call_() {
    call_seen_ms_ = millis();
    answered_elsewhere_ = false;
    if (in_call_) return;
    in_call_ = true;
    talking_ = false;
    call_since_ = millis();
    menu_open_ = info_open_ = false;
    render();
  }
  void clear_chat_() {
    chat_in_.clear();
    show_chat_();
  }
  void end_call_(bool local) {
    if (!in_call_) return;
    if (talking_) set_talk_(false);
    in_call_ = false;
    if (door_call_ != 1) clear_chat_();   // R22: the call is over here and at the door
    visitor_.clear();
    visitor_lang_.clear();
    visitor_role_.clear();
    visitor_urgent_ = false;
    live_text_.clear();
    live_shown_ = 0;
    render_door_labels_();
    if (local && hooks.hangup && !cfg.demo) hooks.hangup();
    render();
  }
  void set_talk_(bool on) {
    if (talking_ == on) return;
    talking_ = on;
    call_seen_ms_ = millis();
    if (on) talk_since_ms_ = millis();
    if (hooks.talk) hooks.talk(on);
    if (hooks.gesture) hooks.gesture(on ? "talk_start" : "talk_stop");
    render_call_();
    render();  // (re)evaluates mic capture
  }
  void menu_select_(int i) {
    ESP_LOGD(TAG, "menu select %d", i);
    menu_open_ = false;
    switch (i) {
      case 0:  // talk to door
        if (hooks.call_door && !cfg.demo) hooks.call_door();
        begin_call_();
        break;
      case 1: info_open_ = true; break;
      case 2: demo_ring_at_ = millis() + 400; break;
      case 3: start_test_alarm_(); break;
      default: break;
    }
    render();
  }
  void start_test_alarm_() {
    test_alarm_ = true;
    saved_alarm_ = alarm_;
    set_alarm(Alarm::ARMED_NIGHT);
    demo_pending_at_ = millis() + 3500;
    demo_trigger_at_ = millis() + 13500;
  }

  // Local simulation, used in demo mode and for the menu's test entries.
  void run_demo_(uint32_t now) {
    if (demo_ring_at_ && now > demo_ring_at_) { demo_ring_at_ = 0; ring_start(); }
    if (demo_pending_at_ && now > demo_pending_at_) { demo_pending_at_ = 0; if (test_alarm_ && !disarming_) set_alarm(Alarm::PENDING); }
    if (demo_trigger_at_ && now > demo_trigger_at_) {
      demo_trigger_at_ = 0;
      if (test_alarm_ && alarm_ == Alarm::PENDING && !disarming_) set_alarm(Alarm::TRIGGERED);
    }
    if (demo_disarm_at_ && now > demo_disarm_at_) {
      demo_disarm_at_ = 0;
      bool was_test = test_alarm_;
      test_alarm_ = false;
      demo_pending_at_ = demo_trigger_at_ = 0;
      set_alarm(Alarm::DISARMED);
      if (was_test && !cfg.demo) { alarm_ = saved_alarm_; render(); }
    }
    if (in_call_ && (cfg.demo || level_in_ < 0)) {  // fake speech envelope
      float t = now / 1000.0f;
      float env = 0.5f + 0.5f * sinf(t * 2.3f) * sinf(t * 0.7f + 1.0f);
      level_demo_ = env * (0.55f + 0.45f * sinf(t * 17.0f));
    }
  }

  // ── animation ─────────────────────────────────────────────────────────────
  static void anim_press_cb_(void *o, int32_t v) {  // v = diameter; keeps the disc centred
    lv_obj_t *d = (lv_obj_t *) o;
    int cy = (int) (intptr_t) lv_obj_get_user_data(d);
    lv_obj_set_size(d, v, v);
    lv_obj_align(d, LV_ALIGN_TOP_MID, 0, cy - v / 2);
  }
  static void anim_rot_cb_(void *o, int32_t v) { lv_obj_set_style_transform_rotation((lv_obj_t *) o, v, 0); }
  static void anim_opa_cb_(void *o, int32_t v) { lv_obj_set_style_opa((lv_obj_t *) o, v, 0); }
  static void anim_bgopa_cb_(void *o, int32_t v) { lv_obj_set_style_bg_opa((lv_obj_t *) o, v, 0); }
  static void anim_x_cb_(void *o, int32_t v) { lv_obj_set_style_translate_x((lv_obj_t *) o, v, 0); }
  static void anim_arc_rot_cb_(void *o, int32_t v) { lv_arc_set_rotation((lv_obj_t *) o, v); }
  static void anim_ripple_cb_(void *o, int32_t v) {  // v: 0..1000
    lv_obj_t *r = (lv_obj_t *) o;
    int s = 118 + v * 54 / 1000;
    lv_obj_set_size(r, s, s);
    lv_obj_align(r, LV_ALIGN_TOP_MID, 0, 140 - s / 2);
    lv_obj_set_style_border_opa(r, (lv_opa_t) (200 - v * 200 / 1000), 0);
  }

  static void anim_(void *var, lv_anim_exec_xcb_t cb, int32_t from, int32_t to, uint32_t ms, bool loop,
                    bool reverse, uint32_t delay = 0, lv_anim_path_cb_t path = lv_anim_path_ease_in_out) {
    lv_anim_t a;
    lv_anim_init(&a);
    lv_anim_set_var(&a, var);
    lv_anim_set_exec_cb(&a, cb);
    lv_anim_set_values(&a, from, to);
    lv_anim_set_duration(&a, ms);
    lv_anim_set_delay(&a, delay);
    lv_anim_set_path_cb(&a, path);
    if (reverse) lv_anim_set_reverse_duration(&a, ms);
    if (loop) lv_anim_set_repeat_count(&a, LV_ANIM_REPEAT_INFINITE);
    lv_anim_start(&a);
  }

  void start_anims_(View v) {
    switch (v) {
      case View::RING:
        if (!ringing_) break;   // answered elsewhere: no ringing animation
        for (int i = 0; i < 2; i++) anim_(ripples_[i], anim_ripple_cb_, 0, 1000, 1400, true, false, i * 700, lv_anim_path_ease_out);
        anim_(ring_icon_, anim_rot_cb_, -140, 140, 90, true, true);
        break;
      case View::ALARM:
        if (disarming_) {  // indeterminate spinner on the hold arc
          lv_arc_set_value(alarm_arc_, 220);
          lv_obj_remove_flag(alarm_arc_, LV_OBJ_FLAG_HIDDEN);
          anim_(alarm_arc_, anim_arc_rot_cb_, 0, 360, 900, true, false, 0, lv_anim_path_linear);
        } else {
          bool trig = alarm_ == Alarm::TRIGGERED;
          for (lv_obj_t *e : alarm_edge_) anim_(e, anim_bgopa_cb_, 0, 255, trig ? 240 : 800, true, true);
        }
        break;
      default: break;
    }
  }
  void stop_anims_() {
    for (int i = 0; i < 2; i++) lv_anim_delete(ripples_[i], anim_ripple_cb_);
    lv_anim_delete(ring_icon_, anim_rot_cb_);
    for (lv_obj_t *e : alarm_edge_) {
      lv_anim_delete(e, anim_bgopa_cb_);
      lv_obj_set_style_bg_opa(e, LV_OPA_TRANSP, 0);
    }
    lv_anim_delete(alarm_arc_, anim_arc_rot_cb_);
    lv_obj_set_style_transform_rotation(ring_icon_, 0, 0);
    lv_arc_set_rotation(alarm_arc_, 270);
    lv_obj_add_flag(alarm_arc_, LV_OBJ_FLAG_HIDDEN);
  }
  void animate_meter_(uint32_t now) {
    float lvl = (cfg.demo || level_in_ < 0) ? level_demo_ : level_in_;
    if (talking_ && mic_level_ >= 0) lvl = mic_level_;  // real microphone when fitted
    for (int i = 0; i < METER_N; i++) {
      float shape = 1.0f - fabsf((float) (i - METER_N / 2)) / (METER_N / 2 + 1);
      float jitter = 0.75f + 0.25f * sinf(now / 90.0f + i * 1.7f);
      int h = 6 + (int) (lvl * shape * jitter * 26);
      lv_obj_set_height(meter_[i], h);
      lv_obj_align(meter_[i], LV_ALIGN_TOP_MID, (i - METER_N / 2) * 13, 232 - h / 2);
    }
  }
  lv_obj_t *active_disc_() {
    switch (view()) {
      case View::HOME: return home_disc_;
      case View::RING: return ring_disc_;
      case View::CALL: return call_disc_;
      case View::ALARM: return alarm_disc_;
      default: return nullptr;
    }
  }
  void press_anim_(bool down) {  // the disc travels with the physical key
    lv_obj_t *d = down ? active_disc_() : pressed_disc_;
    pressed_disc_ = down ? d : nullptr;
    if (!d) return;
    lv_anim_delete(d, anim_press_cb_);
    anim_(d, anim_press_cb_, down ? 118 : 108, down ? 108 : 118, down ? 60 : 160, false, false, 0,
          down ? lv_anim_path_ease_out : lv_anim_path_overshoot);
  }
  void shake_(lv_obj_t *o) {
    lv_anim_delete(o, anim_x_cb_);
    lv_anim_t a;
    lv_anim_init(&a);
    lv_anim_set_var(&a, o);
    lv_anim_set_exec_cb(&a, anim_x_cb_);
    lv_anim_set_values(&a, -7, 7);
    lv_anim_set_duration(&a, 50);
    lv_anim_set_reverse_duration(&a, 50);
    lv_anim_set_repeat_count(&a, 3);
    lv_anim_set_completed_cb(&a, [](lv_anim_t *an) { lv_obj_set_style_translate_x((lv_obj_t *) an->var, 0, 0); });
    lv_anim_start(&a);
  }
  void set_hold_progress_(int permille) {
    lv_obj_t *arc = nullptr;
    View v = view();
    if (v == View::HOME) arc = home_arc_;
    else if (v == View::ALARM) arc = alarm_arc_;
    // The disarming spinner reuses the alarm arc; don't hide it while it's spinning.
    if (disarming_ && v == View::ALARM) return;
    for (lv_obj_t *a : {home_arc_, alarm_arc_}) {
      if (a != arc || permille <= 0) lv_obj_add_flag(a, LV_OBJ_FLAG_HIDDEN);
    }
    if (arc && permille > 0) {
      lv_obj_remove_flag(arc, LV_OBJ_FLAG_HIDDEN);
      lv_arc_set_value(arc, permille > 1000 ? 1000 : permille);
    }
    if (v == View::MENU && permille > 0) {  // menu: fill the selected row's border instead
      lv_obj_set_style_border_width(menu_rows_[menu_sel_], 2 + permille / 350, 0);
    }
  }
  void flash(const char *ic, const char *text, uint32_t color, uint32_t ms) {
    lv_label_set_text(flash_icon_, ic);
    style_disc_(flash_disc_, flash_icon_, color, LV_OPA_20, 3, true);
    lv_label_set_text(flash_text_, text);
    lv_obj_set_style_text_color(flash_text_, lv_color_hex(color), 0);
    lv_obj_remove_flag(v_flash_, LV_OBJ_FLAG_HIDDEN);
    lv_obj_move_foreground(v_flash_);
    lv_obj_move_foreground(toast_);
    flash_until_ = millis() + ms;
    wake();
  }
  void show_toast_(const char *text, uint32_t ms) {
    if (!built_) return;
    lv_label_set_text(toast_text_, text);
    lv_obj_remove_flag(toast_, LV_OBJ_FLAG_HIDDEN);
    lv_obj_move_foreground(toast_);
    toast_until_ = millis() + ms;
  }

  // ── screen power + status LED ─────────────────────────────────────────────
 public:
  void wake() {
    last_input_ms_ = millis();
    if (screen_ != Screen::ACTIVE) { screen_ = Screen::ACTIVE; apply_screen_(true); }
  }

 protected:
  void apply_screen_(bool force) {
    View v = view();
    Screen want = Screen::ACTIVE;
    int32_t idle = age_(last_input_ms_);
    bool calm = v == View::HOME && !key_down_;
    if (calm && cfg.off_after_ms && idle > (int32_t) cfg.off_after_ms) want = Screen::OFF;
    else if (calm && cfg.dim_after_ms && idle > (int32_t) cfg.dim_after_ms) want = Screen::DIM;
    if (want == screen_ && !force) return;
    screen_ = want;
    float b = want == Screen::ACTIVE ? cfg.bright : want == Screen::DIM ? cfg.bright_dim : 0.0f;
    if (hooks.backlight) hooks.backlight(b);
  }
  void apply_led_() {
    if (!hooks.led || led_hold_until_) return;
    switch (view()) {
      case View::RING: hooks.led(pal::CYAN, ringing_ ? "pulse" : "off"); break;   // a join offer stays dark (night)
      case View::CALL: hooks.led(talking_ ? pal::GREEN : pal::CYAN, "solid"); break;
      case View::ALARM:
        if (disarming_) hooks.led(pal::RED, "pulse");
        else if (alarm_ == Alarm::TRIGGERED) hooks.led(pal::RED, "strobe");
        else hooks.led(pal::ORANGE, "pulse");
        break;
      default: hooks.led(0, "off"); break;
    }
  }

  // ── touch ─────────────────────────────────────────────────────────────────
  void cancel_touch_() {
    for (lv_indev_t *i = lv_indev_get_next(nullptr); i; i = lv_indev_get_next(i))
      if (lv_indev_get_type(i) == LV_INDEV_TYPE_POINTER) lv_indev_wait_release(i);
  }
  bool touch_wakes_only_() {  // first touch on a dark screen only wakes it
    bool dark = screen_ != Screen::ACTIVE;
    wake();
    return dark;
  }
  static void on_tap_cb_(lv_event_t *e) {
    auto *c = (Controller *) lv_event_get_user_data(e);
    if (c->key_down_ || c->touch_wakes_only_()) return;
    if (c->hooks.gesture) c->hooks.gesture("tap");
    View v = c->view();
    // Home: a tap never switches anything — in the wall insert the light rocker surrounds the
    // key, so fingers brush the screen all the time. Actions come from the key.
    if (v == View::HOME) c->show_toast_(c->S->tap_hint, 1400);
    else if (v == View::RING) c->answer_();
  }
  static void on_dismiss_cb_(lv_event_t *e) {
    auto *c = (Controller *) lv_event_get_user_data(e);
    if (c->key_down_) return;
    if (c->hooks.dismiss && !c->cfg.demo) c->hooks.dismiss();
    c->dismiss_ring_();
  }
  static void on_hangup_cb_(lv_event_t *e) {
    auto *c = (Controller *) lv_event_get_user_data(e);
    if (!c->key_down_) c->end_call_(true);
  }
  // a finger moved the chat: stay on the call view, and don't jump back to the newest while the user reads
  static void on_chat_scroll_cb_(lv_event_t *e) {
    auto *c = (Controller *) lv_event_get_user_data(e);
    if (lv_indev_active() == nullptr) return;   // our own scroll_chat_()
    c->call_seen_ms_ = c->chat_back_ms_ = millis();
    c->chat_back_ = lv_obj_get_scroll_bottom(c->chat_box_) > 4;
  }
  static void on_call_disc_cb_(lv_event_t *e) {
    auto *c = (Controller *) lv_event_get_user_data(e);
    if (c->key_down_) return;
    lv_event_code_t code = lv_event_get_code(e);
    if (code == LV_EVENT_PRESSED) c->set_talk_(true);
    else if (code == LV_EVENT_RELEASED || code == LV_EVENT_PRESS_LOST) c->set_talk_(false);
  }
  static void on_menu_tap_cb_(lv_event_t *e) {
    auto *c = (Controller *) lv_event_get_user_data(e);
    if (c->key_down_) return;
    c->last_input_ms_ = millis();
    int i = (int) (intptr_t) lv_obj_get_user_data(lv_event_get_target_obj(e));
    c->menu_select_(i);
  }
  static void on_gesture_cb_(lv_event_t *e) {
    auto *c = (Controller *) lv_event_get_user_data(e);
    if (c->key_down_ || c->touch_wakes_only_()) return;
    lv_dir_t dir = lv_indev_get_gesture_dir(lv_indev_active());
    View v = c->view();
    if (dir == LV_DIR_TOP) {  // swipe up: open menu from home
      if (c->hooks.gesture) c->hooks.gesture("swipe_up");
      if (v == View::HOME) c->open_menu();
    } else if (dir == LV_DIR_BOTTOM) {  // swipe down: back / dismiss
      if (c->hooks.gesture) c->hooks.gesture("swipe_down");
      if (v == View::MENU || v == View::INFO) { c->menu_open_ = c->info_open_ = false; c->render(); }
      else if (v == View::RING) { if (c->hooks.dismiss && !c->cfg.demo) c->hooks.dismiss(); c->dismiss_ring_(); }
      else if (v == View::CALL) c->end_call_(true);
    }
    lv_indev_wait_release(lv_indev_active());
  }
  static void tick_cb_(lv_timer_t *t) { ((Controller *) lv_timer_get_user_data(t))->tick(); }

  // ── state ─────────────────────────────────────────────────────────────────
  static constexpr int MENU_N = 5;
  static constexpr int METER_N = 7;
  static constexpr int INFO_N = 7;

  bool built_ = false;
  int lights_ = -1;
  uint32_t lights_pending_until_ = 0;
  Alarm alarm_ = Alarm::UNKNOWN, saved_alarm_ = Alarm::UNKNOWN;
  bool ringing_ = false, in_call_ = false, talking_ = false;
  bool menu_open_ = false, info_open_ = false, disarming_ = false, test_alarm_ = false;
  bool online_ = false;
  bool test_rec_ = false;
  static constexpr uint32_t DOUBLE_MS = 350, CALL_SHOW_MS = 8000;
  uint32_t call_seen_ms_ = 0, talk_since_ms_ = 0;
  bool pending_press_ = false, double_ = false;
  uint32_t pending_press_ms_ = 0;
  bool answered_elsewhere_ = false, door_answered_ = false, floor_busy_ = false, join_dismissed_ = false;
  int door_call_ = -1;                                  // -1 unknown, 0 no call at the door, 1 call
  uint32_t answered_ms_ = 0;
  static constexpr uint32_t JOIN_UNKNOWN_MS = 120000;
  std::string visitor_, visitor_lang_, visitor_role_, live_started_;
  std::vector<ChatMsg> chat_, chat_in_;   // shown; as received from aikos' call log
  bool chat_active_ = false;              // the call log's "active" (R22: no chat without it)
  uint32_t call_id_ = 0;
  bool call_id_known_ = false;
  std::vector<lv_obj_t *> chat_rows_;
  lv_obj_t *chat_box_ = nullptr, *talk_zone_ = nullptr;
  int chat_back_ = 0;            // 1 = scrolled back (a press moves 100 px up; at the top it returns to the newest)
  int chat_end_y_ = 0;
  uint32_t chat_back_ms_ = 0;
  bool visitor_urgent_ = false;
  uint32_t visitor_text_n_ = 0;
  lv_obj_t *ring_door_ = nullptr, *call_door_ = nullptr;
  DoorRow ring_row_, call_row_;
  int menu_sel_ = 0, missed_ = 0;
  char missed_at_[8] = "";
  int hh_ = -1, mm_ = -1, rssi_ = 0;
  std::string ip_;
  float level_in_ = -1.0f, level_demo_ = 0.0f;
  volatile float mic_level_ = -1.0f, mic_db_ = -120.0f;
  bool mic_on_ = false;
  uint32_t ring_since_ = 0, call_since_ = 0, disarm_since_ = 0, pending_since_ = 0;
  uint32_t demo_ring_at_ = 0, demo_pending_at_ = 0, demo_trigger_at_ = 0, demo_disarm_at_ = 0;
  uint32_t last_mic_ui_ = 0, flash_until_ = 0, toast_until_ = 0, led_hold_until_ = 0, last_second_ = 0;
  bool key_down_ = false, hold_fired_ = false, key_consumed_ = false;
  uint32_t key_down_ms_ = 0, last_input_ms_ = 0;
  Screen screen_ = Screen::ACTIVE;
  View shown_ = (View) 255;
  int anim_sig_ = -1;
  lv_obj_t *pressed_disc_ = nullptr;
  lv_timer_t *timer_ = nullptr;

  lv_obj_t *scr_ = nullptr, *status_ = nullptr, *st_time_, *st_alarm_, *st_net_, *st_missed_, *st_demo_;
  lv_obj_t *v_home_, *banner_, *banner_icon_, *banner_text_, *home_disc_, *home_icon_, *home_arc_, *home_title_,
      *home_sub_;
  lv_obj_t *v_menu_, *menu_rows_[MENU_N], *menu_icons_[MENU_N], *menu_texts_[MENU_N];
  lv_obj_t *v_info_, *info_val_[7], *mic_bar_bg_, *mic_bar_;
  lv_obj_t *v_ring_, *ripples_[2], *ring_disc_, *ring_icon_, *ring_title_, *ring_sub_, *ring_live_ = nullptr, *call_live_ = nullptr;
  std::string live_text_;
  size_t live_shown_ = 0;
  lv_obj_t *v_call_, *call_timer_, *call_disc_, *call_icon_, *call_state_, *meter_[METER_N];
  lv_obj_t *v_alarm_, *alarm_edge_[4], *alarm_head_, *alarm_disc_, *alarm_icon_, *alarm_arc_, *alarm_title_, *alarm_sub_;
  lv_obj_t *hints_, *hint_glyph_[2], *hint_verb_[2], *hint_act_[2];
  lv_obj_t *v_flash_, *flash_disc_, *flash_icon_, *flash_text_;
  lv_obj_t *toast_, *toast_text_;
};

inline Controller &ctl() {
  static Controller c;
  return c;
}

}  // namespace roomkey
