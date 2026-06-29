import rPickle
import pickle
from datetime import datetime
from decimal import Decimal

# ========== basic ==========
def test_dumps_int_list(benchmark):
    benchmark(rPickle.dumps, list(range(1000)))

def test_pickle_dumps_int_list(benchmark):
    benchmark(pickle.dumps, list(range(1000)))

def test_loads_int_list(benchmark):
    data = rPickle.dumps(list(range(1000)))
    benchmark(rPickle.loads, data)

def test_pickle_loads_int_list(benchmark):
    data = pickle.dumps(list(range(1000)))
    benchmark(pickle.loads, data)

# ========== str lists ==========
def test_dumps_str_list(benchmark):
    benchmark(rPickle.dumps, ["hello"] * 500)

def test_pickle_dumps_str_list(benchmark):
    benchmark(pickle.dumps, ["hello"] * 500)

def test_loads_str_list(benchmark):
    data = rPickle.dumps(["hello"] * 500)
    benchmark(rPickle.loads, data)

def test_pickle_loads_str_list(benchmark):
    data = pickle.dumps(["hello"] * 500)
    benchmark(pickle.loads, data)

# ========== mixed dict ==========
MIXED_DATA = {
    "a": list(range(100)),
    "b": {"x": "y" * 100, "z": [1, 2, 3]},
    "c": [1.5, 2.5, 3.5],
    "d": None,
    "e": True,
}

def test_dumps_mixed(benchmark):
    benchmark(rPickle.dumps, MIXED_DATA)

def test_pickle_dumps_mixed(benchmark):
    benchmark(pickle.dumps, MIXED_DATA)

def test_loads_mixed(benchmark):
    data = rPickle.dumps(MIXED_DATA)
    benchmark(rPickle.loads, data)

def test_pickle_loads_mixed(benchmark):
    data = pickle.dumps(MIXED_DATA)
    benchmark(pickle.loads, data)

# ========== list ==========
NESTED_DATA = [[[i for i in range(5)] for _ in range(10)] for _ in range(10)]

def test_dumps_nested(benchmark):
    benchmark(rPickle.dumps, NESTED_DATA)

def test_pickle_dumps_nested(benchmark):
    benchmark(pickle.dumps, NESTED_DATA)

def test_loads_nested(benchmark):
    data = rPickle.dumps(NESTED_DATA)
    benchmark(rPickle.loads, data)

def test_pickle_loads_nested(benchmark):
    data = pickle.dumps(NESTED_DATA)
    benchmark(pickle.loads, data)

# ========== big int ==========
BIG_INT = 1 << 1000

def test_dumps_big_int(benchmark):
    benchmark(rPickle.dumps, BIG_INT)

def test_pickle_dumps_big_int(benchmark):
    benchmark(pickle.dumps, BIG_INT)

def test_loads_big_int(benchmark):
    data = rPickle.dumps(BIG_INT)
    benchmark(rPickle.loads, data)

def test_pickle_loads_big_int(benchmark):
    data = pickle.dumps(BIG_INT)
    benchmark(pickle.loads, data)

# ========== Custom datetime==========
DT = datetime.now()
EXT = rPickle.ext.datetime_ext

def test_dumps_datetime(benchmark):
    benchmark(rPickle.dumps, DT, extensions=EXT)

def test_pickle_dumps_datetime(benchmark):
    benchmark(pickle.dumps, DT)

def test_loads_datetime(benchmark):
    data = rPickle.dumps(DT, extensions=EXT)
    benchmark(rPickle.loads, data, extensions=EXT)

def test_pickle_loads_datetime(benchmark):
    data = pickle.dumps(DT)
    benchmark(pickle.loads, data)

# ========== Decimal ==========
DEC = Decimal('3.141592653589793238462643383279502884197')
DEC_EXT = rPickle.ext.Decimal_ext

def test_dumps_decimal(benchmark):
    benchmark(rPickle.dumps, DEC, extensions=DEC_EXT)

def test_pickle_dumps_decimal(benchmark):
    benchmark(pickle.dumps, DEC)

def test_loads_decimal(benchmark):
    data = rPickle.dumps(DEC, extensions=DEC_EXT)
    benchmark(rPickle.loads, data, extensions=DEC_EXT)

def test_pickle_loads_decimal(benchmark):
    data = pickle.dumps(DEC)
    benchmark(pickle.loads, data)