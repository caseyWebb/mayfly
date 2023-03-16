# Mayfly

> Low-power IOT Environmental Monitoring with CircuitPython and the ESP32-S2 RISC-V ULP

This project collects various sensor readings, shows them on an e-paper display, and records to ThingSpeak. It's intended to be used in aquaculture and hydroponics, but it could be used for any application where you want to monitor, display, and record values with a battery-powered device.

```mermaid
flowchart TD
    INIT_ULP --> ULP_BOOT
    subgraph Shared Memory
    RTC_MEMORY[(RTC Memory)]
    end
    subgraph Main Processor
    MAIN_BOOT(Boot)
    ULP_WAKE{ULP wake?}
    INIT_WIFI[Initialize Wifi]
    INIT_TIME[Initialize Time]
    INIT_ULP[Start ULP]
    MAIN_SLEEP(Sleep)
    READ_RTC[Get Sensor Readings]
    UPDATE_DISPLAY[Update Display]
    MAIN_BOOT --> ULP_WAKE
    ULP_WAKE -->|Yes| INIT_WIFI --> INIT_TIME --> INIT_ULP --> MAIN_SLEEP
    ULP_WAKE -->|No| READ_RTC --> UPDATE_DISPLAY --> MAIN_SLEEP
    RTC_MEMORY --> READ_RTC
    end
    subgraph ULP
    ULP_BOOT(Boot)
    READ_SENSORS[Read Sensors]
    SENSOR_DIFF{Values changed?}
    UPDATE_RTC_MEMORY[Store Sensor Readings]
    SET_ULP_WAKE_TIMER[Set ULP Wake Timer]
    ULP_SHUTDOWN(ULP Shutdown)
    ULP_WAKE_TIMER[/ULP Wake Timer/]
    ULP_BOOT --> READ_SENSORS --> SENSOR_DIFF
    SENSOR_DIFF -->|Yes| UPDATE_RTC_MEMORY --> SET_ULP_WAKE_TIMER
    SENSOR_DIFF -->|No| SET_ULP_WAKE_TIMER
    UPDATE_RTC_MEMORY --> RTC_MEMORY
    ULP_WAKE_TIMER --> ULP_BOOT
    SET_ULP_WAKE_TIMER --> ULP_WAKE_TIMER
    SET_ULP_WAKE_TIMER --> ULP_SHUTDOWN
    RTC_MEMORY --> SENSOR_DIFF
    end
```

## Hardware

- [UnexpectedMaker FeatherS2][feathers2]
- [Adafruit Liquid Level Sensor][liquid-level-sensor]
- [Atlas Scientific Gravity Analog pH Kit][ph-kit]
- [Atlas Scientific Gravity Analog Dissolved Oxygen Kit][do-kit]
- [DS18B20 Temperature Sensor][ds18b20]

[feathers2]: https://feathers2.io/
[liquid-level-sensor]: https://www.adafruit.com/product/1786
[ph-kit]: https://atlas-scientific.com/kits/gravity-analog-ph-kit/
[do-kit]: https://atlas-scientific.com/kits/gravity-analog-do-kit/
[ds18b20]: https://www.digikey.com/en/datasheets/maxim-integrated/maxim-integrated-ds18b20
