#
# Shoulder
# Copyright (C) 2018 Assured Information Security, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from shoulder.generator.abstract_generator import AbstractGenerator
from shoulder.register import Register
from shoulder.logger import logger
from shoulder.config import config
from shoulder.exception import *

class CHeaderGenerator(AbstractGenerator):
    def __init__(self):
        self._current_indent_level = 0

    def generate(self, objects, outpath):
        try:
            logger.info("Generating C Header: " + str(outpath))
            with open(outpath, "w") as outfile:
                self._generate_license(outfile)
                self._generate_c_includes(outfile)
                self._generate_include_guard_open(outfile)

                self._generate_objects(objects, outfile)

                self._generate_include_guard_close(outfile)

        except Exception as e:
            msg = "{g} failed to generate output {out}: {exception}".format(
                g = str(type(self).__name__),
                out = outpath,
                exception = e
            )
            raise ShoulderGeneratorException(msg)

    def _generate_license(self, outfile):
        logger.debug("Writing license from " + str(config.license_template_path))
        with open(config.license_template_path, "r") as license:
            for line in license:
                outfile.write("// " + line)
        outfile.write("\n")

    def _generate_c_includes(self, outfile):
        c_includes = "#include <stdint.h>\n"
        c_includes += "#include \"{path}\"\n".format(path=config.regs_h_name)
        outfile.write(c_includes)
        outfile.write("\n")

    def _generate_include_guard_open(self, outfile):
        outfile.write("#ifndef SHOULDER_AARCH64_H\n")
        outfile.write("#define SHOULDER_AARCH64_H\n")
        outfile.write("\n")

    def _generate_include_guard_close(self, outfile):
        outfile.write("#endif\n\n")

    def _generate_objects(self, objects, outfile):
        for obj in objects:
            if(isinstance(obj, Register)):
                logger.debug("Writing register: " + str(obj.name))
                self._generate_register(obj, outfile)
            else:
                msg = "Cannot generate object of unsupported {t} type".format(
                    t = type(obj)
                )
                raise ShoulderGeneratorException(msg)

    def _generate_register(self, reg, outfile):
        reg_c_name = str(reg.name).lower()
        reg_c_size = "uint64_t" if reg.size == 64 else "uint32_t"

        reg_comment = "// {name} ({long_name})\n// {purpose}\n".format(
            name = str(reg.name),
            long_name = str(reg.long_name),
            purpose = str(reg.purpose)
        )
        outfile.write(reg_comment)

        reg_getter = "{indent}{size_t} {c_prefix}_{regname}_{funcname}(void) "
        reg_getter += "{{ GET_SYSREG_FUNC({regname}) }}\n"
        reg_getter = reg_getter.format(
            indent = self._indent_string(),
            size_t = reg_c_size,
            c_prefix = config.c_prefix,
            regname = reg_c_name,
            funcname = config.register_read_function
        )
        outfile.write(reg_getter)

        reg_setter = "{indent}void {c_prefix}_{regname}_{funcname}({size_t} val) "
        reg_setter += "{{ SET_SYSREG_BY_VALUE_FUNC({regname}, val) }}\n"
        reg_setter = reg_setter.format(
            indent = self._indent_string(),
            c_prefix = config.c_prefix,
            regname = reg_c_name,
            funcname = config.register_write_function,
            size_t = reg_c_size
        )
        outfile.write(reg_setter)

        self._generate_fieldsets(reg, outfile)

        # TODO: Make Bareflank independent printing function
        outfile.write("\n")
        dump_func = "{indent}void {c_prefix}_{regname}_dump(int level, char *msg = nullptr)\n{indent}{{\n"
        dump_func = dump_func.format(
            indent = self._indent_string(),
            c_prefix = config.c_prefix,
            regname = reg_c_name
        )
        outfile.write(dump_func)

        self._increase_indent()
        dump_func = "{indent}bfdebug_nhex(level, name, get(), msg);\n"
        for idx, fieldset in enumerate(reg.fieldsets):
            for field in fieldset.fields:
                field_c_name = field.name.lower()
                dump_func += "{indent}{c_prefix}_{regname}_{fieldname}_dump(level, msg);\n"
                dump_func = dump_func.format(
                    indent = self._indent_string(),
                    c_prefix = config.c_prefix,
                    regname = reg_c_name,
                    fieldname = field_c_name
                )
        outfile.write(dump_func)
        self._decrease_indent()

        outfile.write(self._indent_string())
        dump_func = "}\n"
        outfile.write(dump_func)

        outfile.write("\n")

    def _generate_fieldsets(self, reg, outfile):
        if not reg.is_sysreg: return
        fieldsets = reg.fieldsets

        if len(fieldsets) == 1:
            self._generate_single_fieldset(reg, fieldsets[0], outfile)
        elif len(fieldsets) > 1:
            for idx, fieldset in enumerate(fieldsets):
                self._generate_single_fieldset(reg, fieldset, outfile)
        else:
            logger.debug("No fieldsets generated for system register " + str(reg.name))

    def _generate_single_fieldset(self, reg, fieldset, outfile):
        if(fieldset.condition is not None):
            outfile.write("\n")
            self._increase_indent()
            fieldset_comment = "{indent}// Fieldset valid when: {comment}".format(
                indent = self._indent_string(),
                comment = str(fieldset.condition)
            )
            outfile.write(fieldset_comment)
            self._decrease_indent()

        for field in fieldset.fields:
            field_c_name = field.name.lower()
            outfile.write("\n")
            self._increase_indent()
            if(field.msb == field.lsb):
                self._generate_bitfield_accessors(reg, field, outfile)
            else:
                self._generate_field_accessors(reg, field, outfile)
            # TODO: Create Bareflank independent printing function
            dump_func = "{indent}void {c_prefix}_{regname}_{fieldname}_dump(int level, char *msg = nullptr) "
            dump_func += "{{ bfdebug_subnhex(level, name, get(), msg); }}\n"
            dump_func = dump_func.format(
                indent = self._indent_string(),
                c_prefix = config.c_prefix,
                regname = reg.name.lower(),
                fieldname = field.name.lower(),
            )
            outfile.write(dump_func)
            self._decrease_indent()

    def _generate_bitfield_accessors(self, reg, field, outfile):
        mask = "0x" + format(1 << field.msb, 'x')
        reg_c_name = reg.name.lower()
        reg_val_c_name = reg_c_name + "_val"
        reg_c_size = "uint64_t" if reg.size == 64 else "uint32_t"

        field_c_name = field.name.lower()

        # Check bit enabled from the system register directly
        accessor = "{indent}{size_t} {c_prefix}_{regname}_{fieldname}_{func}() "
        accessor += "{{ IS_SYSREG_BIT_ENABLED_FUNC({regname}, {msb}) }}\n"
        accessor = accessor.format(
            indent = self._indent_string(),
            size_t = reg_c_size,
            c_prefix = config.c_prefix,
            regname = reg_c_name,
            fieldname = field_c_name,
            func = config.is_bit_set_function,
            msb = field.msb
        )
        outfile.write(accessor)

        # Check bit enabled from an integer value
        accessor = "{indent}{size_t} {c_prefix}_{regname}_{fieldname}_{func}_val({size_t} {arg}) "
        accessor += "{{ IS_BIT_ENABLED_FUNC({arg}, {msb}) }}\n"
        accessor = accessor.format(
            indent = self._indent_string(),
            size_t = reg_c_size,
            c_prefix = config.c_prefix,
            regname = reg_c_name,
            fieldname = field_c_name,
            func = config.is_bit_set_function,
            arg = reg_val_c_name,
            msb = field.msb
        )
        outfile.write(accessor)

        # Check bit disabled from system register directly
        accessor = "{indent}{size_t} {c_prefix}_{regname}_{fieldname}_{func}() "
        accessor += "{{ IS_SYSREG_BIT_DISABLED_FUNC({regname}, {msb}) }}\n"
        accessor = accessor.format(
            indent = self._indent_string(),
            size_t = reg_c_size,
            c_prefix = config.c_prefix,
            regname = reg_c_name,
            fieldname = field_c_name,
            func = config.is_bit_cleared_function,
            msb = field.msb
        )
        outfile.write(accessor)

        # Check bit disabled from an integer value
        accessor = "{indent}{size_t} {c_prefix}_{regname}_{fieldname}_{func}_val({size_t} {arg}) "
        accessor += "{{ IS_BIT_DISABLED_FUNC({arg}, {msb}) }}\n"
        accessor = accessor.format(
            indent = self._indent_string(),
            size_t = reg_c_size,
            c_prefix = config.c_prefix,
            regname = reg_c_name,
            fieldname = field_c_name,
            func = config.is_bit_cleared_function,
            arg = reg_val_c_name,
            msb = field.msb
        )
        outfile.write(accessor)

        # Enable the bit in the system register directly
        accessor = "{indent}void {c_prefix}_{regname}_{fieldname}_{func}() "
        accessor += "{{ SET_SYSREG_BITS_BY_MASK_FUNC({regname}, {mask}) }}\n"
        accessor = accessor.format(
            indent = self._indent_string(),
            c_prefix = config.c_prefix,
            regname = reg_c_name,
            fieldname = field_c_name,
            func = config.bit_set_function,
            mask = mask
        )
        outfile.write(accessor)

        # Enable the bit in an integer value
        accessor = "{indent}{size_t} {c_prefix}_{regname}_{fieldname}_{func}_val({size_t} {arg}) "
        accessor += "{{ SET_BITS_BY_MASK_FUNC({arg}, {mask}) }}\n"
        accessor = accessor.format(
            indent = self._indent_string(),
            size_t = reg_c_size,
            c_prefix = config.c_prefix,
            regname = reg_c_name,
            fieldname = field_c_name,
            func = config.bit_set_function,
            arg = reg_val_c_name,
            mask = mask
        )
        outfile.write(accessor)

        # Disable the bit in the system register directly
        accessor = "{indent}void {c_prefix}_{regname}_{fieldname}_{func}() "
        accessor += "{{ CLEAR_SYSREG_BITS_BY_MASK_FUNC({regname}, {mask}) }}\n"
        accessor = accessor.format(
            indent = self._indent_string(),
            c_prefix = config.c_prefix,
            regname = reg_c_name,
            fieldname = field_c_name,
            func = config.bit_clear_function,
            mask = mask
        )
        outfile.write(accessor)

        # Disable the bit in an integer value
        accessor = "{indent}{size_t} {c_prefix}_{regname}_{fieldname}_{func}_val({size_t} {arg}) "
        accessor += "{{ CLEAR_BITS_BY_MASK_FUNC({arg}, {mask}) }}\n"
        accessor = accessor.format(
            indent = self._indent_string(),
            size_t = reg_c_size,
            c_prefix = config.c_prefix,
            regname = reg_c_name,
            fieldname = field_c_name,
            func = config.bit_clear_function,
            arg = reg_val_c_name,
            mask = mask
        )
        outfile.write(accessor)

    def _generate_field_accessors(self, reg, field, outfile):
        mask_val = 0
        for i in range(field.lsb, field.msb + 1):
            mask_val |= 1 << i
        mask = "0x" + format(mask_val, 'x')

        reg_c_name = reg.name.lower()
        reg_val_c_name = reg_c_name + "_val"
        reg_c_size = "uint64_t" if reg.size == 64 else "uint32_t"

        field_c_name = field.name.lower()

        # Get the field value from the system register directly
        accessor = "{indent}{size_t} {c_prefix}_{regname}_{fieldname}_{func}() "
        accessor += "{{ GET_SYSREG_FIELD_FUNC({regname}, {mask}, {lsb}) }}\n"
        accessor = accessor.format(
            indent = self._indent_string(),
            size_t = reg_c_size,
            c_prefix = config.c_prefix,
            regname = reg_c_name,
            fieldname = field_c_name,
            func = config.register_field_read_function,
            mask = mask,
            lsb = field.lsb
        )
        outfile.write(accessor)

        # Get the field value from an integer value
        accessor = "{indent}{size_t} {c_prefix}_{regname}_{fieldname}_{func}_val({size_t} {arg}) "
        accessor += "{{ GET_BITFIELD_FUNC({arg}, {mask}, {lsb}) }}\n"
        accessor = accessor.format(
            indent = self._indent_string(),
            size_t = reg_c_size,
            c_prefix = config.c_prefix,
            regname = reg_c_name,
            fieldname = field_c_name,
            func = config.register_field_read_function,
            arg = reg_val_c_name,
            mask = mask,
            lsb = field.lsb
        )
        outfile.write(accessor)

        # Set the field's value in the system register directly
        accessor = "{indent}void {c_prefix}_{regname}_{fieldname}_{func}({size_t} {arg}) "
        accessor += "{{ SET_SYSREG_BITS_BY_VALUE_FUNC({regname}, {arg}, {mask}, {lsb}) }}\n"
        accessor = accessor.format(
            indent = self._indent_string(),
            c_prefix = config.c_prefix,
            regname = reg_c_name,
            fieldname = field_c_name,
            func = config.register_field_write_function,
            size_t = reg_c_size,
            arg = "value",
            mask = mask,
            lsb = field.lsb
        )
        outfile.write(accessor)

        # Set the field's value in an integer value
        accessor = "{indent}{size_t} {c_prefix}_{regname}_{fieldname}_{func}_val({size_t} {arg1}, {size_t} {arg2}) "
        accessor += "{{ SET_BITS_BY_VALUE_FUNC({arg1}, {arg2}, {mask}, {lsb}) }}\n"
        accessor = accessor.format(
            indent = self._indent_string(),
            size_t = reg_c_size,
            c_prefix = config.c_prefix,
            regname = reg_c_name,
            fieldname = field_c_name,
            func = config.register_field_write_function,
            arg1 = reg_c_name,
            arg2 = "value",
            mask = mask,
            lsb = field.lsb
        )
        outfile.write(accessor)

    def _increase_indent(self):
        self._current_indent_level += 1

    def _decrease_indent(self):
        if self._current_indent_level <= 0:
            raise ShoulderGeneratorException("Indent level cannot be negative")
        self._current_indent_level -= 1

    def _indent_string(self):
        indent_str = ""
        for level in range(0, self._current_indent_level):
            indent_str += "\t"
        return indent_str
