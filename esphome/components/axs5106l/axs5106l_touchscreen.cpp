#include "axs5106l_touchscreen.h"

namespace esphome::axs5106l {

i2c::ErrorCode AXS5106LTouchscreen::read_reg_(uint8_t reg, uint8_t *data, uint8_t len) {
  // This controller NACKs repeated-start reads, so write the register pointer
  // as its own transaction (STOP), then issue a separate read.
  i2c::ErrorCode err = this->write(&reg, 1);
  if (err != i2c::ERROR_OK) {
    return err;
  }
  return this->read(data, len);
}

void AXS5106LTouchscreen::setup() {
  // Hardware reset sequence: LOW for 200 ms, then HIGH and wait 300 ms.
  if (this->reset_pin_ != nullptr) {
    this->reset_pin_->setup();
    this->reset_pin_->digital_write(true);
    delay(10);
    this->reset_pin_->digital_write(false);
    delay(200);
    this->reset_pin_->digital_write(true);
    delay(300);
  }

  // Read the device id. The first byte is non-zero when the controller is present.
  uint8_t id[3] = {0, 0, 0};
  if (this->read_reg_(AXS5106L_REG_ID, id, sizeof(id)) != i2c::ERROR_OK) {
    ESP_LOGE(TAG, "AXS5106L not found on I2C bus (0x63) - check SDA/SCL/reset wiring");
    this->mark_failed();
    return;
  }
  ESP_LOGCONFIG(TAG, "AXS5106L id bytes: 0x%02X 0x%02X 0x%02X", id[0], id[1], id[2]);
  if (id[0] == 0) {
    ESP_LOGW(TAG, "AXS5106L returned an empty id (0x00); touch may not work - verify address/wiring");
  }

  if (this->interrupt_pin_ != nullptr) {
    this->interrupt_pin_->setup();
    this->attach_interrupt_(this->interrupt_pin_, gpio::INTERRUPT_FALLING_EDGE);
  }

  // Default raw coordinate range to the panel's native resolution.
  // The user can override with a `calibration:` block in YAML.
  if (this->x_raw_max_ == this->x_raw_min_) {
    this->x_raw_max_ = this->display_->get_native_width();
  }
  if (this->y_raw_max_ == this->y_raw_min_) {
    this->y_raw_max_ = this->display_->get_native_height();
  }
}

void AXS5106LTouchscreen::update_touches() {
  // 14-byte frame: [0]=gesture, [1]=touch count, then 6 bytes per point.
  // Per point (base = 2 + i*6): [0]=event|x_hi(4b), [1]=x_lo, [2]=id|y_hi(4b), [3]=y_lo, [4..5]=weight/area.
  uint8_t data[14];
  if (this->read_reg_(AXS5106L_REG_TOUCH_DATA, data, sizeof(data)) != i2c::ERROR_OK) {
    return;
  }

  uint8_t num = data[1];
  if (num == 0) {
    return;  // no active touches
  }
  if (num > 2) {
    num = 2;  // frame only carries two points; ignore garbage counts
  }

  for (uint8_t i = 0; i < num; i++) {
    uint8_t base = 2 + i * 6;
    uint16_t x = (uint16_t) (((data[base] & 0x0F) << 8) | data[base + 1]);
    uint16_t y = (uint16_t) (((data[base + 2] & 0x0F) << 8) | data[base + 3]);
    this->add_raw_touch_position_(i, x, y);
  }
}

void AXS5106LTouchscreen::dump_config() {
  ESP_LOGCONFIG(TAG, "AXS5106L Touchscreen:");
  LOG_I2C_DEVICE(this);
  LOG_PIN("  Interrupt Pin: ", this->interrupt_pin_);
  LOG_PIN("  Reset Pin: ", this->reset_pin_);
  ESP_LOGCONFIG(TAG, "  x_raw_max: %d, y_raw_max: %d", this->x_raw_max_, this->y_raw_max_);
}

}  // namespace esphome::axs5106l
