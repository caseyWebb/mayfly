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

        memory_map = memorymap.AddressRange(start=0x50000000, length=0x2000)

        self.alarm = espulp.ULPAlarm(self.__program)
        self.shared_mem = memory_map[self.__get_symbol('shared_mem')]

    def start(self):
        self.__program.halt()
        self.__program.run(self.__code, pins=[board.IO11])

    def __get_symbol(self, name):
        sy = self.__symtab.get_first_symbol_by_name(name)
        if sy is None:
            raise ValueError(f'No symbol named "{name}"')
        return sy.entry.st_value