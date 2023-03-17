#include "sdkconfig.h"

ENTRY(reset_vector)

PROVIDE ( SENS = 0xC800 );
PROVIDE ( __assert_func = 0x4001a408 );

MEMORY
{
    ram(RW) : ORIGIN = 0, LENGTH = COPROC_RESERVE_MEM
}

SECTIONS
{
    . = ORIGIN(ram);
    .text :
    {
        *(.text.vectors) /* Default reset vector must link to offset 0x0 */
        *(.text)
        *(.text*)
    } >ram

    .rodata ALIGN(4):
    {
        *(.rodata)
        *(.rodata*)
    } > ram

    .data ALIGN(4):
    {
        *(.data)
        *(.data*)
        *(.sdata)
        *(.sdata*)
    } > ram

    .bss ALIGN(4) :
    {
        *(.bss)
        *(.bss*)
        *(.sbss)
        *(.sbss*)
    } >ram

    __stack_top = ORIGIN(ram) + LENGTH(ram);
}