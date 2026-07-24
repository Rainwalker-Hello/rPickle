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

from typing import BinaryIO as _BinaryIO, Any as _Any
from io import BytesIO as _BytesIO
import warnings as _warnings
import sys as _sys
from importlib import import_module as _import

from .ext import Extension

_version = 5
_python_version = (3, 15)

_version_info = (0, 19, 1)
__version__ = '.'.join(map(str, _version_info))

_MAX_SIZE = 5 << 30
def set_max_size(size: int) -> int:
    '''
    Set the maximum allowed size for deserialization.

    Args:
        size: The maximum size in bytes (e.g., 100 << 20 for 100 MB).

    Raises:
        ValueError: If size is negative 
        TypeError: IF size is not an integer

    Example:
        >>> rPickle.set_max_size(100 << 20)  # 100 MB
    '''
    if not isinstance(size, int): raise TypeError(f"size must be an integer, not '{type(size).__name__}'")
    if size < 0: raise ValueError(f"size must be non-negative, got {size}")
    global _MAX_SIZE
    _MAX_SIZE = size

class set_max_size_ctx:
    '''
    Context manager for temporarily setting the maximum allowed deserialization size.

    Args:
        size: The maximum size in bytes

    Raises:
        TypeError: If `size` is not an integer.
        ValueError: If `size` is negative.

    Example:
        >>> with rPickle.set_max_size_ctx(100 << 20):  # 100 MB
        ...     data = rPickle.loads(packed)
    '''
    def __init__(self, size: int = _MAX_SIZE):
        if not isinstance(size, int): raise TypeError(f"size must be an integer, not '{type(size).__name__}'")
        if size < 0: raise ValueError(f"size must be non-negative, got {size}")
        self.size, self.origin = size, None

    def __enter__(self):
        global _MAX_SIZE
        self.origin = _MAX_SIZE
        _MAX_SIZE = self.size
        return _MAX_SIZE
    
    def __exit__(self, exc_type, exc, tb):
        global _MAX_SIZE
        _MAX_SIZE = self.origin
        self.size = self.origin = None

_MAGIC = b'RPkl'

class _D:
    def __init__(self, x: dict = None): self.x = {} if x is None else x
    def __getitem__(self, key):
        for k, v in *self.x.items(),:
            if _sys.getrefcount(v) <= 3: del self.x[k] # self.x, (*self.x.items(),), sys.getrefcount(v). Three refcount.
        return self.x[key]
    def get(self, key, default = None):
        try: return self.x[key]
        except KeyError: return default
    def __setitem__(self, key, value): self.x[key] = value
    def __delitem__(self, key): del self.x[key]

_SENTINEL_REG = _D()


class VersionError(Exception):
    '''Exception raised when the Python or rPickle version is not compatible.'''
    def __init__(self, text: str = f"Cannot load because Python or rPickle is not the newest version. Need Python {'.'.join(map(str, _python_version))}+"):
        self.text = text # pragma: no cover
        super().__init__(text) # pragma: no cover

class UnsupportedTypeError(Exception):
    '''Exception raised when an unsupported type is encountered.'''
class ExtensionNotFoundError(Exception):
    '''Exception raised when an extension is not found.'''


def load(f: _BinaryIO, extensions: Extension | None = None) -> _Any:
    '''
    Load an object from a file-like object.

    Args:
        f: The file-like object to load from
        extensions: The extensions to use

    Returns:
        The loaded object

    Raises:
        ValueError: If the data is invalid
        VersionError: If the Python or rPickle version is not compatible
        ExtensionNotFoundError: If an extension is not found
    '''
    magic = f.read(4)
    if magic != _MAGIC: raise ValueError('invalid data')
    version = int.from_bytes(f.read(2), 'little')
    py_ver_maj, py_ver_min = f.read(2)
    py_ver = py_ver_maj, py_ver_min
    if py_ver > _python_version: _warnings.warn('may not be compatible', RuntimeWarning)
    try: return _import(f'.pcls.core_p{version}', __package__)._load(f, extensions)
    except ModuleNotFoundError: raise ValueError(f"Unknown protocol: {version}") from None


def loads(source: bytes | bytearray, extensions: Extension | None = None) -> _Any:
    '''
    Load an object from a byte-like object.

    Args:
        source: The byte-like object to load from
        extensions: The extensions to use

    Returns:
        The loaded object

    Raises:
        ValueError: If the data is invalid
        VersionError: If the Python or rPickle version is not compatible
        ExtensionNotFoundError: If an extension is not found
    '''
    return load(_BytesIO(source), extensions)
            
def dump(obj: _Any, f: _BinaryIO, extensions: Extension | None = None, protocol: int = _version):
    '''
    Dump an object to a file-like object.
    
    Args:
        obj: The object to dump
        f: The file-like object to dump to
        extensions: The extensions to use
        protocol: The protocol version to use
    
    Raises:
        ValueError: If the data is invalid
        VersionError: If the Python or rPickle version is not compatible
        ExtensionNotFoundError: If an extension is not found
    '''
    try: return _import(f'.pcls.core_p{protocol}', __package__)._dump(obj, f, extensions)
    except ModuleNotFoundError: raise ValueError(f"Unknown protocol: {protocol}") from None


def dumps(obj: _Any, extensions: Extension | None = None, protocol: int = _version) -> bytes:
    '''
    Dump an object to a byte-like object.

    Args:
        obj: The object to dump
        extensions: The extensions to use
        protocol: The protocol version to use

    Returns:
        The dumped object as bytes

    Raises:
        ValueError: If the data is invalid
        VersionError: If the Python or rPickle version is not compatible
        ExtensionNotFoundError: If an extension is not found
    '''
    buf = _BytesIO()
    dump(obj, buf, extensions, protocol)
    return buf.getvalue()

__all__ = (
    'loads', 'dumps', 'load', 'dump', 'VersionError', 'ExtensionNotFoundError', 'UnsupportedTypeError', 'set_max_size', 'set_max_size_ctx'
)
