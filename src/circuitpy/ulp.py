import board
import espulp
import minielf

class ULP:
    def __init__(self):
        elf = minielf.ELFFile(open("/ulp.bin", "rb"))
        code_header = elf.get_header_by_type(minielf.PT_LOAD)
        self.__code = bytes(elf.pread(code_header.p_offset, code_header.p_filesz))

    def start(self):
        program = espulp.ULP(espulp.Architecture.RISCV)
        program.halt()
        program.run(self.__code, pins=[board.IO11])
        return espulp.ULPAlarm(program)
