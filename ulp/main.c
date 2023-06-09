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
 * Wake-up thresholds
 */

// DS18B20 returns temperature in 1/16ths of a degree C, wake every 0.5C
#define DS18B20_THRESHOLD 8

// Wake every 0.15 pH
//
// pH = (-5.6548 * mV / 1000) + 15.509
// mV = (pH - 15.509) * (1000 / -5.6548)
// ΔmV = (0.15) * (1000 / -5.6548)
// ΔmV = 26.5
// mV approx = raw ADC value / 3.19
// ΔADC = 26.5 * 3.19 = 84.535
#define PH_THRESHOLD 85

// This one is harder to do precisely since it depends on temperature
// but this is a good happy medium without causing unnecessary wake-ups
#define DO_THRESHOLD 60

/**
 * GPIO
 */
#define ANALOG_SENSORS_ENABLE_PIN GPIO_NUM_17
#define PH_ADC_CHANNEL ADC_CHANNEL_5
#define PH_ADC_PIN GPIO_NUM_6
#define DO_ADC_CHANNEL ADC_CHANNEL_4
#define DO_ADC_PIN GPIO_NUM_5
#define ONEWIRE_BUS GPIO_NUM_8
static uint8_t AIR_TEMP_ONEWIRE_ADDRESS[] = {0x28, 0x18, 0x1e, 0x78, 0x25, 0x20, 0x01, 0xb0};
static uint8_t WATER_TEMP_ONEWIRE_ADDRESS[] = {0x28, 0x6e, 0x0d, 0x80, 0x25, 0x20, 0x01, 0xc5};

typedef enum
{
    RUN_MODE_NORMAL,
    RUN_MODE_PAUSED,
    RUN_MODE_CALIBRATION
} run_mode_t;

/**
 * Shared memory values are always 8-bit integers, so to pass larger numbers
 * (ADC has 13-bit resolution) we need to split the number into 2 bytes.
 *
 * See convert_uint16_to_uint8 below and __get_uint16 in ulp.py
 */
#ifdef DEBUG
EXPORT volatile bool debug = true;
#else
EXPORT volatile bool debug = false;
#endif
EXPORT volatile bool calibration_ready;
EXPORT volatile run_mode_t run_mode;
EXPORT volatile uint8_t modified;
EXPORT volatile uint8_t pH_0x00;
EXPORT volatile uint8_t pH_0x01;
EXPORT volatile uint8_t DO_0x00;
EXPORT volatile uint8_t DO_0x01;
EXPORT volatile uint8_t air_temp_0x00;
EXPORT volatile uint8_t air_temp_0x01;
EXPORT volatile uint8_t water_temp_0x00;
EXPORT volatile uint8_t water_temp_0x01;

/**
 * These are used as flags to indicate which sensor reading has been updated
 */
#define PH_SENSOR_ID 0
#define DO_SENSOR_ID 1
#define AIR_TEMP_SENSOR_ID 2
#define WATER_TEMP_SENSOR_ID 3

void convert_uint16_to_uint8(uint32_t input, volatile uint8_t bytes[2])
{
    bytes[0] = input & 0xFF;
    bytes[1] = (input >> 8) & 0xFF;
}

void sleep_us(uint32_t us)
{
    ulp_riscv_delay_cycles(us * ULP_RISCV_CYCLES_PER_US);
}
void sleep_ms(uint32_t ms)
{
    sleep_us(ms * 1000);
}

/**
 * Shared memory helpers
 */
void maybe_update_sensor_reading(int8_t sensor_id,
                                 uint16_t new_reading,
                                 uint8_t threshold,
                                 volatile uint8_t *low_byte,
                                 volatile uint8_t *high_byte)
{
    uint8_t bytes[2];
    convert_uint16_to_uint8(new_reading, bytes);
    // Thresholds are below 255, so only need to check low byte
    if (run_mode == RUN_MODE_CALIBRATION || abs(*low_byte - bytes[0]) > threshold)
    {
        *low_byte = bytes[0];
        *high_byte = bytes[1];
        modified |= 1 << sensor_id;
    }
}

/**
 * Analog sensors
 */
