# rPickle

A safe and efficient Python serialization library.

## Features

- 🔒 **Safety** - No arbitrary code execution, unlike `pickle`
- 📦 **Compact** - Small serialized size
- 🔄 **Circular references** - Handles self-referential structures
- 🧩 **Extensibility** - Custom type support via extensions
- 🤝 **Compatibility** - Written in pure Python, works on all platforms
- ♾️ **No recursion limit** - Can serialize deeply nested structures
- 0️⃣ **Zero dependencies** - No external libraries required

## 🔒 Safety

rPickle is **safe** in the sense that it **does not execute arbitrary code** during deserialization.

Unlike `pickle` (which can call arbitrary functions during `loads()`), rPickle only reconstructs data structures.  
It does not use `__reduce__()`, no implicit imports, and no function calls.

> ✅ `rPickle.loads(data)` does not execute any code — it only restores data.  
❌ `pickle.loads(data)` may execute arbitrary code defined in `__reduce__`.

**However, safety is not absolute:**

- If you use custom extensions (`Extension`), you are responsible for the code you provide — the library author is not liable.
- rPickle does not encrypt data or prevent tampering. If you need integrity or confidentiality, take additional measures.
- rPickle is not a sandbox. If you load untrusted data with malicious extensions, it can execute arbitrary code.

It is recommended to **only load data from trusted sources** and **review any custom extensions** before use.

## Requirements

- Python 3.13+ (all features)
- Python 3.15+ (all features including `frozendict` and `sentinel`)

## Installation

```bash
pip install rPickle
```

## Why rPickle?

Pickle can't handle truly large integers. rPickle can:

```python
>>> import pickle
>>> import rPickle
>>> big_integer = 1 << (1 << 34)
>>> big_integer == pickle.loads(pickle.dumps(big_integer))
Traceback (most recent call last):
  ...
OverflowError: int too large to pickle
>>> big_integer == rPickle.loads(rPickle.dumps(big_integer))
True
```

In Python 3.15, `sentinel` will be added. But pickle cannot handle this case. rPickle can handle it correctly:

```python
>>> import pickle
>>> import rPickle
>>> MISSING = sentinel('MISSING')
>>> S = sentinel('s')

>>> # Pickle: works for one, fails for the other
>>> MISSING is pickle.loads(pickle.dumps(MISSING))
True
>>> S is pickle.loads(pickle.dumps(S))
Traceback (most recent call last):
  ...
_pickle.PicklingError: Can't pickle s: it's not found as __main__.s

>>> # rPickle: works consistently
>>> MISSING is rPickle.loads(rPickle.dumps(MISSING))
True
>>> S is rPickle.loads(rPickle.dumps(S))
True
```

## Quick Start

```python
import rPickle

# Serialize
data = {'name': 'Alice', 'scores': [95, 87, 92]}
packed = rPickle.dumps(data)

# Deserialize
restored = rPickle.loads(packed)
print(restored)  # {'name': 'Alice', 'scores': [95, 87, 92]}
```

## API

### Core Function

| Function        | Description               |
| --------------- | ------------------------- |
| dumps(obj)      | Serialize object to bytes |
| loads(data)     | Deserialize from bytes    |
| dump(obj, file) | Serialize to file         |
| load(file)      | Deserialize from file     |

## Extensions

You can use built-in extensions to support additional types like `datetime`, `Decimal`, `UUID`, etc.

For example, to serialize a dictionary containing a `datetime.datetime` object:

```python
from datetime import datetime

data = {'created': datetime.now()}
packed = rPickle.dumps(data, extensions=rPickle.ext.datetime_ext)
restored = rPickle.loads(packed, extensions=rPickle.ext.datetime_ext)

# Using more extensions at the same time
exts = rPickle.ext.datetime_ext | rPickle.ext.Path_ext | rPickle.ext.Decimal_ext
packed = rPickle.dumps(data, extensions=exts)
```

### Custom Extensions

Add support for your own types using the `extensions` parameter. For example, to support `datetime.datetime`:

```python
import rPickle
from datetime import datetime

# 1. Define dump function (type → bytes)
def dump_datetime(dt: datetime) -> bytes:
    return dt.timestamp().to_bytes(8, 'little')

# 2. Define load function (bytes → type)
def load_datetime(data: bytes) -> datetime:
    timestamp = int.from_bytes(data, 'little')
    return datetime.fromtimestamp(timestamp)

# 3. Register your extension
my_extensions = rPickle.ext.Extension(typ=datetime, load_func=load_datetime, dump_func=dump_datetime)

# 4. Use it
data = {'created': datetime.now()}
packed = rPickle.dumps(data, extensions=my_extensions)
restored = rPickle.loads(packed, extensions=my_extensions)
```

You can also combine your extension with built-in ones or custom ones using `|=`. For example, to combine your `datetime.datetime` extension with the built-in one:

