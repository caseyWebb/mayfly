
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include "ulp_riscv.h"
#include "ulp_riscv_utils.h"
#include "ulp_riscv_gpio.h"

#define EXPORT __attribute__((used, visibility("default")))

#define RTC_CNTL_ULP_CP_TIMER_1_REG (DR_REG_RTCCNTL_BASE + 0x0130)
#define RTC_CNTL_ULP_CP_TIMER_SLP_CYCLE 0x00FFFFFF
#define RTC_CNTL_ULP_CP_TIMER_SLP_CYCLE_M ((RTC_CNTL_ULP_CP_TIMER_SLP_CYCLE_V) << (RTC_CNTL_ULP_CP_TIMER_SLP_CYCLE_S))
#define RTC_CNTL_ULP_CP_TIMER_SLP_CYCLE_V 0xFFFFFF
#define RTC_CNTL_ULP_CP_TIMER_SLP_CYCLE_S 8

#undef ULP_RISCV_CYCLES_PER_MS
#define ULP_RISCV_CYCLES_PER_MS (int)(1000 * ULP_RISCV_CYCLES_PER_US)

#define LED_GPIO_PIN (GPIO_NUM_11)

EXPORT volatile uint8_t shared_mem[1024];

int main(void)
{
    // Using ulp_set_wakeup_period causes all sorts of comiplications with the compiler
    // configuration. So we just set the timer register directly. This ends up being
    // about 3 minutes.
    REG_SET_FIELD(RTC_CNTL_ULP_CP_TIMER_1_REG, RTC_CNTL_ULP_CP_TIMER_SLP_CYCLE, INT64_MAX);

    bool gpio_level = shared_mem[0] % 2 == 0;

    ulp_riscv_gpio_init(LED_GPIO_PIN);
    ulp_riscv_gpio_output_enable(LED_GPIO_PIN);
    ulp_riscv_gpio_output_level(LED_GPIO_PIN, gpio_level);

    shared_mem[0]++;

    ulp_riscv_wakeup_main_processor();

    // ulp_riscv_wakeup_main_processor();

    // ulp_riscv_shutdown() is called automatically when main exits
    return 0;
}