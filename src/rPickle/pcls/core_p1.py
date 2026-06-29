'''
rPickle - A safe and efficient Python serialization library.

Binary format with:
  - Circular reference support
  - Extensible type system
'''

from typing import BinaryIO as _BinaryIO, Any as _Any, Callable as _Callable
import struct as _struct
import builtins as _builtins
from io import BytesIO as _BytesIO
import sys as _sys
import warnings
from ..ext import Extension

_version = 1
_python_version = (3, 15)

_version_info = (0, 4, 0)
__version__ = '.'.join(map(str, _version_info))

_MAGIC = b'RPkl'

class VersionError(Exception):
    def __init__(self, text: str = f"Cannot load because Python or rPickle is not the newest version. Need Python {'.'.join(map(str, _python_version))}+ or rPickle {__version__}+"):
        self.text = text
        super().__init__(text)

class UnsupportedTypeError(Exception): pass
class ExtensionNotFoundError(Exception): pass

if _sys.version_info < (3, 15):
    class frozendict:
        def __init__(self, *args, **kwargs): raise VersionError()
    class sentinel:
        def __init__(self, *args, **kwargs): raise VersionError()


def load(f: _BinaryIO, extensions: Extension | None = None) -> _Any:
    '''load data from file'''
    f: _BytesIO = f

    def read(length: int, need_int: bool = False, signed: bool = False) -> bytes | int:
        data = f.read(length)
        if len(data) != length: raise EOFError(f"expected at least {length}, got {len(data)}")
        if need_int: return int.from_bytes(data, 'little', signed=signed)
        return data
    
    def readinto(length: int) -> bytearray:
        data = bytearray(length)
        n = f.readinto(data)
        if n != length: raise EOFError(f"expected at least {length}, got {n}")
        return data
    
    objs_id: list[_Any] = []
    extensions = {} if extensions is None else {k.__module__ + k.__qualname__: v for k, v in extensions._dict.items()}

    UNSET = sentinel('UNSET') if _sys.version_info >= (3, 15) else object()

    def make_range(items: list) -> range: return range(*items)
    def make_slice(items: list) -> slice: return slice(*items)
    def make_complex(items: list) -> complex: return complex(*items)

    stack: list[list[int | _Any | _Callable]] = []
    # [oi, idx, target, builder, (temp)]
    result: _Any = UNSET

    def push_value(value: _Any) -> None:
        nonlocal result
        if not stack:
            result = value
            return
        
        r = True
        while r and stack:
            frame = stack[-1]
            
            match frame[2]:
                case list():
                    frame[2].append(value)
                    r = False
                case set():
                    frame[2].add(value)
                    r = False
                case dict():
                    if frame[4] is UNSET: frame[4] = value
                    else:
                        frame[2][value] = frame[4]
                        frame[4] = UNSET
                    r = False
            
            if len(frame[2]) == frame[1]:
                stack.pop()
                if not isinstance(frame[3], type) or not isinstance(frame[2], frame[3]): frame[2] = frame[3](frame[2])
                if frame[0] >= 0: objs_id[frame[0]] = frame[2]
                value = frame[2]
                r = True

        if not stack: result = value

    struct_compile = {
        'd' : _struct.Struct('<d'),
        'bB': _struct.Struct('<bB'),
        'h' : _struct.Struct('<h'),
        'b' : _struct.Struct('<b'),
        'i' : _struct.Struct('<i'),
        'f' : _struct.Struct('<f'),
    }

    while result is UNSET:
        opcode = read(1, True)

        match opcode:
            case 0x0 | 0x1: push_value(bool(opcode))
            case 0x2: push_value(None)
            case 0x3:
                value, = struct_compile['d'].unpack(read(8))
                objs_id.append(value)
                push_value(value)
            
            case 0x4:
                idx = len(objs_id)
                objs_id.append(None)
                flag = read(1, True)
                has_real, has_imag = flag >> 4, flag & 1
                if has_real and has_imag:
                    stack.append([idx, 2, [], make_complex])
                elif has_real:
                    stack.append([idx, 1, [], lambda items: complex(items[0], 0)])
                elif has_imag:
                    stack.append([idx, 1, [], lambda items: complex(0, items[0])])
                else:
                    v = 0j
                    objs_id[idx] = v
                    push_value(v)
            
            case 0x5:
                signed_byte, length_of_length = struct_compile['bB'].unpack(read(2))
                value = signed_byte * read(read(length_of_length, True), True)
                objs_id.append(value)
                push_value(value)
            
            case 0x6:
                value = read(read(read(1, True), True)).decode()
                objs_id.append(value)
                push_value(value)
            
            case 0x7:
                idx = len(objs_id)
                objs_id.append(None)
                length = read(read(1, True), True)
                if length == 0:
                    v = ()
                    push_value(v)
                    objs_id[idx] = v
                else: stack.append([idx, length, [], tuple])
            
            case 0x8:
                value: list = []
                idx = len(objs_id)
                objs_id.append(value)
                length = read(read(1, True), True)
                if length == 0: push_value(value)
                else: stack.append([-1, length, value, list])
            
            case 0x9:
                value = set()
                idx = len(objs_id)
                objs_id.append(value)
                length = read(read(1, True), True)
                if length == 0: push_value(value)
                else: stack.append([idx, length, value, set])
            
            case 0xA:
                value = {}
                idx = len(objs_id)
                objs_id.append(value)
                length = read(read(1, True), True)
                if length == 0: push_value(value)
                else: stack.append([idx, length, value, dict, UNSET])
            
            case 0xB | 0xC:
                value = (read if opcode == 0xB else readinto)(read(read(1, True), True))
                objs_id.append(value)
                push_value(value)
            
            case 0xD:
                value, = struct_compile['h'].unpack(read(2))
                push_value(value)
            
            case 0xE:
                value = (read(1, True) ^ 0x80) - 0x80
                push_value(value)
            
            case 0xF:
                value, = struct_compile['i'].unpack(read(4))
                objs_id.append(value)
                push_value(value)
            
            case 0x10:
                idx = len(objs_id)
                objs_id.append(None)
                length = read(read(1, True), True)
                if length == 0:
                    v = frozenset()
                    push_value(v)
                    objs_id[idx] = v
                else: stack.append([idx, length, set(), frozenset])
            
            case 0x11:
                value = read(read(1, True)).decode()
                objs_id.append(value)
                push_value(value)
            
            case 0x12 | 0x13 as code:
                idx = len(objs_id)
                objs_id.append(None)
                stack.append([idx, 3, [], make_range if code == 0x12 else make_slice])
            
            case 0x14: push_value(...)
            case 0x15: push_value(_builtins.NotImplemented)
            case 0x16:
                idx = len(objs_id)
                objs_id.append(None)
                length = read(read(1, True), True)
                if length == 0:
                    v = frozendict()
                    push_value(v)
                    objs_id[idx] = v
                else: stack.append([idx, length, {}, frozendict, UNSET])

            case 0x17:
                value = sentinel(read(read(1, True)).decode())
                objs_id.append(value)
                push_value(value)
            
            case 0xFE: push_value(objs_id[read(read(1, True))])
            case 0xFF:
                name = read(read(1, True)).decode()
                if name not in extensions: raise ExtensionNotFoundError(f"Unknown extension type: '{name}'")
                value = extensions[name][0](read(read(read(1, True), True)))
                objs_id.append(value)
                push_value(value)
            
            case _: raise ValueError(f"Unknown opcode: {opcode:#x}")

    return result