```python
import rPickle
from datetime import datetime

def dump_datetime(dt: datetime) -> bytes:
    return dt.timestamp().to_bytes(8, 'little')

def load_datetime(data: bytes) -> datetime:
    timestamp = int.from_bytes(data, 'little')
    return datetime.fromtimestamp(timestamp)

my_extensions = rPickle.ext.Extension(typ=datetime, load_func=load_datetime, dump_func=dump_datetime)

# Add a built-in extension or others
my_extensions |= rPickle.ext.datetime_ext

packed = rPickle.dumps(data, extensions=my_extensions)
restored = rPickle.loads(packed, extensions=my_extensions)
```

**⚠️Note:** For safety, avoid using `eval()`, `exec()`, or `__import__()` in your custom extensions.

## Overriding Built-in Types With Custom Extensions

You can override built-in types with your own extensions. For example, if you want to change how `list` is serialized:

```python
import rPickle
from rPickle.ext import Extension

def dump_list_plus(lst: list) -> bytes:
    return bytes(lst)

def load_list_plus(data: bytes) -> list:
    return list(data)

list_plus = Extension(typ=list, load_func=load_list_plus, dump_func=dump_list_plus)

data = [1, 2, 5, 3, 4, 5, 8, 9, 7, 5, 9, 5]
packed = rPickle.dumps(data, extensions=list_plus)
restored = rPickle.loads(packed, extensions=list_plus)
```

### ⚠️ Important note when overriding types

When you override a built-in type, keep in mind that your custom serializer may not handle all possible values. For example, if you override `list` to serialize as a compact bytearray, a single value outside the expected range will break the serialization.

To avoid this, consider implementing a fallback in your serializer:

```python
import rPickle

def dump_list_safe(lst: list) -> bytes:
    try:
        return b'\x00' + bytes(lst)
    except (OverflowError, TypeError):
        return rPickle.dumps(lst)  # fallback to default

def load_list_safe(code: bytes) -> list:
    if code.startswith(rPickle.core._MAGIC):
        return rPickle.loads(code)
    else:
        return list(code[1:])
```

This way, your custom logic applies when possible — and gracefully falls back when it doesn't.

**⚠️Note:** For safety, avoid using `eval()`, `exec()`, or `__import__()` in your enhancement extensions

## Supported Types

- `None`, `bool`, `int`, `float`, `complex`, `str`
- `bytes`, `bytearray`
- `list`, `tuple`, `set`, `frozenset`
- `dict`, `frozendict` (Python 3.15+)
- `range`, `slice`
- `Ellipsis`, `NotImplemented`
- `sentinel` (Python 3.15+)
- Custom types

## Sentinel Support

Python 3.15 introduced `sentinel` for creating unique marker objects.
rPickle supports `sentinel` natively with **identity preservation**:

```python
import rPickle

MISSING = sentinel('MISSING')
packed = rPickle.dumps(MISSING)
restored = rPickle.loads(packed)

assert restored is MISSING  # True
```

That makes rPickle more correct.

## Built-in Extensions

rPickle comes with ready-to-use extensions for common types:
see the list below.

| Name                 | Type                      |
|----------------------|---------------------------|
| `datetime_ext`       | `datetime.datetime`       |
| `Decimal_ext`        | `decimal.Decimal`         |
| `UUID_ext`           | `uuid.UUID`               |
| `Fraction_ext`       | `fractions.Fraction`      |
| `Path_ext`           | `pathlib.Path`            |
| `date_ext`           | `datetime.date`           |
| `time_ext`           | `datetime.time`           |
| `Counter_ext`        | `collections.Counter`     |
| `OrderedDict_ext`    | `collections.OrderedDict` |
| `IPv4Address_ext`    | `ipaddress.IPv4Address`   |
| `IPv6Address_ext`    | `ipaddress.IPv6Address`   |
| `array_ext`          | `array.array`             |

## Links

- [PyPI](https://pypi.org/project/rPickle)
- [GitHub](https://github.com/Rainwalker-Hello/rPickle)

## License

MIT License.

---

## Evolution

- **0.19.0** (2026-07-24) — `_fix` only traverses dirty containers, faster
- **0.18.0** (2026-07-23) — v5 protocol, sentinel varint id
- **0.17.0** (2026-07-23) - Protocol loading refactored to dynamic imports; `set_max_size_ctx` introduced; `rPickle.dis` added
- **0.11.2** (2026-07-15) - Circular references fully resolved, graph serialization supported
- **0.10.1** (2026-07-09) - Native `sentinel` forward-compatibility (PEP for Python 3.15)
- **0.9.1** (2026-07-04) - `set_max_size()` introduced, driven by user feedback
- **0.3.0** (2026-06-18) - Recursive descent eliminated, explicit stack for unbounded nesting
- **0.1.0** (2026-06-13) - First public release
