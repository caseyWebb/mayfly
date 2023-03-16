
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include "ulp_riscv.h"
#include "ulp_riscv_utils.h"
#include "ulp_riscv_gpio.h"

#define EXPORT __attribute__((used, visibility("default")))

#undef ULP_RISCV_CYCLES_PER_MS
#define ULP_RISCV_CYCLES_PER_MS (int)(1000 * ULP_RISCV_CYCLES_PER_US)

#define UPDATE_INTERVAL_MINUTES (3)
#define FORCE_UPDATE_INTERVAL_MINUTES (60)

// Analog sensors share an input pin and are enabled by a separate pin
#define ADC_INPUT_PIN (/* GPIO_NUM_? */)
#define PH_ENABLE_PIN (/* GPIO_NUM_? */)
#define DISSOLVED_OXYGEN_ENABLE_PIN (/* GPIO_NUM_? */)
#define WATER_LEVEL_ENABLE_PIN (/* GPIO_NUM_? */)

// 1-wire sensors are connected to a single pin
#define ONE_WIRE_PIN (/* GPIO_NUM_? */)

struct sensor_data
{
    uint8_t air_temp;
    uint8_t water_temp;
    uint8_t pH;
    uint8_t dissolved_oxygen;
    uint8_t water_level;
};

struct sensor_data read_sensors()
{
    struct sensor_data data;

    // Read 1-wire sensors
    // TODO

    // Read analog sensors
    // TODO

    return data;
}

void init_analog_sensor(uint8_t enable_pin)
{
    ulp_riscv_gpio_init(enable_pin);
    ulp_riscv_gpio_output_enable(enable_pin);
    ulp_riscv_gpio_output_level(enable_pin, true);
}

void sleep(int seconds)
{
    ulp_riscv_delay_cycles(seconds * 1000 * ULP_RISCV_CYCLES_PER_MS);
}

int main(void)
{
    ulp_riscv_gpio_init(ADC_INPUT_PIN);
    ulp_riscv_gpio_input_enable(ADC_INPUT_PIN);
    init_analog_sensor(PH_ENABLE_PIN);
    init_analog_sensor(DISSOLVED_OXYGEN_ENABLE_PIN);
    init_analog_sensor(WATER_LEVEL_ENABLE_PIN);

    struct sensor_data sensor_readings = read_sensors();

    uint8_t i = 0;
    while (i++ < (FORCE_UPDATE_INTERVAL_MINUTES / UPDATE_INTERVAL_MINUTES))
    {
        struct sensor_data new_sensor_readings = read_sensors();

        if (new_sensor_readings.air_temp != sensor_readings.air_temp ||
            new_sensor_readings.water_temp != sensor_readings.water_temp ||
            new_sensor_readings.pH != sensor_readings.pH ||
            new_sensor_readings.dissolved_oxygen != sensor_readings.dissolved_oxygen ||
            new_sensor_readings.water_level != sensor_readings.water_level)
        {
            break;
        }

        sensor_readings = new_sensor_readings;

        sleep(60 * UPDATE_INTERVAL_MINUTES);
    }

    ulp_riscv_wakeup_main_processor();

    return 0;
}
