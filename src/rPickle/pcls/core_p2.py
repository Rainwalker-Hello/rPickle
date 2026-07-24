'''
rPickle - A safe and efficient Python serialization library.

Binary format with:
  - Circular reference support
  - Extensible type system

Example usage:
    >>> import rPickle as rp
    >>> data = {'a': 1, 'b': [1, 2, 3], 'c': (1, 2, 3)}
    >>> with open('data.rp', 'wb') as f:
    ...     rp.dump(data, f)
    >>> with open('data.rp', 'rb') as f:
    ...     loaded_data = rp.load(f)
'''

from typing import BinaryIO as _BinaryIO, Any as _Any, Callable as _Callable
import struct as _struct
import builtins as _builtins
from io import BytesIO as _BytesIO
import sys as _sys
from ..ext import Extension

_version = 2
_python_version = (3, 15)

_version_info = (0, 10, 0)
__version__ = '.'.join(map(str, _version_info))

_MAX_SIZE = 5 << 30
def set_max_size(size: int) -> int:
    global _MAX_SIZE
    _MAX_SIZE = size

_MAGIC = b'RPkl'

_SENTINEL_REG = {}

class VersionError(Exception):
    '''Exception raised when the Python or rPickle version is not compatible.'''
    def __init__(self, text: str = f"Cannot load because Python or rPickle is not the newest version. Need Python {'.'.join(map(str, _python_version))}+ or rPickle {__version__}+"):
        self.text = text
        super().__init__(text)

class UnsupportedTypeError(Exception):
    '''Exception raised when an unsupported type is encountered.'''
class ExtensionNotFoundError(Exception):
    '''Exception raised when an extension is not found.'''

if _sys.version_info < (3, 15):
    class frozendict:
        '''A simple implementation of a frozendict for Python versions < 3.15.'''
        def __init__(self, *args, **kwargs): raise VersionError()
    class sentinel:
        '''A simple implementation of a sentinel for Python versions < 3.15.'''
        def __init__(self, *args, **kwargs): raise VersionError()
        __name__: str

    
def _load(f: _BinaryIO, extensions: Extension | None = None) -> _Any:
    f: _BytesIO = f

    def read(length: int, need_int: bool = False, signed: bool = False) -> bytes | int:
        if length > _MAX_SIZE:
            raise ValueError(f"Exceeds the limit ({_MAX_SIZE} bytes) for data size; use rPickle.set_max_size() to increase the limit")
        data = f.read(length)
        if len(data) != length: raise EOFError(f"expected at least {length}, got {len(data)}")
        if need_int: return int.from_bytes(data, 'little', signed=signed)
        return data
    
    def readinto(length: int) -> bytearray:
        if length > _MAX_SIZE:
            raise ValueError(f"Exceeds the limit ({_MAX_SIZE} bytes) for data size; use rPickle.set_max_size() to increase the limit")
        data = bytearray(length)
        n = f.readinto(data)
        if n != length: raise EOFError(f"expected at least {length}, got {n}")
        return data
    
    objs_id: list[_Any] = []
    extensions = {} if extensions is None else {f'{k.__module__}.{k.__qualname__}': v for k, v in extensions._dict.items()}

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
                        frame[2][frame[4]] = value
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
            # basic constant
            case 0x00 | 0x01: push_value(bool(opcode))
            case 0x02: push_value(None)
            case 0x03: push_value(...)
            case 0x04: push_value(_builtins.NotImplemented)

            # specially
            case 0x10:
                value, = struct_compile['d'].unpack(read(8))
                objs_id.append(value)
                push_value(value)
            
            case 0x11:
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

            case 0x12 | 0x13 as code:
                idx = len(objs_id)
                objs_id.append(None)
                stack.append([idx, 3, [], make_range if code == 0x12 else make_slice])

            case 0x14:
                name = read(read(1, True)).decode()
                value = _SENTINEL_REG.get(name)
                if value is None:
                    value = sentinel(name)
                    _SENTINEL_REG[name] = value
                objs_id.append(value)
                push_value(value)
            
            # int
            case 0x20:
                value = read(1, True, True)
                push_value(value)

            case 0x21:
                value = read(2, True, True)
                push_value(value)

            case 0x22:
                value, = struct_compile['i'].unpack(read(4))
                objs_id.append(value)
                push_value(value)

            case 0x23:
                signed_byte, length_of_length = struct_compile['bB'].unpack(read(2))
                value = signed_byte * read(read(length_of_length, True), True)
                objs_id.append(value)
                push_value(value)

            # str
            case 0x30:
                value = read(read(1, True)).decode()
                objs_id.append(value)
                push_value(value)

            case 0x31:
                value = read(read(read(1, True), True)).decode()
                objs_id.append(value)
                push_value(value)
            
            # bytes
            case 0x40 | 0x41 | 0x42 | 0x43:
                length = read(read(1, True), True) if opcode in {0x41, 0x43} else read(1, True)
                value = (read if opcode in {0x40, 0x41} else readinto)(length)
                objs_id.append(value)
                push_value(value)

            # containers
            case 0x50 | 0x60:
                idx = len(objs_id)
                objs_id.append(None)
                length = read(read(1, True), True)
                if length == 0:
                    v = () if opcode == 0x50 else frozenset()
                    push_value(v)
                    objs_id[idx] = v
                else: stack.append([idx, length, [], tuple if opcode == 0x50 else frozenset])

            case 0x51 | 0x61:
                value = [] if opcode == 0x51 else set()
                idx = len(objs_id)
                objs_id.append(value)
                length = read(read(1, True), True)
                if length == 0: push_value(value)
                else: stack.append([-1, length, value, list if opcode == 0x51 else set])

            case 0x70:
                idx = len(objs_id)
                objs_id.append(None)
                length = read(read(1, True), True)
                if length == 0:
                    v = frozendict()
                    push_value(v)
                    objs_id[idx] = v
                else: stack.append([idx, length, {}, frozendict, UNSET])
            
            case 0x71:
                value = {}
                idx = len(objs_id)
                objs_id.append(value)
                length = read(read(1, True), True)
                if length == 0: push_value(value)
                else: stack.append([-1, length, value, dict, UNSET])

            # system
            case 0xF0: push_value(objs_id[read(read(1, True), True)])
            case 0xF1:
                name = read(read(1, True)).decode()
                if name not in extensions: raise ExtensionNotFoundError(f"Unknown extension type: '{name}'")
                value = extensions[name][0](read(read(read(1, True), True)))
                objs_id.append(value)
                push_value(value)
            
            case _: raise ValueError(f"Unknown opcode: {opcode:#x}")

    return result
        
