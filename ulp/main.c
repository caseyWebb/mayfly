
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

/**
 * GPIO
 */
#define ANALOG_SENSORS_ENABLE_PIN GPIO_NUM_0
#define PH_ADC_CHANNEL ADC_CHANNEL_5
#define DO_ADC_CHANNEL ADC_CHANNEL_4
#define ONEWIRE_BUS GPIO_NUM_8
#define AIR_TEMP_ONEWIRE_ADDRESS ((uint64_t)0xA10000017A7DFF28)
#define WATER_TEMP_ONEWIRE_ADDRESS ((uint64_t)0xA10000017A7DFF28)

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
EXPORT volatile uint8_t air_temp_0x00;
EXPORT volatile uint8_t air_temp_0x01;
EXPORT volatile uint8_t water_temp_0x00;
EXPORT volatile uint8_t water_temp_0x01;

EXPORT volatile bool initialized;
EXPORT volatile bool modified;

void sleep_us(uint32_t us)
{
    ulp_riscv_delay_cycles(us * ULP_RISCV_CYCLES_PER_US);
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

/**
 * Shared memory helpers
 */
void maybe_update_sensor_reading(uint16_t new_reading, uint8_t threshold, volatile uint8_t *msb, volatile uint8_t *lsb)
{
    uint16_t last_reading = convert_uint8_to_uint16((uint8_t[]){*msb, *lsb});
    if (abs(new_reading - last_reading) > threshold)
    {
        uint8_t bytes[2];
        convert_uint16_to_uint8(new_reading, bytes);
        *msb = bytes[0];
        *lsb = bytes[1];
        modified = true;
    }
}

/**
 * Analog sensors
 */
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
    maybe_update_sensor_reading(read_analog_sensor(adc_channel), 20, msb, lsb);
}

/**
 * OneWire
 */
#define SKIP_ROM 0xCC
#define MATCH_ROM 0x55
#define CONVERT_T 0x44
#define READ_SCRATCHPAD 0xBE

static void onewire_write_bit(bool bit)
{
    ulp_riscv_gpio_output_level(ONEWIRE_BUS, 0);
    if (bit)
    {
        /* Must pull high within 15 us, without delay this takes 5 us */
        ulp_riscv_gpio_output_level(ONEWIRE_BUS, 1);
    }

    /* Write slot duration at least 60 us */
    sleep_us(60);
    ulp_riscv_gpio_output_level(ONEWIRE_BUS, 1);
}
static bool onewire_read_bit(void)
{
    bool bit;

    /* Pull low minimum 1 us */
    ulp_riscv_gpio_output_level(ONEWIRE_BUS, 0);
    ulp_riscv_gpio_output_level(ONEWIRE_BUS, 1);

    /* Must sample within 15 us of the failing edge */
    sleep_us(5);
    bit = ulp_riscv_gpio_get_level(ONEWIRE_BUS);

    /* Read slot duration at least 60 us */
    sleep_us(55);

    return bit;
}
static void onewire_write_byte(uint8_t data)
{
    for (int i = 0; i < 8; i++)
    {
        onewire_write_bit((data >> i) & 0x1);
    }
}
static uint8_t onewire_read_byte(void)
{
    uint8_t data = 0;
    for (int i = 0; i < 8; i++)
    {
        data |= onewire_read_bit() << i;
    }
    return data;
}
bool onewire_reset(void)
{
    bool presence_pulse;
    /* min 480 us reset pulse + 480 us reply time is specified by datasheet */
    ulp_riscv_gpio_output_level(ONEWIRE_BUS, 0);

    sleep_us(480);

    ulp_riscv_gpio_output_level(ONEWIRE_BUS, 1);

    /* Wait for ds18b20 to pull low before sampling */
    sleep_us(60);
    presence_pulse = ulp_riscv_gpio_get_level(ONEWIRE_BUS) == 0;

    sleep_us(420);

    return presence_pulse;
}
void onewire_match_rom(uint64_t onewire_address)
{
    if (!onewire_reset())
    {
        return;
    }
    onewire_write_byte(MATCH_ROM);
    for (int i = 0; i < 8; i++)
    {
        onewire_write_byte(onewire_address >> (i * 8));
    }
}
void onewire_convert_t()
{
    if (!onewire_reset())
    {
        return;
    }
    onewire_write_byte(SKIP_ROM);
    onewire_write_byte(CONVERT_T);
}
void init_onewire()
{
    ulp_riscv_gpio_init(ONEWIRE_BUS);
    ulp_riscv_gpio_input_enable(ONEWIRE_BUS);
    ulp_riscv_gpio_output_enable(ONEWIRE_BUS);
    ulp_riscv_gpio_set_output_mode(ONEWIRE_BUS, RTCIO_MODE_OUTPUT_OD);
    ulp_riscv_gpio_pullup(ONEWIRE_BUS);
    ulp_riscv_gpio_pulldown_disable(ONEWIRE_BUS);
}

void update_onewire_sensor_reading(uint16_t onewire_address, volatile uint8_t *msb, volatile uint8_t *lsb)
{
    onewire_match_rom(onewire_address);
    onewire_write_byte(READ_SCRATCHPAD);
    uint8_t temp_low_byte = onewire_read_byte();
    uint8_t temp_high_byte = onewire_read_byte();
    uint16_t temp = (temp_high_byte << 8) | temp_low_byte;
    maybe_update_sensor_reading(temp, 20, msb, lsb);
}

/**
 * Business logic
 */

int main(void)
{
    if (!initialized)
    {
        init_analog_sensors();
        init_onewire();
    }

    onewire_convert_t();
    enable_analog_sensors();

    // Wait for ds18b20s t conversion to complete and analog sensors to stabilize
    sleep_ms(750);

    update_analog_sensor_reading(PH_ADC_CHANNEL, &pH_0x00, &pH_0x01);
    update_analog_sensor_reading(DO_ADC_CHANNEL, &DO_0x00, &DO_0x01);
    disable_analog_sensors();

    update_onewire_sensor_reading(AIR_TEMP_ONEWIRE_ADDRESS, &air_temp_0x00, &air_temp_0x01);
    update_onewire_sensor_reading(WATER_TEMP_ONEWIRE_ADDRESS, &water_temp_0x00, &water_temp_0x01);

    if (!initialized || modified)
    {
        initialized = true;
        modified = false;
        ulp_riscv_wakeup_main_processor();
    }

    return 0;
}
