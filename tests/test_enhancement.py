import rPickle
import random

use = 0
def used(func):
    def wrapper(*args, **kwargs):
        global use
        res = func(*args, **kwargs)
        use += 1
        return res
    return wrapper

class TestOverrideBuiltins:
    def test_override_builtin_list(self):
        @used
        def dump_list(lst: list) -> bytes:
            return bytes(lst)

        @used
        def load_list(data: bytes) -> list:
            return list(data)

        list_ext = rPickle.ext.Extension(
            typ=list,
            load_func=load_list,
            dump_func=dump_list
        )

        data = random.choices(range(256), k=100)
        packed = rPickle.dumps(data, extensions=list_ext)
        restored = rPickle.loads(packed, extensions=list_ext)
        assert restored == data
        assert use == 2
