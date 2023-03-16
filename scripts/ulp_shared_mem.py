#!/usr/bin/env python3

import struct
from collections import namedtuple

class StructMixin:
    @classmethod
    def calcsize(cls):
        return struct.calcsize(cls._fmt)

    @classmethod
    def frombuffer(cls, buf):
        return cls(*struct.unpack(cls._fmt, buf))

_ElfHeader32 = namedtuple('_ElfHeader32', """
    e_ident e_type e_machine e_version e_entry e_phoff e_shoff e_flags e_ehsize e_phentsize e_phnum e_shentsize e_shnum e_shstrndx""".split())
class ElfHeader32(_ElfHeader32, StructMixin):
    _fmt='<16s2h5l6h'

_SectionHeader32 = namedtuple('_SectionHeader32', """
        sh_name sh_type sh_flags sh_addr sh_offset sh_size sh_link sh_info
        sh_addralign sh_entsize
        """.split())
class SectionHeader32(_SectionHeader32, StructMixin):
    _fmt = '<10l'

class Section:
    def __init__(self, ef, sh):
        self._elffile = ef
        self._header = sh

    def readat(self, offset, sz):
        return self._elffile.pread(offset + self._header.sh_offset, sz)
    def constructat(self, offset, cls):
        return self._elffile.construct_at(offset + self._header.sh_offset, cls)

class StringTable(Section):
    def symbolat(self, offset):
        result = b''
        stream = self._elffile.stream
        stream.seek(self._header.sh_offset + offset)
        while (c := stream.read(1)) != b'\0' and c != b'':
            result += c
        return result

    def symbolat_matches(self, offset, name):
        stream = self._elffile.stream
        stream.seek(self._header.sh_offset + offset)
        name1 = stream.read(len(name))
        if name1 != name: return False
        nul = stream.read(1)
        if nul != b'\0': return False
        return True
        
_SymbolTableEntry = namedtuple('_SymbolTableEntry',
        ['st_name', 'st_value', 'st_size', 'set_info', 'st_other', 'st_shndx'])

class SymbolTableEntry(_SymbolTableEntry, StructMixin):
    _fmt = '<3l2bh'

class Symbol:
    def __init__(self, name, entry):
        self.name = name
        self.entry = entry

class SymbolTable(Section):
    def __init__(self, ef, sh):
        super().__init__(ef, sh)
        self.strtab = None

    def iter_symbols(self):
        for i in range(0, self._header.sh_size, SymbolTableEntry.calcsize()):
            yield self.constructat(i, SymbolTableEntry)

    def get_first_symbol_by_name(self, name):
        if not isinstance(name, bytes): name = name.encode()
        if self.strtab is None:
            self.strtab = self._elffile.get_section_by_name('.strtab')
        strtab = self.strtab
        for sy in self.iter_symbols():
            if strtab.symbolat_matches(sy.st_name, name):
                return Symbol(name, sy)


section_constructors = {
        2: SymbolTable,
        3: StringTable,
}

_HeaderTableEntry = namedtuple('_HeaderTableEntry',
        ['p_type', 'p_offset', 'p_vaddr', 'p_paddr', 'p_filesz', 'p_memsz', 'p_flags', 'p_align'])

PT_LOAD = 1

class HeaderTableEntry(_HeaderTableEntry, StructMixin):
    _fmt = '<8l'

class ELFFile:
    def __init__(self, stream):
        self.stream = stream
        self._buffer = ()
        if self.pread(0, 4) != b'\177ELF':
            raise ValueError("Not an ELF file")
        if self.pread(4, 3) != b'\1\1\1':
            raise ValueError("Incompatible ELF file")
        self._header = self.construct_at(0, ElfHeader32)

    def pread(self, offset, sz):
        if len(self._buffer) < sz:
            self._buffer = bytearray(sz)
            self._view = memoryview(self._buffer)
        mv = self._view[:sz]
        self.stream.seek(offset)
        self.stream.readinto(mv)
        return mv

    def construct_at(self, offset, cls):
        sz = cls.calcsize()
        mb = self.pread(offset, sz)
        return cls.frombuffer(mb)

    def get_section(self, index):
        if not (0 <= index < self._header.e_shnum):
            raise IndexError("Invalid section number")
        offset = self._header.e_shoff + index * self._header.e_shentsize
        sh = self.construct_at(offset, SectionHeader32)
        constructor = section_constructors.get(sh.sh_type, Section)
        return constructor(self, sh)

    def iter_sections(self):
        for i in range(self._header.e_shnum):
            yield self.get_section(i)

    def get_section_by_name(self, name):
        if not isinstance(name, bytes): name = name.encode()
        idx = self.get_section(self._header.e_shstrndx)
        for sec in self.iter_sections():
            off = sec._header.sh_name
            if idx.symbolat_matches(sec._header.sh_name, name):
                return sec

    def get_header(self, index):
        if not (0 <= index < self._header.e_phnum):
            raise IndexError("Invalid header number")
        offset = self._header.e_phoff + index * self._header.e_phentsize
        return self.construct_at(offset, HeaderTableEntry)

    def iter_headers(self):
        for i in range(self._header.e_phnum):
            yield self.get_header(i)

    def get_header_by_type(self, p_type):
        for h in self.iter_headers():
            if h.p_type == p_type:
                return h


a_out = open("src/circuitpy/ulp.bin", "rb")
e = ELFFile(a_out)
s = e.get_section(1)
s = e.get_section_by_name('.symtab')
print(s)
sy = s.get_first_symbol_by_name('shared_mem')
en = sy.entry
print(f"shared_mem @ 0x{en.st_value:04x} 0x{en.st_size:04x} bytes")