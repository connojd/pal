from pal.writer.abstract_writer import AbstractWriter

from pal.writer.language.cxx11 import Cxx11LanguageWriter
from pal.writer.language.yaml import YamlLanguageWriter
from pal.writer.language.none import NoneLanguageWriter

from pal.writer.access_mechanism.gas_x86_64_intel_syntax import \
    GasX86_64IntelSyntaxAccessMechanismWriter
from pal.writer.access_mechanism.gas_x86_64_att_syntax import \
    GasX86_64AttSyntaxAccessMechanismWriter
from pal.writer.access_mechanism.gas_aarch64 import \
    GasAarch64AccessMechanismWriter
from pal.writer.access_mechanism.gas_aarch32 import \
    GasAarch32AccessMechanismWriter
from pal.writer.access_mechanism.cxx_test import \
    CxxTestAccessMechanismWriter
from pal.writer.access_mechanism.yaml import \
    YamlAccessMechanismWriter
from pal.writer.access_mechanism.none import \
    NoneAccessMechanismWriter

from pal.writer.printer.printf_utf8 import PrintfUtf8PrinterWriter
from pal.writer.printer.none import NonePrinterWriter

from pal.writer.file_format.unix import UnixFileFormatWriter
from pal.writer.file_format.windows import WindowsFileFormatWriter
from pal.writer.file_format.yaml import YamlFileFormatWriter
from pal.writer.file_format.none import NoneFileFormatWriter

language_options = {
    "c++11": Cxx11LanguageWriter,
    "yaml": YamlLanguageWriter,
    "none": NoneLanguageWriter,
}

access_mechanism_options = [
    "gas_intel",
    "gas_att",
    "gas_aarch64",
    "gas_aarch32",
    "test",
    "yaml",
    "none",
]

printer_options = {
    "printf_utf8": PrintfUtf8PrinterWriter,
    "none": NonePrinterWriter,
}

file_format_options = {
    "unix": UnixFileFormatWriter,
    "windows": WindowsFileFormatWriter,
    "yaml": YamlFileFormatWriter,
    "none": NoneFileFormatWriter,
}


def get_access_mechanism_writer(arch, language, access_mechanism):
    if arch == "intel_x64" and access_mechanism == "gas_intel":
        return GasX86_64IntelSyntaxAccessMechanismWriter
    elif arch == "intel_x64" and access_mechanism == "gas_att":
        return GasX86_64AttSyntaxAccessMechanismWriter
    elif arch == "armv8-a" and access_mechanism == "gas_aarch64":
        return GasAarch64AccessMechanismWriter
    elif arch == "armv8-a" and access_mechanism == "gas_aarch32":
        return GasAarch32AccessMechanismWriter
    elif access_mechanism == "test" and language == "c++11":
        return CxxTestAccessMechanismWriter
    elif access_mechanism == "yaml":
        return YamlAccessMechanismWriter
    else:
        return NoneAccessMechanismWriter


def make_writer(arch, language, access_mechanism, printer, file_format):

    if language not in language_options:
        raise Exception("invalid language option: " + str(language))

    if access_mechanism not in access_mechanism_options:
        raise Exception("invalid access mechanism option: " + str(access_mechanism))

    if printer not in printer_options:
        raise Exception("invalid printer option: " + str(printer))

    if file_format not in file_format_options:
        raise Exception("invalid file_format option: " + str(file_format))

    am_writer = get_access_mechanism_writer(arch, language, access_mechanism)

    class Writer(
            AbstractWriter,
            language_options[language],
            am_writer,
            printer_options[printer],
            file_format_options[file_format]
          ):
        pass

    return Writer()
