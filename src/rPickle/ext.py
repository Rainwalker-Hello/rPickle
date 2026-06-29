"rPickle's built-in extensions"

from __future__ import annotations
import struct as _struct
from typing import Any as _Any, Callable as _Callable

class Extension:
    '''A type helps you build an extension.'''
    __slots__ = ('_dict',)

    def __init__(
            self,
            typ: type,
            load_func: _Callable[[bytes], _Any],
            dump_func: _Callable[[_Any], bytes],
        ):
        '''
        Init an Extension object.

        Args:
            typ: The type of the extension
            load_func: The function to load the extension from bytes
            dump_func: The function to dump the extension to bytes

        Returns:
            An Extension object

        Raises:
            TypeError: If the arguments are not of the correct type
        '''
        self._dict = {typ: (load_func, dump_func)}

    def __or__(self, value: Extension):
        if not isinstance(value, Extension):
            raise TypeError(f"unsupported operand type(s) for |: 'Extension' and '{type(value).__name__}'")
        new = self.__new__(Extension)
        new._dict = self._dict | value._dict
        return new
    
    def __ror__(self, value: Extension):
        if not isinstance(value, Extension):
            raise TypeError(f"unsupported operand type(s) for |: 'Extension' and '{type(value).__name__}'")
        return value | self
    
    def __ior__(self, other: Extension):
        if not isinstance(other, Extension):
            raise TypeError(f"unsupported operand type(s) for |=: 'Extension' and '{type(other).__name__}'")
        self._dict |= other._dict
        return self
    

# datetime
from datetime import datetime as _datetime

def _datetime_d(value: _datetime) -> bytes: return _struct.pack('<d', value.timestamp())
def _datetime_l(code: bytes) -> _datetime: return _datetime.fromtimestamp(_struct.unpack('<d', code)[0])

datetime_ext = Extension(typ=_datetime, load_func=_datetime_l, dump_func=_datetime_d)

# Decimal
from decimal import Decimal as _Decimal

def _Decimal_d(value: _Decimal) -> bytes: return str(value).encode('ascii')
def _Decimal_l(code: bytes) -> _Decimal: return _Decimal(code.decode('ascii'))

Decimal_ext = Extension(typ=_Decimal, load_func=_Decimal_l, dump_func=_Decimal_d)

# UUID
from uuid import UUID as _UUID

def _UUID_d(value: _UUID) -> bytes: return value.bytes
def _UUID_l(code: bytes) -> _UUID: return _UUID(bytes=code)

UUID_ext = Extension(typ=_UUID, load_func=_UUID_l, dump_func=_UUID_d)

# Fraction
from fractions import Fraction as _Fraction

def _Fraction_d(value: _Fraction) -> bytes:
    from .core import dumps
    return dumps((value.numerator, value.denominator))

def _Fraction_l(code: bytes) -> _Fraction:
    from .core import loads
    return _Fraction(*loads(code))

Fraction_ext = Extension(typ=_Fraction, load_func=_Fraction_l, dump_func=_Fraction_d)

# Path
from pathlib import Path as _Path

def _Path_d(value: _Path) -> bytes:
    return str(value).encode()

def _Path_l(code: bytes) -> _Path:
    return _Path(code.decode())

Path_ext = Extension(typ=_Path, load_func=_Path_l, dump_func=_Path_d)

# defaultdict
from collections import defaultdict as _defaultdict

def _defaultdict_d(value: _defaultdict) -> bytes:
    from .core import dumps
    return dumps((value.default_factory, dict(value)))

def _defaultdict_l(data: bytes) -> _defaultdict:
    from .core import loads
    factory, items = loads(data)
    d = _defaultdict(factory)
    d.update(items)
    return d

defaultdict_ext = Extension(typ=_defaultdict, load_func=_defaultdict_l, dump_func=_defaultdict_d)

# date
from datetime import date as _date

def _date_d(value: _date) -> bytes:
    return value.isoformat().encode()

def _date_l(code: bytes) -> _date:
    return _date.fromisoformat(code.decode())

date_ext = Extension(typ=_date, load_func=_date_l, dump_func=_date_d)

# time
from datetime import time as _time

def _time_d(value: _time) -> bytes:
    return value.isoformat().encode()

def _time_l(code: bytes) -> _time:
    return _time.fromisoformat(code.decode())

time_ext = Extension(typ=_time, load_func=_time_l, dump_func=_time_d)

# others
__all__ = (
    'Extension',

    'datetime_ext',
    'Decimal_ext',
    'UUID_ext',
    'Fraction_ext',
    'Path_ext',
    'defaultdict_ext',
    'date_ext',
    'time_ext',
)