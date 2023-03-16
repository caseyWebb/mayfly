ifeq ($(origin IDF_PATH),undefined)
$(error You must "source esp-idf/export.sh" before building)
endif

SHELL := /usr/bin/env bash

COPROC_RESERVE_MEM ?= 8176
CROSS := riscv32-esp-elf-
CC := $(CROSS)gcc
STRIP := $(CROSS)strip

CFLAGS := -mabi=ilp32 -mcmodel=medlow -march=rv32imc -Os -ggdb3 -nostdlib -ffunction-sections
CFLAGS += -isystem $(IDF_PATH)/components/ulp/ulp_common/include
CFLAGS += -isystem $(IDF_PATH)/components/ulp/ulp_common/include/esp32s2
CFLAGS += -isystem $(IDF_PATH)/components/ulp/ulp_riscv/include
CFLAGS += -isystem $(IDF_PATH)/components/ulp/ulp_riscv/include/esp32s2
CFLAGS += -isystem $(IDF_PATH)/components/ulp/ulp_riscv/ulp_core/include
CFLAGS += -isystem $(IDF_PATH)/components/soc/esp32s2/include
CFLAGS += -isystem $(IDF_PATH)/components/esp_common/include
CFLAGS += -isystem $(IDF_PATH)/components/esp_hw_support/include
CFLAGS += -isystem src/ulp/include
CFLAGS += -DCOPROC_RESERVE_MEM=$(COPROC_RESERVE_MEM)
CFLAGS += -DCONFIG_IDF_TARGET_ESP32S2

LDFLAGS := -Wl,-A,elf32-esp32s2ulp -nostdlib --specs=nano.specs --specs=nosys.specs -Wl,--gc-sections
LDFLAGS += -Wl,-T,build/ulp.ld

SRCS ?= src/ulp/main.c
SRCS += $(IDF_PATH)/components/ulp/ulp_riscv/ulp_core/ulp_riscv_utils.c
SRCS += $(IDF_PATH)/components/ulp/ulp_riscv/ulp_core/start.S

.PHONY: flash
flash: src/circuitpy/ulp.bin
	./scripts/flash.sh

build:
	mkdir -p build

build/ulp-stripped: build/ulp build
	$(STRIP) -g -o $@ $<

build/ulp: $(SRCS) build/ulp.ld build
	$(CC) $(CFLAGS) $(SRCS) -o $@ $(LDFLAGS)

build/ulp.ld: src/ulp/link.ld build
	$(CC) -E -P -xc $(CFLAGS) -o $@ $<

.PHONY: clean
clean:
	rm -f build/* src/circuitpy/ulp.bin 

src/circuitpy/ulp.bin: build/ulp-stripped
	cp build/ulp-stripped src/circuitpy/ulp.bin