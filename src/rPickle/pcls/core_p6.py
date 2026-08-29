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
from io import BytesIO as _BytesIO
import builtins as _builtins
import struct as _struct
import sys as _sys

from ..ext import Extension
from ..core import UnsupportedTypeError, VersionError, ExtensionNotFoundError
from .. import core

_version = 6

_MAGIC = b'RPkl'

_SENTINEL_REG = core._SENTINEL_REG

class _R:
    def __init__(self, objs_id: list, idx: int): self.objs_id, self.idx = objs_id, idx
    def __hash__(self): return hash(self.idx)
    @property
    def x(self): return self.objs_id[self.idx]


if _sys.version_info < (3, 15):
    class frozendict: # pragma: no cover
        '''A simple implementation of a frozendict for Python versions < 3.15.'''
        def __init__(self, *args, **kwargs): raise VersionError() # pragma: no cover
        def values(self): ...
        def items(self): ...
        def __iter__(self): ...
    class sentinel: # pragma: no cover
        '''A simple implementation of a sentinel for Python versions < 3.15.'''
        def __init__(self, *args, **kwargs): raise VersionError() # pragma: no cover
        __name__: str

_STRUCT_COMPILE = {
    'd' : _struct.Struct('<d'),
    'bB': _struct.Struct('<bB'),
    'cd' : _struct.Struct('<cd'),
    'ch' : _struct.Struct('<ch'),
    'cb' : _struct.Struct('<cb'),
    'ci' : _struct.Struct('<ci'),
    '2c' : _struct.Struct('<2c'),
    'cB' : _struct.Struct('<cB'),
    'cH' : _struct.Struct('<cH'),
    'cI' : _struct.Struct('<cI'),
}

_OBM = {
    tuple     : b'\x50',
    list      : b'\x51',
    frozenset : b'\x60',
    set       : b'\x61',
    frozendict: b'\x70',
    dict      : b'\x71',

    range     : b'\x12',
    slice     : b'\x13',
}

def _fix(obj):
    stack = [obj]
    seen = set()
    while stack:
        obj = stack.pop()
        seen.add(id(obj))
        match obj:
            case tuple(): stack += (i for i in obj if id(i) not in seen)
            case frozendict(): stack += (i for i in obj.values() if id(i) not in seen)
            case list():
                for i in range(len(obj)):
                    if isinstance(obj[i], _R): obj[i] = obj[i].x
                    elif id(obj[i]) not in seen: stack.append(obj[i])
            case dict():
                for k, v in obj.items():
                    if isinstance(v, _R): obj[k] = v.x
                    elif id(v) not in seen: stack.append(v)

