import base64
from collections import defaultdict
from jinja2 import Environment, FileSystemLoader
import os
import re
import minielf as minielf

project_root = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")


class ULPBuilder:
    def __init__(self, source_path, bin_path):
        elf = minielf.ELFFile(open(bin_path, "rb"))
        code_header = elf.get_header_by_type(minielf.PT_LOAD)
        symtab = elf.get_section_by_name(".symtab")
        self.__code = bytes(elf.pread(code_header.p_offset, code_header.p_filesz))
        self.__symbols = self.__get_symbols(source_path, symtab)

    def generate_python_code(self, out_path):
        env = Environment(
            loader=FileSystemLoader(os.path.join(project_root, "templates"))
        )
        template = env.get_template("ulp.py.j2")
        out = template.render(code=self.__code, symbols=self.__symbols)
        with open(out_path, "w") as f:
            f.write(out)

    def __get_symbols(self, source_path, symtab):
        with open(source_path, "r") as f:
            source_code = f.read()

        pattern = r"EXPORT volatile uint8_t ([a-zA-Z_][a-zA-Z_0-9]+)"
        sensor_symbol_names = re.findall(pattern, source_code)
        sensors = defaultdict(list)

        sensor_symbol_names.sort()

        for symbol_name in sensor_symbol_names:
            symbol = symtab.get_first_symbol_by_name(symbol_name)
            if symbol is None:
                raise Exception(f"Symbol {symbol_name} not found")
            try:
                prefix = symbol_name.rsplit("_", 1)[0]
                sensors[prefix].append(symbol.entry.st_value)
            except ValueError:
                sensors[symbol_name].append(symbol.entry.st_value)

        return {
            "debug": symtab.get_first_symbol_by_name("debug").entry.st_value,
            "run_mode": symtab.get_first_symbol_by_name("run_mode").entry.st_value,
            "sensors": sensors,
        }


builder = ULPBuilder(
    os.path.join(project_root, "ulp/main.c"),
    os.path.join(project_root, "build/ulp"),
)
builder.generate_python_code(os.path.join(project_root, "circuitpy/ulp.py"))
