
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include "ulp_riscv.h"
#include "soc/sens_struct.h"
#include "ulp_riscv_adc_ulp_core.h"
#include "ulp_riscv_utils.h"
#include "ulp_riscv_gpio.h"

#define EXPORT __attribute__((used, visibility("default")))

/**
 * These are copied out of esp-idf for the ESP32-S2
 */
#define RTC_CNTL_ULP_CP_TIMER_1_REG (DR_REG_RTCCNTL_BASE + 0x0130)
#define RTC_CNTL_ULP_CP_TIMER_SLP_CYCLE 0x00FFFFFF
#define RTC_CNTL_ULP_CP_TIMER_SLP_CYCLE_V 0xFFFFFF
#define RTC_CNTL_ULP_CP_TIMER_SLP_CYCLE_S 8

#undef ULP_RISCV_CYCLES_PER_MS
#define ULP_RISCV_CYCLES_PER_MS (int)(1000 * ULP_RISCV_CYCLES_PER_US)

// #define ONE_WIRE_BUS GPIO_NUM_12
// #define ADC_CHANNEL ADC1_CHANNEL_7
// #define PH_ENABLE_PIN GPIO_NUM_13
// #define DO_ENABLE_PIN GPIO_NUM_14
// #define WATER_LEVEL_ENABLE_PIN GPIO_NUM_15

/**
 * Shared memory values are always 8-bit integers, so to pass larger numbers
 * (ADC has 13-bit resolution) we need to split the number into 2 bytes.
 *
 * See convert_uint16_to_uint8 below and __get_uint16 in ulp.py
 */
EXPORT volatile uint8_t air_temp_0x00;
EXPORT volatile uint8_t air_temp_0x01;
EXPORT volatile uint8_t pH_0x00;
EXPORT volatile uint8_t pH_0x01;
EXPORT volatile uint8_t dissolved_oxygen_0x00;
EXPORT volatile uint8_t dissolved_oxygen_0x01;
EXPORT volatile uint8_t water_level_0x00;
EXPORT volatile uint8_t water_level_0x01;

/**
 * These values can be all over the place. Use multisampling to smooth.
 */
int16_t sample_adc()
{
    uint8_t samples = 255;
    uint32_t sum = 0;
    for (uint8_t i = 0; i < samples; i++)
    {
        // The ADC has 13-bit resolution, max value 8191.
        // 255 * 8191 = 2087045, which comfortably fits in a 32-bit integer.
        sum += ulp_riscv_adc_read_channel(ADC_UNIT_1, ADC_CHANNEL_0);
    }
    return sum / samples;
}

/**
 * Helpers for converting between 8-bit and 16-bit integers.
 */
void convert_uint16_to_uint8(uint32_t input, uint8_t bytes[2])
{
    for (int i = 0; i < 2; i++)
    {
        bytes[i] = (input >> (i * 8)) & 0xff;
    }
}
uint16_t convert_uint8_to_uint16(uint8_t bytes[2])
{
    uint16_t output = 0;
    for (int i = 0; i < 2; i++)
    {
        output |= bytes[i] << (i * 8);
    }
    return output;
}

void update_analog_sensor(uint8_t *msb, uint8_t *lsb, bool *modified)
{
    uint16_t last_reading = convert_uint8_to_uint16((uint8_t[]){*msb, *lsb});
    uint16_t current_reading = sample_adc();
    if (abs(current_reading - last_reading) > 20) {
        uint8_t bytes[2];
        convert_uint16_to_uint8(current_reading, bytes);
        *msb = bytes[0];
        *lsb = bytes[1];
        *modified = true;
    }
}


int main(void)
{
    // ulp_riscv_gpio_init(ONE_WIRE_BUS);
    // ulp_riscv_gpio_init(PH_ENABLE_PIN);
    // ulp_riscv_gpio_init(DO_ENABLE_PIN);
    // ulp_riscv_gpio_init(WATER_LEVEL_ENABLE_PIN);
    
    bool modified = false;

    update_analog_sensor(&air_temp_0x00, &air_temp_0x01, &modified);
    update_analog_sensor(&pH_0x00, &pH_0x01, &modified);
    update_analog_sensor(&dissolved_oxygen_0x00, &dissolved_oxygen_0x01, &modified);
    update_analog_sensor(&water_level_0x00, &water_level_0x01, &modified);

    if (modified) {
        ulp_riscv_wakeup_main_processor();
    }

    /**
     * Using ulp_set_wakeup_period causes all sorts of complications with the compiler
     * configuration so set the timer register directly.
     *
     * UINT64_MAX ends up being about 3 minutes, perfect for the e-ink display max refresh rate.
     */
    // REG_SET_FIELD(RTC_CNTL_ULP_CP_TIMER_1_REG, RTC_CNTL_ULP_CP_TIMER_SLP_CYCLE, UINT64_MAX);

    return 0;
}