def _load(f: _BinaryIO, extensions: Extension | None = None) -> _Any:
    f: _BytesIO = f
    _MAX_SIZE = core._MAX_SIZE

    def read(length: int, need_int: bool = False, signed: bool = False) -> bytes | int:
        if length > _MAX_SIZE:
            raise ValueError(f"exceeds the limit ({_MAX_SIZE} bytes) for data size; use rPickle.set_max_size() to increase the limit")
        data = f.read(length)
        if len(data) != length: raise EOFError(f"expected at least {length} byte{'s' * (length > 1)}, got {len(data)} byte{'s' * (length > 1)}{f', at {f.tell()}' if f.seekable() else ''}")
        if need_int: return int.from_bytes(data, 'little', signed=signed)
        return data
    
    def readinto(length: int) -> bytearray:
        if length > _MAX_SIZE:
            raise ValueError(f"exceeds the limit ({_MAX_SIZE} bytes) for data size; use rPickle.set_max_size() to increase the limit")
        data = bytearray(length)
        n = f.readinto(data)
        if n != length: raise EOFError(f"expected at least {length} byte{'s' * (length > 1)}, got {len(data)} byte{'s' * (length > 1)}{f', at {f.tell()}' if f.seekable() else ''}")
        return data
    
    objs_id: list[_Any] = []
    extensions = {} if extensions is None else {f'{k.__module__}.{k.__qualname__}': v for k, v in extensions._dict.items()}

    UNSET = sentinel('UNSET') if _sys.version_info >= (3, 15) else object()

    stack: list[list[int | _Any | _Callable]] = []
    # [Frame_tag, oi, idx, target, builder, (temp)]
    result = UNSET

    def push_value(value):
        nonlocal result
        if not stack:
            result = value
            return
        
        r = True
        while r and stack:
            frame = stack[-1]
            
            match frame[3]:
                case list():
                    frame[3].append(value)
                    r = False
                case set():
                    frame[3].add(value)
                    r = False
                case dict():
                    if frame[5] is UNSET: frame[5] = value
                    else:
                        frame[3][frame[5]] = value
                        frame[5] = UNSET
                    r = False
            
            if len(frame[3]) == frame[2]:
                stack.pop()
                if not isinstance(frame[4], type) or not isinstance(frame[3], frame[4]): frame[3] = frame[4](frame[3])
                if frame[1] >= 0: objs_id[frame[1]] = frame[3]
                value = frame[3]
                r = True

        if not stack: result = value

    def push_ref(value):
        if isinstance(value, _R):
            value = value.x
            if isinstance(value, _R):
                for frame in reversed(stack):
                    if frame[0] is UNSET and frame[4] in {dict, list}:
                        refs_containers.append(frame)
            push_value(value)
        else: push_value(value)

    refs_containers = []

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
                value, = _STRUCT_COMPILE['d'].unpack(read(8))
                objs_id.append(value)
                push_value(value)
            
            case 0x11:
                idx = len(objs_id)
                flag = read(1, True)
                has_real, has_imag = flag >> 4, flag & 1
                real, = _STRUCT_COMPILE['d'].unpack(read(8)) if has_real else (0,)
                imag, = _STRUCT_COMPILE['d'].unpack(read(8)) if has_imag else (0,)
                value = complex(real, imag)
                objs_id.append(value)
                push_value(value)

            case 0x12 | 0x13 as code:
                value_l = []
                for _ in range(3):
                    tag = read(1, True, True)
                    if tag in {1, -1}:
                        value_l.append(tag * read(read(1, True), True))
                    else:
                        value_l.append(None)
                value = (range if code == 0x12 else slice)(*value_l)
                objs_id.append(value)
                push_value(value)

            case 0x14:
                name = read(read(1, True)).decode()
                s_id = read(read(1, True), True)
                value = _SENTINEL_REG.get(s_id)
                if value is None:
                    value = sentinel(name)
                    _SENTINEL_REG[id(value)] = value
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
                value = read(4, True, True)
                objs_id.append(value)
                push_value(value)

            case 0x23:
                signed_byte, length_of_length = _STRUCT_COMPILE['bB'].unpack(read(2))
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
                if not length:
                    v = () if opcode == 0x50 else frozenset()
                    push_value(v)
                    objs_id[idx] = v
                else:
                    stack.append([UNSET, idx, length, [], tuple if opcode == 0x50 else frozenset])
                    objs_id[idx] = _R(objs_id, idx)

            case 0x51 | 0x61:
                value = [] if opcode == 0x51 else set()
                idx = len(objs_id)
                objs_id.append(value)
                length = read(read(1, True), True)
                if not length: push_value(value)
                else: stack.append([UNSET, -1, length, value, list if opcode == 0x51 else set])

            case 0x70:
                idx = len(objs_id)
                objs_id.append(None)
                length = read(read(1, True), True)
                if not length:
                    v = frozendict()
                    push_value(v)
                    objs_id[idx] = v
                else:
                    stack.append([UNSET, idx, length, {}, frozendict, UNSET])
                    objs_id[idx] = _R(objs_id, idx)
            
            case 0x71:
                value = {}
                idx = len(objs_id)
                objs_id.append(value)
                length = read(read(1, True), True)
                if not length: push_value(value)
                else: stack.append([UNSET, -1, length, value, dict, UNSET])

            # ref
            case 0xE0:
                value = objs_id[read(1, True)]
                push_ref(value)
            
            case 0xE1:
                value = objs_id[read(2, True)]
                push_ref(value)
            
            case 0xE2:
                value = objs_id[read(4, True)]
                push_ref(value)
            
            case 0xE3:
                value = objs_id[read(read(read(1, True), True), True)]
                push_ref(value)

            # system
            case 0xF0:
                name = read(read(1, True)).decode()
                if name not in extensions: raise ExtensionNotFoundError(f"unknown extension type: '{name}'")
                value = extensions[name][0](read(read(read(1, True), True)))
                objs_id.append(value)
                push_value(value)
            
            case _:
                raise ValueError(f"unknown opcode: {opcode:#02X}{f', at {f.tell()}' if f.seekable() else ''}")

    for container in refs_containers: _fix(container)
    return result

        
