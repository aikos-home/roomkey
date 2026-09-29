#pragma once

#include "esphome/components/i2c/i2c.h"
#include "esphome/components/touchscreen/touchscreen.h"
#include "esphome/core/component.h"
#include "esphome/core/hal.h"
#include "esphome/core/log.h"

namespace esphome::axs5106l {

static const char *const TAG = "axs5106l.touchscreen";

// AXS5106L registers (from the Waveshare Arduino driver / AXS5106L C library)
static const uint8_t AXS5106L_REG_TOUCH_DATA = 0x01;  // read 14 bytes of touch data
static const uint8_t AXS5106L_REG_ID = 0x08;          // device id (first byte non-zero when present)

class AXS5106LTouchscreen final : public touchscreen::Touchscreen, public i2c::I2CDevice {
 public:
  void setup() override;
  void update_touches() override;
  void dump_config() override;

  void set_interrupt_pin(InternalGPIOPin *pin) { this->interrupt_pin_ = pin; }
  void set_reset_pin(GPIOPin *pin) { this->reset_pin_ = pin; }

 protected:
  // The AXS5106L does not accept repeated-start (write-then-read) transactions.
  // Read = write the register pointer as its own transaction (STOP), then read.
  i2c::ErrorCode read_reg_(uint8_t reg, uint8_t *data, uint8_t len);

  InternalGPIOPin *interrupt_pin_{nullptr};
  GPIOPin *reset_pin_{nullptr};
};

}  // namespace esphome::axs5106l
