
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include "ulp_riscv.h"
#include "ulp_riscv_utils.h"
#include "ulp_riscv_gpio.h"

#define EXPORT __attribute__((used, visibility("default")))

#undef ULP_RISCV_CYCLES_PER_MS
#define ULP_RISCV_CYCLES_PER_MS (int)(1000 * ULP_RISCV_CYCLES_PER_US)

#define LED_GPIO_PIN (GPIO_NUM_11)

int main(void)
{
    bool gpio_level = true;

    ulp_riscv_gpio_init(LED_GPIO_PIN);
    ulp_riscv_gpio_output_enable(LED_GPIO_PIN);

    uint8_t i = 0;

    while (i < 10)
    {
        ulp_riscv_gpio_output_level(LED_GPIO_PIN, gpio_level);
        ulp_riscv_delay_cycles(1 * 1000 * ULP_RISCV_CYCLES_PER_MS);
        gpio_level = !gpio_level;
        i++;
    }

    ulp_riscv_wakeup_main_processor();

    // ulp_riscv_shutdown() is called automatically when main exits
    return 0;
}