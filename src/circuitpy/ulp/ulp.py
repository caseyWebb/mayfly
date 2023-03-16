import minielf
import espulp
import board

class ULP:
    def __init__(self):
        self.elf = minielf.ELFFile(open("/ulp/bin", "rb"))
        code_header = self.elf.get_header_by_type(minielf.PT_LOAD)
        self.code = bytes(self.elf.pread(code_header.p_offset, code_header.p_filesz))
        self.symtab = self.elf.get_section_by_name('.symtab')
        
    def run(self):
        ulp = espulp.ULP(espulp.Architecture.RISCV)
        ulp.halt()
        ulp.run(self.code, pins=[board.IO11])