def loads(source: bytes | bytearray, extensions: Extension | None = None) -> _Any:
    '''load data from byte-like'''
    return load(_BytesIO(source), extensions)
            
def dump(obj: _Any, f: _BinaryIO, extensions: Extension | None = None):
    '''dump data to file'''
    f.write(_MAGIC)
    f.write(_version.to_bytes(2, 'little'))
    f.write(_sys.version_info.major.to_bytes())
    f.write(_sys.version_info.minor.to_bytes())
    extensions = {} if extensions is None else extensions._dict
    stack = [obj]
    obm = {
        tuple     : b'\x07',
        list      : b'\x08',
        set       : b'\x09',
        frozenset : b'\x10',

        dict      : b'\x0A',
        frozendict: b'\x16',

        bytes     : b'\x0B',
        bytearray : b'\x0C',

        range     : b'\x12',
        slice     : b'\x13',
    }
    struct_compile = {
        'cd' : _struct.Struct('<cd'),
        'cbB': _struct.Struct('<cbB'),
        'ch' : _struct.Struct('<ch'),
        'cb' : _struct.Struct('<cb'),
        'ci' : _struct.Struct('<ci'),
        '2c' : _struct.Struct('<2c'),
        'cB' : _struct.Struct('<cB'),
    }

    objs_id: dict[int, int] = {}
    id_count = 0
    while stack:
        obj = stack.pop()
        obj_id = id(obj)
        if obj_id in objs_id:
            f.write(b'\xFE')
            content = objs_id[obj_id].to_bytes(8, 'little').rstrip(b'\x00')
            f.write(len(content).to_bytes())
            f.write(content)
            continue

        if not (
                isinstance(obj, bool)
                or obj is None
                or obj is ...
                or obj is _builtins.NotImplemented
                or (isinstance(obj, int) and -32768 <= obj < 32768)
            ):
            objs_id[obj_id] = id_count
            id_count += 1

        match obj:
            case bool()   : f.write(bytes((obj,)))
            case None     : f.write(b'\x02')
            case float():
                f.write(struct_compile['cd'].pack(b'\x03', obj))

            case complex():
                f.write(b'\x04')
                has_real, has_imag = bool(obj.real), bool(obj.imag)
                f.write(bytes((has_real << 4 | has_imag,)))
                stack += (obj.imag, obj.real)[not has_imag : has_real + 1]

            case int():
                if -128 <= obj < 128: # very short
                    f.write(struct_compile['cb'].pack(b'\x0E', obj))
                    continue

                elif -32768 <= obj < 32768: # short
                    f.write(struct_compile['ch'].pack(b'\x0D', obj))
                    continue

                elif -2147483648 <= obj < 2147483648 : # int
                    f.write(struct_compile['ci'].pack(b'\x0F', obj))
                    continue

                num = abs(obj)
                digits = num.to_bytes((num.bit_length() + 7) >> 3, 'little')
                f.write(struct_compile['2c'].pack(b'\x05', b'\xFF' if obj < 0 else b'\x01')) # signed
                length_of_length = len(digits).to_bytes(8, 'little').rstrip(b'\x00') # length
                f.write(len(length_of_length).to_bytes()) # length of length
                f.write(length_of_length)
                f.write(digits)
            
            case str():
                content = obj.encode()
                if len(content) < 256:
                    f.write(struct_compile['cB'].pack(b'\x11', len(content)))
                    f.write(content)
                else:
                    f.write(b'\x06')
                    length = len(content).to_bytes(8, 'little').rstrip(b'\x00')
                    f.write(len(length).to_bytes())
                    f.write(length)
                    f.write(content)

            case tuple() | list() | set() | frozenset():
                f.write(obm[type(obj)])
                length = len(obj).to_bytes(8, 'little').rstrip(b'\x00')
                f.write(len(length).to_bytes())
                f.write(length)
                stack += [None] * len(obj)
                stack[-1:-1-len(obj):-1] = obj

            case dict() | frozendict():
                f.write(obm[type(obj)])
                length = len(obj).to_bytes(8, 'little').rstrip(b'\x00')
                f.write(len(length).to_bytes())
                f.write(length)
                stack += [None] * (len(obj) << 1)
                stack[-1:-1-(len(obj)<<1):-1] = (item for key, value in obj.items() for item in (value, key))
                # To maintain order, this genexpr must reverse (key, value) to (value, key)
                # stack will become [..., k3, v3, k2, v2, k1, v1]
                # When stack pop, it'll pop v1 first, then pop k1, and so on

            case bytes() | bytearray():
                f.write(obm[type(obj)])
                length = len(obj).to_bytes(8, 'little').rstrip(b'\x00')
                f.write(len(length).to_bytes())
                f.write(length)
                f.write(obj)

            case range() | slice():
                f.write(obm[type(obj)])
                stack += (obj.step, obj.stop, obj.start)

            case sentinel():
                f.write(b'\x17')
                content = obj.__name__.encode()
                f.write(len(content).to_bytes())
                f.write(content)

            case _ if obj is ...: f.write(b'\x14')
            case _ if obj is _builtins.NotImplemented: f.write(b'\x15')
            case _:
                if type(obj) in extensions:
                    f.write(b'\xFF')
                    name = (type(obj).__module__ + type(obj).__qualname__).encode()
                    f.write(len(name).to_bytes())
                    f.write(name)
                    value = extensions[type(obj)][1](obj)
                    length = len(value).to_bytes(8, 'little').rstrip(b'\x00')
                    f.write(len(length).to_bytes())
                    f.write(length)
                    f.write(value)
                else:
                    raise UnsupportedTypeError(f"Unsupported type: '{type(obj).__name__}'")

def dumps(obj: _Any, extensions: Extension | None = None) -> bytes:
    '''dump data to byte-like'''
    buf = _BytesIO()
    dump(obj, buf, extensions)
    return buf.getvalue()

__all__ = (
    'loads', 'dumps', 'load', 'dump', 'VersionError', 'ExtensionNotFoundError', 'UnsupportedTypeError',
)