void init_analog_sensors()
{
    ulp_riscv_gpio_init(ANALOG_SENSORS_ENABLE_PIN);
    ulp_riscv_gpio_output_enable(ANALOG_SENSORS_ENABLE_PIN);
    ulp_riscv_gpio_set_output_mode(ANALOG_SENSORS_ENABLE_PIN, RTCIO_MODE_OUTPUT_OD);
    ulp_riscv_gpio_pulldown_disable(ANALOG_SENSORS_ENABLE_PIN);
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
void update_analog_sensor_reading(uint8_t sensor_id, adc_channel_t adc_channel, uint8_t threshold, volatile uint8_t *msb, volatile uint8_t *lsb)
{
    maybe_update_sensor_reading(sensor_id, read_analog_sensor(adc_channel), threshold, msb, lsb);
}

/**
 * OneWire
 *
 * This is based on the example in the ESP-IDF docs, modified to support
 * multiple devices on the same bus.
 *
 * https://github.com/espressif/esp-idf/blob/master/examples/system/ulp_riscv/ds18b20_onewire/main/ulp/main.c
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
        ulp_riscv_gpio_output_level(ONEWIRE_BUS, 1);
    }

    sleep_us(60);
    ulp_riscv_gpio_output_level(ONEWIRE_BUS, 1);
}
static bool onewire_read_bit(void)
{
    bool bit;
    ulp_riscv_gpio_output_level(ONEWIRE_BUS, 0);
    ulp_riscv_gpio_output_level(ONEWIRE_BUS, 1);
    sleep_us(5);
    bit = ulp_riscv_gpio_get_level(ONEWIRE_BUS);
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
    ulp_riscv_gpio_output_level(ONEWIRE_BUS, 0);
    sleep_us(480);
    ulp_riscv_gpio_output_level(ONEWIRE_BUS, 1);
    sleep_us(60);
    presence_pulse = ulp_riscv_gpio_get_level(ONEWIRE_BUS) == 0;
    sleep_us(420);
    return presence_pulse;
}
bool onewire_match_rom(uint8_t *onewire_address)
{
    if (!onewire_reset())
    {
        return false;
    }
    onewire_write_byte(MATCH_ROM);
    for (int i = 0; i < 8; i++)
    {
        onewire_write_byte(onewire_address[i]);
    }
    return true;
}
bool onewire_convert_t()
{
    if (!onewire_reset())
    {
        return false;
    }
    onewire_write_byte(SKIP_ROM);
    onewire_write_byte(CONVERT_T);
    return true;
}
uint8_t crc8(const uint8_t *data, uint8_t len)
{
    uint8_t crc = 0;
    for (uint8_t i = 0; i < len; i++)
    {
        uint8_t inbyte = data[i];
        for (uint8_t j = 0; j < 8; j++)
        {
            uint8_t mix = (crc ^ inbyte) & 0x01;
            crc >>= 1;
            if (mix)
            {
                crc ^= 0x8C;
            }
            inbyte >>= 1;
        }
    }
    return crc;
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

void update_onewire_sensor_reading(uint8_t sensor_id, uint8_t *onewire_address, volatile uint8_t *low_byte, volatile uint8_t *high_byte)
{
    if (!onewire_match_rom(onewire_address))
    {
        return;
    };
    onewire_write_byte(READ_SCRATCHPAD);
    uint8_t scratchpad[9];
    for (int i = 0; i < 9; i++)
    {
        scratchpad[i] = onewire_read_byte();
    }
    uint8_t crc = crc8(scratchpad, 8);
    if (crc != scratchpad[8])
    {
        maybe_update_sensor_reading(-1, 0, DS18B20_THRESHOLD, low_byte, high_byte);
        return;
    }
    uint16_t temp = (scratchpad[1] << 8) | scratchpad[0];
    maybe_update_sensor_reading(sensor_id, temp, DS18B20_THRESHOLD, low_byte, high_byte);
}

/**
 * Business logic
 */

void update()
{
    enable_analog_sensors();

    bool onewire_convert_t_success = onewire_convert_t();

    // Wait for ds18b20s t conversion to complete and analog sensors to stabilize
    sleep_ms(750);

    modified = 0;

    update_analog_sensor_reading(PH_SENSOR_ID, PH_ADC_CHANNEL, PH_THRESHOLD, &pH_0x00, &pH_0x01);
    update_analog_sensor_reading(DO_SENSOR_ID, DO_ADC_CHANNEL, DO_THRESHOLD, &DO_0x00, &DO_0x01);
    disable_analog_sensors();

    if (onewire_convert_t_success)
    {
        update_onewire_sensor_reading(AIR_TEMP_SENSOR_ID, AIR_TEMP_ONEWIRE_ADDRESS, &air_temp_0x00, &air_temp_0x01);
        update_onewire_sensor_reading(WATER_TEMP_SENSOR_ID, WATER_TEMP_ONEWIRE_ADDRESS, &water_temp_0x00, &water_temp_0x01);
    }
}

void start_calibration()
{
    enable_analog_sensors();
    sleep_ms(750);
    calibration_ready = true;
    while (run_mode == RUN_MODE_CALIBRATION)
    {
        update_analog_sensor_reading(PH_SENSOR_ID, PH_ADC_CHANNEL, PH_THRESHOLD, &pH_0x00, &pH_0x01);
        update_analog_sensor_reading(DO_SENSOR_ID, DO_ADC_CHANNEL, DO_THRESHOLD, &DO_0x00, &DO_0x01);
    }
    disable_analog_sensors();
    calibration_ready = false;
}

int main(void)
{
    if (!run_mode)
    {
        init_analog_sensors();
        init_onewire();
        run_mode = RUN_MODE_NORMAL;
    }

    switch (run_mode)
    {
    case RUN_MODE_PAUSED:
        break;

    case RUN_MODE_CALIBRATION:
        start_calibration();
        break;

    case RUN_MODE_NORMAL:
        update();

        // run_mode could have been mutated while updating
        if (run_mode == RUN_MODE_CALIBRATION)
        {
            return main();
        }

#ifdef DEBUG
        /**
         * During development run the shortest possible loop to allow for rapid iteration
         * while avoiding conflicts with the main processor
         */
        run_mode = RUN_MODE_PAUSED;
        ulp_riscv_wakeup_main_processor();
#else
        /*
         * Using ulp_set_wakeup_period causes all sorts of madness with the compiler configuration,
         * so set the timer register directly. This is less precise and readable, but ends up being
         * about 3 minutes which is perfect for the EPD refresh rate.
         */
        REG_SET_FIELD(RTC_CNTL_ULP_CP_TIMER_1_REG, RTC_CNTL_ULP_CP_TIMER_SLP_CYCLE, UINT32_MAX);
        if (modified > 0)
        {
            ulp_riscv_wakeup_main_processor();
        }
#endif
    }

    return 0;
}
