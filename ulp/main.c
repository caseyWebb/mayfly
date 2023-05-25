
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

#define ANALOG_SENSORS_ENABLE_PIN GPIO_NUM_0
#define PH_ADC_CHANNEL ADC_CHANNEL_5
#define DO_ADC_CHANNEL ADC_CHANNEL_4
#define ONE_WIRE_BUS GPIO_NUM_8

/**
 * Shared memory values are always 8-bit integers, so to pass larger numbers
 * (ADC has 13-bit resolution) we need to split the number into 2 bytes.
 *
 * See convert_uint16_to_uint8 below and __get_uint16 in ulp.py
 */
EXPORT volatile uint8_t pH_0x00;
EXPORT volatile uint8_t pH_0x01;
EXPORT volatile uint8_t DO_0x00;
EXPORT volatile uint8_t DO_0x01;

EXPORT volatile uint8_t step;
EXPORT volatile bool modified;

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

void init_analog_sensors()
{
    ulp_riscv_gpio_init(ANALOG_SENSORS_ENABLE_PIN);
    ulp_riscv_gpio_output_enable(ANALOG_SENSORS_ENABLE_PIN);
}
void enable_analog_sensors()
{
    ulp_riscv_gpio_output_level(ANALOG_SENSORS_ENABLE_PIN, 1);
}
void disable_analog_sensors()
{
    ulp_riscv_gpio_output_level(ANALOG_SENSORS_ENABLE_PIN, 0);
}
uint16_t read_analog_sensor(adc_channel_t adc_channel)
{
    // ADC has 13-bit resolution, 2^16 / 2^13 = 2^3 = 8 samples
    uint16_t sum = 0;
    for (uint8_t i = 0; i < 8; i++)
    {
        sum += ulp_riscv_adc_read_channel(ADC_UNIT_1, adc_channel);
    }
    return sum / 8;
}
void update_analog_sensor_reading(adc_channel_t adc_channel, volatile uint8_t *msb, volatile uint8_t *lsb)
{
    uint16_t last_reading = convert_uint8_to_uint16((uint8_t[]){*msb, *lsb});
    uint16_t current_reading = read_analog_sensor(adc_channel);
    if (abs(current_reading - last_reading) > 20)
    {
        uint8_t bytes[2];
        convert_uint16_to_uint8(current_reading, bytes);
        *msb = bytes[0];
        *lsb = bytes[1];
        modified = true;
    }
}

static void ds18b20_write_bit(bool bit)
{
    ulp_riscv_gpio_output_level(ONE_WIRE_BUS, 0);
    if (bit)
    {
        /* Must pull high within 15 us, without delay this takes 5 us */
        ulp_riscv_gpio_output_level(ONE_WIRE_BUS, 1);
    }

    /* Write slot duration at least 60 us */
    ulp_riscv_delay_cycles(60 * ULP_RISCV_CYCLES_PER_US);
    ulp_riscv_gpio_output_level(ONE_WIRE_BUS, 1);
}
static bool ds18b20_read_bit(void)
{
    bool bit;

    /* Pull low minimum 1 us */
    ulp_riscv_gpio_output_level(ONE_WIRE_BUS, 0);
    ulp_riscv_gpio_output_level(ONE_WIRE_BUS, 1);

    /* Must sample within 15 us of the failing edge */
    ulp_riscv_delay_cycles(5 * ULP_RISCV_CYCLES_PER_US);
    bit = ulp_riscv_gpio_get_level(ONE_WIRE_BUS);

    /* Read slot duration at least 60 us */
    ulp_riscv_delay_cycles(55 * ULP_RISCV_CYCLES_PER_US);

    return bit;
}
static void ds18b20_write_byte(uint8_t data)
{
    for (int i = 0; i < 8; i++)
    {
        ds18b20_write_bit((data >> i) & 0x1);
    }
}
static uint8_t ds18b20_read_byte(void)
{
    uint8_t data = 0;
    for (int i = 0; i < 8; i++)
    {
        data |= ds18b20_read_bit() << i;
    }
    return data;
}
bool ds18b20_reset_pulse(void)
{
    bool presence_pulse;
    /* min 480 us reset pulse + 480 us reply time is specified by datasheet */
    ulp_riscv_gpio_output_level(EXAMPLE_1WIRE_GPIO, 0);
    ulp_riscv_delay_cycles(480 * ULP_RISCV_CYCLES_PER_US);

    ulp_riscv_gpio_output_level(EXAMPLE_1WIRE_GPIO, 1);

    /* Wait for ds18b20 to pull low before sampling */
    ulp_riscv_delay_cycles(60 * ULP_RISCV_CYCLES_PER_US);
    presence_pulse = ulp_riscv_gpio_get_level(EXAMPLE_1WIRE_GPIO) == 0;

    ulp_riscv_delay_cycles(420 * ULP_RISCV_CYCLES_PER_US);

    return presence_pulse;
}

void on_cycle_complete()
{
    step = 1;
    if (modified)
    {
        modified = false;
        ulp_riscv_wakeup_main_processor();
    }
}

void init_onewire()
{
    ulp_riscv_gpio_init(ONE_WIRE_BUS);
    ulp_riscv_gpio_input_enable(ONE_WIRE_BUS);
    ulp_riscv_gpio_output_enable(ONE_WIRE_BUS);
    ulp_riscv_gpio_set_output_mode(ONE_WIRE_BUS, RTCIO_MODE_OUTPUT_OD);
    ulp_riscv_gpio_pullup(ONE_WIRE_BUS);
    ulp_riscv_gpio_pulldown_disable(ONE_WIRE_BUS);
}

void update_sensor_readings()
{
    enable_analog_sensors();

    if (!ds18b20_reset_pulse())
    {
        temp_reg_val = INT32_MIN;
        br
    }

    sleep(750);

    update_analog_sensor_reading(PH_ADC_CHANNEL, &pH_0x00, &pH_0x01);
    update_analog_sensor_reading(DO_ADC_CHANNEL, &DO_0x00, &DO_0x01);

    disable_analog_sensors();
}

int main(void)
{
    switch (step++)
    {
    case 0:
        init_analog_sensors();
        init_onewire();

        update_sensor_readings();

        on_cycle_complete();
        break;
    default:
        on_cycle_complete();
    }

    return 0;
}
