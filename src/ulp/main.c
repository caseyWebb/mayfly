
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include "ulp_riscv.h"
#include "ulp_riscv_utils.h"
#include "ulp_riscv_gpio.h"

#define EXPORT __attribute__((used, visibility("default")))

// global variables will be exported as public symbols, visible from main CPU
EXPORT uint8_t shared_mem[1024];
EXPORT uint16_t shared_mem_len = 1024;

#undef ULP_RISCV_CYCLES_PER_MS
#define ULP_RISCV_CYCLES_PER_MS (int)(1000 * ULP_RISCV_CYCLES_PER_US)

#define LED_GPIO_PIN (GPIO_NUM_11)

int main(void)
{
    shared_mem[0] = 10;
    shared_mem_len = 1024;

    bool gpio_level = true;

    ulp_riscv_gpio_init(LED_GPIO_PIN);
    ulp_riscv_gpio_output_enable(LED_GPIO_PIN);

    while (1)
    {
        ulp_riscv_gpio_output_level(LED_GPIO_PIN, gpio_level);
        ulp_riscv_delay_cycles(10 * 10 * ULP_RISCV_CYCLES_PER_MS);
        gpio_level = !gpio_level;
    }

    // ulp_riscv_shutdown() is called automatically when main exits
    return 0;
}