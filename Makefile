ifeq ($(origin IDF_PATH),undefined)
$(error You must "source ./lib/esp-idf/export.sh" before building)
endif

SHELL := /usr/bin/env bash

COPROC_RESERVE_MEM ?= 8176
CROSS := riscv32-esp-elf-
CC := $(CROSS)gcc
STRIP := $(CROSS)strip

CFLAGS := -mabi=ilp32 -mcmodel=medlow -march=rv32imc -Os -ggdb3 -nostdlib -ffunction-sections
CFLAGS += -isystem $(IDF_PATH)/components/esp_common/include
CFLAGS += -isystem $(IDF_PATH)/components/esp_hw_support/include
CFLAGS += -isystem $(IDF_PATH)/components/esp_rom/include
CFLAGS += -isystem $(IDF_PATH)/components/hal/include
CFLAGS += -isystem $(IDF_PATH)/components/hal/esp32s2/include
CFLAGS += -isystem $(IDF_PATH)/components/hal/platform_port/include
CFLAGS += -isystem $(IDF_PATH)/components/log/include
CFLAGS += -isystem $(IDF_PATH)/components/soc/include
CFLAGS += -isystem $(IDF_PATH)/components/soc/esp32s2/include
CFLAGS += -isystem $(IDF_PATH)/components/ulp/ulp_common/include
CFLAGS += -isystem $(IDF_PATH)/components/ulp/ulp_common/include/esp32s2
CFLAGS += -isystem $(IDF_PATH)/components/ulp/ulp_riscv/include
CFLAGS += -isystem $(IDF_PATH)/components/ulp/ulp_riscv/include/esp32s2
CFLAGS += -isystem $(IDF_PATH)/components/ulp/ulp_riscv/ulp_core/include
CFLAGS += -isystem ulp/include
CFLAGS += -DCOPROC_RESERVE_MEM=$(COPROC_RESERVE_MEM)
CFLAGS += -DCONFIG_IDF_TARGET_ESP32S2

ifeq ($(DEBUG),1)
CFLAGS += -DDEBUG
endif

LDFLAGS := -Wl,-A,elf32-esp32s2ulp -nostdlib --specs=nano.specs --specs=nosys.specs -Wl,--gc-sections
LDFLAGS += -Wl,-T,build/ulp.ld

SRCS ?= ulp/main.c
SRCS += $(IDF_PATH)/components/ulp/ulp_common/ulp_common.c
SRCS += $(IDF_PATH)/components/ulp/ulp_riscv/ulp_core/ulp_riscv_adc.c
SRCS += $(IDF_PATH)/components/ulp/ulp_riscv/ulp_core/ulp_riscv_utils.c
SRCS += $(IDF_PATH)/components/ulp/ulp_riscv/ulp_core/start.S

.PHONY: flash-all
flash-all: circuitpy/lib /Volumes/CIRCUITPY
	rsync -avhP --exclude secrets.py.example --delete circuitpy/ /Volumes/CIRCUITPY

.PHONY: flash
flash: circuitpy/ulp.py /Volumes/CIRCUITPY
	rsync -avhP --exclude secrets.py.example --exclude lib --exclude font --delete circuitpy/ /Volumes/CIRCUITPY

.PHONY: flash-git-diff
flash-git-diff: circuitpy/ulp.py /Volumes/CIRCUITPY
	rsync -avhP --exclude secrets.py.example --exclude lib --exclude font --delete --files-from=<(git diff --name-only) circuitpy/ /Volumes/CIRCUITPY

build:
	mkdir -p build

build/ulp: build/ulp-debug build
	$(STRIP) -g -o $@ $<

build/ulp-debug: $(SRCS) build/ulp.ld build
	$(CC) $(CFLAGS) $(SRCS) -o $@ $(LDFLAGS)

build/ulp.ld: ulp/link.ld build
	$(CC) -E -P -xc $(CFLAGS) -o $@ $<

.PHONY: clean
clean:
	rm -f build/* circuitpy/ulp.py 

circuitpy/ulp.py: build/ulp templates/ulp.py.j2
	python ./support/ulp_builder.py

/Volumes/CIRCUITPY:
	test -d /Volumes/CIRCUITPY