def _dump(obj: _Any, f: _BinaryIO, extensions: Extension | None = None, pure_data: bool = False):
    if not pure_data:
        f.write(_MAGIC)
        f.write(_version.to_bytes(2, 'little'))
        f.write(_sys.version_info.major.to_bytes())
        f.write(_sys.version_info.minor.to_bytes())

    extensions = {} if extensions is None else extensions._dict
    stack = [obj]

    objs_id: dict[int, int] = {}
    id_count = 0
    while stack:
        obj = stack.pop()
        obj_id = id(obj)
        if obj_id in objs_id:
            count = objs_id[obj_id]
            if count < 256: # very short
                f.write(_STRUCT_COMPILE['cB'].pack(b'\xE0', count))
            
            elif count < 65536: # short
                f.write(_STRUCT_COMPILE['cH'].pack(b'\xE1', count))
            
            elif count < 4294967296 : # int
                f.write(_STRUCT_COMPILE['cI'].pack(b'\xE2', count))

            else:
                num = count
                digits = num.to_bytes((num.bit_length() + 7) >> 3, 'little')
                f.write(b'\xE3')
                length = len(digits).to_bytes(8, 'little').rstrip(b'\x00') # length
                f.write(len(length).to_bytes()) # length of length
                f.write(length)
                f.write(digits)

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
            f.write(b'\xF0')
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
            case float()  : f.write(_STRUCT_COMPILE['cd'].pack(b'\x10', obj))
            case complex():
                f.write(b'\x11')
                has_real, has_imag = bool(obj.real), bool(obj.imag)
                f.write(bytes((has_real << 4 | has_imag,)))
                if has_real: f.write(_STRUCT_COMPILE['d'].pack(obj.real))
                if has_imag: f.write(_STRUCT_COMPILE['d'].pack(obj.imag))

            case int():
                if -128 <= obj < 128: # very short
                    f.write(_STRUCT_COMPILE['cb'].pack(b'\x20', obj))
                    continue

                elif -32768 <= obj < 32768: # short
                    f.write(_STRUCT_COMPILE['ch'].pack(b'\x21', obj))
                    continue

                elif -2147483648 <= obj < 2147483648 : # int
                    f.write(_STRUCT_COMPILE['ci'].pack(b'\x22', obj))
                    continue

                num = abs(obj)
                digits = num.to_bytes((num.bit_length() + 7) >> 3, 'little')
                f.write(_STRUCT_COMPILE['2c'].pack(b'\x23', b'\xFF' if obj < 0 else b'\x01')) # signed
                length = len(digits).to_bytes(8, 'little').rstrip(b'\x00') # length
                f.write(len(length).to_bytes()) # length of length
                f.write(length)
                f.write(digits)
            
            case str():
                content = obj.encode()
                if len(content) < 256:
                    f.write(_STRUCT_COMPILE['cB'].pack(b'\x30', len(content)))
                    f.write(content)
                else:
                    f.write(b'\x31')
                    length = len(content).to_bytes(8, 'little').rstrip(b'\x00')
                    f.write(len(length).to_bytes())
                    f.write(length)
                    f.write(content)

            case tuple() | list() | set() | frozenset():
                f.write(_OBM[type(obj)])
                length = len(obj).to_bytes(8, 'little').rstrip(b'\x00')
                f.write(len(length).to_bytes())
                f.write(length)
                stack += [None] * len(obj)
                stack[-1:-1-len(obj):-1] = obj

            case dict() | frozendict():
                f.write(_OBM[type(obj)])
                length = len(obj).to_bytes(8, 'little').rstrip(b'\x00')
                f.write(len(length).to_bytes())
                f.write(length)
                stack += [None] * (len(obj) << 1)
                stack[-1:-1-(len(obj)<<1):-1] = (item for kv in obj.items() for item in kv)

            case bytes() | bytearray():
                if len(obj) < 256:
                    f.write(_STRUCT_COMPILE['cB'].pack(b'\x40' if isinstance(obj, bytes) else b'\x42', len(obj)))
                    f.write(obj)
                else:
                    f.write(b'\x41' if isinstance(obj, bytes) else b'\x43')
                    length = len(obj).to_bytes(8, 'little').rstrip(b'\x00')
                    f.write(len(length).to_bytes())
                    f.write(length)
                    f.write(obj)

            case range() | slice():
                f.write(_OBM[type(obj)])
                for num in obj.start, obj.stop, obj.step:
                    if num is None:
                        f.write(b'\x02')
                    else:
                        signed, num = (b'\xFF', -num) if num < 0 else (b'\x01', num)
                        f.write(signed)
                        content = num.to_bytes((num.bit_length() + 7) >> 3, 'little')
                        f.write(len(content).to_bytes())
                        f.write(content)

            case sentinel():
                _SENTINEL_REG[id(obj)] = obj
                f.write(b'\x14')
                content = obj.__name__.encode()
                f.write(len(content).to_bytes())
                f.write(content)
                length = id(obj).to_bytes(8, 'little').rstrip(b'\x00')
                f.write(len(length).to_bytes())
                f.write(length)

            case _ if obj is ...: f.write(b'\x03')
            case _ if obj is _builtins.NotImplemented: f.write(b'\x04')
            case _: raise UnsupportedTypeError(f"unsupported type: '{type(obj).__name__}'")
