
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

EXPORT volatile uint8_t shared_mem[1024];
EXPORT volatile uint16_t shared_mem_len = 1024;

int main(void)
{
    bool gpio_level = true;

    shared_mem[0] = 0;
    shared_mem_len = 1024;

    ulp_riscv_gpio_init(LED_GPIO_PIN);
    ulp_riscv_gpio_output_enable(LED_GPIO_PIN);

    while (shared_mem[0] < 10)
    {
        ulp_riscv_gpio_output_level(LED_GPIO_PIN, gpio_level);
        ulp_riscv_delay_cycles(10 * 1000 * ULP_RISCV_CYCLES_PER_MS);
        gpio_level = !gpio_level;
        shared_mem[0]++;
        ulp_riscv_wakeup_main_processor();
    }

    // ulp_riscv_wakeup_main_processor();

    // ulp_riscv_shutdown() is called automatically when main exits
    return 0;
}