def _dump(obj: _Any, f: _BinaryIO, extensions: Extension | None = None):
    f.write(_MAGIC)
    f.write(_version.to_bytes(2, 'little'))
    f.write(_sys.version_info.major.to_bytes())
    f.write(_sys.version_info.minor.to_bytes())
    extensions = {} if extensions is None else extensions._dict
    stack = [obj]
    obm = {
        tuple     : b'\x50',
        list      : b'\x51',
        frozenset : b'\x60',
        set       : b'\x61',
        frozendict: b'\x70',
        dict      : b'\x71',

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
            f.write(b'\xF0')
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

        if type(obj) in extensions:
            f.write(b'\xF1')
            name = f'{type(obj).__module__}.{type(obj).__qualname__}'.encode()
            f.write(len(name).to_bytes())
            f.write(name)
            value = extensions[type(obj)][1](obj)
            length = len(value).to_bytes(8, 'little').rstrip(b'\x00')
            f.write(len(length).to_bytes())
            f.write(length)
            f.write(value)
            continue

        match obj:
            case bool()   : f.write(bytes((obj,)))
            case None     : f.write(b'\x02')
            case float():
                f.write(struct_compile['cd'].pack(b'\x10', obj))

            case complex():
                f.write(b'\x11')
                has_real, has_imag = bool(obj.real), bool(obj.imag)
                f.write(bytes((has_real << 4 | has_imag,)))
                stack += (obj.imag, obj.real)[not has_imag : has_real + 1]

            case int():
                if -128 <= obj < 128: # very short
                    f.write(struct_compile['cb'].pack(b'\x20', obj))
                    continue

                elif -32768 <= obj < 32768: # short
                    f.write(struct_compile['ch'].pack(b'\x21', obj))
                    continue

                elif -2147483648 <= obj < 2147483648 : # int
                    f.write(struct_compile['ci'].pack(b'\x22', obj))
                    continue

                num = abs(obj)
                digits = num.to_bytes((num.bit_length() + 7) >> 3, 'little')
                f.write(struct_compile['2c'].pack(b'\x23', b'\xFF' if obj < 0 else b'\x01')) # signed
                length_of_length = len(digits).to_bytes(8, 'little').rstrip(b'\x00') # length
                f.write(len(length_of_length).to_bytes()) # length of length
                f.write(length_of_length)
                f.write(digits)
            
            case str():
                content = obj.encode()
                if len(content) < 256:
                    f.write(struct_compile['cB'].pack(b'\x30', len(content)))
                    f.write(content)
                else:
                    f.write(b'\x31')
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
                stack[-1:-1-(len(obj)<<1):-1] = (item for kv in obj.items() for item in kv)

            case bytes() | bytearray():
                if len(obj) < 256:
                    f.write(struct_compile['cB'].pack(b'\x40' if isinstance(obj, bytes) else b'\x42', len(obj)))
                    f.write(obj)
                else:
                    f.write(b'\x41' if isinstance(obj, bytes) else b'\x43')
                    length = len(obj).to_bytes(8, 'little').rstrip(b'\x00')
                    f.write(len(length).to_bytes())
                    f.write(length)
                    f.write(obj)

            case range() | slice():
                f.write(obm[type(obj)])
                stack += (obj.step, obj.stop, obj.start)

            case sentinel():
                _SENTINEL_REG[obj.__name__] = obj
                f.write(b'\x14')
                content = obj.__name__.encode()
                f.write(len(content).to_bytes())
                f.write(content)

            case _ if obj is ...: f.write(b'\x03')
            case _ if obj is _builtins.NotImplemented: f.write(b'\x04')
            case _: raise UnsupportedTypeError(f"Unsupported type: '{type(obj).__name__}'")
