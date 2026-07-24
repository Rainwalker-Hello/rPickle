'rPickle disassembler — human-readable view of rPickle bytecode.'

import sys as _sys
from typing import TextIO as _TextIO
import struct as _struct

_OBM = {
    **dict(enumerate(map(str, (False, True, None, ..., NotImplemented)))),
    0x12: 'range', 0x13: 'slice',
    0x30: 'short str', 0x31: 'long str',
    0x40: 'short bytes', 0x41: 'long bytes', 0x42: 'short bytearray', 0x43: 'long bytearray',
    0x50: 'tuple', 0x51: 'list', 0x60: 'frozenset', 0x61: 'set', 0x70: 'frozendict', 0x71: 'dict'
}


def dis(source: bytes, file: _TextIO = _sys.stdout) -> None:
    '''
    Disassemble rPickle bytecode into human-readable instructions.

    Args:
        source: The rPickle bytecode to disassemble.
        file: Output stream (default: sys.stdout).
    '''
    if len(source) < 8:
        file.write('Truncated or invalid rPickle data\n')
        return

    i = 0
    # Magic
    file.write(f"{source[i:i+4].hex(' ').upper():<49} # Magic\n")
    i += 4
    # Protocol version
    file.write(f"{source[i:i+2].hex(' ').upper():<49} # Protocol {source[i]}\n")
    i += 2
    # Python version
    file.write(f"{source[i:i+2].hex(' ').upper():<49} # Python {source[i]}.{source[i+1]}\n")
    i += 2

    while i < len(source):
        op = source[i]
        i += 1

        match op:
            case x if x in range(5) or x in {0x12, 0x13}: file.write(f'{op:02X} {' ' * 46} # {_OBM[op]}\n')
            case 0x10:
                val = _struct.unpack('<d', source[i:i+8])[0]
                i += 8
                file.write(f"{op:02X} {val:<46} # float\n")

            case 0x11:
                flag = source[i]
                i += 1
                has_real = (flag >> 4) & 1
                has_imag = flag & 1
                real, imag = 0.0, 0.0
                if has_real:
                    real, = _struct.unpack('<d', source[i:i+8])
                    i += 8
                if has_imag:
                    imag, = _struct.unpack('<d', source[i:i+8])
                    i += 8
                value = complex(real, imag)
                file.write(f"{op:02X} {value:<46} # complex\n")

            case 0x14:
                name_len = source[i]
                i += 1
                name = source[i:i+name_len].decode()
                i += name_len
                s_id = '0x' + format(int.from_bytes(source[i:i+8], 'little'), '016X')
                i += 8
                file.write(f"{op:02X} {name} {s_id:<46} # sentinel\n")

            case 0x20:
                val = source[i]
                i += 1
                file.write(f"{op:02X} {val:<46} # int8\n")
            case 0x21:
                val = source[i:i+2]
                i += 2
                file.write(f"{op:02X} {val.hex(' ').upper():<46} # int16\n")
            case 0x22:
                val = source[i:i+4]
                i += 4
                file.write(f"{op:02X} {val.hex(' ').upper():<46} # int32\n")
            case 0x23:
                signed_byte = source[i]
                i += 1
                length_of_length = source[i]
                i += 1
                length = int.from_bytes(source[i:i+length_of_length], 'little')
                i += length_of_length
                digits = str(int.from_bytes(source[i:i+length], 'little') * signed_byte)
                i += length
                if len(digits) > 43: digits = digits[:40] + '...'
                file.write(f"{op:02X} {length_of_length:02X} {digits:<43} # int\n")

            case 0x30 | 0x40 | 0x42:
                length = source[i]
                i += 1
                val = source[i:i+length]
                if op == 0x30: val = val.decode()
                i += length
                if len(val) > 43: val = val[:40] + '...' if op == 0x30 else b'...'
                file.write(f"{op:02X} {length:02X} {val:<43} # {_OBM[op]}\n")


            case 0x31 | 0x41 | 0x43:
                length_of_length = source[i]
                i += 1
                length = int.from_bytes(source[i:i+length_of_length], 'little')
                i += length_of_length
                val = source[i:i+length]
                if op == 0x31: val = val.decode()
                i += length
                if len(val) > 41: val = val[:38] + '...' if op == 0x31 else b'...'
                file.write(f"{op:02X} {length:<43} {val:<4} # {_OBM[op]}\n")

            case 0x50 | 0x51 | 0x60 | 0x61 | 0x70 | 0x71:
                length_of_length = source[i]
                i += 1
                length = int.from_bytes(source[i:i+length_of_length], 'little')
                i += length_of_length
                file.write(f"{op:02X} {length:<46} # {_OBM[op]}\n")

            case 0xF0:
                length = source[i]
                i += 1
                ref = int.from_bytes(source[i:i+length], 'little')
                i += length
                file.write(f"{op:02X} {length:02X} {ref:<43} # ref\n")
                
            case 0xF1:
                name_len = source[i]
                i += 1
                name = source[i:i+name_len].decode()
                i += name_len
                length_of_length = source[i]
                i += 1
                length = int.from_bytes(source[i:i+length_of_length], 'little')
                i += length_of_length
                val = source[i:i+length].hex(' ').upper()
                i += length
                file.write(f"{op:02X} {name_len:02X} {name} {length_of_length:02X} {length} {val:<46} # ext\n")

            case _: file.write(f"{op:02X} {' ' * 46} # UNKNOWN\n")

__all__ = ('dis',)