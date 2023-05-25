import board
import espulp
import minielf
import memorymap

class ULP:
    def __init__(self):
        elf = minielf.ELFFile(open("/ulp.bin", "rb"))
        code_header = elf.get_header_by_type(minielf.PT_LOAD)
        self.__code = bytes(elf.pread(code_header.p_offset, code_header.p_filesz))
        self.__program = espulp.ULP(espulp.Architecture.RISCV)
        self.__symtab = elf.get_section_by_name('.symtab')
        self.__memory_map = memorymap.AddressRange(start=0x50000000, length=0x2000)

        self.alarm = espulp.ULPAlarm(self.__program)
        self.shared_memory = SharedMemory(self.__memory_map, self.__symtab)

    def start(self):
        self.__program.halt()
        self.shared_memory.set_uint8('step', 0)
        self.__program.run(
            self.__code,
            pins=[board.IO14, board.IO18],
            adc_pin=board.A10
        )


class SharedMemory:
    def __init__(self, memory_map, symtab):
        self.__memory_map = memory_map
        self.__symtab = symtab

    def read_uint16(self, name):
        output = 0
        for i in range(2):
            symbol = self.__get_symbol(f'{name}_0x0{i}')
            byte = self.__memory_map[symbol]
            output |= byte << (i * 8)
        return output
    
    def set_uint8(self, name, value):
        symbol = self.__get_symbol(name)
        self.__memory_map[symbol] = value

    def __get_symbol(self, name):
        sy = self.__symtab.get_first_symbol_by_name(name)
        if sy is None:
            raise ValueError(f'No symbol named "{name}"')
        return sy.entry.st_value